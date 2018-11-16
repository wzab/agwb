#!/bin/bash
set -e
(
  git clone git://ohwr.org/hdl-core-lib/general-cores.git
  cd general-cores
  # I have done simply:
  # git checkout propose_master
  # but as general-cores may further evolve, and get incompatible 
  # with my codes, here I get the particular commit:
  git checkout 3bbcf4a385999625bfdeac568410f248b017f57f
)
