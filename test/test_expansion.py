#Test script to verify template expansion logic

import json

def load_config():
    """Load and return config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)

def load_mappings():
    """Load and return mappings.json"""
    with open('mappings.json', 'r') as f:
        return json.load(f)

def expand_transfer_templates(config):
    """Expand Transfer subcategories templates with actual provider names from mappings.json"""
    mappings = load_mappings()
    if mappings is None:
        return config

    # Expand for cashflow
    if 'cashflow' in config and 'Subcategory' in config['cashflow'] and 'Transfer' in config['cashflow']['Subcategory']:
        transfer_templates = config['cashflow']['Subcategory']['Transfer']
        expanded = []

        for template in transfer_templates:
            # Check if template contains placeholder
            if '{' in template and '}' in template:
                # Extract placeholder: "To{Acc1}" -> "Acc1"
                start = template.index('{')
                end = template.index('}')
                placeholder = template[start+1:end]

                # Get mapped value
                if placeholder in mappings:
                    # Replace placeholder with actual value
                    expanded_value = template[:start] + mappings[placeholder] + template[end+1:]
                    expanded.append(expanded_value)
                else:
                    # Placeholder not found in mappings, keep as-is
                    expanded.append(template)
            else:
                # No placeholder (e.g., "Invest"), keep as-is
                expanded.append(template)

        # Update config with expanded values
        config['cashflow']['Subcategory']['Transfer'] = expanded

    return config

if __name__ == "__main__":
    print("Testing template expansion...")

    # Load original config
    config = load_config()
    print("Original Transfer subcategories (templates):")
    print(config['cashflow']['Subcategory']['Transfer'])

    # Expand templates
    expanded_config = expand_transfer_templates(config)
    print("Expanded Transfer subcategories (actual names):")
    print(expanded_config['cashflow']['Subcategory']['Transfer'])

    expected_values = [
        "ToHype", "ToBBVA", "ToRevolut", "ToING", "ToINGCD",
        "ToDirecta", "ToBitget", "ToCash", "Invest",
        "FromHype", "FromBBVA", "FromRevolut", "FromING", "FromINGCD",
        "FromDirecta", "FromBitget", "FromCash"
    ]

    actual_values = expanded_config['cashflow']['Subcategory']['Transfer']

    print(f"Expected {len(expected_values)} subcategories, got {len(actual_values)}")

    missing = set(expected_values) - set(actual_values)
    extra = set(actual_values) - set(expected_values)

    if missing:
        print(f"Missing values: {missing}")
    if extra:
        print(f"Extra values: {extra}")

    if not missing and not extra:
        print("All expected subcategories present!")

    print("Expanded subcategories as comma-separated (like API response):")
    print(','.join(actual_values))
