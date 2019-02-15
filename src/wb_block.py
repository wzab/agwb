""" 
This is the script that generates the VHDL code needed to access 
the registers in a hierarchical Wishbone-conencted system.

Written by Wojciech M. Zabolotny
(wzab01@gmail.com or wzab@ise.pw.edu.pl)

The code is published under LGPL V2 license

This file implements the class handling a Wishbone connected block
"""
import re
import zlib

# Template for generation of the VHDL package
templ_pkg = """\
library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.wishbone_pkg.all;

package {p_entity}_pkg is
{p_package}
end {p_entity}_pkg;

package body {p_entity}_pkg is
{p_package_body}
end {p_entity}_pkg;
"""

# The function below returns the template for generation of the VHDL code
# There is one argument, describing if it is the top block, that requires
# the multi-master support or not.
def templ_wb(nof_masters):
  res = """\
--- This code is automatically generated by the addrgen_wb.py tool
--- Please don't edit it manaully, unless you really have to do it.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library work;
use work.wishbone_pkg.all;
use work.{p_entity}_pkg.all;

entity {p_entity} is
  port (
"""
  if nof_masters>1 :
    res += """\
    slave_i : in t_wishbone_slave_in_array(0 to {nof_masters}-1);
    slave_o : out t_wishbone_slave_out_array(0 to {nof_masters}-1);
"""
  else:
    res += """\
    slave_i : in t_wishbone_slave_in;
    slave_o : out t_wishbone_slave_out;
"""
  res+="""\
{subblk_busses}
{signal_ports}
    rst_n_i : in std_logic;
    clk_sys_i : in std_logic
    );

end {p_entity};

architecture gener of {p_entity} is
{signal_decls}
  -- Internal WB declaration
  signal int_regs_wb_m_o : t_wishbone_master_out;
  signal int_regs_wb_m_i : t_wishbone_master_in;
  signal int_addr : std_logic_vector({reg_adr_bits}-1 downto 0);
  signal wb_up_o : t_wishbone_slave_out_array(0 to 0);
  signal wb_up_i : t_wishbone_slave_in_array(0 to 0);
  signal wb_m_o : t_wishbone_master_out_array(0 to {nof_subblks}-1);
  signal wb_m_i : t_wishbone_master_in_array(0 to {nof_subblks}-1);

  -- Constants
  constant c_address : t_wishbone_address_array(0 to {nof_subblks}-1) := {p_addresses};
  constant c_mask : t_wishbone_address_array(0 to {nof_subblks}-1) := {p_masks};

begin
"""
  if nof_masters == 1:
    res += """\
  wb_up_i(0) <= slave_i;
  slave_o <= wb_up_o(0);
"""
  res += """\
  int_addr <= int_regs_wb_m_o.adr({reg_adr_bits}-1 downto 0);

-- Main crossbar 
  xwb_crossbar_1: entity work.xwb_crossbar
  generic map (
     g_num_masters => {nof_masters},
     g_num_slaves  => {nof_subblks},
     g_registered  => {p_registered},
     g_address     => c_address,
     g_mask        => c_mask)
  port map (
     clk_sys_i => clk_sys_i,
     rst_n_i   => rst_n_i,
"""
  if nof_masters > 1:
     res += """\
     slave_i   => slave_i,
     slave_o   => slave_o,
"""
  else:
     res += """\
     slave_i   => wb_up_i,
     slave_o   => wb_up_o,
"""
  res += """\
     master_i  => wb_m_i,
     master_o  => wb_m_o,
    sdb_sel_o => open);

-- Process for register access
  process(clk_sys_i)
  begin
    if rising_edge(clk_sys_i) then
      if rst_n_i = '0' then
        -- Reset of the core
        int_regs_wb_m_i <= c_DUMMY_WB_MASTER_IN;
      else
        -- Normal operation
        int_regs_wb_m_i.rty <= '0';
        int_regs_wb_m_i.ack <= '0';
        int_regs_wb_m_i.err <= '0';
{signals_idle}
        if (int_regs_wb_m_o.cyc = '1') and (int_regs_wb_m_o.stb = '1') then
          int_regs_wb_m_i.err <= '1'; -- in case of missed address
          -- Access, now we handle consecutive registers
          case int_addr is
{register_access}
          when {block_id_addr} =>
             int_regs_wb_m_i.dat <= {block_id};
             int_regs_wb_m_i.ack <= '1';
             int_regs_wb_m_i.err <= '0';
          when {block_ver_addr} =>
             int_regs_wb_m_i.dat <= {block_ver};
             int_regs_wb_m_i.ack <= '1';
             int_regs_wb_m_i.err <= '0';
          when others =>
             int_regs_wb_m_i.dat <= x"A5A5A5A5";
             int_regs_wb_m_i.ack <= '1';
             int_regs_wb_m_i.err <= '0';
          end case;
        end if;
      end if;
    end if;
  end process;
{cont_assigns}
end architecture;
"""
  return res

