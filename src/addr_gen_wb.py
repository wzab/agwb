#!/usr/bin/python3
"""
This is the script that generates the VHDL code needed to access
the registers in a hierarchical Wishbone-conencted system.

Written by Wojciech M. Zabolotny
(wzab01@gmail.com or wzab@ise.pw.edu.pl)

The code is published under LGPL V2 license
"""
import xml.etree.ElementTree as et
import xml.parsers.expat as pe
import wb_block as wb
import time
import sys
import os.path
import include
import zlib
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--infile", help="Input file path", default='../example1.xml')
parser.add_argument("--hdl", help="VHDL outputs destination", default='.')
parser.add_argument("--ipbus", help="IPbus outputs destination", default='.')
parser.add_argument("--fs", help="Forth outputs destination", default='.')
args = parser.parse_args()

infilename=args.infile
ipbus_path=args.ipbus+"/"
vhdl_path=args.hdl+"/"
forth_path=args.fs+"/"

print(ipbus_path)
print(vhdl_path)

# The module expressions accepts definitions of constants (function addval)
# and evaluates the expressions (function exprval)
import expressions as ex

# The line below reads the XML and recursively inserts included XMLs
# it also generates the list of objects describing the origin of each line
# in the final XML (to facilitate future error detection)
final_xml, lines_origin = include.handle_includes(infilename)

# The version ID is calculated as a hash of the XML defining the interface
# it is encoded in UTF-8, to avoid problems with different locales
ver_id = zlib.crc32(bytes(final_xml.encode('utf-8')))

# We get the root element, and find the corresponding block
try:
    er=et.fromstring(final_xml)
except et.ParseError as perr:
    # Handle the parsing error
    row,col = perr.position
    print("Parsing error "+str(perr.code)+"("+\
      pe.ErrorString(perr.code)+") in column "+\
      str(col)+" of the line "+str(row)+" of the concatenated XML:")
    print(final_xml.split("\n")[row-1])
    print(col*"-"+"|")
    print("The erroneous line was produced from the following sources:")
    err_src = include.find_error(lines_origin,row)
    for src in err_src:
        print("file: "+src[0]+", line:"+str(src[1]))
    sys.exit(1)
top_name=er.attrib["top"]
if "masters" in er.attrib:
    n_masters=ex.exprval(er.attrib["masters"])
else:
    n_masters=1
# Find constants and feed them into the expressions module
for el in er.findall("constant"):
    ex.addval(el.attrib['name'],el.attrib['val'])
# We prepare the packages with constants for different backends
# For VHDL
with open(vhdl_path+"/"+top_name+"_const_pkg.vhd","w") as fo:
    fo.write("""library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
""")
    fo.write("package "+top_name+"_const_pkg is\n")
    for cnst in ex.defines:
        fo.write("constant "+cnst+" : integer := "+\
        str(ex.defines[cnst])+"; -- "+\
        ex.comments[cnst]+"\n")
    fo.write("end "+top_name+"_const_pkg;\n")
# For C
with open(ipbus_path+"/"+top_name+"_const.h","w") as fo:
    guard_name="_"+top_name+"_inc_H_"
    fo.write("#ifndef "+guard_name+"\n")
    fo.write("#define "+guard_name+"\n\n")
    for cnst in ex.defines:
        fo.write("#define "+cnst+" "+str(ex.defines[cnst])+\
        " // "+ex.comments[cnst]+"\n")
    fo.write("\n#endif\n")
# For Python
with open(ipbus_path+"/"+top_name+"_const.py","w") as fo:
    for cnst in ex.defines:
        fo.write(cnst+" = "+str(ex.defines[cnst])+\
        " # "+ex.comments[cnst]+"\n")
# Generation of constants for Forth is added to the generation of
# the access words

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
with open(forth_path+"/"+top_name+".fs","w") as fo:
    #First generate constants
    for cnst in ex.defines:
        fo.write(": %"+cnst+" $"+format(ex.defines[cnst],'x')+" ; \\ "+\
        ex.comments[cnst]+"\n")
    #Now generate the HW access words
    root_word='%/'
    #Add empty definition for root_word
    fo.write(": "+root_word+" $0 ;\n")
    fo.write(bl.gen_forth(ver_id,root_word))
