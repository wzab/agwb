#!/bin/bash
set -e
mkdir -p src/created/gen
( cd src/created ; ../../../src/addr_gen_wb.py --infile example1.xml --hdl gen --ipbus gen --fs gen )
