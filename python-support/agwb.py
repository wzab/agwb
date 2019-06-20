#!/usr/bin/python3
""" Written by Wojciech M. Zabolotny
wzab01<at>gmail.com.
The file below implements the access to AGWB supported
system from Python using a generic interface
The implementation was prepared so that in case
of vectors of blocks or registers the minimal
set of information is duplicated.
The reference to fields is also natural.
(See the example at the end)"""

class AwBfd(object):
    def __init__(self, msb, lsb, is_signed):
        self.lsb = lsb
        self.msb = msb
        if is_signed:
            self.sign_mask = 1 << (msb-lsb)
            self.vmin = -self.sign_mask
            self.vmax = self.sign_mask+1
        else:
            self.vmin = 0
            self.vmax = (1 << (msb-lsb+1))-1
            self.sign_mask = 0
        self.mask = ((1 << (msb+1)) - 1) ^ ((1<<lsb)-1)

# Table emulating the register file
rf = 1024 * [int(0),]

# The class iface provides just two methods
# read(address) and write(address,value)
class AwIface(object):
    def __init__(self):
        pass
    def read(self, addr):
        global rf
        print("reading from address:"+hex(addr)+" val="+hex(rf[addr]))
        return rf[addr]
    def write(self, addr, val):
        global rf
        print("writing "+hex(val)+" to address "+hex(addr))
        rf[addr] = val

# Class that calculates the base address for an
# item from a vector
class AwMvec(object):
    def __init__(self, iface, base, nitems, margs):
        self.x__iface = iface
        self.x__base = base
        self.x__class = margs[0]
        self.x__args = None
        if len(margs) > 1:
            self.x__args = margs[1]
        self.x__nitems = nitems
    def __getitem__(self, key):
        if key >= self.x__nitems:
            raise Exception("Access outside the vector")
        if self.x__args != None:
            return self.x__class(self.x__iface, self.x__base+key*self.x__class.x__size, self.x__args)
        return self.x__class(self.x__iface, self.x__base+key*self.x__class.x__size)


class AwObj(object):
    def __init__(self, iface, base):
        self.x__base = base
        self.x__iface = iface
        # Each created object must have its base
    x__size = 1
    _fields = {}
    def __getattr__(self, name):
        g = self._fields[name]
        if len(g) == 3:
            return AwMvec(self.x__iface, self.x__base+g[0], g[1], g[2])
        elif len(g) == 2:
            if len(g[1]) == 1:
                return g[1][0](self.x__iface, self.x__base+g[0])
            # pass addititional argument to the constructor
            return g[1][0](self.x__iface, self.x__base+g[0], g[1][1])

# How we should implement the bitfields?
# Maybe we should pass it when constructing the
# The internal representation in agwb contains the lsb and the msb, so maybe we will
# use them all

class AwBf(object):
    def __init__(self, iface, base, bf):
        self.x__iface = iface
        self.x__base = base
        self.x__bf = bf

    def read(self):
        rval = self.x__iface.read(self.x__base)
        rval &= self.x__bf.mask
        rval >>= self.x__bf.lsb
        if self.x__bf.sign_mask:
            if rval & self.x__bf.sign_mask:
                rval -= (self.x__bf.sign_mask << 1)
        return rval

    def write(self, value):
        # Check if the value to be stored is correct
        if (value < self.x__bf.vmin) or (value > self.x__bf.vmax):
            raise Exception("Value doesn't fit in the bitfield")
        # If the bitfield is signed, convert the negative values
        if self.x__bf.sign_mask:
            if value < 0:
                value += (self.x__bf.sign_mask << 1)
                print("final value: "+str(value))
                # Read the whole register
        rval = self.x__iface.read(self.x__base)
        # Mask the bitfield
        rval |= self.x__bf.mask
        rval ^= self.x__bf.mask
        # Shift the new value
        value = value << self.x__bf.lsb
        value &= self.x__bf.mask
        rval |= value
        self.x__iface.write(self.x__base, rval)

# The class that provides access to the register
class AwReg(object):
    def __init__(self, iface, base, bfields={}):
        self.x__iface = iface
        self.x__base = base
        self.x__bfields = bfields
    def read(self):
        return self.x__iface.read(self.x__base)
    def write(self, value):
        self.x__iface.write(self.x__base, value)
    def __getattr__(self, name):
        return AwBf(self.x__iface, self.x__base, self.x__bfields[name])

AwCreg = AwReg

class AwSreg(AwReg):
    def write(self, value):
        raise Exception("Status register at "+hex(self.x__base)+" can't be written")

class c2(AwObj):
    x__size = 3
    _fields = {
        'r1':(1, (AwSreg,
                 { \
                   't1':AwBfd(3, 1, False), \
                   't2':AwBfd(9, 4, True), \
                 }))
    }
class c1(AwObj):
    x__size = 100
    _fields = {
        'f1':(0, 10, (c2,)), \
        'f2':(11, (c2,)), \
        'size':(32, (c2,))
    }

mf = AwIface()
a = c1(mf, 12)
a.f1[0].r1.t2.write(-3)
