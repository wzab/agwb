Python
------

If :code:`--python` argument is specified, AGWB generates special :code:`agwb` package, which can be used for simulation or interaction with real hardware.
To be able to import the package it must be in the path.
It is left for the user how it is achieved.

The hardware-related structure of blocks and registers is represented as a nested structure of proper classes and attributes.
The details are well abstracted from the user.
Accessing a register feels exactly the same as accessing regular Python class attributes.
Assume there is :code:`top` block, which contains :code:`foo` subblock, which containts :code:`bar` status register.
After instantiating the :code:`top` class reading the :code:`bar` register can be simply done with :code:`top.foo.bar.read()`.

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
