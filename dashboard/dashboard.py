#!/usr/bin/env python3
"""Generate a static, self-contained HTML dashboard for BudgetBash data.

No Flask server involved: this script loads data through the existing
``lib`` layer (the same classes the TUI backend uses), builds Plotly
figures, and writes a single .html file. A shared client-side <select>
drives the "Categories by Year" and "Monthly Expenses" figures together
via small inline JS (Plotly.restyle/relayout), so both switch year in sync.
"""
import argparse
import calendar
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
from plotly import graph_objects as go

from lib import FlaskWrapper

YEAR_DIR_RE = re.compile(r"^\d{4}$")
TEMPLATE = "plotly_dark"
PAPER_BG = "#111318"
PLOT_BG = "#111318"

CATEGORY_COLORS = {
    'Shop':      '#CDC1FF',
    'Groceries': '#C96868',
    'Other':     '#95D2B3',
    'Leisure':   '#FCDC94',
    'Transport': '#B9B28A',
    'Subs':      '#C9E9D2',
    'Health':    '#D4F6FF',
    'Family':    '#FFCF9D',
    'Holiday':   '#FEFBD8',
    'Bills':     '#E7D4B5',
    'Car':       '#A0C4FF',
    'Karma':     '#FFADAD',
    'Income':    '#9BF6FF',
}


def discover_years(data_path: Path):
    years = []
    for entry in sorted(data_path.iterdir()):
        if entry.is_dir() and YEAR_DIR_RE.match(entry.name):
            if (entry / f"{entry.name}_init.json").exists():
                years.append(int(entry.name))
    return sorted(years)


class YearData:
    def __init__(self, year):
        self.year = year
        self.df_m_cashflow = pd.DataFrame()
        self.nw_global = pd.DataFrame()      # month-end net worth rows only
        self.nw_today = pd.DataFrame()        # single live "today" row, only set for the latest year
        self.year_expenses = pd.DataFrame()   # raw rows: Category/Subcategory/Qty (whole year)
        self.year_incomes = pd.DataFrame()    # raw rows: Category/Subcategory/Qty (whole year)
        self.month_expenses = {}  # month(int) -> df with Category/Subcategory/Qty
        self.all_balances = {}            # account -> balance (liquidity)
        self.investments_by_class = {}    # asset class -> value (today)
        self.holdings_by_class = pd.DataFrame()  # month-end value per asset class (+ 'Total')


def load_all_years(data_path: Path, years):
    per_year = []
    for i, year in enumerate(years):
        wrapper = FlaskWrapper()
        try:
            wrapper.initialize(year, str(data_path))
        except Exception as e:
            print(f"WARNING: failed to initialize year {year}: {e}", file=sys.stderr)
            continue

        yd = YearData(year)

        yd.all_balances = {k: round(float(v), 2) for k, v in wrapper.get_all_balances().items()}
        df_today_class = wrapper.finInvestments.df_today_holdings_class
        if not df_today_class.empty:
            row = df_today_class.iloc[-1]
            yd.investments_by_class = {
                c: round(float(row[c]), 2) for c in df_today_class.columns if c != 'Total'
            }

        df_m_cashflow = wrapper.finCashflow.df_m_cashflow
        if i > 0:
            df_m_cashflow = df_m_cashflow.iloc[1:]  # drop synthetic init row, chained from prior year
        yd.df_m_cashflow = df_m_cashflow

        is_last_year = (i == len(years) - 1)
        try:
            nw_global = wrapper.calc_global_nw()
            # calc_global_nw() always appends a single synthetic "today" row
            # (based on the real current date) after the month-end rows,
            # regardless of which year is being processed. For any year that
            # isn't the most recent one, that row is bogus (it re-evaluates
            # "today" against stale, frozen holdings from a past year) and
            # must be dropped, otherwise several such rows pile up on the
            # same date and distort the net worth chart.
            nw_monthly, nw_today = nw_global.iloc[:-1], nw_global.iloc[-1:]
            if i > 0:
                nw_monthly = nw_monthly.iloc[1:]  # drop synthetic init row, chained from prior year
            yd.nw_global = nw_monthly
            if is_last_year:
                yd.nw_today = nw_today

            df_holdings_class = wrapper.finInvestments.df_year_holdings_class
            if not df_holdings_class.empty and i > 0:
                df_holdings_class = df_holdings_class.iloc[1:]  # drop row chained from prior year
            yd.holdings_by_class = df_holdings_class
        except Exception as e:
            print(f"WARNING: net worth unavailable for {year} (investments fetch failed): {e}", file=sys.stderr)
            fallback = df_m_cashflow[['liquidity']].copy()
            fallback['investments'] = 0.0
            fallback['networth'] = fallback['liquidity']
            fallback['nwch'] = fallback['networth'].diff()
            fallback['ch%'] = fallback['networth'].diff() / fallback['networth']
            yd.nw_global = fallback

        yd.year_expenses = wrapper.finCashflow.calc_expenses()
        yd.year_incomes = wrapper.finCashflow.calc_incomes()

        for month in range(1, 13):
            yd.month_expenses[month] = wrapper.finCashflow.calc_expenses(month=month)

        per_year.append(yd)

    return per_year


