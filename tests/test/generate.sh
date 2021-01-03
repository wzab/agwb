#!/bin/bash
set -e
mkdir -p gen
../../src/addr_gen_wb.py --infile example1.xml --fs ./gen --hdl ./gen  --amapxml ./gen_amap --header ./gen --python ./python_raw --html ./gen


