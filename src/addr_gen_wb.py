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
import time
import sys
import os.path
# import Path

def print_usage():
  print("Usage: %s [infile.xml] [ipbus_directory] [vhdl_directory]", sys.argv[0])
  sys.exit()

infilename = "../example1.xml"
ipbus_path  = ""
vhdl_path  = ""

# As the version for generated code (HDL and SW)
# we take the 32-bit of the system time.
ver_id = int(time.time()) & 0xFFFFffff

nargs = len(sys.argv)

if nargs>=2:
  infilename = sys.argv[1]

  if not os.path.isfile(infilename):
    print("Invalid path for input file!")
    print_usage()

if nargs>=3:
  ipbus_path = sys.argv[2]

  if (not os.path.exists(ipbus_path)) or os.path.isfile(ipbus_path):
    print("Invalid ipbus directory!")
    print_usage()

  ipbus_path=ipbus_path+"/"

if nargs>=4:
  vhdl_path = sys.argv[3]

  if (not os.path.exists(vhdl_path)) or os.path.isfile(vhdl_path):
    print("Invalid vhdl directory!")
    print_usage()

  vhdl_path=vhdl_path+"/"

if nargs>4:
    print("Too many arguments!")
    print_usage()

sysdef=et.ElementTree(file=infilename)
# We get the root element, and find the corresponding block
er=sysdef.getroot()
top_name=er.attrib["top"]
if "masters" in er.attrib:
  n_masters=er.attrib["masters"]
else:
  n_masters=1

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
   bl = wb.wb_block(el, vhdl_path, ipbus_path)
   wb.blocks[bn] = bl
# Here we have everything, we could get from the first scan.
bl=wb.blocks[top_name]
#overwite the number of master ports in the top module
bl.n_masters=n_masters
bl.analyze()
for key,bl in wb.blocks.items():
   if bl.used:
     bl.gen_vhdl(ver_id)
# Now we generate the address tables
for key,bl in wb.blocks.items():
   if bl.used:
     bl.gen_ipbus_xml(ver_id)

# Generate the Forth address table
bl=wb.blocks[top_name]
with open("wb_addr.fs","w") as fo:
   root_word='%/'
   #Add empty definition for root_word
   fo.write(": "+root_word+" ;\n") 
   fo.write(bl.gen_forth(ver_id,root_word))


   