def first_active_month(per_year):
    """First month with any real cashflow activity (income or expense), so
    the all-time charts don't start with a stretch of empty leading months."""
    dfs = [yd.df_m_cashflow for yd in per_year if not yd.df_m_cashflow.empty]
    if not dfs:
        return None
    df = pd.concat(dfs).sort_index()
    df = df[pd.to_numeric(df['incomes'], errors='coerce').notna()]
    active = df[(df['incomes'].astype(float) != 0) | (df['liabilities'].astype(float) != 0)]
    if active.empty:
        return df.index.min() if not df.empty else None
    return active.index.min()


def round2(df, cols=None):
    if cols is None:
        return df.round(2)
    df = df.copy()
    df[cols] = df[cols].round(2)
    return df


def make_sunburst_trace(df, values_col='Qty', visible=True):
    """Build a Category -> Subcategory sunburst trace with monthly-mean hover info."""
    if df is None or df.empty:
        return go.Sunburst(labels=[], parents=[], values=[], visible=visible), 0.0

    df = df.copy()
    df[values_col] = df[values_col].round(2)
    total = round(float(df[values_col].sum()), 2)
    pxfig = px.sunburst(
        df, path=['Category', 'Subcategory'], values=values_col,
        color='Category', color_discrete_map=CATEGORY_COLORS,
    )
    trace = pxfig.data[0]
    monthly_mean = [round(v / 12, 2) for v in trace.values]
    sunburst = go.Sunburst(
        labels=trace.labels, parents=trace.parents, values=trace.values,
        ids=trace.ids, branchvalues="total", marker=trace.marker,
        visible=visible, customdata=monthly_mean,
        hovertemplate='%{label}<br>Total: €%{value}<br>Monthly mean: €%{customdata}<extra></extra>',
    )
    return sunburst, total


def shrink_domain_for_label(domain, frac=0.14):
    """Free up a bottom strip of a domain-type subplot cell to fit a total label.

    Returns (new_domain, label_x, label_y) where new_domain is the shrunk
    domain the sunburst trace should occupy, and (label_x, label_y) is the
    paper-coordinate position for a total annotation placed below the chart.
    """
    x0, x1 = domain.x
    y0, y1 = domain.y
    h = y1 - y0
    new_domain = dict(x=[x0, x1], y=[y0 + frac * h, y1])
    label_x = (x0 + x1) / 2
    label_y = y0 + 0.02 * h
    return new_domain, label_x, label_y


def total_annotation(x, y, total, font_size=13):
    return dict(
        x=x, y=y, xref='paper', yref='paper', showarrow=False,
        text=f"Total: €{total:,.2f}", font=dict(size=font_size, color="#c9c9c9"),
    )


# ---------------- Figure builders ----------------

def build_alltime_cashflow_fig(per_year, cutoff=None):
    dfs = [yd.df_m_cashflow for yd in per_year if not yd.df_m_cashflow.empty]
    df = pd.concat(dfs).sort_index()
    df = df[pd.to_numeric(df['incomes'], errors='coerce').notna()]
    df = round2(df, ['incomes', 'liabilities', 'saving_rate'])

    # Start at the first month with real activity, and reindex to a
    # complete, evenly-spaced monthly range so the x axis stays linear
    # (no leading empty months, no gaps).
    start = cutoff if cutoff is not None else df.index.min()
    df = df[df.index >= start]
    full_index = pd.date_range(start=start, end=df.index.max(), freq='ME')
    df = df.reindex(full_index, fill_value=0)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=df.index, y=df['incomes'], name='Incomes', marker_color='#3ddc84'),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(x=df.index, y=df['liabilities'].abs().round(2), name='Expenses', marker_color='#ff6b6b'),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=(df['saving_rate'] * 100).round(2),
            line=dict(color='#5b9cff'), name='Saving Rate %',
        ),
        secondary_y=True,
    )
    fig.update_layout(
        template=TEMPLATE, paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        title=dict(text="All-Time Cashflow", x=0.5),
        barmode='group', height=450,
        xaxis=dict(type='date'),
        yaxis=dict(title=dict(text="€"), side="left"),
        yaxis2=dict(title=dict(text="Saving Rate %"), side="right", overlaying="y", range=[0, 100]),
    )
    return fig


