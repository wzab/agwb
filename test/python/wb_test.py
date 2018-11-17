#!/usr/bin/python3
import cbus
cbus.bus_delay(100)
print("Test the ID")
print ("ID read:"+ hex(cbus.bus_read(0x80)))
print ("VER read:"+ hex(cbus.bus_read(0x81)))
cbus.bus_delay(250)
print("SLAV1 ID read:"+hex(cbus.bus_read(0x00)))
print("SLAV1 VER read:"+hex(cbus.bus_read(0x01)))
cbus.bus_delay(250)
cbus.bus_write(0x2,0xabcdef01)
cbus.bus_delay(250)
print("SLAV1 STATUS read:"+hex(cbus.bus_read(0x03)))
cbus.bus_delay(250)
print("SLAV1 CTRL read:"+hex(cbus.bus_read(0x02)))
cbus.bus_delay(3000)


