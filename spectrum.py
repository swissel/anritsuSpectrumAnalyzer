import visa
import string
import numpy as np
import matplotlib.pyplot as pyp

def setupSpectrumAnalyzer(sa):
	sa.write("UNITS:POW DBM\n")
	

def readHeader(sa):
	headStr = sa.query("TRAC:PRE?\n")
	print(headStr)	
	
	head = tokenizeHeader(headStr)
	
	# Read the components that have to do with frequencies
	# CENTER_FREQ, RBW, VBW, SPAN, START_FREQ, STOP_FREQ
	freq_names = {'CENTER_FREQ':'center_freq_hz', 'RBW':'rbw_hz', 'VBW':'vbw_hz',
		      'SPAN':'span_hz', 'START_FREQ':'start_freq_hz', 'STOP_FREQ':'stop_freq_hz'}
	freq_units = {'Hz':1, 'KHZ':1e3, 'MHZ':1e6, 'GHZ':1e9}
	for fn in freq_names.keys():
		unit = head[fn][-3:]
		head[freq_names[fn]] = float(head[fn][0:-3]) * freq_units[unit]		
	
	head['units'] = sa.query("UNIT:POW?\n")
	head['npoints'] = float(head['UI_DATA_POINTS'])
	freq_hz = np.linspace(head['start_freq_hz'], head['stop_freq_hz'], head['npoints'])
	return head, freq_hz

def tokenizeHeader(headStr):
	snPos = headStr.find("SN")
	head = {}
	for item in headStr[snPos:].split(',')[:-1]:
		spl = item.split("=")
		if( len(spl) == 2):
			head[spl[0]] = spl[1]
		else:
			print("Error reading header", spl)
	return head

def readData(dataStr):
	# This assumes that the data are all negative (which may not be true!!!)
	# It works if the units are in dBm
	firstNegSign  = dataStr.find("-")
	data = np.array([float(datum) for datum in dataStr[firstNegSign:].split(',')[:-1]])
	return data

rm = visa.ResourceManager()
dev_name = "TCPIP0::169.254.24.65::INSTR"
sa = rm.get_instrument(dev_name)
# need to wait 3 s for a response from the Anritsu Spectrum Analyzer
sa.timeout = 5000

# Read the identificaiton string
stat = sa.write("*IDN?\n")
read = sa.read()
print(stat, read)

read = sa.query("*IDN?\n")
print(read)

# Set up
setupSpectrumAnalyzer(sa)

# Read a header
head, freq_hz = readHeader(sa)
print(head)

data = sa.query("TRAC:DATA?\n")
print(data)
data = readData(data)
print(data, len(data))
print(freq_hz, len(freq_hz))

print("UNITS ", head['units'], "NPOINTS ", head['UI_DATA_POINTS'])

pyp.figure(figsize=(8,16))
pyp.subplot(2,1,1)
pyp.plot(freq_hz/1e6, data)
pyp.xlabel("Frequency (MHz)")
pyp.ylabel("Power (dBm)")
pyp.subplot(2,1,2)
pyp.plot(freq_hz/1e6, data - 10.*np.log10(head['rbw_hz']))
pyp.xlabel("Frequency (MHz)")
pyp.ylabel("Power Spectral Density (dBm/Hz)")
pyp.show()