blocks={}
blackboxes={}

class wb_field(object):
   def __init__(self,fl,lsb):
      self.name = fl.attrib['name']
      self.lsb = lsb
      self.size = int(fl.attrib['width'])
      self.msb = lsb + self.size - 1
      self.type = fl.get('type','std_logic_vector')
     
          

class wb_reg(object):
   """ The class wb_reg describes a single register
   """
   def __init__(self,el,adr):
       """
       The constructor gets the XML node defining the register
       """
       nregs=int(el.get('reps',1))
       self.regtype = el.tag
       self.type = el.get('type','std_logic_vector')
       self.base = adr
       self.size = nregs
       self.name = el.attrib['name']
       self.ack = int(el.get('ack',0))
       self.stb = int(el.get('stb',0))
       # Read list of fields
       self.fields=[]
       self.free_bit=0
       for fl in el.findall('field'):
           fdef=wb_field(fl,self.free_bit)
           self.free_bit += fdef.size
           if self.free_bit > 32:
              raise Exception("Total width of fields in register " +self.name+ " is above 32-bits")
           self.fields.append(fdef)
       

   def gen_vhdl(self,parent):
       """
       The method generates the VHDL block responsible for access
       to the registers.
       We append our definitions to the appropriate sections
       in the parrent block.
       
       We need to generate two sections:
       * Declaration of signals used to input or output the signal,
          and the optional ACK or STB flags
       * Read or write sequence to be embedded in the process
       """
       dt=""
       dtb=""
       dti=""
       # Generate the type corresponding to the register
       tname = "t_"+self.name
       if len(self.fields) == 0:
          # Simple register, no fields
          dt+="subtype "+tname+" is "+\
             self.type+"(31 downto 0);\n" 
       else:
          # Register with fields, we have to create a record
          dt+="type "+tname+" is record\n"
          for fl in self.fields:
             dt+= "  "+fl.name+":"+fl.type+"("+str(fl.size-1)+" downto 0);\n"
          dt+="end record;\n\n"

          #Conversion function stlv to record
          dt+="function stlv2"+tname+"(x : std_logic_vector) return "+tname+";\n"
          dtb+="function stlv2"+tname+"(x : std_logic_vector) return "+tname+" is\n"
          dtb+="variable res : "+tname+";\n"
          dtb+="begin\n"
          for fl in self.fields:
            dtb+="  res."+fl.name+" := "+fl.type+"(x("+str(fl.msb)+" downto "+str(fl.lsb)+"));\n"
          dtb+="  return res;\n"
          dtb+="end stlv2"+tname+";\n\n"
          
          #conversion function record to stlv
          dt+="function "+tname+"2stlv(x : "+tname+") return std_logic_vector;\n"
          dtb+="function "+tname+"2stlv(x : "+tname+") return std_logic_vector is\n"
          dtb+="variable res : std_logic_vector(31 downto 0);\n"
          dtb+="begin\n"
          dtb+="  res := (others => '0');\n"
          for fl in self.fields:
            dtb+="  res("+str(fl.msb)+" downto "+str(fl.lsb)+") := std_logic_vector(x."+fl.name+");\n"
          dtb+="  return res;\n"
          dtb+="end "+tname+"2stlv;\n\n"
       # If this is a vector of registers, create the array type
       if self.size > 1:
          dt+="type "+tname+"_array is array(0 to "+ str(self.size-1) +") of "+tname+";\n"
       # Append the generated types to the parents package section
       parent.add_templ('p_package',dt,0)
       parent.add_templ('p_package_body',dtb,0)

       # Now generate the entity ports
       sfx = '_i'
       sdir = "in "
       if self.regtype == 'creg':
         sfx = '_o'
         sdir = "out "
       if self.size == 1:
          dt=self.name+sfx+" : "+sdir+" "+tname+";\n"
       else:
          dt=self.name+sfx+" : "+sdir+" "+tname+"_array;\n"
       # Now we generate the STB or ACK ports (if required)
       if self.regtype == 'creg' and self.stb == 1:
          dt += self.name+sfx+"_stb : out std_logic;\n"
          # We need to generate STB output
          pass # To be implemented!
       if self.regtype == 'sreg' and self.ack == 1:
          dt += self.name+sfx+"_ack : out std_logic;\n"
          # We need to generate ACK output
          pass # To be implemented!
       parent.add_templ('signal_ports',dt,4)
       # Generate the intermediate signals for output ports
       # (because they can't be read back)
       if self.regtype == 'creg':
          #Create the intermediate readable signal
          if self.size == 1:
            dt = "signal int_"+self.name+sfx+" : "+tname+";\n"
          else:  
            dt = "signal int_"+self.name+sfx+" : "+tname+"_array;\n"
          dt2 = self.name+sfx+" <= int_"+self.name+sfx+";\n"
          parent.add_templ('signal_decls',dt,4)
          parent.add_templ('cont_assigns',dt2,2)          
       # Generate the signal assignment in the process
       for i in range(0,self.size):
          # We prepare the index string used in case if this is a vector of registers
          if self.size > 1:
             ind ="("+str(i)+")"
          else:
             ind = ""
          dt= "when \""+format(self.base+i,"0"+str(parent.reg_adr_bits)+"b")+"\" => -- "+hex(self.base+i)+"\n"
          # The conversion functions
          if len(self.fields)==0:
             conv_fun="std_logic_vector"
             iconv_fun=self.type
          else:
             conv_fun="t_"+self.name+"2stlv"
             iconv_fun="stlv2t_"+self.name
          # Read access
          if self.regtype == 'sreg':
             dt+="   int_regs_wb_m_i.dat <= "+conv_fun+"("+self.name+"_i"+ind+");\n"
             if self.ack == 1:
                dt += "   if int_regs_wb_m_i.ack = \'0\' then\n" #We shorten the STB to a single clock
                dt += "      "+self.name+sfx+"_ack <= '1';\n"
                dt += "   end if;\n"
                # Add clearing of ACK signal at the begining of the process
                dti += self.name+sfx+"_ack <= '0';\n"
          else:
             dt+="   int_regs_wb_m_i.dat <= "+conv_fun+"(int_"+self.name+"_o"+ind+");\n"             
          # Write access
          if self.regtype == 'creg':
             dt+="   if int_regs_wb_m_o.we = '1' then\n"
             dt+="     int_"+self.name+"_o"+ind+" <= "+iconv_fun+"(int_regs_wb_m_o.dat);\n"
             if self.stb == 1:
                dt += "   if int_regs_wb_m_i.ack = \'0\' then\n" #We shorten the STB to a single clock
                dt += "      "+self.name+sfx+"_stb <= '1';\n"
                dt += "   end if;\n"
                # Add clearing of STB signal at the begining of the process
                dti += self.name+sfx+"_stb <= '0';\n"
             dt+="   end if;\n"
          dt += "   int_regs_wb_m_i.ack <= '1';\n"
          dt += "   int_regs_wb_m_i.err <= '0';\n"
          parent.add_templ('register_access',dt,10)
          parent.add_templ('signals_idle',dti,10)

   def gen_ipbus_xml(self,reg_base):
      # The generated code depends on the fact it is a single register or the vector of registers
      res=""
      for rn in range(0,self.size):
         adr = reg_base+self.base+rn
         # The name format depends whether its a single register or an item in a vector
         if self.size == 1:
            rname = self.name
         else:
            rname = self.name + "["+str(rn)+"]"
         # Set permissions
         if self.regtype == 'creg':
            perms = "rw"
         elif self.regtype == 'sreg':
            perms = "r"
         else:
            raise Exception("Unknown type of register")
         # Finally the format of the description depends on the presence of bitfields
         if len(self.fields) == 0:
            res+="  <node id=\""+rname+"\" address=\"0x"+format(adr,"08x")+"\" permission=\""+perms+"\"/>\n"
         else:
            res+="  <node id=\""+rname+"\" address=\"0x"+format(adr,"08x")+"\" permission=\""+perms+"\">\n"
            for bf in self.fields:
               maskval=((1<<(bf.msb+1))-1) ^ ((1<<bf.lsb)-1)
               mask = format(maskval,"08x")
               res+="    <node id=\""+bf.name+"\" mask=\"0x"+mask+"\"/>\n"
            res+="  </node>\n"
            
      return res

   def gen_forth(self,reg_base,parent):
      # The generated code depends on the fact it is a single register or the vector of registers
      cdefs=""
      adr = reg_base+self.base
      # The name format depends whether its a single register or an item in a vector
      if self.size == 1:
         node = parent+"_"+self.name
         cdefs += ": "+node+" $"+format(adr,'x')+" + " + parent + " ;\n"
      else:
         node = parent+"#"+self.name
         cdefs += ": "+node+" + $"+format(adr,'x')+" + "+ parent + " ;\n"
      if len(self.fields) != 0:
         for bf in self.fields:
            maskval=((1<<(bf.msb+1))-1) ^ ((1<<bf.lsb)-1)
            cdefs += ": "+node+"."+bf.name+" "+node+" $"+format(maskval,'x')+" $"+format(bf.lsb,'x')+" ;\n"                     
      return cdefs

