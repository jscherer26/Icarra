from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "Fidelity"
	
	def getUrl(self):
		return "https://ofx.fidelity.com/ftgw/OFX/clients/download"
	
	def getOrg(self):
		return "fidelity.com"
	
	def getFid(self):
		return "7776"
	
	def getBrokerId(self):
		return "fidelity.com"
	
	def getNotes(self):
		return ["Set username to your fidelity Customer ID", "Automatically imports 3 months of transactions"]

	def massageTransaction(self, trans):
		# Use __CASH__ if ticker is FCFXX (money market)
		if trans.ticker.upper() == "FCFXX":
			trans.ticker = "__CASH__"
