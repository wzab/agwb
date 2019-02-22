This demo shows a possibility to use the _addr\_gen\_wb_ framework to build
a system with multiple clocks. It is controlled via the JTAG2WB interface
(published at https://github.com/wzab/wzab-hdl-library/tree/master/jtag2wb ).
There are three different clocks in the design.
The design uses the VEXTPROJ ( https://github.com/wzab/vextproj ) system to create and build the 
project in Xilinx Vivado environment.
To rebuild and verify the design, run in order:

* prepare.sh
* generate.sh
* build.sh

