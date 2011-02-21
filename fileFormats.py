# Copyright (c) 2006-2010, Jesse Liesch
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE IMPLIED
# DISCLAIMED. IN NO EVENT SHALL JESSE LIESCH BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import math
import re
import sgmlop

from transaction import *
from userprice import *
from positionCheck import *
from brokerage import *
from appGlobal import *

class FileFormat:	
	def __init__(self):
		self.numNew = 0
		self.numOld = 0
		self.newTickers = []
	
	def Guess(self, text):
		return False
	
	def StartParse(self, text, portfolio, status):
		# Count lines
		self.lines = 0
		for i, l in enumerate(text):
			pass
		self.lines = i + 1
		
		return self.Parse(text, portfolio, status)

	def Parse(self, text, portfolio, status):
		pass
	
	def saveTransaction(self, brokerage, portfolio, transaction):
		if brokerage:
			brokerage.massageTransaction(transaction)

		# Check if transaction exists
		if transaction.uniqueId:
			# Check by uniqueId
			res = portfolio.db.select("transactions", where = {"uniqueId": transaction.uniqueId})
			row = res.fetchone()
			notFound = not row
		else:
			# Check by duplicate transaction (not implemented yet)
			notFound = false
		if notFound:
			transaction.save(portfolio.db)
			self.numNew += 1
		else:
			self.numOld += 1
	
	def checkStockInfo(self, portfolio, uniqueId, uniqueIdType, name, ticker):
		# Insert into db if new
		cursor = portfolio.db.select("stockInfo", where = {
			"uniqueId": uniqueId,
			"uniqueIdType": uniqueIdType})
		row = cursor.fetchone()
		if not row:
			# Insert
			ins = portfolio.db.insertOrUpdate("stockInfo", {
				"uniqueId": uniqueId,
				"uniqueIdType": uniqueIdType,
				"secName": name,
				"ticker": ticker},
				on = {"ticker": ticker})
			self.newTickers.append(ticker)
	
ofxTransactions = {
	"buymf": 1,
	"buyoption": 1,
	"buyother": 1,
	"buystock": 1,
	"buydebt": 1,
	"income": 1,
	"invbanktran": 1,
	"invexpense": 1,
	"reinvest": 1,
	"retofcap": 1,
	"sellmf": 1,
	"sellstock": 1,
	"selloption": 1,
	"sellother": 1,
	"selldebt": 1,
	"split": 1,
	"transfer": 1
}

def hasKey(t, key):
	return key in t and len(t[key]) > 0

def keyEqual(t, key, value):
	if not hasKey(t, key):
		return False
	return t[key].upper() == value.upper()

