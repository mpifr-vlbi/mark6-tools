#!/usr/bin/env python

import socket
import atexit
from datetime import datetime

class Mark6Exception(Exception):
	pass

class Mark6CommandError (Exception):
	pass
	
class CplaneResponse():

	def __init__(self):
		self.cplaneCode = -1
		self.dplaneCode = -1
		self.baseCommand = ""
		self.type = ""
		self.fields = []

	def parse (self, response):
		
		# strip off semicolon and newline from the end of the response string
		response = response.strip()[:-1]
		# VSIS command
		pos = response.find('=')
		if pos == -1:
			# VSIS query
			pos = response.find('?')
			if pos == -1:
				return None
			self.type = "command"
		else:
			self.type = "query"
		
	
		self.baseCommand = response[1:pos]

		tokens = response[pos+1:].split(":")
		self.cplaneCode = tokens[0].strip()
		self.dplaneCode = tokens[1].strip()
		for token in tokens[2:]:
			self.fields.append(token.strip())
	#	self.fields = tokens[2:]
		
		

class Mark6Module():
	def __init__(self):
		self.group = ""
		self.slot = -1
		self.eMSN = ""
		self.vsn = ""
		self.capacity = -1
		self.datarate = -1
		self.numDisksDiscovered = -1
		self.numDisksRegistered = -1
		self.capacityRemainingGB = 0
		self.freePercentage = 0.0
		self.groupCapacityGB = 0
		self.status1 = ""
		self.status2 = ""
		self.type = ""

	def parseMstatResponse(self, response):
		'''
		parses the reponse received by the mtstat? command and populates
		the class members accordingly.
		Note that this works only for single slot mstat commands e.g. mstat?1
		and will currently fail for mstat?all calls
		'''
		if '-' not in response.fields[0]: 
			self.group = response.fields[0]

		self.slot = int(response.fields[1])
		self.eMSN = response.fields[2].strip()
		self.numDisksDiscovered = int(response.fields[3])
		self.numDisksRegistered = int(response.fields[4])
		if response.fields[5].strip() != "-":
			self.capacityRemainingGB = int(response.fields[5].strip())
		self.groupCapacityGB = int(response.fields[6])
		self.status1 = response.fields[7].strip()
		self.status2 = response.fields[8].strip()
		self.type = response.fields[9].strip()
		
		if self.capacityRemainingGB > 0:
			self.freePercentage =  float(self.capacityRemainingGB) / float(self.groupCapacityGB) * 100.0

		if self.eMSN != "-":
			tokens = self.eMSN.split("/")
			self.vsn = tokens[0]
			self.capacity = tokens[1]
			self.datarate = tokens[2]
		else:
			tokens = ""
                        self.vsn = "unknown"
                        self.capacity = ""
                        self.datarate = ""




class Mark6Scan():
	def __init__(self):
		self.scanNumber = -1
		self.name = ""
		self.size = 0.0
		self.dateCreated = None

		
	
		
class Mark6():
	def __init__(self, host, port, timeout=5, commMethod='cplane'):

		legalCommMethods=['cplane']

		self.host = host
		self.port = port
		self.socket = None
		self.timeout = timeout
		self.commMethod = commMethod
		self.slots = [None,None,None,None]
		self.scans = []
		self.recordingState = {'state': "unknown", 'scanNo': -1, 'scanName': "unknown"}

		if self.commMethod not in legalCommMethods:
			raise Mark6Exception("commMethod must be one of %s" % (str(legalCommMethods)))

		atexit.register(self.__cleanup)

	def connect(self):

		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.settimeout(self.timeout) 
		try:
			self.socket.connect((self.host, self.port))
		except:
			raise Mark6Exception("Failed to connect to %s on port %d." % (self.host, self.port))

		

		
	def sendCommand(self, command):
		'''
		send command to cplane
		'''
		
		command = command.strip()
		# add closing semicolon if not present yet
		if not command[-1] == ";":
			command += ";"
		# add newline
		command += "\n"
	
		if self.commMethod == 'cplane':
			response = CplaneResponse()
		
		try:
			rv = self.socket.send(command)
			if rv <= 0:
				raise Mark6Exception()
			ret = self.__getResponse()
		except:
			raise Mark6Exception("An error in the communication to %s has occured" % (self.host))

		# inspect response
		response.parse(ret)

		return response
		
			

	def __getResponse(self):
		'''	
		Fetch response of the last issued command from cplane
		'''

		BUFF_SIZE= 4096 
		data = b''
		while True:
			part = self.socket.recv(BUFF_SIZE)
			data += part
			if part.strip().endswith(';'):
				break
		return data
		

	
	def __cleanup(self):

		self.socket.close()

	def readScanList(self):
		'''
		obtain the list of scans on the module (list?)
		'''

		ret = self.sendCommand("list?")
		
		
		self.scans = []

		# empty modules
		if int(ret.fields[1]) == 0:
			return
		
		for i in range (1, len(ret.fields), 4):  # skip the group ref field (first)
			
			try:
				scan = Mark6Scan()
				scan.number = int(ret.fields[i])
				scan.name = ret.fields[i+1].strip()
				scan.size = float(ret.fields[i+2])
				scan.dateCreated = datetime.strptime (ret.fields[i+3].strip(), "%Yy%jd%Hh%Mm%Ss")
				self.scans.append(scan)
			except:
				pass	
			
			
	def getScanByName(self, scanName):
		for scan in self.scans:
			if scan.name == scanName.strip():
				return scan
		return None
		

	def readSlotInfo(self):

		for slotId in range(len(self.slots)):
			module = Mark6Module()
			ret = self.sendCommand("mstat?%d" % (slotId+1))
			module.parseMstatResponse(ret)
			self.slots[slotId] = module

	def getRecordingState(self):
		"""
		Get the current recording state by issuing a record? query

		Returns:
			dict: (state, scanNo, scanName)
		"""

		ret = self.sendCommand("record?")
		self.recordingState['state'] = ret.fields[0]
		self.recordingState['scanNo'] = ret.fields[1]
		self.recordingState['scanName'] = ret.fields[2]

		return (self.recordingState)

	def getInputStreams(self):
		"""
		Get the defined input streams by issuing a input_stream? query

		Returns:
			dict: (state, scanNo, scanName)
		"""
		streams = []
		stream = {'label': "", 'format': "", 'payloadSize': 0, 'payloadOffset': 0, 'psnOffset': 0, 'interface': "", 'filterAdress': "", 'port': 0, 'slots': ""}

		ret = self.sendCommand("input_stream?")

		for i in range (0, len(ret.fields), 9):  
			stream = {}
			stream['label'] = ret.fields[i]
			stream['format'] =  ret.fields[i+1]
			stream['payloadSize'] =  int(ret.fields[i+2])
			stream['payloadOffset'] =  int(ret.fields[i+3])
			stream['psnOffset'] =  int(ret.fields[i+4])
			stream['interface'] =  ret.fields[i+5] 
			stream['filterAdress'] =  ret.fields[i+6] 
			stream['port'] =  int(ret.fields[i+7])
			stream['slots'] =  ret.fields[i+8] 

			streams.append(stream)


		return (streams)
			
			

if __name__ == "__main__":

	mark6 = Mark6("192.168.0.33", 14242, commMethod="cplane")

	mark6.connect()
	mark6.readScanList()
	for scan in mark6.scans:
		print (vars(scan))
	
	mark6.readSlotInfo()
	for slot in mark6.slots:
		print (vars(slot))
	
