# anritsuSpectrumAnalyzer
Scripts for talking to Anritsu MS2721A over ethernet with pyVisa and vxi11

1. Connect your spectrum analyzer to a local area network (LAN) and use ifconfig (or ipconfig on Windows) to find your LAN DNS, subnet mask, and gateway. 
2. Setup the Anritsu MS2721A with a static IP address by going through Shift->System->Ethernet Config->Manual IP

e.g. IP   169.254.24.65
  Gateway 0.0.0.0
  Subnet  255.255.0.0
  
3. Install the linux device drivers from NI to use the VISA device drivers for a TCP/IP connection. Install pyVisa as well

4. Setup a new VISA resource by running visaconf on the command line and adding a new resouce with the following options:
  a. Some useful alias name (e.g. Anritsu_MS2721A)
  b. Your static ip address that you entered on the spectrum analyzer (e.g. 169.254.24.65)
  c. Check VXI-11 Protocol
  
5. Test you connection in the ipython interactive shell:

 [radio@toucan anritsu_sa]$ ipython
Python 3.6.5 |Anaconda, Inc.| (default, Apr 29 2018, 16:14:56) 
Type 'copyright', 'credits' or 'license' for more information
IPython 6.4.0 -- An enhanced Interactive Python. Type '?' for help.

In [1]: import visa

In [2]: rm = visa.ResourceManager()

In [3]: print(rm.list_resources())
('GPIB0::23::INSTR', 'ASRL1::INSTR', 'ASRL2::INSTR', 'ASRL3::INSTR', 'ASRL4::INSTR', 'TCPIP0::169.254.24.65::INSTR')

In [4]: devname = "TCPIP0::169.254.24.65::INSTR"

In [5]: sa = rm.get_instrument(devname)

In [6]: test = sa.write("*IDN?\n")

In [7]: test = sa.read()

In [8]: print(test)
"Anritsu,MS2721A/25/27,551039,1.71"