def make_expense_mean_bar_trace(df_year_expenses, visible=True):
    """Horizontal bar of each expense category's average monthly spend
    (yearly total / 12), sorted so the highest-mean category is on top."""
    if df_year_expenses is None or df_year_expenses.empty:
        return go.Bar(x=[], y=[], orientation='h', visible=visible)

    means = (df_year_expenses.groupby('Category')['Qty'].sum() / 12).round(2)
    means = means.sort_values(ascending=True)  # ascending -> largest ends up on top
    colors = [CATEGORY_COLORS.get(cat, '#8a8f99') for cat in means.index]
    return go.Bar(
        x=means.values, y=means.index, orientation='h',
        marker_color=colors, visible=visible,
        hovertemplate='%{y}<br>Avg/month: €%{x}<extra></extra>',
    )


def build_year_categories_fig(per_year, div_id):
    fig = make_subplots(
        rows=2, cols=2,
        specs=[
            [{"type": "domain"}, {"type": "domain"}],
            [{"type": "xy", "colspan": 2}, None],
        ],
        subplot_titles=["Expenses", "Incomes", "Avg Monthly Expenses by Category"],
        row_heights=[0.42, 0.58], vertical_spacing=0.12,
    )
    base_annotations = [a.to_plotly_json() for a in fig.layout.annotations]  # the three subplot titles

    n_traces_per_year = 3
    label_pos = [None, None]  # (x, y) per pie column, same across years
    totals_by_year = []
    for i, yd in enumerate(per_year):
        visible = (i == len(per_year) - 1)

        trace_exp, total_exp = make_sunburst_trace(yd.year_expenses, visible=visible)
        fig.add_trace(trace_exp, row=1, col=1)
        new_domain, lx, ly = shrink_domain_for_label(fig.data[-1].domain)
        fig.data[-1].domain = new_domain
        if label_pos[0] is None:
            label_pos[0] = (lx, ly)

        trace_inc, total_inc = make_sunburst_trace(yd.year_incomes, visible=visible)
        fig.add_trace(trace_inc, row=1, col=2)
        new_domain, lx, ly = shrink_domain_for_label(fig.data[-1].domain)
        fig.data[-1].domain = new_domain
        if label_pos[1] is None:
            label_pos[1] = (lx, ly)

        fig.add_trace(make_expense_mean_bar_trace(yd.year_expenses, visible=visible), row=2, col=1)

        totals_by_year.append((total_exp, total_inc))

    annotations_by_year = {}
    visibility_by_year = {}
    title_by_year = {}
    total_traces = len(per_year) * n_traces_per_year
    for i, yd in enumerate(per_year):
        total_exp, total_inc = totals_by_year[i]
        annotations_by_year[yd.year] = base_annotations + [
            total_annotation(*label_pos[0], total_exp),
            total_annotation(*label_pos[1], total_inc),
        ]
        visible_mask = [False] * total_traces
        visible_mask[i * n_traces_per_year:i * n_traces_per_year + n_traces_per_year] = [True, True, True]
        visibility_by_year[yd.year] = visible_mask
        title_by_year[yd.year] = f"Categories — {yd.year}"

    default_year = per_year[-1].year if per_year else ""
    fig.update_layout(
        template=TEMPLATE, paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        title=dict(text=f"Categories — {default_year}", x=0.5),
        height=900, showlegend=False,
        annotations=annotations_by_year.get(default_year, base_annotations),
        xaxis=dict(title=dict(text="€ / month")),
    )
    meta = dict(
        div_id=div_id,
        years=[yd.year for yd in per_year],
        visibility=visibility_by_year,
        annotations=annotations_by_year,
        title=title_by_year,
    )
    return fig, meta


