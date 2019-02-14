# Generation of addresses for FORTH CPU #
adr\_gen\_wb is capable of creating the address tables for Forth CPU like J1B.
An example of such system may be the [AFCK_J1B_FORTH](https://github.com/wzab/AFCK_J1B_FORTH).

Let's assume, that our system, described by _example1.xml_ file is connected
to the Wishbone bus, at the base address $1000.
Then to put the  address of the CTRL register, you have to issue the command:

    $1000 %/_CTRL
	
The "%/" denotes the top of the the included WB system. "\_" separates the hierarchy levels.
If there is a vector of objects, the name of generated word includes '#', and you need to add the number of the element on the stack after the base address. For example if you want to put on the stack the address of the 4th _ENABLEs_ register in the 3rd _LINKS_ block, you have to use:

    $1000 3 4 %/#LINKS#ENABLEs 
	
If you want to write $56 to that register, you use:

    $56 $1000 3 4 %/#LINKS#ENABLEs wb!
	
If you want to read the value from the register, you use:

    $1000 3 4 %/#LINKS#ENABLEs  wb@
	
Similarly you may access the bitfields. To write 1 to the START bit in the 
CTRL register of the 2nd LINKS block you use:

    1 $1000 2 %/#LINKS_CTRL.START bf!
	
To read the value from the STOP bit in the 2nd LINKS block you use:

    $1000 2 %/#LINKS_CTRL.STOP bf@
	

	
