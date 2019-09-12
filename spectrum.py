import string
import numpy as np
import matplotlib.pyplot as pyp
import time
import datetime
import pandas as pd
import visa
import sys

class SpectrumAnalyzer():

    def __init__(self, dirc, run=None, freqband=None, boxno=None, pol=None, weather=None, daynight=None, before_stage1_attenfilter=None, after_stage2_attenfilter=None, comments=None):

        # directory where you will store the run
        self.dirc = dirc
        if(dirc[-1] != "/"):  # make sure there's a slash at the end
            self.dirc = self.dirc + "/"

        # setup some dictionaries for saving data
        # these will be indexed by the date-time
        self.headStream = {}
        self.dataStream = {}

        self.getCommonInfo(run=run, freqband=freqband, boxno=boxno, pol=pol, weather=weather, daynight=daynight, before_stage1_attenfilter=before_stage1_attenfilter, after_stage2_attenfilter=after_stage2_attenfilter, comments=comments)

        self.setupSpectrumAnalyzer()

    def getCommonInfo(self, run=None, freqband=None, boxno=None, pol=None, weather=None, daynight=None, before_stage1_attenfilter=None, after_stage2_attenfilter=None, comments=None):
        # Store the settings of the run.
        # We want to store the start date and time
        # UHF/VHF boxes, antennas, polarization
        # Any comments on the run setup

        # time stamp
        self.timestamp = time.time()
        self.datestr = datetime.datetime.fromtimestamp(
            self.timestamp).strftime("%Y-%m-%d_%H-%M-%S")
        # store run number, if given
        # if not, then check this file folder and make sure you're not overwriting a run
        self.run = run
        # Add this later
        # if( self.run == None):
        #    runsInDirc = glob.glob(self.dirc + "run[0-9]+.*.hdf5")
        #    print runsInDirc
        if(self.run == None):
            self.run = int(input("Run Number? (Integer please)"))

        # use the run number and date-time to name the output file
        self.outputFileName = "specanalyzer_run%d_%s.hdf5" % (self.run, self.datestr)
        print("File name %s" % self.outputFileName)

        # Now store the prompts
        # Frequency band -- either UHF or VHF
        self.freqband = freqband
        if((self.freqband == None) or (self.freqband != 'UHF' and self.freqband != 'VHF')):
            self.freqband = input("Frequency band? (UHF/VHF)")

        # Sets of Boxes -- either 1 or 2
        self.boxno = boxno
        if((self.boxno == None) or (self.boxno != 1 and self.boxno != 2)):
            self.boxno = int(float(input("Box No.? (1/2)")))

        # Attenuation or filters
        # Before stage1
        self.before_stage1_attenfilter = before_stage1_attenfilter
        if (self.before_stage1_attenfilter == None):
            self.before_stage1_attenfilter = input(
                "Attenuation or Filters before Stage 1? ( e.g. 0 dB, SLP-80)")

        # After Stage2
        self.after_stage2_attenfilter = after_stage2_attenfilter
        if (self.after_stage2_attenfilter == None):
            self.after_stage2_attenfilter = input(
                "Attenuation or Filters after Stage 2? ( e.g. 10 dB, 450 MHz Notch)")


        # Polarization -- either H or V
        self.pol = pol
        if((self.pol == None) or (self.pol != 'H' and self.pol != 'V' and self.pol != 'None')):
            self.pol = input("Polarization? (H/V/None)")
        # Weather -- whatever you like
        self.weather = weather
        if((self.weather == None)):
            self.weather = input("Weather?")
        # Day / Night
        self.daynight = daynight
        if(self.daynight == None):
            self.daynight = input("Day or Night? (Day/Night)")
        # Comments
        self.comments = comments
        if(self.comments == None):
            self.comments = input("Any other comments?")

    def setupSpectrumAnalyzer(self):
        # Setup the spectrum analyzer
        self.rm = visa.ResourceManager()
        self.dev_name = "TCPIP0::169.254.24.65::INSTR"
        self.sa = self.rm.get_instrument(self.dev_name)
        # need to wait 3 s for a response from the Anritsu Spectrum Analyzer
        self.sa.timeout = 300000

        self.sa.write("UNITS:POW DBM\n")
        self.rbw = float(self.sa.query("SENS:BAND:RES?"))
        self.vbw = float(self.sa.query("SENS:BAND:VID?"))
        self.span = float(self.sa.query("SENS:FREQ:SPAN?"))
        self.sweep_time = 2.5*self.span/(self.rbw*self.vbw)
        print("Setting minimum sweep time: ",
              self.sa.query("SENS:SWE:TIME?"), "s")
        self.sa.write("SENS:SWETIME %3e6f" % self.sweep_time)
        print("....If this seems long, reduce your span (%3.3e MHz) or increase your RBW (%3.3e kHz)/VBW (%3.3e kHz)." %
              (self.span/1e6, self.rbw/1e3, self.vbw/1e3))
        print("....The minimum sweep time is = 2.5 * span / (RBW * VBW)")
        self.ntraces = float(self.sa.query("SENS:AVER:COUN?"))
        self.spec_time = self.sweep_time * self.ntraces
        print("Setting time between spectra to sweeptime ( %3.3e ms)x ntraces (%d) = %3.3e s " % (
            self.sweep_time/1e3, self.ntraces, self.spec_time))

    def readHeader(self):
        headStr = self.sa.query("TRAC:PRE?\n")
        head = self.tokenizeHeader(headStr)

        # Read the components that have to do with frequencies
        # CENTER_FREQ, RBW, VBW, SPAN, START_FREQ, STOP_FREQ
        freq_names = {'CENTER_FREQ': 'center_freq_hz', 'RBW': 'rbw_hz', 'VBW': 'vbw_hz',
                      'SPAN': 'span_hz', 'START_FREQ': 'start_freq_hz', 'STOP_FREQ': 'stop_freq_hz'}
        freq_units = {'Hz': 1, 'KHZ': 1e3, 'MHZ': 1e6, 'GHZ': 1e9}
        for fn in freq_names.keys():
            unit = head[fn][-3:]
            head[freq_names[fn]] = float(head[fn][0:-3]) * freq_units[unit]

        head['units'] = self.sa.query("UNIT:POW?\n")
        head['npoints'] = int(float(head['UI_DATA_POINTS']))
        # calculate the sweep time
        head['sweep_time_s'] = 2.5*head['span_hz'] / \
            (head['rbw_hz'] * head['vbw_hz'])
        #print("MIN. SWEEP TIME: ", head['sweep_time_s'])
        freq_hz = np.linspace(head['start_freq_hz'],
                              head['stop_freq_hz'], head['npoints'])
        print('%d Spectrum at '%(len(self.headStream)+1), head['DATE'])
        return head, freq_hz

    def tokenizeHeader(self, headStr):

        # split up header string at the commas
        # start after the #NUMBER_OF_BYTES part at the beginning
        # the first key tends to be SN, so we find its position and start from there
        snPos = headStr.find("SN")
        head = {}
        # drop the last bit after the comma, since the string ends in a comma
        for item in headStr[snPos:].split(',')[:-1]:
            spl = item.split("=")
            if(len(spl) == 2):
                head[spl[0]] = spl[1]
            else:
                print("Error reading header", spl)
        return head

    def readData(self):
        # This assumes that the data are all negative (which may not be true!!!)
        # It works if the units are in dBm

        dataStr = self.sa.query("TRAC:DATA?\n")
        firstNegSign = dataStr.find("-")
        data = np.array([float(datum)
                         for datum in dataStr[firstNegSign:].split(',')[:-1]])
        return data

    def readSpectrum(self):
        # Read a header
        head, freq_hz = self.readHeader()
        data = self.readData()

        # these are the latest values
        self.head = head
        self.data = data
        self.freq_hz = freq_hz

        # store to the stream
        self.headStream[head['DATE']] = head
        self.dataStream[head['DATE']] = {'power_dBm': data, 'freq_hz': freq_hz}

        return head, freq_hz, data

    def readSpectrogram(self, nspectra=10):

        for i in range(nspectra):
            # read a spectrum
            head, freq_hz, data = self.readSpectrum()
            # wait for spectrum to reset
            # time.sleep(self.spec_time)

    def writeSpectrum(self):
        print("Writing data to %s%s" % (self.dirc, self.outputFileName))

        # Store all the header information in a dataframe
        self.run_header = pd.DataFrame({'run': self.run, 'timestamp': self.timestamp, 'filename': self.outputFileName,
                                        'freqband': self.freqband, 'pol': self.pol, 'weather': self.weather,
                                        'daynight': self.daynight, 'comments': self.comments,
                                        'boxno': self.boxno, 
                                        'before_stage1_attenfilter':self.before_stage1_attenfilter,
                                        'after_stage2_attenfilter':self.after_stage2_attenfilter
                                        }, index=[0])

        #print(("Writing data to %s%s" % (self.dirc, self.outputFileName)))
        self.run_header.to_hdf(self.dirc + self.outputFileName,
                               key='run_header', mode='a', )
        self.headerStored = True

        headDf = pd.DataFrame(self.headStream)
        dataDf = pd.DataFrame(self.dataStream)
        headDf.to_hdf(self.dirc + self.outputFileName, key='header', mode='a')
        dataDf.to_hdf(self.dirc + self.outputFileName, key='spectra', mode='a')

    def plotSpectrum(self):
        pyp.figure(figsize=(8, 16))
        pyp.subplot(2, 1, 1)
        pyp.title(self.head['DATE'])
        pyp.plot(self.freq_hz/1e6, self.data)
        pyp.xlabel("Frequency (MHz)")
        pyp.ylabel("Power (dBm)")
        pyp.subplot(2, 1, 2)
        pyp.plot(self.freq_hz/1e6, self.data - 10. *
                 np.log10(self.head['rbw_hz']/1e6))
        pyp.xlabel("Frequency (MHz)")
        pyp.ylabel("Power Spectral Density (dBm/MHz)")
        pyp.show()

    def plotSpectrogram(self):
        pyp.figure(figsize=(8, 16))
        pyp.subplot(2, 1, 1)
        pyp.title(self.datestr)
        timestamps = list(self.headStream)

        # Get all the time stamps
        datestrf = '%Y-%m-%d-%W-%H-%M-%S'
        datetimestamps = [datetime.datetime.strptime(
            ts, datestrf) for ts in timestamps]

        starttime = datetimestamps[0]
        tdelta = np.zeros(len(datetimestamps))
        for i, ts in enumerate(datetimestamps):
            tdelta[i] = (ts - starttime).total_seconds()

        # Setup the spectrogram array
        spectrogram = np.zeros((len(datetimestamps), len(
            self.dataStream[timestamps[0]]['power_dBm'])))
        for i, dt in enumerate(tdelta):
            timestamp = timestamps[i]
            spec = self.dataStream[timestamp]['power_dBm']
            spectrogram[i, :] = spec

        # make a mesh for plotting
        freqmesh, timemesh = np.meshgrid(
            self.dataStream[timestamp]['freq_hz']/1e6, tdelta)
        # plot!
        pyp.pcolormesh(freqmesh, timemesh, spectrogram)
        pyp.xlabel("Frequency (MHz)")
        pyp.ylabel("Time(s)")
        pyp.title(starttime.strftime(format=datestrf))
        cbar = pyp.colorbar()
        cbar.set_label("Power (dBm)")

        # plot!
        pyp.subplot(2, 1, 2)
        pyp.pcolormesh(freqmesh, timemesh, spectrogram -
                       10.*np.log10(self.rbw/1e6))
        pyp.xlabel("Frequency (MHz)")
        pyp.ylabel("Time(s)")
        pyp.title(starttime.strftime(format=datestrf))
        cbar = pyp.colorbar()
        cbar.set_label("Power (dBm/MHz)")

    def readWritePlotSpectrogram(self, nspectra=10):
	# now some diagonostics
        self.readSpectrogram(nspectra)
	
        print("Writing the spectra.")
        self.writeSpectrum()

        #print("Closing the spectrum analyzer")
        #self.sa.close()

        print("Plotting the spectrogram")        
        self.plotSpectrogram()
        pyp.show()

if __name__ == '__main__':

	dirc = '/home/radio/data/beacon/201910/'
	if( len(sys.argv) > 1):
		dirc = sys.argv[1]
	
        # Setup
	specAnal = SpectrumAnalyzer(dirc=dirc)

	# Read the identificaiton string
	stat = specAnal.sa.write("*IDN?\n")
	read = specAnal.sa.read()
	print(stat, read)

	idn = specAnal.sa.query("*IDN?\n")
	print(idn)

	# read the data -- runs for about 5 minutes with 30 spectra
	# specAnal.readSpectrum()
	specAnal.readSpectrogram(nspectra=30)
	specAnal.sa.close()
	specAnal.writeSpectrum()
	# specAnal.plotSpectrum()
	specAnal.plotSpectrogram()
	pyp.show()