def build_month_expenses_fig(per_year, div_id):
    n_rows, n_cols = 4, 3
    month_names = [calendar.month_name[m] for m in range(1, 13)]
    specs = [[{"type": "domain"} for _ in range(n_cols)] for _ in range(n_rows)]

    fig = make_subplots(
        n_rows, n_cols, specs=specs, subplot_titles=month_names,
        horizontal_spacing=0.02, vertical_spacing=0.06,
    )
    base_annotations = [a.to_plotly_json() for a in fig.layout.annotations]  # the 12 month titles

    n_traces_per_year = 12
    label_pos = [None] * 12  # (x, y) per grid cell, same across years
    totals_by_year = []
    for i, yd in enumerate(per_year):
        visible = (i == len(per_year) - 1)
        totals = []
        for month in range(1, 13):
            row = (month - 1) // n_cols + 1
            col = (month - 1) % n_cols + 1
            trace, total = make_sunburst_trace(yd.month_expenses[month], visible=visible)
            fig.add_trace(trace, row=row, col=col)
            new_domain, lx, ly = shrink_domain_for_label(fig.data[-1].domain)
            fig.data[-1].domain = new_domain
            if label_pos[month - 1] is None:
                label_pos[month - 1] = (lx, ly)
            totals.append(total)
        totals_by_year.append(totals)

    annotations_by_year = {}
    visibility_by_year = {}
    title_by_year = {}
    total_traces = len(per_year) * n_traces_per_year
    for i, yd in enumerate(per_year):
        year_annotations = list(base_annotations)
        for month in range(1, 13):
            year_annotations.append(
                total_annotation(*label_pos[month - 1], totals_by_year[i][month - 1], font_size=11)
            )
        annotations_by_year[yd.year] = year_annotations

        visible_mask = [False] * total_traces
        for month in range(1, 13):
            visible_mask[i * n_traces_per_year + (month - 1)] = True
        visibility_by_year[yd.year] = visible_mask
        title_by_year[yd.year] = f"Monthly Expenses — {yd.year}"

    default_year = per_year[-1].year if per_year else ""
    fig.update_layout(
        template=TEMPLATE, paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        title=dict(text=f"Monthly Expenses — {default_year}", x=0.5),
        height=1300,
        annotations=annotations_by_year.get(default_year, base_annotations),
    )
    meta = dict(
        div_id=div_id,
        years=[yd.year for yd in per_year],
        visibility=visibility_by_year,
        annotations=annotations_by_year,
        title=title_by_year,
    )
    return fig, meta


def build_networth_fig(per_year, cutoff=None):
    dfs = [yd.nw_global for yd in per_year if not yd.nw_global.empty]
    df = pd.concat(dfs).sort_index()
    if cutoff is not None:
        df = df[df.index >= cutoff]

    # Append the live "today" point (partial current month) separately, kept
    # out of the month-end series above so it never gets treated as a
    # regular monthly bar (see first_active_month / load_all_years notes on
    # why only the latest year contributes one).
    today_rows = [yd.nw_today for yd in per_year if not yd.nw_today.empty]
    if today_rows:
        df = pd.concat([df, today_rows[-1]])

    df = round2(df, ['liquidity', 'investments', 'networth'])
    df['ch%'] = (df['ch%'] * 100).round(2)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=df.index, y=df['liquidity'], name='Liquidity', marker_color='#f4a261'),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(x=df.index, y=df['investments'], name='Investments', marker_color='#9d7fe8'),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df['ch%'], line=dict(color='#ffb703'), name='Net Worth Change %'),
        secondary_y=True,
    )
    fig.update_layout(
        template=TEMPLATE, paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        title=dict(text="All-Time Net Worth", x=0.5),
        barmode='stack', height=450,
        yaxis=dict(title=dict(text="€"), side="left"),
        yaxis2=dict(title=dict(text="Change %"), side="right", overlaying="y"),
    )
    return fig


def build_investments_fig(per_year):
    dfs = [yd.holdings_by_class for yd in per_year if not yd.holdings_by_class.empty]
    if not dfs:
        return None

    df = pd.concat(dfs).sort_index()
    df = df[~df.index.duplicated(keep='last')]
    asset_classes = [c for c in df.columns if c != 'Total']
    df = round2(df, asset_classes + ['Total'])

    # Start once something is actually invested, rather than a stretch of zeros.
    active = df[df['Total'] != 0]
    if not active.empty:
        df = df[df.index >= active.index.min()]

    palette = ['#5b9cff', '#ffb703', '#3ddc84', '#ff6b6b', '#9d7fe8', '#f4a261']
    fig = go.Figure()
    for idx, cls in enumerate(asset_classes):
        fig.add_trace(go.Bar(x=df.index, y=df[cls], name=cls, marker_color=palette[idx % len(palette)]))
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Total'], name='Investments (Total)',
        line=dict(color='#e8e8e8', width=2),
    ))

    fig.update_layout(
        template=TEMPLATE, paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        title=dict(text="Investments by Asset Class", x=0.5),
        barmode='stack', height=450,
        yaxis=dict(title=dict(text="€")),
    )
    return fig