class Ofx(FileFormat):
	def Guess(self, text):
		if text[:9] == "OFXHEADER":
			return True
		return False
	
	def Parse(self, ofx, portfolio, status):
		brokerage = getApp().plugins.getBrokerage(portfolio.brokerage)
		
		class ParsedTransaction(dict):
			def hasKey(self, key):
				return key in self and len(self[key]) > 0
			
			def keyEqual(self, key, value):
				if not self.hasKey(key):
					return False
				return self[key].upper() == value.upper()

			def keyContains(self, key, value):
				if not self.hasKey(key):
					return False
				return self[key].upper().find(value.upper()) != -1
			
			def hasDate(self):
				if self.hasKey("dtposted"):
					return True
				elif self.hasKey("dttrade"):
					return True
				elif self.hasKey("dtsettle"):
					return True
				elif self.hasKey("dtpriceasof"):
					return True
				
				return False
			
			def getDate(self):
				if self.hasKey("dtposted"):
					return Transaction.ofxDateToSql(self["dtposted"])
				elif self.hasKey("dttrade"):
					return Transaction.ofxDateToSql(self["dttrade"])
				elif self.hasKey("dtsettle"):
					return Transaction.ofxDateToSql(self["dtsettle"])
				elif self.hasKey("dtpriceasof"):
					return Transaction.ofxDateToSql(self["dtpriceasof"])
				
				raise Exception

		
		class xmlHandler:
			currentTag = False
			currentData = False
			
			# Which xml depth transactions occur at.  Value is set at invtranlist tag.
			inTranLevel = 1000000
	
			currentTransaction = False
			transactions = []
	
			currentStockInfo = False
			stockInfo = []
			
			currentPosStock = False
			stockPos = []
			availCash = 0
			
			endDate = False
			
			tagCount = 0
	
			def finish_starttag(self, tag, attrs):
				self.tagCount += 1
				status.setStatus(level = 10 + 90 * self.tagCount / self.tags)
				
				if self.inTranLevel:
					self.inTranLevel += 1
				
				tag = tag.strip().lower()

				if self.currentData:
					self.finish_endtag(self.currentTag)
				self.currentTag = tag
				self.currentData = ""
				if tag in ofxTransactions:
					self.currentTransaction = ParsedTransaction()
				elif tag == "stockinfo" or tag == "mfinfo" or tag == "debtinfo" or tag == "otherinfo":
					self.currentStockInfo = {}
				elif tag == "posstock" or tag == "posmf" or tag == "posother":
					self.currentPosStock = {}
				elif tag == "invtranlist":
					self.inTranLevel = 1
				
				#print self.inTranLevel, "start", tag
	
			def finish_endtag(self, tag):
				self.tagCount += 1
				if self.inTranLevel:
					self.inTranLevel -= 1

				tag = tag.strip().lower()
				
				#print self.inTranLevel, "end", tag

				# Handle tag closed but not by /
				if tag != self.currentTag and self.currentTag:
					self.finish_endtag(self.currentTag)
				
				#print "END", tag, "=", self.currentData, self.currentStockInfo
				
				if tag in ofxTransactions:
					#print "transaction =", self.currentTransaction
					self.currentTransaction["type"] = tag.lower()
					self.transactions.append(self.currentTransaction)
					self.currentTransaction = False
				elif self.currentTransaction != False and self.currentData != False:
					self.currentTransaction[tag] = self.currentData
				elif tag == "stockinfo" or tag == "mfinfo" or tag == "debtinfo" or tag == "otherinfo":
					#print "stockinfo = ", self.currentStockInfo
					self.stockInfo.append(self.currentStockInfo)
					self.currentStockInfo = False
				elif self.currentStockInfo != False and self.currentData != False:
					self.currentStockInfo[tag] = self.currentData
				elif tag == "posstock" or tag == "posmf" or tag == "posother":
					#print "posstock = ", self.currentPosStock
					self.stockPos.append(self.currentPosStock)
					self.currentPosStock = False
				elif self.currentPosStock != False and self.currentData != False:
					self.currentPosStock[tag] = self.currentData
				elif tag == "dtstart":
					# Ignore dtstart
					pass
				elif tag == "dtend":
					# Save ending date
					self.endDate = Transaction.ofxDateToSql(self.currentData)
				elif tag == "availcash":
					target.availCash += float(self.currentData)
				elif tag == "marginbalance":
					target.availCash += float(self.currentData)
				elif self.inTranLevel == 1:
					if self.currentTransaction:
						status.addError("Could not handle tag %s #%d from %s" % (tag, self.tagCount, self.currentTransaction))
					else:
						status.addError("Could not handle tag %s #%d" % (tag, self.tagCount))
				
				self.currentTag = False
				self.currentData = False
	
			def handle_data(self, data):
				data = data.strip()
				if data and self.currentTag:
					#print "data =", data
					self.currentData += data

		parser = sgmlop.XMLParser()
		target = xmlHandler()

		# Replace any newlines with an empty string
		ofx = re.sub("\n", "", ofx)
		
		# Search for ! inside an unclosed tag
		# Only for non-letters
		# Ex: <sh!ares1<price> becomes <shares>1<price>
		ofx = re.sub(r"(<[a-zA-z]+)!([a-zA-Z]+)([-_0-9:\[\]\.]+<)", r"\1\2>\3", ofx)

		# Search for ! that should be a closed >
		# Ex: <units!6<unitprice>... becomes <units>6<unitprice>...
		ofx = re.sub(r"(<[a-zA-z]+)!([-_0-9a-zA-Z:\[\]\.]*<)", r"\1>\2", ofx)

		# Search for ! plus any number of whitespace and replace with empty string
		ofx = re.sub("!\s*", "", ofx)
		
		# Replace any space inside tags <xx y> to <xxy>
		count = 1
		while count > 0:
			(ofx, count) = re.subn(r"(<[a-zA-z]*)\s+([-_0-9a-zA-Z:\[\]\.]*>)", r"\1\2", ofx)
		
		# Best attempt at replacing missing tags
		# Ex: <INVBUY   <INVTRAN><FITID>xxx becomes <INVBUY><INVTRAN><FITID>xxx
		count = 1
		while count > 0:
			(ofx, count) = re.subn(r"(<[/a-zA-Z]*)\s*([-_0-9a-zA-Z:\[\]\.]*)\s*<", r"\1>\2<", ofx)
		
		# Count tags
		target.tags = ofx.count("<")
		
		# Parse it
		parser.register(target)
		parser.parse(ofx)
		
		# Update stockInfo table
		ids = {}
		for i in target.stockInfo:
			if "uniqueid" not in i:
				print "no uniqueid in %s" % (i)
			
			# Use ticker first, then secname if not found
			ticker = False
			if "ticker" in i:
				ticker = i["ticker"]
			elif "secname" in i:
				ticker = i["secname"]
			if ticker is False:
				status.addError("no ticker or secname in %s" % i)
				continue
			# Check for duplicate ids
			if i["uniqueid"] in ids:
				raise Exception("Duplicate id: %s for %s, stockInfo=%s" % (i["uniqueid"], i, target.stockInfo))
			ids[i["uniqueid"]] = ticker
			
			# Check for new stock
			self.checkStockInfo(
				portfolio,
				i["uniqueid"],
				i["uniqueidtype"],
				i["secname"],
				ticker)
			
			# Check update of name
			getApp().stockData.checkEmptyName(ticker, i["secname"])

		# Update transactions
		transactionErrors = []
		transactionTickers = {}
		for t in target.transactions:
			#print "t =", t
			# Missing keys and other errors will be caught and logged
			try:
				assert("fitid" in t)
				assert(t.hasDate())

				fees = 0.0
				if t.hasKey("commission"):
					fees += float(t["commission"])
				if t.hasKey("fees"):
					fees += float(t["fees"])
				shares = False
				if t.hasKey("units"):
					shares = float(t["units"])
				
				# Try pre-parsing the transaction 
				if brokerage:
					trans = brokerage.preParseTransaction(t)
					
					# Check if transaction should be ignored
					if trans is True:
						continue
				else:
					trans = False
				
				if trans:
					# Handled by brokerage preParseTransaction
					pass
				elif t.keyEqual("trntype", "credit") or t.keyEqual("trntype", "dep"):
					# Deposit
					trans = Transaction(
						t["fitid"],
						"__CASH__",
						t.getDate(),
						Transaction.deposit,
						t["trnamt"])
				elif t.keyEqual("trntype", "debit"):
					# Withdrawal
					trans = Transaction(
						t["fitid"],
						"__CASH__",
						t.getDate(),
						Transaction.withdrawal,
						math.fabs(float(t["trnamt"])))
				elif t.keyEqual("trntype", "int") or (t.keyEqual("type", "income") and t.keyEqual("incometype", "interest")):
					amount = False
					if "trnamt" in t:
						amount =  math.fabs(float(t["trnamt"]))
					elif "total" in t:
						amount =  math.fabs(float(t["total"]))
					if amount is False:
						raise Exception
	
					# Interest
					trans = Transaction(
						t["fitid"],
						"__CASH__",
						t.getDate(),
						Transaction.dividend,
						amount)
				elif t.keyEqual("trntype", "fee"):
					# Expense
					trans = Transaction(
						t["fitid"],
						"__CASH__",
						t.getDate(),
						Transaction.expense,
						math.fabs(float(t["trnamt"])))
				elif t.hasKey("uniqueid"):
					# Make sure we have info
					if not t["uniqueid"] in ids:
						status.addError("No stock info found for %s" % t["uniqueid"])
						continue
					
					# Stock transaction
					if t.keyEqual("type", "income") and t.keyEqual("incometype", "div"):
						total = float(t["total"])
						if total >= 0:
							trans = Transaction(
								t["fitid"],
								ids[t["uniqueid"]],
								t.getDate(),
								Transaction.dividend,
								total)
						else:
							trans = Transaction(
								t["fitid"],
								ids[t["uniqueid"]],
								t.getDate(),
								Transaction.expense,
								total)
					elif t.keyEqual("type", "income") and t.keyEqual("incometype", "cglong"):
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							Transaction.dividend,
							float(t["total"]),
							subType = Transaction.capitalGainLongTerm)
					elif t.keyEqual("type", "income") and t.keyEqual("incometype", "cgshort"):
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							Transaction.dividend,
							float(t["total"]),
							subType = Transaction.capitalGainShortTerm)
					elif t.keyEqual("type", "retofcap"):
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							Transaction.dividend,
							float(t["total"]),
							subType = Transaction.returnOfCapital)
					elif t.keyEqual("type", "buystock") or t.keyEqual("type", "buyother") or t.keyEqual("type", "buymf") or t.keyEqual("type", "buydebt"):
						if t.hasKey("buytype") and t.keyEqual("buytype", "buytocover"):
							buyType = Transaction.cover
						else:
							buyType = Transaction.buy
	
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							buyType,
							t["total"],
							shares,
							t["unitprice"],
							fees)
					elif t.keyEqual("type", "sellstock") or t.keyEqual("type", "sellother") or t.keyEqual("type", "sellmf") or t.keyEqual("type", "selldebt"):
						if t.hasKey("selltype") and t.keyEqual("selltype", "sellshort"):
							sellType = Transaction.short,
						else:
							sellType = Transaction.sell
						
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							sellType,
							t["total"],
							shares,
							t["unitprice"],
							fees)
					elif t.keyEqual("type", "reinvest"):
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							Transaction.dividendReinvest,
							t["total"],
							shares,
							t["unitprice"],
							fees)
					elif t.keyEqual("type", "invexpense"):
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							Transaction.expense,
							t["total"])
					elif t.keyEqual("type", "transfer") and t.keyEqual("tferaction", "in"):
						if "unitprice" in t:
							pps = t["unitprice"]
						else:
							pps = ""
	
						if "total" in t:
							total = t["total"]
						else:
							total = ""
						
						if shares and pps:
							total = abs(float(shares) * float(pps)) + abs(float(fees))
						
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							Transaction.transferIn,
							total,
							shares,
							pps,
							fees)
					elif t.keyEqual("type", "transfer") and t.keyEqual("tferaction", "out"):
						if "unitprice" in t:
							pps = t["unitprice"]
						else:
							pps = ""
	
						if "total" in t:
							total = t["total"]
						else:
							total = ""
						
						if shares and pps:
							total = abs(float(shares) * float(pps)) + abs(float(fees))
						
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							Transaction.transferOut,
							total,
							shares,
							pps,
							fees)
					elif t.keyEqual("type", "split"):
						if t.hasKey("numerator") and t.hasKey("denominator"):
							value = float(t["numerator"]) / float(t["denominator"])
						elif t.hasKey("newunits") and t.hasKey("oldunits"):
							value = float(t["newunits"]) / float(t["oldunits"])
						else:
							raise Exception
						
						trans = Transaction(
							t["fitid"],
							ids[t["uniqueid"]],
							t.getDate(),
							Transaction.split,
							value,
							fee = fees)
					else:
						raise Exception
				else:
					raise Exception
				
				# Insert or update based on fitid
				if trans:
					self.saveTransaction(brokerage, portfolio, trans)
					transactionTickers[trans.ticker] = True
					if trans.ticker2:
						transactionTickers[trans.ticker2] = True
			except Exception:
				transactionErrors.append(t)
		
		# Remove newTickers if not actually saved
		for ticker in self.newTickers[:]:
			if not ticker in transactionTickers:
				self.newTickers.remove(ticker)

		# Update userPrices
		for u in target.stockPos:
			if hasKey(u, "uniqueid"):
				if not "unitprice" in u:
					status.addError("Could not find unitprice in %s" % u)
					continue
				
				date = Transaction.ofxDateToSql(u["dtpriceasof"])
				price = UserPrice(
					date,
					ids[u["uniqueid"]],
					u["unitprice"])
				price.save(portfolio.db)				
					
				check = PositionCheck(
					date,
					ids[u["uniqueid"]],
					u["units"],
					u["mktval"])
				check.save(portfolio.db)
		
		# Update cash userPrices
		if target.availCash != 0:
			check = PositionCheck(
				target.endDate,
				"__CASH__",
				target.availCash,
				target.availCash)
			check.save(portfolio.db)
		
		if transactionErrors:
			if len(transactionErrors) == 1:
				s = ''
			else:
				s = 's'
			status.addError("Error parsing %d transaction%s" % (len(transactionErrors), s))
			for t in transactionErrors:
				status.addError("Could not parse transaction %s" % t)
		
		return (self.numNew, self.numOld, self.newTickers)

