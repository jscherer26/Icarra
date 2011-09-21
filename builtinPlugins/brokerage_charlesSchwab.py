from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "Charles Schwab"
	
	def getUrl(self):
		return "https://ofx.schwab.com/cgi_dev/ofx_server"
	
	def getOrg(self):
		return "ISC"
	
	def getFid(self):
		return "5104"
	
	def getBrokerId(self):
		return "Schwab.com"
	
	def getNotes(self):
		return []

	def massageTransaction(self, trans):
		pass
