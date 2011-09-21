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
		self.transactions = []
	
	def Guess(self, text):
		return False
	
	def StartParse(self, text, portfolio, status):
		# Count lines
		self.lines = 0
		for i, l in enumerate(text):
			pass
		self.lines = i + 1
		
		self.Parse(text, portfolio, status)
		
		if portfolio:
			return self.saveTransactions(portfolio)
		else:
			tickers = {}
			for t in self.transactions:
				tickers[t.ticker] = True
			return (len(self.transactions), 0, tickers.keys())

	def Parse(self, text, portfolio, status):
		'Must be overloaded'
		raise Exception("Parse is not overloaded!")
	
	def saveTransaction(self, brokerage, portfolio, transaction):
		if brokerage:
			brokerage.massageTransaction(transaction)
		self.transactions.append(transaction)
	
	def saveTransactions(self, portfolio):
		numNew = 0
		numOld = 0
		newTickers = []
		
		# Count of number of matching transactions with same id
		# Key is transaction, value is count
		noIdCount = {}
		
		portfolio.db.beginTransaction()
	
		for transaction in self.transactions:
			# Check if transaction exists
			if transaction.uniqueId:
				# Check by uniqueId
				res = portfolio.db.select("transactions", where = {"uniqueId": transaction.uniqueId})
				row = res.fetchone()
				notFound = not row
			else:
				# This transaction does not have a unique id
				# Check by duplicate transactions
				# If identical transactions are not found do not save
				# Otherwise assign a unique id
				
				# Build noIdCount for this transaction only once
				if not transaction in noIdCount:
					# Count how many transactions there are that are equal to this not counting uniqueId
					where = transaction.getSaveData()
					del where["uniqueId"]
					del where["edited"]
					del where["deleted"]
					res = portfolio.db.select("transactions", where = where)
					if res.fetchone():
						# Count how many matching transactions
						noIdCount[transaction] = 1
						while res.fetchone():
							noIdCount[transaction] += 1
					else:
						# No matching transactions
						noIdCount[transaction] = 0
				
				if noIdCount[transaction] == 0:
					# New data, assign unique id
					notFound = True
					transaction.uniqueId = "__" + portfolio.portPrefs.getTransactionId() + "__"
				else:
					notFound = False
					noIdCount[transaction] -= 1
	
			if notFound:
				transaction.save(portfolio.db)
				numNew += 1
			else:
				numOld += 1
		
		portfolio.db.commitTransaction()

		return (numNew, numOld, newTickers)
	
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
	"stmttrn": 1,
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
			
			def getKey(self, key):
				if self.hasKey(key):
					return self[key]
				else:
					return ""
			
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
				if status:
					status.setStatus(level = 10 + 90 * self.tagCount / self.tags)
				
				if self.inTranLevel:
					self.inTranLevel += 1
				
				tag = tag.strip().lower()

				if self.currentData:
					self.finish_endtag(self.currentTag)
				self.currentTag = tag
				self.currentData = ""
				if tag in ofxTransactions and self.currentTransaction is False:
					# Create new transaction if not already in a transaction
					self.currentTransaction = ParsedTransaction()
					self.currentTransaction["type"] = tag.lower()
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
				
				if tag in ofxTransactions and self.currentTransaction["type"] == tag:
					#print "transaction =", self.currentTransaction
					if not self.currentTransaction:
						if status:
							status.addError("No transaction for tag " + tag)
						return
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
					if status:
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
				status.addError("no uniqueid in %s" % (i))
			
			# Use ticker first, then secname if not found
			ticker = False
			if "ticker" in i:
				ticker = i["ticker"]
			elif "secname" in i:
				ticker = i["secname"]
			if ticker is False:
				if status:
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
					if t.keyEqual("name", "Interest Paid"):
						# ING Direct
						thisType = Transaction.dividend
					else:
						thisType = Transaction.deposit
					# Deposit
					trans = Transaction(
						t["fitid"],
						"__CASH__",
						t.getDate(),
						thisType,
						t["trnamt"])
				elif t.keyEqual("trntype", "debit") or t.keyEqual("trntype", "check") or t.keyEqual("trntype", "atm"):
					if portfolio.isBank() and t.keyEqual("trntype", "debit"):
						# Withdrawal
						# Try to get name of expense
						ticker = "__CASH__"
						if t.hasKey("name"):
							ticker = t.getKey("name")
						
						trans = Transaction(
							t["fitid"],
							ticker,
							t.getDate(),
							Transaction.withdrawal,
							math.fabs(float(t["trnamt"])))
					else:
						# Investment withdrawal
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
				elif t.keyEqual("trntype", "payment"):
					# BofA
					if t.hasKey("name"):
						thisTicker = t.getKey("name")
					else:
						thisTicker = "__CASH__"
					# Withdrawal
					trans = Transaction(
						t["fitid"],
						thisTicker,
						t.getDate(),
						Transaction.withdrawal,
						math.fabs(float(t["trnamt"])))
				elif t.keyEqual("type", "invbanktran") and t.keyEqual("trntype", "other"):
					# Deposit if > 0, withdrawal if < 0
					amount = False
					if "trnamt" in t:
						amount =  math.fabs(float(t.getKey("trnamt")))
					elif "total" in t:
						amount =  math.fabs(float(t.getKey("total")))
					if amount is False:
						print "no amount", amount, t
						raise Exception
	
					# Deposit
					if amount > 0:
						trans = Transaction(
							t["fitid"],
							"__CASH__",
							t.getDate(),
							Transaction.deposit,
							amount)
					elif amount < 0:
						trans = Transaction(
							t["fitid"],
							"__CASH__",
							t.getDate(),
							Transaction.withdrawal,
							amount)
				elif t.hasKey("uniqueid"):
					# Make sure we have info
					if t["uniqueid"] in ids:
						t["ticker"] = ids[t["uniqueid"]]
					else:
						if status:
							status.addError("No stock info found for %s" % t["uniqueid"])
						continue
					
					# Stock transaction
					if t.keyEqual("type", "income") and t.keyEqual("incometype", "div"):
						total = float(t["total"])
						if total >= 0:
							trans = Transaction(
								t["fitid"],
								t["ticker"],
								t.getDate(),
								Transaction.dividend,
								total)
						else:
							trans = Transaction(
								t["fitid"],
								t["ticker"],
								t.getDate(),
								Transaction.expense,
								total)
					elif t.keyEqual("type", "income") and t.keyEqual("incometype", "cglong"):
						trans = Transaction(
							t["fitid"],
							t["ticker"],
							t.getDate(),
							Transaction.dividend,
							float(t["total"]),
							subType = Transaction.capitalGainLongTerm)
					elif t.keyEqual("type", "income") and t.keyEqual("incometype", "cgshort"):
						trans = Transaction(
							t["fitid"],
							t["ticker"],
							t.getDate(),
							Transaction.dividend,
							float(t["total"]),
							subType = Transaction.capitalGainShortTerm)
					elif t.keyEqual("type", "retofcap"):
						trans = Transaction(
							t["fitid"],
							t["ticker"],
							t.getDate(),
							Transaction.dividend,
							float(t["total"]),
							subType = Transaction.returnOfCapital)
					elif t.keyEqual("type", "buystock") or t.keyEqual("type", "buyother") or t.keyEqual("type", "buymf") or t.keyEqual("type", "buydebt"):
						if t.hasKey("buytype") and t.keyEqual("buytype", "buytocover"):
							buyType = Transaction.buyToClose
						else:
							buyType = Transaction.buy
	
						trans = Transaction(
							t["fitid"],
							t["ticker"],
							t.getDate(),
							buyType,
							t["total"],
							shares,
							t["unitprice"],
							fees)
					elif t.keyEqual("type", "sellstock") or t.keyEqual("type", "sellother") or t.keyEqual("type", "sellmf") or t.keyEqual("type", "selldebt"):
						if t.hasKey("selltype") and t.keyEqual("selltype", "sellshort"):
							sellType = Transaction.sellToOpen,
						else:
							sellType = Transaction.sell
						
						trans = Transaction(
							t["fitid"],
							t["ticker"],
							t.getDate(),
							sellType,
							t["total"],
							shares,
							t["unitprice"],
							fees)
					elif t.keyEqual("type", "reinvest"):
						trans = Transaction(
							t["fitid"],
							t["ticker"],
							t.getDate(),
							Transaction.dividendReinvest,
							t["total"],
							shares,
							t["unitprice"],
							fees)
					elif t.keyEqual("type", "invexpense"):
						trans = Transaction(
							t["fitid"],
							t["ticker"],
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
							t["ticker"],
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
							t["ticker"],
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
							t["ticker"],
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

		# Update userPrices
		for u in target.stockPos:
			if hasKey(u, "uniqueid"):
				if not "unitprice" in u:
					if status:
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
		
		if status and transactionErrors:
			if len(transactionErrors) == 1:
				s = ''
			else:
				s = 's'
			status.addError("Error parsing %d transaction%s" % (len(transactionErrors), s))
			for t in transactionErrors:
				status.addError("Could not parse transaction %s" % t)

# Ofx2 is based on Ofx
class Ofx2(Ofx):
	def Guess(self, text):
		return text.find("?OFX") != -1 and text.find("?xml") != -1
	
	def Parse(self, text, portfolio, status):
		return Ofx.Parse(self, text, portfolio, status)

class AmeritradeCsv(FileFormat):
	# Two known file formats
	header1 = "DATE,TRANSACTION ID,DESCRIPTION,QUANTITY,SYMBOL,PRICE,COMMISSION,AMOUNT,SALES FEE,SHORT-TERM RDM FEE,FUND REDEMPTION FEE, DEFERRED SALES CHARGE"
	header2 = "DATE,TRANSACTION ID,DESCRIPTION,QUANTITY,SYMBOL,PRICE,COMMISSION,AMOUNT,NET CASH BALANCE,SALES FEE,SHORT-TERM RDM FEE,FUND REDEMPTION FEE, DEFERRED SALES CHARGE"
	
	def Guess(self, text):
		if text.startswith(self.header1):
			return True
		elif text.startswith(self.header2):
			return True
		else:
			return False
	
	def Parse(self, text, portfolio, status):
		brokerage = getApp().plugins.getBrokerage(portfolio.brokerage)

		def checkDescription(description, str):
			return description[:len(str)].upper() == str.upper()
		
		lines = text.split("\n")
		lineNumber = 0
		for line in lines:
			if line == self.header1 or line == self.header2 or line == "***END OF FILE***" or not line:
				continue
			
			lineNumber += 1
			if status:
				status.setStatus(level = 10 + 90 * lineNumber / self.lines)
			
			s = line.split(",")
			if len(s) == 12:
				# Format 1
				(date, transactionId, description, quantity, symbol, price, commission, amount, salesFee, shortTermRdmFee, fundRedemptionFee, deferredSalesCharge) = s
			elif len(s) == 13:
				# Format 2
				(date, transactionId, description, quantity, symbol, price, commission, amount, netCashbalance, salesFee, shortTermRdmFee, fundRedemptionFee, deferredSalesCharge) = s
			else:
				status.addError("Missed line: " + line)
				continue

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
			if checkDescription(description, "journal entry") or checkDescription(description, "receive & deliver") or checkDescription(description, "money market purchase") or checkDescription(description, "money market redemption"):
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
				# Previous transaction is a "dividend reinvestment (cash debit)" transaction
				found = False
				for t in self.transactions:
					if t.type == Transaction.dividendReinvest and t.ticker == symbol and t.date.strftime("%Y-%m-%d %H:%M:%S") == date:
						found = True
						transaction = t
						break
				if not found:
					if status:
						status.addError("Dividend reinvest but no previous transaction")
				else:
					transaction.setType(Transaction.buy)
					transaction.setShares(quantity)
					if transaction.shares > 0:
						transaction.setPricePerShare(abs(transaction.total / transaction.shares))
					
					# Don't add this transaction after updating the old transaction
					continue
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
			elif status:
				status.addError("Missed line: " + line)

class OptionsHouseCsv(FileFormat):
	header = "Activity Date,Transaction,Description,Symbol,Qty,Fill Price,Commission,Net Amount"
	
	def Guess(self, text):
		return text.startswith(self.header)
	
	def Parse(self, text, portfolio, status):
		brokerage = getApp().plugins.getBrokerage(portfolio.brokerage)

		def checkTransaction(transaction, str):
			return transaction[:len(str)].upper() == str.upper()
		
		def checkDescription(description, str):
			return description[:len(str)].upper() == str.upper()

		lines = text.split("\n")
		lineNumber = 0
		for line in lines:
			if line == self.header or line == "***END OF FILE***" or not line:
				continue
			elif line == '"This report does not serve as an official record and the information it contains is for informational purposes only.  For an official record of your positions and account activity, please refer to your confirmations and account statements."':
				break
			
			lineNumber += 1
			if status:
				status.setStatus(level = 10 + 90 * lineNumber / self.lines)
			
			s = line.split(",")
			if len(s) == 8:
				(date, transactionType, description, symbol, quantity, price, commission, netAmount) = s
				date = Transaction.optionsHouseDateToSql(date)
				fee = 0.0
				
				try:
					netAmount = float(netAmount)
				except:
					netAmount = False
				try:
					quantity = float(quantity)
				except:
					quantity = False
					
				isStock = description.lower().endswith("stock")
				# TODO: Do not know exercised option transaction
				if not isStock and (checkTransaction(transactionType, "buy to open") or checkTransaction(transactionType, "buy to close") or checkTransaction(transactionType, "sell to open") or checkTransaction(transactionType, "sell to close") or checkTransaction(transactionType, "optass")):
					# Try parse "ATVI Nov 11 13.00 Call"
					possibleOption = description.split(" ")
					if len(possibleOption) == 5:
						(optionSymbol, month, year, optionStrike, optionType) = possibleOption
	
						# Parse expire
						if len(year) < 3:
							if int(year) < 70:
								year = "20" + year
							else:
								year = "19" + year
						monthMap = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
						
						# Calculate 3rd saturday of month.  First find the first saturday, then add 12
						# Note saturday is 5
						day = 1
						d = datetime.datetime(year = int(year), month = int(monthMap[month]), day = day)
						wday = d.weekday()
						if wday < 5:
							# Monday thru Friday
							day += 5 - wday
						elif wday == 6:
							# Sunday
							day += 6
						day += 14
						optionExpire = "%s-%s-%d 00:00:00" % (year, monthMap[month], day)
						
						# Parse call or put
						if optionType.lower() == "put":
							subType = Transaction.optionPut
						elif optionType.lower() == "call":
							subType = Transaction.optionCall
						else:
							raise Exception("Unknown option type " + optionType)
				
				if commission:
					fee += float(commission)
				
				if netAmount and quantity and abs(quantity) > 0:
					if fee:
						price = (abs(netAmount) - abs(fee)) / abs(quantity)
					else:
						price = abs(netAmount / quantity)
				
				# Types:
				# buy: buy to open
				# sell: sell to close
				# short: sell to open
				# cover: buy to close
				# split: 
				# deposit/withdrawal: acats journal entry (description), cash journal (description), settled ach deposit (descrption)
				# dividend: qualified dividend
				# dividendReinvest: 
				# expense: hard to borrow fee (description), in lieu dividend (description)
				# transferIn: transfer
				# interest: money market dividends paid (description)
				# ignore: pending ach deposit (description), short account mark to market (description)
				
				transaction = False
				if checkDescription(description, "pending ach deposit") or description.lower().find("short account mark to market") != -1:
					continue
				elif checkDescription(description, "acats journal entry") or checkDescription(description, "cash journal") or checkDescription(description, "settled ach deposit"):
					if netAmount >= 0:
						transaction = Transaction(False, "__CASH__", date, Transaction.deposit, netAmount, fee = fee)
					else:
						transaction = Transaction(False, "__CASH__", date, Transaction.withdrawal, abs(netAmount), fee = fee)
				elif checkTransaction(transactionType, "z"):
					transaction = Transaction(False, symbol, date, Transaction.buy, amount, quantity, price, fee = fee)
				elif checkTransaction(transactionType, "z"):
					transaction = Transaction(False, symbol, date, Transaction.sell, amount, -abs(float(quantity)), price, fee = fee)
				elif checkTransaction(transactionType, "buy to open"):
					if isStock:
						transaction = Transaction(False, symbol, date, Transaction.buy, netAmount, quantity, price, fee = fee)
					else:
						transaction = Transaction(False, symbol, date, Transaction.buyToOpen, netAmount, quantity, price, fee = fee, optionStrike = optionStrike, optionExpire = optionExpire, subType = subType)
				elif checkTransaction(transactionType, "sell to close"):
					if isStock:
						transaction = Transaction(False, symbol, date, Transaction.sell, netAmount, quantity, price, fee = fee)
					else:
						transaction = Transaction(False, symbol, date, Transaction.sellToClose, netAmount, quantity, price, fee = fee, optionStrike = optionStrike, optionExpire = optionExpire, subType = subType)
				elif checkTransaction(transactionType, "sell to open"):
					if isStock:
						transaction = Transaction(False, symbol, date, Transaction.short, netAmount, quantity, price, fee = fee)
					else:
						transaction = Transaction(False, symbol, date, Transaction.sellToOpen, netAmount, quantity, price, fee = fee, optionStrike = optionStrike, optionExpire = optionExpire, subType = subType)
				elif checkTransaction(transactionType, "buy to close"):
					if isStock:
						transaction = Transaction(False, symbol, date, Transaction.cover, netAmount, quantity, price, fee = fee)
					else:
						transaction = Transaction(False, symbol, date, Transaction.buyToClose, netAmount, quantity, price, fee = fee, optionStrike = optionStrike, optionExpire = optionExpire, subType = subType)
				elif checkTransaction(transactionType, "optass"):
					transaction = Transaction(False, symbol, date, Transaction.assign, netAmount, quantity, fee = fee, optionStrike = optionStrike, optionExpire = optionExpire, subType = subType)
				elif description.lower().find("hard to borrow fee") != -1:
					transaction = Transaction(False, "__CASH__", date, Transaction.expense, netAmount)
				elif description.lower().find("in lieu dividend") != -1:
					transaction = Transaction(False, symbol, date, Transaction.expense, netAmount)
				elif checkDescription(description, "qualified dividend"):
					transaction = Transaction(False, symbol, date, Transaction.dividend, netAmount, fee = fee)
				elif checkTransaction(transactionType, "transfer"):
					transaction = Transaction(False, symbol, date, Transaction.transferIn, shares = quantity, fee = fee)
				elif checkDescription(description, "money market dividends paid"):
					transaction = Transaction(False, "__CASH__", date, Transaction.dividend, netAmount, fee = fee)
				
				if transaction:
					self.saveTransaction(brokerage, portfolio, transaction)
				elif status:
					status.addError("Missed line: " + line)
			elif status:
				status.addError("Missed line: " + line)

class FidelityCsv(FileFormat):
	header = "Trade Date,Action,Symbol,Security Description,Security Type,Quantity,Price ($),Commission ($),Fees ($),Accrued Interest ($),Amount ($),Settlement Date"
	
	def Guess(self, text):
		return text.startswith(self.header)
	
	def Parse(self, text, portfolio, status):
		brokerage = getApp().plugins.getBrokerage(portfolio.brokerage)

		def checkAction(action, str):
			return action.upper().startswith(str.upper())

		monthMap = {'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'}

		lines = text.split("\n")
		lineNumber = 0
		for line in lines:
			if line == self.header or not line:
				continue
			
			# Remove extra white space
			line = line.strip(" ").replace(", ", ",")

			lineNumber += 1
			if status:
				status.setStatus(level = 10 + 90 * lineNumber / self.lines)
			
			s = line.split(",")
			if len(s) == 12:
				(date, action, symbol, description, securityType, quantity, price, commission, salesFee, interest, amount, settlementDate) = s
				date = Transaction.ameritradeDateToSql(date)
				fee = 0.0
				if commission:
					fee += float(commission)
				if salesFee:
					fee += float(salesFee)
				
				# Check for option
				isOption = False
				subType = False
				if checkAction(description, "call"):
					isOption = True
					subType = Transaction.optionCall
				elif checkAction(description, "put"):
					isOption = True
					subType = Transaction.optionPut
				
				if isOption:
					# CALL (BWLD) BUFFALO WILD WINGS MAR 19 11 $50 (100 SHS)
					# Extract symbol, strike, expire
					options = description.split(" ")
					year = int(options[-4])
					day = int(options[-5])
					month = monthMap[options[-6]]
					if year < 75:
						year += 2000
					else:
						year += 1900

					symbol = options[1].strip("(").strip(")")
					optionStrike = float(options[-3].strip("$"))
					optionExpire = "%04d-%s-%02d 00:00:00" % (year, month, day)
					opening = action.lower().endswith("opening transaction")
					#print symbol, optionStrike, optionExpire
				
				if symbol == "FDRXX":
					symbol = "__CASH__"
				
				# Types:
				# deposit: cash contribution current year, electronic funds transfer received, check received, moneyline received
				# withdrawal: transferred to
				# buy: you bought, reinvestment (if not cash)
				# sell: you sold
				# buy: you bought
				# dividend RoC: return of capital
				# dividend LTCG: long-term cap gain
				# dividend STCG: short-term cap gain
				# dividend to cash: interest earned, in lieu of frx share spinoff
				# expense: foreign tax paid, fee charged, margin interest
				# spinoff: distributon spinof from:(XX)
				# assign: assigned
				# expire: expired
				# transferIn: rollver shares (includes extra contents but it's ignored)
				
				# Ignore:
				# reinvestment into fdrxx: Covered by dividend received
				# redemption from core account, pruchase into core account: Moving cash around
				
				transaction = False
				if checkAction(action, "cash contribution current year") or checkAction(action, "electronic funds transfer received") or checkAction(action, "check received") or checkAction(action, "moneyline received"):
					transaction = Transaction(False, "__CASH__", date, Transaction.deposit, amount, fee = fee)
				elif checkAction(action, "transferred to"):
					transaction = Transaction(False, "__CASH__", date, Transaction.withdrawal, amount, fee = fee)
				elif checkAction(action, "you bought"):
					if isOption:
						if opening:
							transaction = Transaction(False, symbol, date, Transaction.buyToOpen, amount, quantity, price, fee = fee, subType = subType, optionStrike = optionStrike, optionExpire = optionExpire)
						else:
							transaction = Transaction(False, symbol, date, Transaction.buyToClose, amount, quantity, price, fee = fee, subType = subType, optionStrike = optionStrike, optionExpire = optionExpire)
					else:
						transaction = Transaction(False, symbol, date, Transaction.buy, amount, quantity, price, fee = fee)
				elif checkAction(action, "you sold"):
					if isOption:
						if opening:
							transaction = Transaction(False, symbol, date, Transaction.sellToOpen, amount, -abs(float(quantity)), price, fee = fee, subType = subType, optionStrike = optionStrike, optionExpire = optionExpire)
						else:
							transaction = Transaction(False, symbol, date, Transaction.sellToClose, amount, -abs(float(quantity)), price, fee = fee, subType = subType, optionStrike = optionStrike, optionExpire = optionExpire)
					else:
						transaction = Transaction(False, symbol, date, Transaction.sell, amount, -abs(float(quantity)), price, fee = fee)
				elif checkAction(action, "assigned"):
					# No amount
					transaction = Transaction(False, symbol, date, Transaction.assign, False, quantity, fee = fee, subType = subType, optionStrike = optionStrike, optionExpire = optionExpire)
				elif checkAction(action, "expired"):
					# No amount
					transaction = Transaction(False, symbol, date, Transaction.expire, False, quantity, fee = fee, subType = subType, optionStrike = optionStrike, optionExpire = optionExpire)
				elif checkAction(action, "dividend received"):
					transaction = Transaction(False, symbol, date, Transaction.dividend, amount, fee)
				elif checkAction(action, "long-term cap gain"):
					transaction = Transaction(False, symbol, date, Transaction.dividend, amount, fee, subType = Transaction.capitalGainLongTerm)
				elif checkAction(action, "short-term cap gain"):
					transaction = Transaction(False, symbol, date, Transaction.dividend, amount, fee, subType = Transaction.capitalGainShortTerm)
				elif checkAction(action, "return of capital"):
					transaction = Transaction(False, symbol, date, Transaction.dividend, amount, fee, subType = Transaction.returnOfCapital)
				elif checkAction(action, "interest earned"):
					transaction = Transaction(False, "__CASH__", date, Transaction.dividend, amount, fee)
				elif checkAction(action, "foreign tax paid") or checkAction(action, "fee charged") or checkAction(action, "margin interest"):
					transaction = Transaction(False, symbol, date, Transaction.expense, -float(amount))
				elif checkAction(action, "rollover shares"):
					transaction = Transaction(False, symbol, date, Transaction.transferIn, shares = quantity, fee = fee)
				elif checkAction(action, "reinvestment"):
					if symbol == "__CASH__":
						# Skip reinvestment for cash, it's a duplicate transaction
						continue
					else:
						# Buy for other types
						transaction = Transaction(False, symbol, date, Transaction.buy, amount, quantity, price, fee = fee)
				elif checkAction(action, "distribution"):
					# Match "distribution      spinoff from:(wlt   )"
					if action.lower().find("spinoff from") == -1:
						continue
					openParen = action.find("(")
					closeParen = action.find(")")
					if openParen == -1 or closeParen == -1 or openParen >= closeParen:
						continue
					symbol2 = symbol
					symbol = action[openParen + 1:closeParen].strip(" ")
					transaction = Transaction(False, symbol, date, Transaction.spinoff, ticker2 = symbol2, shares = quantity, fee = fee)
				elif checkAction(action, "in lieu of frx share spinoff"):
					# "in lieu of frx share spinoff from:(wlt   )"
					if action.lower().find("from") == -1:
						continue
					openParen = action.find("(")
					closeParen = action.find(")")
					if openParen == -1 or closeParen == -1 or openParen >= closeParen:
						continue
					symbol = action[openParen + 1:closeParen].strip(" ")
					transaction = Transaction(False, symbol, date, Transaction.dividend, amount, subType = Transaction.returnOfCapital, fee = fee)
				elif checkAction(action, "redemption from core account") or checkAction(action, "purchase into core account"):
					continue
				
				if transaction:
					self.checkStockInfo(portfolio, transaction.uniqueId, "AMERITRADE", "", transaction.ticker)
					self.saveTransaction(brokerage, portfolio, transaction)
				elif status:
					status.addError("Missed line: " + line)
			elif status:
				status.addError("Missed line: " + line)

class Qif(FileFormat):
	def Guess(self, text):
		return text.startswith("!Type") or text.startswith("!Account")

	def Parse(self, text, portfolio, status):
		if getApp():
			brokerage = getApp().plugins.getBrokerage(portfolio.brokerage)
		else:
			brokerage = False

		def check(action, str):
			return action.upper().startswith(str.upper())
		
		transactionMap = {
			"buy": Transaction.buy,
			"div": Transaction.dividend,
			"intinc": Transaction.dividend,
			"miscexp": Transaction.expense,
			"miscinc": Transaction.dividend,
			"reinvdiv": Transaction.buy,
			"reinvint": Transaction.buy,
			"reinvlg": Transaction.buy,
			"reinvmd": Transaction.buy,
			"reinvsh": Transaction.buy,
			"sell": Transaction.sell,
			"shrsin": Transaction.transferIn,
			"shrsout": Transaction.transferOut,
			"stksplit": Transaction.split,
			"tax exempt dividend": Transaction.dividend,
			"xin": Transaction.transferIn,
			"xout": Transaction.transferOut}
		transactionSubTypeMap = {
			"tax exempt dividend": Transaction.taxExempt}
		transactionTickerMap = {
			"intinc": "__CASH__"}
		
		bankTransactionMap = {
			"credit": Transaction.deposit,
			"debit": Transaction.withdrawal,
			"fee": Transaction.expense}

		lines = text.split("\n")
		lineNumber = 0
		trnType = False
		newTransaction = {}
		for line in lines:
			if not line:
				continue

			lineNumber += 1
			if status:
				status.setStatus(level = 10 + 90 * lineNumber / self.lines)
			
			if line.startswith("!Account"):
				trnType = "Account"
			elif line.startswith("!Type:"):
				trnType = line[6:]
			elif line.startswith("^"):
				if not newTransaction:
					continue
					
				# Save transaction, prepare next transaction for parsing
				t = newTransaction
				newTransaction = {}

				# Defaults
				if not "price" in t:
					t["price"] = False
				if not "quantity" in t:
					t["quantity"] = False
				if not "total" in t:
					t["total"] = False
				if not "subType" in t:
					t["subType"] = False
				if not "fee" in t:
					t["fee"] = False
				
				# Fill in some transaction types
				if trnType == "Bank" and not "type" in t and "memo" in t:
					if check(t["memo"], "dividend") or check(t["memo"], "credit interest"):
						t["type"] = Transaction.dividend
					elif check(t["memo"], "journal"):
						# Skip journal
						continue
					elif check(t["memo"], "cash receipt"):
						t["type"] = Transaction.deposit
				if not "ticker" in t and "memo" in t:
					if check(t["memo"], "int - "):
						t["type"] = Transaction.dividend
						t["ticker"] = "__CASH__"
					elif check(t["memo"], "iracc - ") or check(t["memo"], "ira - ira contribution"):
						t["type"] = Transaction.deposit
						t["ticker"] = "__CASH__"
					elif check(t["memo"], "div - "):
						t["type"] = Transaction.dividend
						t["ticker"] = "__CASH__"
					elif check(t["memo"], "xch - "):
						# Ignore
						continue
				
				# Required fields for all transactions
				# Note: ticker is checked for later, may be added by some checks
				if not "date" in t:
					status.addError("No date for transaction %s" % t)
					continue
				if not "type" in t:
					status.addError("No type for transaction %s" % t)
					continue

				# Remove commas
				if t["price"]:
					t["price"] = float(t["price"].replace(",", ""))
				if t["quantity"]:
					t["quantity"] = float(t["quantity"].replace(",", ""))
				if t["total"]:
					t["total"] = float(t["total"].replace(",", ""))
				
				# Updates for specific transaction types
				if t["type"] == Transaction.split:
					# Split must have quantity
					if not "quantity" in t:
						status.addError("No quantity for split transaction %s" % t)
						continue
					
					# Crude method to get accurate split
					for num in range(1, 11):
						for den in range(1, 11):
							if abs(float(den) / num - float(t["quantity"])) < 0.01:
								t["total"] = float(num) / den
					t["quantity"] = False
				if t["type"] in [Transaction.transferIn, Transaction.transferOut]:
					# Check for dollar transfer (deposit or withdrawal)
					if "transferAmount" in t:
						if t["type"] == Transaction.transferIn:
							t["type"] = Transaction.deposit
						else:
							t["type"] = Transaction.withdrawal
						t["ticker"] = "__CASH__"
						del t["transferAmount"]
				if trnType == "Bank":
					t["ticker"] = "__CASH__"
				
				# Required fields for all transactions
				if not "ticker" in t:
					status.addError("No ticker for transaction %s" % t)
					continue

				# Build transaction and save
				t = Transaction(False, t["ticker"], t["date"], t["type"], t["total"], t["quantity"], pricePerShare = t["price"], fee = t["fee"], subType = t["subType"])
				self.saveTransaction(brokerage, portfolio, t)
			elif trnType == "Account":
				# Skip account
				pass
			# Transactions common to invst and bank
			elif line.startswith("D"):
				if line.find("'") == -1:
					# Format is MM/DD/YY or MM/DD/YYYY
					(month, day, year) = line[1:].split("/")
				else:
					# Format is MM/DD'YY
					(remSplit, year) = line[1:].split("'")
					(month, day) = remSplit.split("/")
				if int(year) < 1000:
					if int(year) > 70:
						year = 1900 + int(year)
					else:
						year = 2000 + int(year)
				newTransaction["date"] = "%04d-%02d-%02d 00:00:00" % (int(year), int(month), int(day))
			elif line.startswith("T") or line.startswith("U"):
				# Check for different total for T or U
				if "total" in newTransaction:
					if type(newTransaction["total"]) == float:
						total1 = newTransaction["total"]
					else:
						total1 = float(newTransaction["total"].replace(",", ""))
					total2 = float(line[1:].replace(",", ""))
					if abs(total1 - total2) > 1.0e-6:
						status.addError("Differing totals %f and %f" % (total1, total2))
				newTransaction["total"] = line[1:]
			elif line.startswith("M") or line.startswith("P"):
				newTransaction["memo"] = line[1:]
			elif trnType == "Invst":
				# Transactions for invst only
				if line.startswith("Y"):
					# Set ticker if not set already
					if not "ticker" in newTransaction:
						newTransaction["ticker"] = line[1:].strip(" ")
				elif line.startswith("I"):
					newTransaction["price"] = line[1:]
				elif line.startswith("$"):
					newTransaction["transferAmount"] = line[1:]
				elif line.startswith("L"):
					newTransaction["accountForTransfer"] = line[1:]
				elif line.startswith("Q"):
					newTransaction["quantity"] = line[1:]
				elif line.startswith("O"):
					newTransaction["fee"] = line[1:]
				elif line.startswith("N"):
					transactionType = line[1:].lower()
					if transactionType in transactionMap:
						newTransaction["type"] = transactionMap[transactionType]
					else:
						status.addError("Unknown type " + transactionType)
					if transactionType in transactionSubTypeMap:
						newTransaction["subType"] = transactionSubTypeMap[transactionType]
					if transactionType in transactionTickerMap:
						newTransaction["ticker"] = transactionTickerMap[transactionType]
				elif line.startswith("C"):
					# Cleared status, skip
					continue
				else:
					status.addError("Missed line: " + line)
			elif trnType == "Bank":
				# Transactions for bank only
				if line.startswith("N"):
					transactionType = line[1:].lower()
					if transactionType in bankTransactionMap:
						newTransaction["type"] = bankTransactionMap[transactionType]
				elif line.startswith("P"):
					newTransaction["payee"] = line[1:]
				elif line.startswith("L"):
					newTransaction["category"] = line[1:]
				else:
					status.addError("Missed line: " + line)
			else:
				status.addError("Unknown type " + trnType)

def getFileFormats():
	return [Ofx(), Ofx2(), AmeritradeCsv(), OptionsHouseCsv(), FidelityCsv(), Qif()]

