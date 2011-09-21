from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "Fidelity NetBenefits"
	
	def getUrl(self):
		return "https://nbofx.fidelity.com/netbenefits/ofx/download"
	
	def getOrg(self):
		return "nbofx.fidelity.com"
	
	def getFid(self):
		return "8288"
	
	def getBrokerId(self):
		return "nbofx.fidelity.com"
	
	def getNotes(self):
		return []

	def massageTransaction(self, trans):
		pass
