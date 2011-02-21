from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "Wells Fargo Investments"
	
	def getUrl(self):
		return "https://invmnt.wellsfargo.com/inv/directConnect"
	
	def getOrg(self):
		return "wellsfargo.com"
	
	def getFid(self):
		return "10762"
	
	def getBrokerId(self):
		return "wellsfargo.com"

	def preParseTransaction(self, trans):
		if "type" in trans and "incometype" in trans:
			if trans["type"] == 'income' and trans["incometype"] == 'INTEREST':
				trans["trntype"] = "int"
		
			if "dttrade" in trans and not "dtposted" in trans:
				trans["dtposted"] = trans["dttrade"]
			if "total" in trans and not "trnamt" in trans:
				trans["trnamt"] = trans["total"]
		
		# Turn some invbanktrn into deposits
		if trans["type"] == "invbanktran" and trans.keyContains("memo", "contribution"):
			trans["trntype"] = "dep"
		elif trans["type"] == "invbanktran" and trans.keyEqual("trntype", "other") and trans.keyContains("memo", "transfer cash balance"):
			trans["trntype"] = "dep"
		
		return False

