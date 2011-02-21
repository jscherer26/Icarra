from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "ShareBuilder"
	
	def getUrl(self):
		return "https://ofx.sharebuilder.com"
	
	def getOrg(self):
		return "ShareBuilder"
	
	def getFid(self):
		return "5575"
	
	def getBrokerId(self):
		return "sharebuilder.com"

