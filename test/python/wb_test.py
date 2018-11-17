#!/usr/bin/python3
import cbus
cnt=0x80
mem=0x0
mem_mod=0x80000000
cbus.bus_delay(100)
print("Test the ID")
print ("ID read:"+ hex(cbus.bus_read(cnt)))
cbus.bus_delay(250)
print("SLAV1 ID read:"+hex(cbus.bus_read(0x00)))
cbus.bus_delay(250)
cbus.bus_delay(3000)