# ---------------- Dashboard status (top section) ----------------

def build_status_html(yd_latest):
    """Replicates the terminal app's 'Dashboard Status' view: current net
    worth summary plus balances per bank account and per investment asset
    class, using the most recent year's data."""
    nw_source = yd_latest.nw_today if not yd_latest.nw_today.empty else yd_latest.nw_global
    primary_card_html = ""
    secondary_cards_html = ""
    if not nw_source.empty:
        nw = nw_source.iloc[-1]
        liquidity = round(float(nw['liquidity']), 2)
        investments = round(float(nw['investments']), 2)
        networth = round(float(nw['networth']), 2)
        nwch = round(float(nw['nwch']), 2) if pd.notna(nw['nwch']) else 0.0
        pct_ch = round(float(nw['ch%']) * 100, 2) if pd.notna(nw['ch%']) else 0.0
        sign = '+' if nwch >= 0 else ''

        primary_card_html = (
            '<div class="stat-card stat-card--primary">'
            '<div class="stat-label">Net Worth</div>'
            f'<div class="stat-value">€{networth:,.2f}</div>'
            f'<div class="stat-change">{sign}€{nwch:,.2f} ({sign}{pct_ch:.2f}%)</div>'
            '</div>'
        )
        secondary_cards_html = "".join(
            f'<div class="stat-card stat-card--secondary"><div class="stat-label">{label}</div>'
            f'<div class="stat-value">{value}</div></div>'
            for label, value in [
                ("Liquidity", f"€{liquidity:,.2f}"),
                ("Investments", f"€{investments:,.2f}"),
            ]
        )

    cards_html = (
        f'<div class="status-cards-primary">{primary_card_html}</div>'
        f'<div class="status-cards-secondary">{secondary_cards_html}</div>'
        if primary_card_html else
        '<div class="stat-card"><div class="stat-label">Status</div><div class="stat-value">Unavailable</div></div>'
    )

    balances_rows = "".join(
        f"<tr><td>{acct}</td><td>€{val:,.2f}</td></tr>"
        for acct, val in yd_latest.all_balances.items()
    ) or '<tr><td colspan="2">No account data</td></tr>'

    invest_rows = "".join(
        f"<tr><td>{cls}</td><td>€{val:,.2f}</td></tr>"
        for cls, val in yd_latest.investments_by_class.items()
    ) or '<tr><td colspan="2">No investment data</td></tr>'

    return f"""
    <p class="status-subtitle">As of the latest data in {yd_latest.year}</p>
    {cards_html}
    <div class="status-tables">
      <div class="status-table">
        <h3>Bank Accounts</h3>
        <table>{balances_rows}</table>
      </div>
      <div class="status-table">
        <h3>Investments by Asset Class</h3>
        <table>{invest_rows}</table>
      </div>
    </div>
    """


# ---------------- Shared year control (drives multiple figures at once) ----------------

def build_year_control(control_id, metas):
    """One <select> that restyles/relayouts every figure listed in `metas`
    (each a dict from a builder's second return value) in lockstep."""
    years = metas[0]['years'] if metas else []
    fig_data = {
        meta['div_id']: {
            "visibility": {str(y): meta['visibility'][y] for y in meta['years']},
            "annotations": {str(y): meta['annotations'][y] for y in meta['years']},
            "title": {str(y): meta['title'][y] for y in meta['years']},
        }
        for meta in metas
    }
    default_year = years[-1] if years else ""
    options = "".join(
        f'<option value="{y}"{" selected" if y == default_year else ""}>{y}</option>' for y in years
    )
    data_json = json.dumps(fig_data)

    return f"""
    <div class="control-row">
      <label for="{control_id}">Year:</label>
      <select id="{control_id}">{options}</select>
    </div>
    <script>
    (function() {{
      const FIG_META = {data_json};
      function applyYear(year) {{
        Object.keys(FIG_META).forEach(function(divId) {{
          const meta = FIG_META[divId];
          Plotly.restyle(divId, {{visible: meta.visibility[year]}});
          Plotly.relayout(divId, {{title: meta.title[year], annotations: meta.annotations[year]}});
        }});
      }}
      document.getElementById('{control_id}').addEventListener('change', function(e) {{
        applyYear(e.target.value);
      }});
    }})();
    </script>
    """


