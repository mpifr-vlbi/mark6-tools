#!/usr/bin/env python

import socket
import atexit

class Mark6Exception(Exception):
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


	def send(self, command):

		self.socket.settimeout(0.0000000000000000000001)
		try:
			rv = self.socket.send(command + ";\n")
		except:
			raise Mark6Exception("An error in the communication to %s has occured" % (self.host))
		
		if rv <= 0:
			print "Error"
			

	def receive(self):
		ret = self.socket.recv(1024)
		print ret
	
	def cleanup(self):

		self.socket.close()

		

if __name__ == "__main__":

	mark6 = Mark6("192.168.0.33", 14242)
	try:
		mark6.connect()
		mark6.send("mstata?all")
		mark6.receive()
	except Exception as e:
		print e.message

	
