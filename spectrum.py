import visa

rm = visa.ResourceManager()
dev_name = "TCPIP0::169.254.24.65::INSTR"
sa = rm.get_instrument(dev_name)
# need to wait 3 s for a response from the Anritsu Spectrum Analyzer
sa.timeout = 3000

# Read the identificaiton string
stat = sa.write("*IDN?\n")
read = sa.read()
print(stat, read)

read = sa.query("*IDN?\n")
print(read)

# Read a header
head = sa.query(":TRAC:PRE?\n")
print(head)
data = sa.quert(":TRAC:DATA?\n")
print(data)


