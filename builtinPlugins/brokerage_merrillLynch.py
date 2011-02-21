from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "Merrill Lynch"
	
	def getUrl(self):
		return "https://taxcert.mlol.ml.com/eftxweb/access.ofx"
	
	def getOrg(self):
		return "Merrill Lynch &amp; Co., Inc."
	
	def getFid(self):
		return "5550"
	
	def getBrokerId(self):
		return "www.mldirect.ml.com"
