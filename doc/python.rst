Python
------

If :code:`--python` argument is specified, AGWB generates special :code:`agwb` package, which can be used for simulation or interaction with real hardware.
To be able to import the package it must be in the path.
It is left for the user how it is achieved.

Register interface
##################

Currently register interface supports following methods:

#. :code:`read()`.
#. :code:`read_fifo(count)` - read register *count* times.
#. :code:`write(value)`.
#. :code:`write_fifo(values)` - write register with *values*, where *values* is a list.

Both :code:`read_fifo` and :code:`write_fifo` are useful not only for interacting with real FIFOs.
For example, :code:`write_fifo([1,0])` is a concise way for resetting modules (assuming required pulse width on a reset port can be shorter than single write operation within the FPGA).

Example
#######
