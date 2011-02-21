from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "Vanguard"
	
	def getUrl(self):
		return "https://vesnc.vanguard.com/us/OfxDirectConnectServlet"
	
	def getOrg(self):
		return "The Vanguard Group"
	
	def getFid(self):
		return "1358"
	
	def getBrokerId(self):
		return "vanguard.com"
	
	def getNotes(self):
		return ["Automatically imports 12 months of transactions"]

	def preParseTransaction(self, trans):
		retTrans = False

		# Turn some buys into transferIn
		if trans.keyEqual("buytype", "buy") and (trans.keyContains("memo", "employee asset trnsfr") or trans.keyContains("memo", "employee contribution") or trans.keyContains("memo", "buy electronic bank transfer")):
			trans["type"] = "transfer"
			trans["tferaction"] = "in"

		# Check for special dividends
		if trans.keyEqual("buytype", "buy") and trans.keyContains("memo", "dividend from"):
			trans["type"] = "reinvest"

		# Ignore transfers from money market
		if trans.keyEqual("name", "transfer from money market fund"):
			return True
		elif trans.keyEqual("name", "transfer to money market fund"):
			return True

		return retTrans
