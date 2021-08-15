#!/bin/bash
set -e
(
  git clone https://ohwr.org/project/general-cores.git
  cd general-cores
  # I have done simply:
  # git checkout propose_master
  # but as general-cores may further evolve, and get incompatible 
  # with my codes, here I get the particular commit:
  git checkout 63f3671351127a398006e01f66b37adb7eda9a37
)
