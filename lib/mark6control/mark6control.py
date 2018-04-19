#!/usr/bin/env python

import socket
import atexit

class Mark6Exception(Exception):
	pass

class Mark6CommandError (Exception):
	pass
	
class Mark6():
	def __init__(self, host, port, timeout=5):

		self.host = host
		self.port = port
		self.socket = None
		self.timeout = timeout
		atexit.register(self.cleanup)

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
	
		try:
			rv = self.socket.send(command)
			if rv <= 0:
				raise Mark6Exception()
			ret = self.__getResponse()
		except:
			raise Mark6Exception("An error in the communication to %s has occured" % (self.host))

		return ret
		
			

	def __getResponse(self):
		'''	
		Fetch response of the last issued command from cplane
		'''

		ret = self.socket.recv(1024)
		return ret
	
	def cleanup(self):

		self.socket.close()

		

if __name__ == "__main__":

	mark6 = Mark6("192.168.0.33", 14242)
	try:
		mark6.connect()
		ret = mark6.sendCommand("mstat?all;")
		print ret
	except Exception as e:
		print e.message

	
