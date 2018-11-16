#!/usr/bin/python3
"""
This is the script that generates the VHDL code needed to access 
the registers in a hierarchical Wishbone-conencted system.

Written by Wojciech M. Zabolotny
(wzab01@gmail.com or wzab@ise.pw.edu.pl)

The code is published under LGPL V2 license
"""
import xml.etree.ElementTree as et
import wb_block as wb
sysdef=et.ElementTree(file="../example1.xml")
# We get the root element, and find the corresponding block
er=sysdef.getroot()
top_name=er.attrib["top"]
# Now we find the top block definition

# We should evaluate the address space requirements in each block
# In the first run, we calculate the space occupied by registers,
# but as blocks may be defined in different order, we also
# analyze the block dependencies.

# Create the list of blocks
for el in er.findall("block"):
   # Here we take each block and count registers inside
   # We also prepare the list of subblocks (of vectors of
   # subblocks)
   bn=el.attrib['name']
   if bn in wb.blocks:
      raise Exception("Duplicate definition of block: "+bn)
   bl = wb.wb_block(el)
   wb.blocks[bn] = bl
# Here we have everything, we could get from the first scan.
bl=wb.blocks[top_name]
bl.analyze()
for key,bl in wb.blocks.items():
   bl.gen_vhdl()


   