# ---------------- HTML assembly ----------------

STATUS_CSS = """
.status-subtitle{color:#888;margin-top:-6px;}
.status-cards-primary{display:flex;margin:16px 0 10px;}
.status-cards-secondary{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px;}
.stat-card{background:#181b21;border:1px solid #2a2e37;border-radius:8px;
  padding:14px 20px;min-width:150px;}
.stat-card--primary{min-width:240px;padding:20px 28px;border-color:#3a4a63;
  background:#161c26;}
.stat-card--secondary{opacity:0.85;}
.stat-card--secondary .stat-value{font-size:1.1em;}
.stat-label{color:#9aa0aa;font-size:0.8em;text-transform:uppercase;letter-spacing:0.04em;}
.stat-value{font-size:1.4em;font-weight:600;margin-top:4px;}
.stat-card--primary .stat-value{font-size:2em;}
.stat-change{margin-top:6px;color:#9aa0aa;font-size:0.95em;}
.status-tables{display:flex;flex-wrap:wrap;gap:24px;margin-bottom:10px;}
.status-table{flex:1;min-width:260px;}
.status-table h3{margin-bottom:6px;color:#cfd3da;}
.status-table table{width:100%;border-collapse:collapse;}
.status-table td{padding:6px 8px;border-bottom:1px solid #232730;}
.status-table td:last-child{text-align:right;font-variant-numeric:tabular-nums;}
.control-row{margin:10px 0 18px;}
.control-row label{color:#9aa0aa;margin-right:8px;}
.control-row select{background:#181b21;color:#e8e8e8;border:1px solid #2a2e37;
  border-radius:6px;padding:5px 10px;font-size:0.95em;}
"""


def build_html(body_parts):
    parts = [
        "<title>BudgetBash Dashboard</title>",
        "<style>"
        "body{font-family:sans-serif;max-width:1100px;margin:0 auto;padding:20px;"
        "background:#0b0c0f;color:#e8e8e8;}"
        "h2{border-bottom:1px solid #333;padding-bottom:6px;}"
        f"{STATUS_CSS}"
        "</style>",
    ]
    parts.extend(body_parts)
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-path", default=str(REPO_ROOT / "demo"))
    parser.add_argument("--output", default=str(REPO_ROOT / "dashboard" / "dashboard.html"))
    args = parser.parse_args()

    data_path = Path(args.data_path)
    years = discover_years(data_path)
    if not years:
        print(f"No year data found under {data_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading years: {years}")
    per_year = load_all_years(data_path, years)
    if not per_year:
        print("No data could be loaded.", file=sys.stderr)
        sys.exit(1)

    status_html = build_status_html(per_year[-1])
    cutoff = first_active_month(per_year)

    cashflow_fig = build_alltime_cashflow_fig(per_year, cutoff)
    cat_fig, cat_meta = build_year_categories_fig(per_year, div_id="cat-year-fig")
    month_fig, month_meta = build_month_expenses_fig(per_year, div_id="month-expenses-fig")
    networth_fig = build_networth_fig(per_year, cutoff)
    investments_fig = build_investments_fig(per_year)

    year_control_html = build_year_control("categories-year-select", [cat_meta, month_meta])

    body_parts = [
        "<h2>Dashboard Status</h2>", status_html,
        "<h2>Cashflow</h2>", cashflow_fig.to_html(full_html=False, include_plotlyjs='cdn'),
        "<h2>Categories by Year</h2>", year_control_html,
        cat_fig.to_html(full_html=False, include_plotlyjs=False, div_id="cat-year-fig"),
        "<h2>Monthly Expenses</h2>",
        month_fig.to_html(full_html=False, include_plotlyjs=False, div_id="month-expenses-fig"),
        "<h2>Net Worth</h2>", networth_fig.to_html(full_html=False, include_plotlyjs=False),
    ]
    if investments_fig is not None:
        body_parts += ["<h2>Investments</h2>", investments_fig.to_html(full_html=False, include_plotlyjs=False)]

    html = build_html(body_parts)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Dashboard written to {output_path}")


if __name__ == "__main__":
    main()
