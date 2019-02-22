#!/bin/bash
set -e
mkdir -p src/created/gen
( cd src/created ; ../../../src/addr_gen_wb.py example1.xml gen gen )
