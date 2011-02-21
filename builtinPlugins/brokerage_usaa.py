from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "USAA"
	
	def getUrl(self):
		return "https://service2.usaa.com/ofx/OFXServlet"
	
	def getOrg(self):
		return "USAA"
	
	def getFid(self):
		return "24592" # or 24591 is the bank
	
	def getBrokerId(self):
		return "USAA.COM"
	
	def getNotes(self):
		return []

	def preParseTransaction(self, trans):
		retTrans = False
		return retTrans
