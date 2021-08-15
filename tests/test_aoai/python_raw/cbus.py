#!/usr/bin/python3
# -*- coding: utf-8 -*-

def bus_write(adr,dana):
    cmd="W"+("%8.8x" % adr)+","+("%8.8x" % dana)+"\n"
    wrpip.write(cmd)
    wrpip.flush()
    s=rdpip.readline()
    if s.strip()=="ACK":
       return
    else:
       print("Wrong status returned:"+s.strip())
       return
def bus_read(adr):
    cmd="R"+("%8.8x" % adr)+"\n"
    wrpip.write(cmd)
    wrpip.flush()
    s=rdpip.readline()
    if s.strip()=="ERR":
       print("Error status returned")
       return 0xa5a5a5a5
    return eval("0x"+s)

def bus_delay(time_ns):
    cmd="T"+("%8.8x" % time_ns)+"\n"
    wrpip.write(cmd)
    wrpip.flush()
print("Python controller ready. Start the simulation!\n")
wrpip=open("/tmp/wrpipe","w")
rdpip=open("/tmp/rdpipe","r")

class cbus_iface(object):
  def write(self,address,value):
      return bus_write(address, value)
         
  def read(self,address):
      return bus_read(address)

