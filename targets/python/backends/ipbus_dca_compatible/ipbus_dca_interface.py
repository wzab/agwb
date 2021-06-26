"""
Written by Wojciech M. Zabolotny 2019-2021
added support for extended interface, according
to proposal of Walter F.J. Müller
w.f.j.mueller<at>gsi.de 21.06.2021

"""
import uhal

class IPbusInterface:
    """Class representing interface compatible with interface expected by the agwb."""

    def __init__(self, connection_manager, device):
        """
        Parameters
        ----------
        connection_manager
            Connection manager returned by the uhal.ConnectionManager().
        device
            Name of the device.
        """
        self.device = connection_manager.getDevice(device)
        self.client = self.device.getClient()
        self.rmw_addr = None
        self.rmw_mask = 0
        self.rmw_nval = 0

    def read(self, addr):
        self._check_wbm() # Test for uncompleted writeb_masked
        ret = self.client.read(addr)
        self.client.dispatch()
        return ret

    def read_fifo(self, addr, count):
        self._check_wbm() # Test for uncompleted writeb_masked
        val = self.client.readBlock(addr,count,uhal.BlockReadWriteMode.NON_INCREMENTAL)
        self.client.dispatch()
        return val.value()

    def write(self, addr, val):
        self._check_wbm() # Test for uncompleted writeb_masked
        self.client.write(addr, val)
        self.client.dispatch()

    def writeb(self, addr, val):
        self._check_wbm() # Test for uncompleted writeb_masked
        self.client.write(addr, val)

    def _do_read(self,val):
        self.client.dispatch()
        return val

    def readb(self, addr):
        self._check_wbm() # Test for uncompleted writeb_masked
        ret = self.client.read(addr)
        return lambda : self._do_read(ret)

    def write_masked(self,address,mask,value):
        self._check_wbm() # Test for uncompleted writeb_masked
        self.client.rmw_bits(address, 0xffffffff ^ mask, value & mask )

    def writeb_masked(self,address,mask,value, more=False):
        # Check if another RMW was not completed
        if (self.rmw_addr is not None) and (addr != self.rmw_addr):
            raise Exception("aggregated writeb_masked must use the same address")
        if self.rmw_addr is None:
            self.rmw_addr = address
            self.rmw_mask = mask
            self.rmw_nval = value
        else:
            self.rmw_mask |= mask
            self.rmw_nval &= ~mask
            self.rmw_nval |= (value & mask)
        if not more:
            # Schedule reading of the initial value of the register
            addr = self.rmw_addr
            mask = self.rmw_mask
            nval = self.rmw_nval
            self.client.rmw_bits(address, 0xffffffff ^ mask, nval & mask)
            self.rmw_addr = None

    def _check_wbm(self):
        if (self.rmw_addr is not None):
            raise Exception("Another operation can't be done when writeb_masked is not completed")

    def dispatch(self):
        self.client.dispatch()

