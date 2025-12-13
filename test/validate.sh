#!/bin/bash

printf "VALIDATION OF LIB FUNCTIONALITY\n"

cd ..
python3 -m lib.libtest.test_expansion
python3 -m lib.libtest.test_load_data