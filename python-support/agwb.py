# Written by Wojciech M. Zabolotny
# wzab01<at>gmail.com.
# The file below implements the access to AGWB supported
# system from Python using a generic interface
# The implementation was prepared so that in case
# of vectors of blocks or registers the minimal
# set of information is duplicated.
# The reference to fields is also natural.
# (See the example at the end)

class agwb_bfd:
    def __init__(self,msb,lsb,is_signed):
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
class agwb_iface(object):
    def __init__(self):
        pass
    def read(self,addr):
        global rf
        print("reading from address:"+hex(addr)+" val="+hex(rf[addr]))
        return rf[addr]
    def write(self,addr,val):
        global rf
        print("writing "+hex(val)+" to address "+hex(addr))
        rf[addr] = val

# Class that calculates the base address for an
# item from a vector
class agwb_mvec(object):
    def __init__(self,iface,base,nitems,margs):
        self._iface = iface
        self._base = base
        self._mclass = margs[0]
        self._margs = None
        if len(margs)>1:
            self._margs = margs[1]
        self._nitems = nitems
    def __getitem__(self,key):
        if key >= self._nitems:
            raise Exception("Access outside the vector")
        if self._margs != None:
            return self._mclass(self._iface,self._base+key*self._mclass._size,self._margs)
        else:
            return self._mclass(self._iface,self._base+key*self._mclass._size)


class agwb_obj(object):
    def __init__(self,iface,base):
        self._base = base
        self._iface = iface
        # Each created object must have its base
    _size = 1
    _fields = {}
    def __getattr__(self,name):
        g = self._fields[name]
        if(len(g)==3):
            return agwb_mvec(self._iface,self._base+g[0],g[1],g[2])
        elif(len(g)==2):
            if len(g[1])==1:
                return g[1][0](self._iface,self._base+g[0])
            else:
                # pass addititional argument to the constructor
                return g[1][0](self._iface,self._base+g[0],g[1][1])

# How we should implement the bitfields?
# Maybe we should pass it when constructing the
# The internal representation in agwb contains the lsb and the msb, so maybe we will
# use them all

class agwb_bf(object):
    def __init__(self,iface,base,bf):
        self._iface = iface
        self._base = base
        self._bf = bf

    def read(self):
        rval = self._iface.read(self._base)
        rval &= self._bf.mask
        rval >>= self._bf.lsb
        if self._bf.sign_mask:
            if rval & self._bf.sign_mask:
                rval -= (self._bf.sign_mask << 1)
        return rval        
        
    def write(self,value):
        # Check if the value to be stored is correct
        if (value < self._bf.vmin) or (value > self._bf.vmax):
            raise Exception("Value doesn't fit in the bitfield")
        # If the bitfield is signed, convert the negative values
        if self._bf.sign_mask:
            if value < 0:
                value += (self._bf.sign_mask << 1)
        print("final value: "+str(value))
        # Read the whole register
        rval = self._iface.read(self._base)
        # Mask the bitfield
        rval |= self._bf.mask
        rval ^= self._bf.mask
        # Shift the new value
        value = value << self._bf.lsb
        value &= self._bf.mask
        rval |= value
        self._iface.write(self._base,rval)

# The class that provides access to the register
class agwb_reg(object):
    def __init__(self,iface,base,bfields={}):
        self._iface = iface
        self._base = base
        self._bfields = bfields
    def read(self):
        return self._iface.read(self._base)
    def write(self,value):
        self._iface.write(self._base,value)
    def __getattr__(self,name):
        return agwb_bf(self._iface,self._base,self._bfields[name])

agwb_creg = agwb_reg
    
class agwb_sreg(agwb_reg):
    def write(self,value):
        raise Exception("Status register at "+hex(self._base)+" can't be written")
    
class c2(agwb_obj):
    _size=3
    _fields={
        'r1':(1,(agwb_sreg,
                 { \
                   't1':agwb_bfd(3,1,False), \
                   't2':agwb_bfd(9,4,True), \
        }))
    }
class c1(agwb_obj):
    _size=100
    _fields={
        'f1':(0,10,(c2,)), \
        'f2':(11,(c2,)), \
        'size':(32,(c2,))
    }

mf=agwb_iface()
a=c1(mf,12)
a.f1[0].r1.t2.write(-3)