# Ofx2 is based on Ofx
class Ofx2(Ofx):
	def Guess(self, text):
		return text.find("?OFX") != -1 and text.find("?xml") != -1
	
	def Parse(self, text, portfolio, status):
		print "parsing OFX2"
		return Ofx.Parse(self, text, portfolio, status)

class AmeritradeCsv(FileFormat):
	header = "DATE,TRANSACTION ID,DESCRIPTION,QUANTITY,SYMBOL,PRICE,COMMISSION,AMOUNT,SALES FEE,SHORT-TERM RDM FEE,FUND REDEMPTION FEE, DEFERRED SALES CHARGE"
	
	def Guess(self, text):
		if text[:len(self.header)] == self.header:
			return True
		return False
	
	def Parse(self, text, portfolio, status):
		brokerage = getApp().plugins.getBrokerage(portfolio.brokerage)

		def checkDescription(description, str):
			return description[:len(str)].upper() == str.upper()
		
		lines = text.split("\n")
		lastTransaction = False
		lineNumber = 0
		for line in lines:
			if line == self.header or line == "***END OF FILE***" or not line:
				continue
			
			lineNumber += 1
			status.setStatus(level = 10 + 90 * lineNumber / self.lines)
			
			s = line.split(",")
			if len(s) == 12:
				(date, transactionId, description, quantity, symbol, price, commission, amount, salesFee, shortTermRdmFee, fundRedemptionFee, deferredSalesCharge) = s
				date = Transaction.ameritradeDateToSql(date)
				fee = 0.0
				if commission:
					fee += float(commission)
				if salesFee:
					fee += float(salesFee)
				if shortTermRdmFee:
					fee += float(shortTermRdmFee)
				if fundRedemptionFee:
					fee += float(fundRedemptionFee)
				if deferredSalesCharge:
					fee += float(deferredSalesCharge)
				
				# Types:
				# buy: Bought
				# sell: Sold
				# split: STOCK SPLIT
				# deposit: ACCOUNT TRANSFER INCOMING, PERSONAL CHECK RECEIPT, CASH RECEIPTS THIRD PARTY, CASH RECEIPT, CLIENT REQUESTED ELECTRONIC FUNDING RECEIPT
				# withdrawal: CLIENT REQUESTED ELECTRONIC FUNDING DISBURSEMENT
				# dividend: ORDINARY DIVIDEND, LONG TERM GAIN DISTRIBUTION, QUALIFIED DIVIDEND
				# dividendReinvest: DIVIDEND REINVESTMENT
				# dividend: (__CASH__ if no ticker, else dividend) DIVIDEND OR INTEREST
				# dividend (__CASH__): FREE BALANCE INTEREST ADJUSTMENT
				# expense: QUARTERLY MAINTENANCE FEE
				# ignore: JOURNAL ENTRY, RECEIVE & DELIVER, MONEY MARKET PURCHASE, MONEY MARKET REDEMPTION
				
				transaction = False
				if checkDescription(description, "journaley entry") or checkDescription(description, "receive & deliver") or checkDescription(description, "money market purchase") or checkDescription(description, "money market redemption"):
					continue
				elif checkDescription(description, "account transfer incoming") or checkDescription(description, "personal check receipt") or checkDescription(description, "cash receipts third party"):
					transaction = Transaction(transactionId, "__CASH__", date, Transaction.deposit, amount, fee = fee)
				elif checkDescription(description, "bought"):
					transaction = Transaction(transactionId, symbol, date, Transaction.buy, amount, quantity, price, fee = fee)
				elif checkDescription(description, "sold"):
					transaction = Transaction(transactionId, symbol, date, Transaction.sell, amount, -abs(float(quantity)), price, fee = fee)
				elif checkDescription(description, "dividend reinvestment (cash debit)"):
					# First part of dividend reinvest
					transaction = Transaction(transactionId, symbol, date, Transaction.dividendReinvest, amount, fee = fee)
				elif checkDescription(description, "dividend reinvestment (shares)"):
					# Second part of dividend reinvest
					# Read transaction from db and update
					res = portfolio.db.select("transactions", where = {
						"type": Transaction.dividendReinvest,
						"ticker": symbol,
						"date": date})					
					row = res.fetchone()
					if not row:
						status.addError("dividend reinvest but no previous")
					else:
						transaction = Transaction(
							row["uniqueId"],
							row["ticker"],
							row["date"],
							row["type"],
							row["total"],
							row["shares"],
							row["pricePerShare"],
							row["fee"])
						transaction.setType(Transaction.buy)
						transaction.setShares(quantity)
						if transaction.shares > 0:
							transaction.setPricePerShare(abs(transaction.total / transaction.shares))
				elif checkDescription(description, "ordinary dividend") or checkDescription(description, "long term gain distribution") or checkDescription(description, "qualified dividend"):
					transaction = Transaction(transactionId, symbol, date, Transaction.dividend, amount, fee = commission + salesFee + shortTermRdmFee + fundRedemptionFee + deferredSalesCharge)
				elif checkDescription(description, "money market interest") or checkDescription(description, "free balance interest adjustment"):
					if quantity > amount:
						amount = quantity
					transaction = Transaction(transactionId, "__CASH__", date, Transaction.dividend, amount, fee = commission + salesFee + shortTermRdmFee + fundRedemptionFee + deferredSalesCharge)
				elif checkDescription(description, "stock split"):
					transaction = Transaction(transactionId, symbol, date, Transaction.stockDividend, amount, shares = quantity, fee = commission + salesFee + shortTermRdmFee + fundRedemptionFee + deferredSalesCharge)
				
				if transaction:
					self.checkStockInfo(portfolio, transaction.uniqueId, "AMERITRADE", "", transaction.ticker)
					
					self.saveTransaction(brokerage, portfolio, transaction)
					lastTransaction = transaction
				else:
					status.addError("Missed line: " + line)
			else:
				status.addError("Missed line: " + line)
				
		return (self.numNew, self.numOld, self.newTickers)
