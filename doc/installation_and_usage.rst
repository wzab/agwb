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
   
   name: ::dpb_agwb
   
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
            infile: dpb_top.xml
            hdl: . # Do not change this path, it should always be ".".
            # Commented parameters are optional.
            # Paths for generated output files in below parameters are relative.
            # header: c_headers/destination
            # html: html/destination
            # ipbus: ipbus_outputs/destination
            # python: python_raw/destination
            # fs: Forth_outputs/destination
