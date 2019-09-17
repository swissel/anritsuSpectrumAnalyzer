import os

if __name__ == '__main__':
	
	dirc = '/home/radio/data/beacon/201910/test_run2'
	nspectra=30
	nruns=120

	for r in range(1, nruns+1, 1):
		os.system("python spectrum.py %s %d %d"%(dirc, r, nspectra))	
