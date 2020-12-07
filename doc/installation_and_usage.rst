Installation and usage
----------------------
AGWB is not installable from PyPI via pip.
To be able to use AGWB you have to clone the repository from https://github.com/wzab/addr_gen_wb and use :code:`src/addr_gen_wb.py` in a script way.

Although AGWB is not installable from PyPI via pip it is possible to install some parts of it.
Namely, the :code:`agwb` Python package, which can be used for interaction with flashed FPGAs or simulation purposes.
To install the package execute the following command in the repository root directory.

.. code-block:: Python

   python setup.py install --user


AGWB and FuseSoc
################
AGWB can be used as a FuseSoc (https://github.com/olofk/fusesoc) generator.
Following snippet from *.core* file can serve as an example.

.. code-block:: yaml

   CAPI=2:
   
   # Choose whatever name you want.
   # If you have only single AGWB description of the system
   # within your design, then it is good to use 'agwb' name.
   name: ::agwb
   
   filesets:
     agwb_dep:
       depend:
         - wzab::addr_gen_wb
   
   targets:
     default:
       generate:
         - agwb_regs
       filesets:
         - agwb_dep
   
   generate:
     agwb_regs:
       generator: addr_gen_wb
       parameters:
         infile: top.xml
         # hdl parameter is optional. If you don't provide it
         # VHDL files will be generated to the FuseSoc cache directory.
         hdl: ./optional/relative/path/for/generated/vhdl/files
         # Below commented parameters are programming language specific
         # and are also optional. Unlike 'hdl' parameter, if they are not
         # provided particular files will not be generated.
         # Paths for generated output files in all below parameters are relative.
         # header: c_headers/destination
         # html: html/destination
         # ipbus: ipbus_outputs/destination
         # python: python_raw/destination
         # fs: Forth_outputs/destination
