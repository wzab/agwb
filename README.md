# adr\_gen\_wb.py - register access for hierarchical Wishbone connected systems #
The [wbgen2](https://www.ohwr.org/projects/wishbone-gen/wiki/wbgen2-documentation) is a very nice tool. However, it has certain limitations that were critical for me. Namely it does not support arrays of registers, and does not support nested blocks. Probably it can be extended to support those features, but I definitely prefere to write code generators in Python than in Lua. Therefore I decided to try to write adr\_gen\_wb.py in Python, almost from scratch.

The code is licensed under GPL v2 license.
The generated code is free, and you can freely use it in your design.

I'd like to thank Marek Gumiński for important suggestions related to concept of that solution.

To see the demonstration of the system, please go to the "test" directory, then run the "prepare.sh" script (which downloads the Wishbone related components), after that run the "generate.sh" script (which generates the files for a simple demo system described by "example1.xml"), and finally run "test_wb.sh".
Please note, that ghdl must be in your PATH.

