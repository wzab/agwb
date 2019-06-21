#!/usr/bin/python3
"""
This is the script that generates the VHDL code needed to access
the registers in a hierarchical Wishbone-conencted system.

Written by Wojciech M. Zabolotny
(wzab01<at>gmail.com or wzab<at>ise.pw.edu.pl)

Significant improvements by
Michal Kruszewski (mkru<at>protonmail.com)
and
Marek Guminski (marek.guminski<at>gmail.com)

The code is published under LGPL V2 license
"""
import xml.etree.ElementTree as et
import xml.parsers.expat as pe
import sys
import zlib
import argparse
import wb_block as wb
import include
# The module expressions accepts definitions of constants (function addval)
# and evaluates the expressions (function exprval)
import expressions as ex


PARSER = argparse.ArgumentParser()
PARSER.add_argument("--infile", help="Input file path", default='../example1.xml')
PARSER.add_argument("--hdl", help="VHDL outputs destination", default='.')
PARSER.add_argument("--ipbus", help="IPbus outputs destination", default='.')
PARSER.add_argument("--header", help="C header outputs destination", default='.')
PARSER.add_argument("--fs", help="Forth outputs destination", default='.')
PARSER.add_argument("--python", help="Python outputs destination", default='.')
ARGS = PARSER.parse_args()

INFILENAME = ARGS.infile
IPBUS_PATH = ARGS.ipbus+"/"
VHDL_PATH = ARGS.hdl+"/"
FORTH_PATH = ARGS.fs+"/"
C_HEADER_PATH = ARGS.header+"/"
PYTHON_PATH = ARGS.python+"/"

print(IPBUS_PATH)
print(VHDL_PATH)

# The line below reads the XML and recursively inserts included XMLs
# it also generates the list of objects describing the origin of each line
# in the final XML (to facilitate future error detection)
FINAL_XML, LINES_ORIGIN = include.handle_includes(INFILENAME)

# The version ID is calculated as a hash of the XML defining the interface
# it is encoded in UTF-8, to avoid problems with different locales
VER_ID = zlib.crc32(bytes(FINAL_XML.encode('utf-8')))

# We get the root element, and find the corresponding block
try:
    EL_ROOT = et.fromstring(FINAL_XML)
except et.ParseError as perr:
    # Handle the parsing error
    ROW, COL = perr.position
    print("Parsing error "+str(perr.code)+"("+\
      pe.ErrorString(perr.code)+") in column "+\
      str(COL)+" of the line "+str(ROW)+" of the concatenated XML:")
    print(FINAL_XML.split("\n")[ROW-1])
    print(COL*"-"+"|")
    print("The erroneous line was produced from the following sources:")
    ERR_SRC = include.find_error(LINES_ORIGIN, ROW)
    for src in ERR_SRC:
        print("file: "+src[0]+", line:"+str(src[1]))
    sys.exit(1)
TOP_NAME = EL_ROOT.attrib["top"]
if "masters" in EL_ROOT.attrib:
    N_MASTERS = ex.exprval(EL_ROOT.attrib["masters"])
else:
    N_MASTERS = 1
# Find constants and feed them into the expressions module
for el in EL_ROOT.findall("constant"):
    ex.addval(el.attrib['name'], el.attrib['val'])
# We prepare the packages with constants for different backends
# For VHDL
with open(VHDL_PATH+"/agwb_"+TOP_NAME+"_const_pkg.vhd", "w") as fo:
    fo.write("""library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
""")
    fo.write("package agwb_"+TOP_NAME+"_const_pkg is\n")
    for cnst in ex.defines:
        fo.write("constant "+cnst+" : integer := "+\
        str(ex.defines[cnst])+"; -- "+\
        ex.comments[cnst]+"\n")
    fo.write("end agwb_"+TOP_NAME+"_const_pkg;\n")
# For C
with open(IPBUS_PATH+"/agwb_"+TOP_NAME+"_const.h", "w") as fo:
    GUARD_NAME = "_agwb_"+TOP_NAME+"_inc_H_"
    fo.write("#ifndef "+GUARD_NAME+"\n")
    fo.write("#define "+GUARD_NAME+"\n\n")
    for cnst in ex.defines:
        fo.write("#define "+cnst+" "+str(ex.defines[cnst])+\
        " // "+ex.comments[cnst]+"\n")
    fo.write("\n#endif\n")
# For Python
with open(IPBUS_PATH+"/agwb_"+TOP_NAME+"_const.py", "w") as fo:
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
for el in EL_ROOT.findall("block"):
    # Here we take each block and count registers inside
    # We also prepare the list of subblocks (of vectors of
    # subblocks)
    bn = el.attrib['name']
    if bn in wb.blocks():
        raise Exception("Duplicate definition of block: "+bn)
    bl = wb.WbBlock(el, VHDL_PATH, IPBUS_PATH, C_HEADER_PATH)
    wb.blocks()[bn] = bl
# Here we have everything, we could get from the first scan.
BL = wb.blocks()[TOP_NAME]
#overwite the number of master ports in the top module
BL.N_MASTERS = N_MASTERS
BL.analyze()
# Now we can generate the VHDL code that implements
# the system
for key, BL in wb.blocks().items():
    if BL.used:
        BL.gen_vhdl(VER_ID)
# Now we generate the Python access code
res = "from agwb import AwObj,AwSreg,AwCreg\n"
for key, BL in wb.blackboxes().items():
    res += BL.gen_python(VER_ID)
for key, BL in wb.blocks().items():
    if BL.used:
        res += BL.gen_python(VER_ID)
with open(PYTHON_PATH+"/agwb_"+TOP_NAME+".py", "w") as fo:
    fo.write(res)
# Now we generate the IPbus address tables
for key, BL in wb.blocks().items():
    if BL.used:
        BL.gen_ipbus_xml(VER_ID)
# Now we generate the C address tables
for key, BL in wb.blackboxes().items():
    BL.gen_c_header(VER_ID)
for key, BL in wb.blocks().items():
    if BL.used:
        BL.gen_c_header(VER_ID)
# Generate the Forth address table
BL = wb.blocks()[TOP_NAME]
with open(FORTH_PATH+"/agwb_"+TOP_NAME+".fs", "w") as fo:
    #First generate constants
    for cnst in ex.defines:
        fo.write(": %"+cnst+" $"+format(ex.defines[cnst], 'x')+" ; \\ "+\
        ex.comments[cnst]+"\n")
    #Now generate the HW access words
    ROOT_WORD = '%/'
    #Add empty definition for ROOT_WORD
    fo.write(": "+ROOT_WORD+" $0 ;\n")
    fo.write(BL.gen_forth(VER_ID, ROOT_WORD))