class wb_area(object):
    """ The class representing the address area
    """
    def __init__(self,size,name,obj,reps):
        self.name=name
        self.size=size
        self.obj=obj
        self.adr=0
        self.mask=0
        self.total_size=0
        self.reps=reps
    def sort_key(self):
        return self.size

class wb_blackbox(object):     
   def __init__(self,el):
      self.name = el.attrib['name']
      self.adr_bits = int(el.attrib['addrbits'])
      self.addr_size = 1<<self.adr_bits
      #We do not store "reps" in the instance, as it may depend on the instance!

   def gen_forth(self,ver_id,parent):
      #We do not need to generate any special words for blackboxes
      return ""
   
class wb_block(object):
   def __init__(self,el, vhdl_path, ipbus_path):
     self.vhdl_path=vhdl_path
     self.ipbus_path=ipbus_path
     """
     The constructor takes an XML node that describes the block
     It also calculates the number of registers, and creates
     the description of the record
     """
     self.used = False # Mark the block as not used yet
     self.templ_dict={}
     self.name = el.attrib['name']
     # We prepare the list of address areas
     self.areas=[]
     # We prepare the table for storing the registers.
     self.regs=[]
     self.free_reg_addr=2 # The first free address after ID & VER
     # Prepare the list of subblocks
     self.subblks=[]
     self.n_masters=1
     for child in el.findall("*"):
         # Now for registers we allocate addresses in order
         # We don't to alignment (yet)
        if child.tag == 'creg':
            # This is a control register
           reg = wb_reg(child,self.free_reg_addr)
           self.free_reg_addr += reg.size
           self.regs.append(reg)
        elif child.tag == 'sreg':
            # This is a status register
           reg = wb_reg(child,self.free_reg_addr)
           self.free_reg_addr += reg.size
           self.regs.append(reg)
        elif child.tag == 'subblock':
            # This is a subblock definition
            # We only add it to the list, the addresses can't be allocated yet
           self.subblks.append(child)
        elif child.tag == 'blackbox':
            # This is a blackbox subblock definition
            # We only add it to the list, the addresses can't be allocated yet
           self.subblks.append(child)
        else:
            # Unknown child
           raise Exception("Unknown node in block: "+el.name)
       # After that procedure, the field free_reg_addr contains
       # the length of the block of internal registers
     self.reg_adr_bits = (self.free_reg_addr-1).bit_length()
       
   def analyze(self):
     # Add the length of the local addresses to the list of areas
     self.areas.append(wb_area(self.free_reg_addr,"int_regs",None,1))
     # Scan the subblocks
     for sblk in self.subblks:
        if sblk.tag == 'subblock':
           #@!@ Here we must to correct something! The name of the subblock
           #Is currently lost. We must to decide how it should be passed
           #To the generated code@!@
           bl = blocks[sblk.attrib['type']]
           # If the subblock was not analyzed yet, analyze it now
           if len(bl.areas)==0:
               bl.analyze()
               # Now we can be sure, that it is analyzed, so we can 
               # add its address space to ours.
           # Check if this is a vector of subblocks
           reps = int(sblk.get('reps',1))
           print("reps:"+str(reps))
           # Now recalculate the size of the area, considering possible
           # block repetitions
           addr_size = bl.addr_size * reps
           self.areas.append(wb_area(addr_size,sblk.get('name'),bl,reps))
        elif sblk.tag == 'blackbox':
           # We don't need to analyze the blackbox. We allready have its
           # address area size.
           if not sblk.attrib['type'] in blackboxes:
              blackboxes[sblk.attrib['type']] = wb_blackbox(sblk)
           bl = blackboxes[sblk.attrib['type']]
           reps = int(sblk.get('reps',1))
           print("reps:"+str(reps))
           addr_size = bl.addr_size * reps
           self.areas.append(wb_area(addr_size,sblk.get('name'),bl,reps))
        else:
           raise Exception("Unknown type of subblock")        
     # Now we can calculate the total length of address space
     # We use the simplest algorithm - all blocks are sorted,
     # their size is rounded up to the nearest power of 2
     # They are allocated in order.
     cur_base = 0
     self.areas.sort(key=wb_area.sort_key, reverse=True)
     for ar in self.areas:
         if ar.obj==None:
             # This is the register block
             self.reg_base = cur_base
         ar.adr = cur_base
         ar.adr_bits = (ar.size-1).bit_length()
         ar.total_size = 1 << ar.adr_bits
         # Now we shift the position of the next block
         cur_base += ar.total_size
         print("added size:"+str(ar.total_size))
     self.addr_size = cur_base
     # We must adjust the address space to the power of two
     self.adr_bits = (self.addr_size-1).bit_length()
     self.addr_size = 1 << self.adr_bits
     self.used = True
     # In fact, here we should be able to generate the HDL code
     
     print('analyze: '+self.name+" addr_size:"+str(self.addr_size))

   def add_templ(self,templ_key,value,indent):
       """ That function adds the new text to the dictionary
           used to fill the templates for code generation.
       """
       if templ_key not in self.templ_dict:
          self.templ_dict[templ_key] = ""
       # Now we add all lines from value, providing the appropriate indentation
       for ln in re.findall(r'.*\n?',value)[:-1]:
          if ln != "":
             self.templ_dict[templ_key] += indent*" " + ln            
     
   def gen_vhdl(self,ver_id):
       # To fill the template, we must to set the following values:
       # p_entity, valid_bits
       
       # subblk_busses, signal_ports, signal_decls
       # nof_subblks,
       # subblk_assignments,
       # n_slaves,
       # p_registered,
       # p_addresses, p_masks
       # block_id, block_ver - to verify that design matches the software

       # First - generate code for registers
       # We give empty declaration in case if the block does not contain
       # any registers
       self.add_templ('p_package','',0)
       self.add_templ('p_package_body','',0)
       self.add_templ('signal_decls','',0)
       self.add_templ('register_access','',0)
       self.add_templ('subblk_busses','',0)
       for reg in self.regs:
          #generate 
          reg.gen_vhdl(self)
       # Generate code for connection of all areas
       ar_adr_bits=[]
       ar_addresses=[]
       n_ports=0
       dt = ""
       for ar in self.areas:
           if (ar.reps == 1):
              ar.first_port = n_ports
              ar.last_port = n_ports
              n_ports += 1
              ar_addresses.append(ar.adr)
              ar_adr_bits.append(ar.adr_bits)
              #generate the entity port but not for internal registers
              if ar.obj != None:
                 dt = ar.name+"_wb_m_o : out t_wishbone_master_out;\n"
                 dt += ar.name+"_wb_m_i : in t_wishbone_master_in;\n"
                 self.add_templ('subblk_busses',dt,4)
              #generate the signal assignment
              dt = "wb_m_i("+str(ar.first_port)+") <= "+ar.name+"_wb_m_i;\n"
              dt += ar.name+"_wb_m_o  <= "+"wb_m_o("+str(ar.first_port)+");\n"
              self.add_templ('cont_assigns',dt,2)
           else: 
              # The area is associated with the vector of subblocks
              ar.first_port = n_ports
              ar.last_port = n_ports+ar.reps-1
              n_ports += ar.reps
              #generate the entity port
              dt = ar.name+"_wb_m_o : out t_wishbone_master_out_array(0 to "+str(ar.last_port-ar.first_port)+");\n"
              dt += ar.name+"_wb_m_i : in t_wishbone_master_in_array(0 to "+str(ar.last_port-ar.first_port)+");\n"
              self.add_templ('subblk_busses',dt,4)              
              # Now we have to assign addresses and masks for each subblock and connect the port
              base = ar.adr
              nport = ar.first_port
              for i in range(0,ar.reps):
                 ar_addresses.append(base)
                 base += ar.obj.addr_size
                 ar_adr_bits.append(ar.obj.adr_bits)
                 dt = "wb_m_i("+str(nport)+") <= "+ar.name+"_wb_m_i("+str(i)+");\n"
                 dt += ar.name+"_wb_m_o("+str(i)+")  <= "+"wb_m_o("+str(nport)+");\n"
                 self.add_templ('cont_assigns',dt,2)
                 nport += 1
       #Now generate vectors with addresses and masks
       adrs="("
       masks="("
       for i in range(0,n_ports):
          if i>0:
             adrs+=","
             masks+=","
          adrs +=str(i)+"=>\""+format(ar_addresses[i],"032b")+"\""
          #Calculate the mask
          maskval = ((1<<self.adr_bits)-1) ^ ((1<<ar_adr_bits[i])-1)
          masks +=str(i)+"=>\""+format(maskval,"032b")+"\""
       adrs += ")"
       masks += ")"
       #Generate the register address for
       self.add_templ('block_id_addr',"\""+format(0,"0"+str(self.reg_adr_bits)+"b")+"\"",0)
       self.add_templ('block_ver_addr',"\""+format(1,"0"+str(self.reg_adr_bits)+"b")+"\"",0)
       self.add_templ('reg_adr_bits',str(self.reg_adr_bits),0)
       block_id_val = zlib.crc32(bytes(self.name.encode('utf-8')))
       self.add_templ('block_id',"x\""+format(block_id_val,"08x")+"\"",0)
       self.add_templ('block_ver',"x\""+format(ver_id,"08x")+"\"",0)
       self.add_templ('p_addresses',adrs,0)
       self.add_templ('p_masks',masks,0)
       self.add_templ('p_registered','false',0)
       self.add_templ('nof_subblks',str(n_ports),0)
       self.add_templ('nof_masters',str(self.n_masters),0)
       self.add_templ('p_entity',self.name+"_wb",0)
       # All template is filled, so we can now generate the files
       print(self.templ_dict)
       with open(self.vhdl_path+self.name+"_wb.vhd","w") as fo:
          fo.write(templ_wb(self.n_masters).format(**self.templ_dict))
       with open(self.vhdl_path+self.name+"_pkg.vhd","w") as fo:
          fo.write(templ_pkg.format(**self.templ_dict))

   def gen_ipbus_xml(self,ver_id):
      """ This function generates the address map in the XML format

      """
      res="<node id=\""+self.name+"\">\n"
      # Iterate the areas, generating the addresses
      for ar in self.areas:
         if ar.obj == None:
            #Registers area
            #Add two standard registers - ID and VER
            adr = ar.adr
            res+="  <node id=\"ID\" address=\"0x"+format(adr,"08x")+"\" permission=\"r\"/>\n"
            res+="  <node id=\"VER\" address=\"0x"+format(adr+1,"08x")+"\" permission=\"r\"/>\n"
            #Now add other registers in a loop
            for reg in self.regs:
               res += reg.gen_ipbus_xml(adr)
         else:
            #Subblock or vector of subblocks            
            if ar.reps==1:
               #Single subblock
               res += "  <node id=\""+ar.name+"\""+\
                      " address=\"0x"+format(ar.adr,"08x")+"\""+\
                      " module=\"file://"+ar.obj.name+"_address.xml\"/>\n"
            else:
               #Vector of subblocks
               for nb in range(0,ar.reps):
                  res += "  <node id=\""+ar.name+"["+str(nb)+"]\""+\
                         " address=\"0x"+format(ar.adr+nb*ar.obj.addr_size,"08x")+"\""+\
                         " module=\"file://"+ar.obj.name+"_address.xml\"/>\n"
      res+="</node>\n"
      with open(self.ipbus_path+self.name+"_address.xml","w") as fo:
         fo.write(res)

   def gen_forth(self,ver_id,parent):
      """ This function generates the address map in the Forth format
          The "path" argument informs how the object should be named in the Forth access words
      """
      # Iterate the areas, generating the addresses
      cdefs=""
      for ar in self.areas:
         if ar.obj == None:
            #Registers area
            #Add two standard registers - ID and VER
            adr = ar.adr
            #res+=": "+parent+<node id=\"ID\" address=\"0x"+format(adr,"08x")+"\" permission=\"r\"/>\n"
            #res+=":  <node id=\"VER\" address=\"0x"+format(adr+1,"08x")+"\" permission=\"r\"/>\n"
            #Now add other registers in a loop
            for reg in self.regs:
               cdefs += reg.gen_forth(adr,parent)
         else:
            #Subblock or vector of subblocks            
            if ar.reps==1:
               node = parent+"_"+ar.name
               #Single subblock
               cdefs += ": "+node+" $"+format(ar.adr,'x')+" + "+parent+" ;\n"
               cdefs += ar.obj.gen_forth(ver_id,node)
            else:
               #Vector of subblocks
               node = parent+"#"+ar.name
               #Single subblock
               cdefs += ": "+node+" $"+format(ar.adr,'x')+" + swap $"+format(ar.obj.addr_size,'x')+" * + "+parent+" ;\n" 
               cdefs += ar.obj.gen_forth(ver_id,node)
      return cdefs

