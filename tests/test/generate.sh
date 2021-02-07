#!/bin/bash
set -e
mkdir -p gen
../../src/addr_gen_wb.py --infile example1.xml --fs ./gen --hdl ./gen  --ipbus ./ipbusxml --amapxml ./gen_amap --header ./gen --pythondca ./python_raw --html ./gen --fusesoc 


