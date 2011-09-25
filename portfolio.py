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

from db import *
from ofxToolkit import *
from fileFormats import *
from userprice import *
from positionCheck import *
from twrr import *

import prefs
try:
	import autoUpdater
	haveAutoUpdater = True
except:
	haveAutoUpdater = False
import chart

import time
import datetime
import os
import copy
import operator
import uuid

def floatCompare(a, b):
	if a > b:
		num = a
		dem = b
	else:
		num = b
		dem = a
	if num == 0 and dem == 0:
		return 0
	elif dem == 0:
		return 1e9
	else:
		return num / dem

class PortfolioPrefs(prefs.Prefs):
	def __init__(self, db):
		prefs.Prefs.__init__(self, db)
		
		self.checkDefaults("dirty", "True")
		self.checkDefaults("positionIncSplits", "False")
		self.checkDefaults("positionIncDividends", "True")
		self.checkDefaults("positionIncFees", "False")
		self.checkDefaults("positionIncBenchmark", "True")
		self.checkDefaults("chartType", "Value")
		self.checkDefaults("positionPeriod", "Since Inception")
		self.checkDefaults("performanceCurrent", "False")
		self.checkDefaults("performanceDividends", "True")
		self.checkDefaults("lastImport", "ofx")
		self.checkDefaults("combinedComponents", "")
		self.checkDefaults("brokerage", "False")
		self.checkDefaults("sync", "")

	def getTransactionId(self):
		return uuid.uuid4().hex

	def getDirty(self):
		return self.getPreference("dirty") == "True"

	def getPositionIncSplits(self):
		return self.getPreference("positionIncSplits") == "True"

	def getPositionIncDividends(self):
		return self.getPreference("positionIncDividends") == "True"

	def getPositionIncFees(self):
		return self.getPreference("positionIncFees") == "True"

	def getPositionIncBenchmark(self):
		return self.getPreference("positionIncBenchmark") == "True"
	
	def getChartType(self):
		return self.getPreference("chartType")

	def getPositionPeriod(self):
		return self.getPreference("positionPeriod")

	def getPerformanceCurrent(self):
		return self.getPreference("performanceCurrent") == "True"

	def getPerformanceDividends(self):
		return self.getPreference("performanceDividends") == "True"

	def getLastImport(self):
		return self.getPreference("lastImport")

	def getCombinedComponents(self):
		if not self.getPreference("combinedComponents"):
			return []
		return self.getPreference("combinedComponents").split(",")
	
	def getBrokerage(self):
		return self.getPreference("brokerage")

	def getUrl(self):
		return self.getPreference("url")

	def getSync(self):
		if not self.getPreference("sync"):
			return []
		return self.getPreference("sync").split(",")

	def setDirty(self, dirty):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": dirty}, {"name": "dirty"})
		self.db.commitTransaction()

	def setPositionIncSplits(self, inc):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": inc}, {"name": "positionIncSplits"})
		self.db.commitTransaction()

	def setPositionIncDividends(self, inc):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": inc}, {"name": "positionIncDividends"})
		self.db.commitTransaction()

	def setPositionIncFees(self, inc):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": inc}, {"name": "positionIncFees"})
		self.db.commitTransaction()

	def setPositionIncBenchmark(self, inc):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": inc}, {"name": "positionIncBenchmark"})
		self.db.commitTransaction()

	def setChartType(self, type):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": type}, {"name": "chartType"})
		self.db.commitTransaction()

	def setPositionPeriod(self, period):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": period}, {"name": "positionPeriod"})
		self.db.commitTransaction()

	def setPerformanceCurrent(self, value):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": value}, {"name": "performanceCurrent"})
		self.db.commitTransaction()

	def setPerformanceDividends(self, value):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": value}, {"name": "performanceDividends"})
		self.db.commitTransaction()

	def setLastImport(self, value):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": value}, {"name": "lastImport"})
		self.db.commitTransaction()

	def setCombinedComponents(self, value):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": value}, {"name": "combinedComponents"})
		self.db.commitTransaction()

	def setBrokerage(self, value):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": value}, {"name": "brokerage"})
		self.db.commitTransaction()

	def setUrl(self, value):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": value}, {"name": "url"})
		self.db.commitTransaction()

	def setSync(self, value):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": value}, {"name": "sync"})
		self.db.commitTransaction()

class Portfolio:	
	def __init__(self, name = False, brokerage = "", username = "", account = "", customDb = False):
		self.open(name, customDb)
		
	def open(self, name, customDb = False):
		self.name = name

		if prefs.prefs:
			info = prefs.prefs.getPortfolioInfo(name)
			if not info:
				raise Exception("No portfolio " + name)
			self.brokerage = info["brokerage"]
			self.username = info["username"]
			self.account = info["account"]
	
		if customDb:
			self.db = Db(customDb)
		else:
			self.db = Db(appGlobal.getApp().prefs.getPortfolioPath(name))

		self.db.beginTransaction()

		self.portPrefs = PortfolioPrefs(self.db)
		self.portPrefs.checkDefaults("nextTransactionId", "1")
		self.portPrefs.checkDefaults("lastTicker", "__COMBINED__")
		self.portPrefs.checkDefaults("benchmark", "S&P 500")
		self.portPrefs.checkDefaults("isBrokerage", "True")
		self.portPrefs.checkDefaults("isBank", "False")
		self.portPrefs.checkDefaults("isBenchmark", "False")
		self.portPrefs.checkDefaults("isCombined", "False")
		self.portPrefs.checkDefaults("url", "")
		self.portPrefs.checkDefaults("summaryYears", "lastYear")
		self.portPrefs.checkDefaults("summaryChart1", chart.oneYearVsBenchmarkCash)
		if self.isBank():
			self.portPrefs.checkDefaults("summaryChart2", chart.oneMonthSpending)
		else:
			self.portPrefs.checkDefaults("summaryChart2", chart.oneMonthMovers)

		self.db.checkTable("stockInfo", [
			{"name": "uniqueId", "type": "text"},
			{"name": "uniqueIdType", "type": "text"},
			{"name": "secName", "type": "text"},
			{"name": "ticker", "type": "text"}])
	
		self.db.checkTable("transactions", [
			{"name": "uniqueId", "type": "text"},
			{"name": "date", "type": "text"},
			{"name": "ticker", "type": "text"},
			{"name": "ticker2", "type": "text"},
			{"name": "type", "type": "integer"},
			{"name": "subType", "type": "integer"},
			{"name": "shares", "type": "float"},
			{"name": "pricePerShare", "type": "float"},
			{"name": "fee", "type": "float"},
			{"name": "total", "type": "float"},
			{"name": "optionStrike", "type": "float"},
			{"name": "optionExpire", "type": "text"},
			{"name": "edited", "type": "text not null default False"},
			{"name": "deleted", "type": "bool not null default False"},
			{"name": "auto", "type": "bool not null default False"}], index = [
			{"name": "tickerDate", "cols": ["ticker", "date"]}])
		
		self.db.checkTable("userPrices", [
			{"name": "date", "type": "datetime"},
			{"name": "ticker", "type": "text"},
			{"name": "price", "type": "float"}])
		
		self.db.checkTable("positionCheck", [
			{"name": "date", "type": "datetime"},
			{"name": "ticker", "type": "text"},
			{"name": "shares", "type": "float"},
			{"name": "value", "type": "float"}])

		self.db.checkTable("positionHistory", [
			{"name": "date", "type": "datetime"},
			{"name": "ticker", "type": "text"},
			{"name": "shares", "type": "float"},
			{"name": "options", "type": "float"},
			{"name": "value", "type": "float"},
			{"name": "normSplit", "type": "float"},
			{"name": "normDividend", "type": "float"},
			{"name": "normFee", "type": "float"},
			{"name": "profitSplit", "type": "float"},
			{"name": "profitDividend", "type": "float"},
			{"name": "profitFee", "type": "float"}],
			index = [{"name": "positionHistoryIndex", "cols": ["ticker, date"]}])
		
		self.db.checkTable("allocation", [
			{"name": "ticker", "type": "text"},
			{"name": "percentage", "type": "float"}],
			unique = [{"name": "tickerIndex", "cols": ["ticker"]}])

		self.db.checkTable("categories", [
			{"name": "ticker", "type": "text"},
			{"name": "category", "type": "text"}],
			unique = [{"name": "tickerIndex", "cols": ["ticker"]}])

		self.db.checkTable("rules", [
			{"name": "rule", "type": "text"},
			{"name": "category", "type": "text"}],
			unique = [{"name": "ruleIndex", "cols": ["rule"]}])

		self.db.checkTable("availCategories", [
			{"name": "category", "type": "text"}],
			unique = [{"name": "categoryIndex", "cols": ["category"]}])

		self.db.commitTransaction()
		
		# List of transactions
		self.transactions = []
		
		# List of user prices
		self.userPrices = []
		
	def close(self):
		self.db.close()
	
	def strToDatetime(self, date, zeroHMS = False):
		# Remove HMS if specified
		if zeroHMS:
			date = str(date)
			date = date[0:10] + " 00:00:00"
		
		return Transaction.parseDate(date)
	
	def delete(self, prefs):
		self.db.close()
		os.remove(prefs.getPortfolioPath(self.name))
		prefs.deletePortfolio(self.name)
	
	def updateFromFile(self, data, app, status = False):
		if status:
			status.setSubTask(50)
			status.setStatus("Parsing transactions", 10)
		
		found = False
		format = False
		for format in getFileFormats():
			if format.Guess(data):
				found = True
				break
		
		if not found:
			if status:
				status.addError("Unknown file format")
				status.finishSubTask()
				status.setStatus("Aborted", 100)
			return (False, False, False)
		
		try:
			app.beginBigTask('importing transactions', status)
	
			(numNew, numOld, newTickers) = format.StartParse(data, self, status)
			
			if status:
				status.setStatus("Parsing transactions")
				status.finishSubTask()
	
			# Download new stock data
			# NOTE: This function may be called by auto-updater when rebuilding portfolios
			# We know this is the case if status is false
			if haveAutoUpdater and self.isBrokerage():
				# Temporarily end big task so autoUpdater can run
				app.endBigTask()
				
				autoUpdater.wakeUp()
				if status:
					if autoUpdater.percentDone() == 100:
						status.setStatus(level = 99)
					else:
						status.setSubTask(99)
						status.setStatus("Downloading stock data\nWarning: This operation may take a while")
						# Wait for downloading to finish
						autoUpdater.wakeUp()
						while not autoUpdater.sleeping():
							status.setStatus(level = autoUpdater.percentDone())
							# Sleep for 1 second
							app.processEvents(QEventLoop.AllEvents, 1000)
						status.finishSubTask()
				
				# Resume big task
				app.beginBigTask('importing transactions', status)
				
			# Check for new positions not in stockData
			if newTickers and self.isBrokerage():
				notFound = []
				for ticker in newTickers:
					if ticker == "__CASH__":
						continue
					
					p = app.stockData.getPrices(ticker)
					if not p:
						notFound.append(ticker)
				
				if notFound:
					message = "No stock data was found for the following tickers: " + ", ".join(notFound)
					message += ".  You can fix this problem by going to the \"Stock Data\" page, choosing a position from the list, then clicking the \"Suggest\" button."
					if status:
						status.addMessage(message)
	
			self.portPrefs.setDirty(True)
			if status:
				status.setStatus("Finished\nImported %d new transactions.\n%d transactions had already been imported." % (numNew, numOld), 100)
				status.setFinished()
			
			app.endBigTask()
	
			return (numNew, numOld, newTickers)
		except:
			app.endBigTask()
			raise

	def readFromDb(self):
		res = self.db.select("transactions")
		
		self.transactions = []
		for row in res.fetchall():
			t = Transaction(
				uniqueId = row["uniqueId"],
				ticker = row["ticker"].upper(),
				date = row["date"],
				transactionType = row["type"],
				amount = row["total"],
				shares = row["shares"],
				pricePerShare = row["pricePerShare"],
				fee = row["fee"],
				optionStrike = row["optionStrike"],
				optionExpire = row["optionExpire"],
				edited = row["edited"],
				deleted = row["deleted"],
				ticker2 = row["ticker2"],
				subType = row["subType"],
				auto = row["auto"])
			self.transactions.append(t)
		
		# Sort transactions
		self.transactions.sort()
	
		res = self.db.select("userPrices")
		
		for row in res.fetchall():
			ticker = row["ticker"]
			p = UserPrice(
				row["date"],
				ticker,
				row["price"])
			self.userPrices.append(p)

	def isValid(self):
		return self.getPositionFirstLast("__COMBINED__")
	
	def getTickers(self, includeAllocation = False):
		if self.isCombined():
			# Combined portfolio
			tickers = {}
			
			components = self.portPrefs.getCombinedComponents()
			for name in components:
				if not name:
					continue
				p = Portfolio(name)
				p.readFromDb()
				pTickers = p.getTickers(includeAllocation)
				for ticker in pTickers:
					tickers[ticker] = ticker
		else:
			# Regular portfolio
			tickers = {}
			for t in self.transactions:
				if t.ticker and not t.deleted and not t.ticker in tickers:
					tickers[t.ticker] = t.ticker
				if t.ticker2 and not t.deleted and not t.ticker2 in tickers:
					tickers[t.ticker2] = t.ticker2
					
			# Add in positionCheck
			cursor = self.db.select("positionCheck", what = "distinct(ticker) as ticker")
			for row in cursor.fetchall():
				if not row["ticker"] in tickers:
					tickers[row["ticker"]] = row["ticker"]
			
			# Optionally add allocation
			if includeAllocation:
				allocation = self.getAllocation()
				for a in allocation:
					tickers[a] = a
			
			if not "__CASH__" in tickers:
				tickers["__CASH__"] = "__CASH__"
		
		return sorted(tickers.keys())

	def getLastTicker(self):
		return self.portPrefs.getPreference("lastTicker")
	
	def isBrokerage(self):
		return self.portPrefs.getPreference("isBrokerage") == "True"

	def isBank(self):
		return self.portPrefs.getPreference("isBank") == "True"

	def isBenchmark(self):
		return self.portPrefs.getPreference("isBenchmark") == "True"

	def isCombined(self):
		return self.portPrefs.getPreference("isCombined") == "True"

	def makeBenchmark(self):
		self.db.update("prefs", {"value": "True"}, {"name": "isBenchmark"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBrokerage"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBank"})
		self.db.update("prefs", {"value": "False"}, {"name": "isCombined"})
	
	def makeCombined(self):
		self.db.update("prefs", {"value": "True"}, {"name": "isCombined"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBrokerage"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBank"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBenchmark"})
	
	def makeBank(self):
		self.db.update("prefs", {"value": "True"}, {"name": "isBank"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBrokerage"})
		self.db.update("prefs", {"value": "False"}, {"name": "isCombined"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBenchmark"})
	
	def getCategories(self):
		# Read categories from DB
		categories = []
		cursor = self.db.select("availCategories")
		for row in cursor.fetchall():
			categories.append(row["category"])
		
		if len(categories) > 0:
			return sorted(categories)
		else:
			# If no categories (first time called) insert
			defaultCategories = ["Charity", "Childcare", "Clothing", "Debt Repayment", "Eating Out", "Entertainment", "Fees & Interest", "Groceries", "Health & Fitness", "Hobbies", "Housing", "Luxuries", "Medical & Dental", "Miscellaneous", "Pets", "Savings & Investmentments", "Transportation", "Uncategorized", "Utilities", "Vacations"]
			self.db.beginTransaction()
			for c in defaultCategories:
				self.db.insert("availCategories", {"category": c})
			self.db.commitTransaction()
			return sorted(defaultCategories)
	
	def getRules(self):
		# Read rules from DB
		rules = []
		cursor = self.db.select("rules")
		for row in cursor.fetchall():
			rules.append((row["rule"], row["category"]))
		return rules

	def addCategory(self, category):
		self.db.beginTransaction()
		self.db.insert("availCategories", {"category": category})
		self.db.commitTransaction()
	
	def addRule(self, rule, category):
		self.db.beginTransaction()
		self.db.insert("rules", {"rule": rule, "category": category})
		self.db.commitTransaction()

	def removeCategory(self, category):
		self.db.beginTransaction()
		self.db.delete("availCategories", {"category": category})
		self.db.delete("categories", {"category": category})
		self.db.delete("rules", {"category": category})
		self.db.commitTransaction()

	def removeRule(self, rule):
		self.db.beginTransaction()
		self.db.delete("rules", {"rule": rule})
		self.db.commitTransaction()

	def getCategory(self, ticker):
		cursor = self.db.select("categories", where = {"ticker": ticker})
		for row in cursor.fetchall():
			return row["category"]
		return "Uncategorized"
	
	def setCategory(self, ticker, category):
		self.db.insertOrUpdate("categories", {"ticker": ticker, "category": category}, {"ticker": ticker})

	def getBenchmark(self):
		return self.portPrefs.getPreference("benchmark")

	def setBenchmark(self, benchmark):
		self.db.update("prefs", {"value": benchmark}, {"name": "benchmark"})

	def getSummaryYears(self):
		return self.portPrefs.getPreference("summaryYears")

	def getSummaryChart1(self):
		return int(self.portPrefs.getPreference("summaryChart1"))

	def getSummaryChart2(self):
		return int(self.portPrefs.getPreference("summaryChart2"))

	def setSummaryYears(self, all):
		self.db.update("prefs", {"value": all}, {"name": "summaryYears"})

	def setSummaryChart1(self, type):
		self.db.update("prefs", {"value": type}, {"name": "summaryChart1"})

	def setSummaryChart2(self, type):
		self.db.update("prefs", {"value": type}, {"name": "summaryChart2"})

	def setLastTicker(self, last):
		self.db.update("prefs", {"value": last}, {"name": "lastTicker"})
	
	def getStartDate(self):
		cursor = self.db.select("transactions", orderBy = "date asc", limit = 1)
		row = cursor.fetchone()
		if row:
			return Transaction.parseDate(row["date"])
		return False		

	def getEndDate(self):
		cursor = self.db.select("positionHistory", orderBy = "date desc", limit = 1)
		row = cursor.fetchone()
		if row:
			return Transaction.parseDate(row["date"])
		return False		

	def getLastTransactionDate(self):
		cursor = self.db.select("transactions", orderBy = "date desc", limit = 1)
		row = cursor.fetchone()
		if row:
			return Transaction.parseDate(row["date"])
		return False		

	def getFirstTransactionDate(self):
		cursor = self.db.select("transactions", orderBy = "date asc", limit = 1)
		row = cursor.fetchone()
		if row:
			return Transaction.parseDate(row["date"])
		return False		

	def getTransactions(self, ticker = False, ascending = False, getDeleted = False, deletedOnly = False, buysToCash = True, limit = False, transType = False):
		retTrans = []
		
		if ticker:
			ticker = ticker.upper()
			for t in self.transactions:
				# Ignore type if type is specified and it doesn't match
				if type(transType) == int and t.type != transType:
					continue
				
				# Ignore deleted transactions
				if not getDeleted and not deletedOnly and t.deleted:
					continue
				if deletedOnly and not t.deleted:
					continue

				if buysToCash and ticker == "__CASH__":
					if t.ticker == "__CASH__":
						# Don't modify cash transactions
						retTrans.append(t)
					elif t.getCashMod() != 0:
						# Transaction modifies cash, create copy
						t2 = copy.deepcopy(t)
						t2.ticker = "__CASH__"
						t2.fee = 0.0
						if t.getCashMod() > 0:
							# Deposit if cashMod > 0
							t2.type = Transaction.deposit
							t2.total = t.getCashMod()
						else:
							# Withdrawal if cashMod < 0
							t2.type = Transaction.withdrawal
							t2.total = -t.getCashMod()
						retTrans.append(t2)
				elif ticker == "__CASH__" and t.type == Transaction.transferIn:
					# Tranfser in must get a deposit to signify that value was added to the account
					t2 = copy.deepcopy(t)
					t2.type = Transaction.deposit
					t2.total = abs(t2.total)
					t2.fee = 0.0
					retTrans.append(t2)			
				elif ticker == "__CASH__" and t.type == Transaction.transferOut:
					# Tranfser out must get a withdrawal to signify that value was removed from the account
					t2 = copy.deepcopy(t)
					t2.type = Transaction.withdrawal
					t2.total = abs(t2.total)
					t2.fee = 0.0
					retTrans.append(t2)			
				elif not ticker or t.ticker.upper() == ticker or (t.ticker2 and t.ticker2 != "False" and t.ticker2.upper() == ticker):
					# Append if we are getting all tickers
					# or the requested ticker matches ticker or ticker2
					retTrans.append(t)
		else:
			for t in self.transactions:
				if type(transType) == int and t.type != transType:
					continue
				
				# Ignore deleted transactions
				if not getDeleted and not deletedOnly and t.deleted:
					continue
				if deletedOnly and not t.deleted:
					continue

				retTrans.append(t)
				if limit and len(retTrans) == limit:
					break
		
		if ascending:
			retTrans.reverse()
		
		if limit and len(retTrans) > limit:
			del retTrans[limit:]
		
		return retTrans
	
	def getDividendForDate(self, ticker, date):
		"""Get a dividend nearest to the given ticker and date"""
		query = "select * From transactions where ticker='%s' and type='%s' order by abs(julianday('%s') - julianday(date)) limit 1;" % (ticker, Transaction.dividend, date.strftime("%Y-%m-%d"))
		res = self.db.query(query)
		row = res.fetchone()
		if row:
			return Transaction(
				row["uniqueId"],
				row["ticker"].upper(),
				row["date"],
				row["type"],
				row["total"],
				row["shares"],
				row["pricePerShare"],
				row["fee"],
				row["edited"],
				row["deleted"],
				row["ticker2"],
				row["auto"])
		else:
			return False
	
	def getUserPrices(self, ticker):
		retPrices = []
		
		ticker = ticker.upper()
		for p in self.userPrices:
			if p.ticker.upper() == ticker:
				retPrices.append(p)
		
		return retPrices
	
	def addUserAndTransactionPrices(self, ticker, prices, transactions):
		userPrices = self.getUserPrices(ticker)
		
		# Use buys/sells to add to user price
		for t in transactions:
			if t.type in [Transaction.buy, Transaction.sell, Transaction.transferIn, Transaction.transferOut, Transaction.short, Transaction.cover, Transaction.buyToOpen, Transaction.sellToClose, Transaction.sellToOpen, Transaction.buyToClose]:
				# Add to user prices
				# Note there may already be a user price for this date
				
				if t.pricePerShare:
					price = t.pricePerShare
				else:
					price = abs(t.total / t.shares)
				userPrices.append(UserPrice(t.date, t.ticker, price))

		# Add user prices and transaction prices to prices array
		appended = False
		for p in userPrices:
			date = self.strToDatetime(p.date, zeroHMS = True)

			# Check if date is already there
			found = False
			for p2 in prices:
				if p2["date"] == date:
					found = True
					break
			if not found:
				appended = True
				prices.append({'volume': 0, 'high': p.price, 'low': p.price, 'date': date, 'close': p.price, 'open': p.price})
		
		# If we added prices, sort by date
		if appended:
			prices.sort(key = lambda p: p['date'])
		
	
	def getPositionCheck(self, ticker):
		checks = []
		
		cursor = self.db.select("positionCheck", where = {"ticker": ticker})
		for row in cursor.fetchall():
			check = PositionCheck(
				self.strToDatetime(row["date"]),
				row["ticker"],
				float(row["shares"]),
				float(row["value"]))
			checks.append(check)
		
		return checks

	def getPositionForCheck(self, ticker, check):
		# Check position on 3 closest days
		d = datetime.datetime(check.date.year, check.date.month, check.date.day, 0, 0, 0)

		# Check if same day matches
		same = self.getPositionOnDate(ticker, d)
		if same and abs(check.shares - same["shares"]) < 1.0e-6 and floatCompare(check.value, same["value"]):
			return same

		# Check 1 day before
		pos = self.getPositionOnDate(ticker, d - datetime.timedelta(days = 1))
		if pos and abs(check.shares - pos["shares"]) < 1.0e-6 and floatCompare(check.value, pos["value"]):
			return pos

		# Check 1 day after
		pos = self.getPositionOnDate(ticker, d + datetime.timedelta(days = 1))
		if pos and abs(check.shares - pos["shares"]) < 1.0e-6 and floatCompare(check.value, pos["value"]):
			return pos

		# Day before or after is not any better
		# May be false
		return same

	def getPositionHistory(self, ticker, startDate = False):
		where = {"ticker": ticker}
		if startDate:
			where["date >="] = "%d-%02d-%02d 00:00:00" % (startDate.year, startDate.month, startDate.day)
		cursor = self.db.select("positionHistory", where = where)
		
		ret = {}
		for row in cursor.fetchall():
			row["date"] = self.strToDatetime(row["date"])
			ret[row["date"]] = row
		
		return ret
	
	def getPositionOnDate(self, ticker, date):
		cursor = self.db.select("positionHistory", where = {"ticker": ticker, "date": date.strftime("%Y-%m-%d %H:%M:%S")})
		
		row = cursor.fetchone()
		if not row:
			return False
		
		row["date"] = self.strToDatetime(row["date"])

		return row
	
	def getPositions(self, current = False):
		cursor = self.db.getConn().execute("select ticker, shares, value, max(date) as maxDate from positionHistory group by ticker")
		
		rows = []
		for row in cursor.fetchall():
			rows.append(row)

		if current:
			maxDate = "0000-00-00"
			
			for row in rows:
				if row["maxDate"] > maxDate:
					maxDate = row["maxDate"]
		
		ret = {}
		for row in rows:
			if not current or row["maxDate"] == maxDate:
				ret[row["ticker"]] = row
			
		return ret
	
	def getPositionFirstLast(self, ticker):
		conn = self.db.getConn()
		select = "select min(date) as minDate, max(date) as maxDate from positionHistory where ticker=?"
		cursor = conn.execute(select, [ticker])
		
		row = cursor.fetchone()
		if not row:
			return False

		if row['minDate'] is None or row['maxDate'] is None:
			return False
		
		d1 = self.strToDatetime(row['minDate'])
		d2 = self.strToDatetime(row['maxDate'])
		return (d1, d2)
	
	def sumInflow(self, first, last, ticker = False):
		transactions = self.getTransactions(ticker, transType = Transaction.deposit)
		
		# Filter for transactions in time period, then sum
		tInDate = filter(lambda t: first <= t.date <= last, transactions)
		sumA = reduce(lambda x, t: x + abs(t.total), tInDate, 0.0)

		transactions = self.getTransactions(ticker, transType = Transaction.withdrawal)
		
		# Filter for transactions in time period, then sum
		tInDate = filter(lambda t: first <= t.date <= last, transactions)
		sumA = reduce(lambda x, t: x - abs(t.total), tInDate, sumA)


		# Next do transferIn and transferOut
		transactions = self.getTransactions(ticker, transType = Transaction.transferIn)
		tInDate = filter(lambda t: first <= t.date <= last, transactions)
		sumB = reduce(lambda x, t: x + abs(t.total), tInDate, 0.0)

		transactions = self.getTransactions(ticker, transType = Transaction.transferOut)
		tInDate = filter(lambda t: first <= t.date <= last, transactions)
		sumB = reduce(lambda x, t: x - abs(t.total), tInDate, sumB)

		return sumA + sumB

	def sumDistributions(self, first, last, ticker = False):
		transactions = self.getTransactions(ticker, transType = Transaction.dividend)
		
		# Filter for transactions in time period, then sum
		tInDate = filter(lambda t: first <= t.date <= last, transactions)
		sum = reduce(lambda x, t: x + t.total, tInDate, 0.0)

		transactions = self.getTransactions(ticker, transType = Transaction.dividendReinvest)
		
		# Filter for transactions in time period, then sum
		tInDate = filter(lambda t: first <= t.date <= last, transactions)
		sum = reduce(lambda x, t: x + t.total, tInDate, sum)

		return sum
	
	def sumFees(self, first, last, ticker = False):
		transactions = self.getTransactions(ticker)
		
		# Filter for transactions in time period, then sum
		tInDate = filter(lambda t: first <= t.date <= last, transactions)
		sum = reduce(lambda x, t: x + abs(t.fee), tInDate, 0.0)
		return sum

	# Returns (performance string, years)
	def calculatePerformanceTimeWeighted(self, ticker, first, last, divide = True, dividend = True, format = True, isInception = False):
		if last < first:
			return ("n/a", 0)
		
		# Next normalize
		diff = last - first
		days = diff.days
		years = (days + 1) / 365.25
		if days == 0:
			return ("n/a", years)

		# Computer starting and ending values
		val1 = self.getPositionOnDate(ticker, first)
		val2 = self.getPositionOnDate(ticker, last)
		if not val1 or not val2:
			return ("n/a", years)
		if dividend:
			val1 = val1["normDividend"]
			val2 = val2["normDividend"]
		else:
			val1 = val1["normSplit"]
			val2 = val2["normSplit"]
		if abs(val1) < 1.0e-6:
			return ("n/a", years)
		
		if divide and not isInception:
			ret = val2 / val1
		else:
			ret = val2
		negative = ret < 0
		if negative:
			ret = -ret
		if days > 365:
			ret = pow(ret, 365.0 / days)
		if negative:
			ret = -ret
		if format:
			ret = "%.2f%%" % (100.0 * ret - 100.0)
		
		#print ticker, ret, val1, val2, years, days, first, last
		return (ret, years)
	
	# Returns (performance string, years)
	def calculatePerformanceProfit(self, ticker, first, last, divide = True, dividend = True, format = True, isInception = False):
		if last < first:
			return ("n/a", 0)
		
		# Next compute years
		diff = last - first
		days = diff.days
		years = (days + 1) / 365.25
		
		# Computer starting and ending values
		val1 = self.getPositionOnDate(ticker, first)
		val2 = self.getPositionOnDate(ticker, last)
		if not val1 or not val2:
			return ("n/a", 0)
		if dividend:
			val1 = val1["profitDividend"]
			val2 = val2["profitDividend"]
		else:
			val1 = val1["profitSplit"]
			val2 = val2["profitSplit"]

		if not val1 or not val2:
			return ("n/a", 0)
		
		if isInception:
			ret = val2
		else:
			ret = val2 - val1
		if format:
			ret = Transaction.formatDollar(ret)
		
		#print ticker, ret, val1, val2, years, days, first, last
		return (ret, years)
	
	# Returns (performance string, years)
	def calculatePerformanceValue(self, ticker, first, last, divide = True, dividend = True, format = True, isInception = False):
		if last < first:
			return ("n/a", 0)
		
		# Next compute years
		diff = last - first
		days = diff.days
		years = (days + 1) / 365.25
		
		# Computer starting and ending values
		val1 = self.getPositionOnDate(ticker, first)
		val2 = self.getPositionOnDate(ticker, last)
		if not val1 or not val2:
			return ("n/a", years)
		if dividend:
			val1 = val1["value"] + val1["profitDividend"] - val1["profitSplit"]
			val2 = val2["value"] + val2["profitDividend"] - val2["profitSplit"]
		else:
			val1 = val1["value"]
			val2 = val2["value"]
		
		if isInception:
			ret = val2
		else:
			ret = val2 - val1
		if format:
			ret = Transaction.formatDollar(ret)
		
		#print ticker, ret, val1, val2, years, days, first, last
		return (ret, years)
	
	def runRules(self):
		rules = self.getRules()
		
		# First build unique tickers
		tickers = {}
		for t in self.getTransactions():
			if not t.isBankSpending():
				continue
			tickers[t.ticker] = t
		
		# Try to match for all uncategorized
		for t in tickers:
			if self.getCategory(t) != "Uncategorized":
				continue
			
			# r[0] is the rule, r[1] is the category
			for r in rules:
				if re.match(".*" + r[0] + ".*", t, re.IGNORECASE):
					self.setCategory(t, r[1])
	
	def getAllocation(self):
		cursor = self.db.select("allocation", where = {"percentage >=": 0})
		
		ret = {}
		for row in cursor.fetchall():
			ret[row["ticker"]] = float(row["percentage"])
		
		return ret
	
	def saveAllocation(self, oldTicker, newTicker, percent = False):
		if not newTicker:
			self.db.delete("allocation", {"ticker": oldTicker})
		elif oldTicker:
			self.db.insertOrUpdate("allocation", {"ticker": newTicker, "percentage": percent}, {"ticker": oldTicker})
		else:
			self.db.insert("allocation", {"ticker": newTicker, "percentage": percent})
	
	def rebuildBenchmarkTransactions(self, stockData, status):
		if status:
			status.setStatus("Rebuilding Benchmark Transactions", 0)
		self.db.beginTransaction()
		self.db.delete("transactions")
		
		positions = self.getAllocation()
		if not positions:
			return

		ticker = positions.keys()[0]
		
		# Compute start date of portfolio
		first = True
		for ticker in positions:
			if first:
				firstDate = stockData.getFirstDate(ticker)
				if firstDate:
					first = False
					date = firstDate
			else:
				firstDate = stockData.getFirstDate(ticker)
				if firstDate > date:
					date = firstDate
		
		# No stock data found
		if first:
			return

		date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
		currentYear = -1
		
		# Get last second of today's date
		now = datetime.datetime.now()
		now = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)

		transactionId = 1
		# Deposit $10,000
		t = Transaction(
			"__" + str(transactionId) + "__",
			"__CASH__",
			date,
			Transaction.deposit,
			10000,
			auto = True)
		cash = 10000
		t.save(self.db)
		transactionId += 1
		
		stockPrices = {}
		currentStockPrice = {}
		stockDividends = {}
		currentStockDividend = {}
		for ticker in positions:
			stockPrices[ticker] = stockData.getPrices(ticker)
			currentStockPrice[ticker] = 0
			stockDividends[ticker] = stockData.getDividends(ticker)
			currentStockDividend[ticker] = 0
		
		value = 0.0
		shares = {}
		stockVal = {}
		if status:
			status.setStatus("Rebuilding Benchmark Transactions", 20)
		yieldCount = 0
		while date < now:
			yieldCount += 1
			if yieldCount == 100:
				yieldCount = 0
				if status:
					status.appYield()
					if status.canceled:
						break

			# Get current price
			while currentStockPrice[ticker] < len(stockPrices[ticker]) and stockPrices[ticker][currentStockPrice[ticker]]["date"] < date:
				currentStockPrice[ticker] += 1
			if currentStockPrice[ticker] < len(stockPrices[ticker]) and stockPrices[ticker][currentStockPrice[ticker]]["date"] == date:
				val = stockPrices[ticker][currentStockPrice[ticker]]
				stockVal[ticker] = val

			# Compute value if we own shares
			if shares:
				newValue = 0.0
				doNewValue = False
				for ticker in shares:
					# Get current dividend
					# Possible bug if multiple dividends on the same day
					while currentStockDividend[ticker] < len(stockDividends[ticker]) and stockDividends[ticker][currentStockDividend[ticker]]["date"] < date:
						currentStockDividend[ticker] += 1
					if val["close"] > 0 and currentStockDividend[ticker] < len(stockDividends[ticker]) and stockDividends[ticker][currentStockDividend[ticker]]["date"] == date:
						div = stockDividends[ticker][currentStockDividend[ticker]]

						amount = div["value"] * shares[ticker]
						buyShares = amount / val["close"]
						shares[ticker] += buyShares

						t = Transaction(
							"__" + str(transactionId) + "__",
							ticker,
							date,
							Transaction.dividendReinvest,
							amount,
							shares = buyShares,
							pricePerShare = val["close"],
							auto = True)
						t.save(self.db)
						transactionId += 1
					
					newValue += shares[ticker] * val["close"]
					doNewValue = True
				if doNewValue:
					value = newValue + cash
					#print date, newValue
					
			# Rebalance on the first transaction and on the first of every year
			if date.year != currentYear:
				# Rebalance if data is available today (exchanges are open)
				#if stockVal:
				currentYear = date.year
				
				if not shares:
					# Original purchase
					for ticker in positions:
						if ticker not in stockVal:
							continue
						close = stockVal[ticker]["close"]
						if close <= 0:
							continue
							
						# Buy allocation for portfolio value of $10,000
						buyShares = 10000.0 / close * positions[ticker] / 100.0
						amount = buyShares * close
						shares[ticker] = buyShares

						t = Transaction(
							"__" + str(transactionId) + "__",
							ticker,
							date,
							Transaction.buy,
							-amount,
							shares = buyShares,
							pricePerShare = close,
							auto = True)
						cash -= amount
						t.save(self.db)
						transactionId += 1
				elif value:
					for ticker in positions:
						if ticker not in stockVal:
							continue
						close = stockVal[ticker]["close"]
						if close <= 0:
							continue
							
						# Buy allocation for portfolio value of $value
						finalShares = value / close * positions[ticker] / 100.0
						if ticker in shares:
							buyShares = finalShares - shares[ticker]
							shares[ticker] = finalShares
						else:
							buyShares = finalShares
							shares[ticker] = finalShares
						
						# amount is < 0 for sell, > 0 for buy
						amount = buyShares * close
						
						if buyShares > 1.0e-6:
							t = Transaction(
								"__" + str(transactionId) + "__",
								ticker,
								date,
								Transaction.buy,
								amount,
								shares = buyShares,
								pricePerShare = close,
								auto = True)
							cash -= amount
							t.save(self.db)
							transactionId += 1
						elif buyShares < -1.0e-6:
							t = Transaction(
								"__" + str(transactionId) + "__",
								ticker,
								date,
								Transaction.sell,
								amount,
								shares = buyShares,
								pricePerShare = close,
								auto = True)
							cash -= amount # amount is < 0 for sell
							t.save(self.db)
							transactionId += 1
			
			date += datetime.timedelta(1)

		self.db.commitTransaction()
	
	def rebuildCombinedTransactions(self, update):
		# Rebuild transactions
		self.db.delete("transactions")
		
		subPorts = self.portPrefs.getCombinedComponents()

		# Read transactions from subPorts and insert into this portfolio
		for portName in subPorts:
			sp = Portfolio(portName)
			res = sp.db.select('transactions', where = {'deleted': 'False'})
			for t in res.fetchall():
				t["edited"] = False
				self.db.insert('transactions', t)

	def rebuildBankPositionHistory(self, update = False):
		# Only allow one thread to update a portfolio at a time
		appGlobal.getApp().beginBigTask('rebuilding a portfolio', update)
		
		self.db.beginTransaction()
		try:
			# Delete auto transactions and position history
			self.db.delete("transactions", {"auto": "True"})
			self.db.delete("positionHistory")
			
			self.readFromDb()

			# Get last second of today's date
			now = datetime.datetime.now()
			now = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)

			# Get first date
			portfolioFirstDate = self.getStartDate()
			if not portfolioFirstDate:
				self.db.rollbackTransaction()
				appGlobal.getApp().endBigTask()
				return

			count = 0
			tickers = self.getTickers()
			for ticker in tickers:
				count += 1
				value = 0
				normDividend = 1
				normFee = 1
				profitDividend = 0
				profitFee = 0
				currentTrans = 0
				yieldCount = 0
				transactions = self.getTransactions(ticker, ascending = True)
				
				if len(transactions) == 0:
					continue
				
				# Begin cash at first date, others at first transaction
				if ticker == "__CASH__":
					date = portfolioFirstDate
				else:
					date = transactions[currentTrans].getDate()
				
				update.setStatus("Rebuilding " + ticker, 20 + 80 * count / len(tickers))

				# Loop until current time if cash, or until last transaction if other
				while date < now and (currentTrans < len(transactions) or ticker == "__CASH__"):
					yieldCount += 1
					if yieldCount == 100:
						yieldCount = 0
						if update:
							update.appYield()
							if update.canceled:
								break
						
					while currentTrans < len(transactions) and transactions[currentTrans].getDate() <= date:
						t = transactions[currentTrans]

						value += t.getCashMod()

						if t.getFee() > 0:
							profitFee -= t.getFee()
							if abs(value) > 1.0e-6:
								normFee *= 1.0 - t.getTotal() / value
						
						if t.type == Transaction.dividend:
							profitDividend += t.getTotal()
							if abs(value) > 1.0e-6:
								normDividend *= 1.0 + t.getTotal() / value

						currentTrans += 1

					self.db.insert("positionHistory", {
						"date": date.strftime("%Y-%m-%d 00:00:00"),
						"ticker": ticker,
						"shares": value,
						"options": 0,
						"value": value,
						"normSplit": 1,
						"normDividend": normDividend,
						"normFee": normFee,
						"profitSplit": 0,
						"profitDividend": profitDividend,
						"profitFee": profitFee})

					date += datetime.timedelta(1)
			
			# The cash position is the combined position
			query = "insert into positionHistory (date, ticker, shares, options, value, normSplit, normDividend, normFee, profitSplit, profitDividend, profitFee) select date, '__COMBINED__', shares, options, value, normSplit, normDividend, normFee, profitSplit, profitDividend, profitFee from positionHistory where ticker='__CASH__'"
			self.db.query(query)
		except Exception:
			self.db.rollbackTransaction()
			if update:
				update.addException()
				update.setFinished()
			else:
				raise
		
		self.db.commitTransaction()
		appGlobal.getApp().endBigTask()

	def rebuildPositionHistory(self, stockData, update = False):
		# TODO: do not combine individual days
		def addToBasis(ticker, d, s, pps):
			if ticker not in basis:
				basis[ticker] = {}
			if d in basis[ticker]:
				# Update basis for this day
				(oldShares, oldPricePerShare) = basis[ticker][d]
				newShares = s + oldShares
				if newShares == 0:
					self.db.rollbackTransaction()
					appGlobal.getApp().endBigTask()
					raise Exception("Added shares to 0")
				newPricePerShare = (oldShares * oldPricePerShare + s * pps) / newShares
				basis[ticker][d] = (newShares, newPricePerShare)
			else:
				basis[ticker][d] = (s, pps)
		
			# Update combined basis
			d = datetime.datetime(d.year, d.month, d.day)
			if not d in combinedBasis:
				combinedBasis[d] = 0.0
			combinedBasis[d] += abs(s * pps)
		
		def getShares(ticker):
			if not ticker in basis:
				return 0
			
			s = 0
			for d in basis[ticker]:
				s += basis[ticker][d][0]
			return s
		
		def getBasis(ticker, update = False, shareCount = False):
			if not ticker in basis:
				return 0
		
			basisVal = 0
			basisShares = 0
			if shareCount:
				# Use up all shares in shareCount
				for d in basis[ticker]:
					(s, pps) = basis[ticker][d]
					if s > shareCount:
						basisVal += shareCount * pps
						basisShares += shareCount
						shareCount -= shareCount
						break
					else:
						basisVal += s * pps
						basisShares += s
						shareCount -= s
				if update and shareCount > 0:
					update.addError("Invalid share count for " + ticker)
			else:
				# Compute over all shares
				for d in basis[ticker]:
					(s, pps) = basis[ticker][d]
					basisVal += s * pps
					basisShares += s
			
			if basisShares == 0:
				return 0
			else:
				return basisVal / basisShares

		def getBasisValue(ticker):
			if not ticker in basis:
				return 0
		
			val = 0
			# Compute over all shares
			for d in basis[ticker]:
				(s, pps) = basis[ticker][d]
				val += s * pps
			
			return val

		def removeFromBasis(ticker, remove):
			while len(basis[ticker]) > 0 and abs(remove) > 0:
				(s, pricePerShare) = basis[ticker][basis[ticker].keys()[0]]
				if abs(s) > abs(remove):
					basis[ticker][basis[ticker].keys()[0]] = (s - remove, pricePerShare)
					remove = 0

					# Update combined basis
					d = datetime.datetime(t.date.year, t.date.month, t.date.day)
					if not d in combinedBasis:
						combinedBasis[d] = 0.0
					else:
						combinedBasis[d] -= abs(remove * pricePerShare)
				else:
					del basis[ticker][basis[ticker].keys()[0]]
					remove -= s

					# Update combined basis
					d = datetime.datetime(t.date.year, t.date.month, t.date.day)
					if not d in combinedBasis:
						combinedBasis[d] = 0.0
					else:
						combinedBasis[d] -= abs(s * pricePerShare)
			if abs(remove) > 1.0e-6:
				if update:
					update.addError("Could not finish basis for %s %s %s" % (ticker, remove, basis[ticker]))
			
		def adjustBasisStockDividend(ticker, adjustShares):
			"""Add or remove shares from basis"""
			shares = getShares(ticker)
			if shares == 0:
				if update:
					update.addError("Split but zero shares for " + ticker)
				return
			shareFactor = (shares + adjustShares) / shares
			if shareFactor == 0:
				if update:
					update.addError("Split to zero shares for " + ticker)
				return
			
			for d in basis[ticker]:
				(s, pps) = basis[ticker][d]
				basis[ticker][d] = (s * shareFactor, pps / shareFactor)
		
		def adjustBasisValue(ticker, percent):
			"""Modify basis value by percent"""
			for d in basis[ticker]:
				(s, pps) = basis[ticker][d]
				basis[ticker][d] = (s, pps * percent)

		# TODO: do not combine individual days
		def addToOptionsBasis(ticker, d, s, pps, strike, expire):
			if d in optionsBasis:
				# Update basis for this day
				optionsBasis[d].append((ticker, s, pps, strike, expire))
			else:
				optionsBasis[d] = [(ticker, s, pps, strike, expire)]
		
			# Update combined basis
			# TODO: Should this be done?
			d = datetime.datetime(d.year, d.month, d.day)
			if not d in combinedBasis:
				combinedBasis[d] = 0.0
			combinedBasis[d] += abs(s * pps)
		
		def getOptionsShares(ticker):
			s = 0
			for d in optionsBasis:
				for i in range(len(optionsBasis[d])):
					s += optionsBasis[d][i][1]
			return s
		
		def getOptionsBasis(ticker, update = False):
			basisVal = 0
			basisShares = 0
			# Compute over all shares
			for d in optionsBasis:
				for i in range(len(optionsBasis[d])):
					(ignoreTicker, s, pps, strike, expire) = optionsBasis[d][i]
					basisVal += s * pps
					basisShares += s
			
			if basisShares == 0:
				return 0
			else:
				return basisVal / basisShares

		def getOptionsBasisValue(ticker, update = False):
			basisVal = 0
			# Compute over all shares
			for d in optionsBasis:
				for i in range(len(optionsBasis[d])):
					(ignoreTicker, s, pps, strike, expire) = optionsBasis[d][i]
					basisVal += s * pps
			
			return basisVal
		
		def getSpecificOptionsBasis(optionStrike, optionExpire):
			basisVal = 0
			basisShares = 0
			# Compute over matching shares
			for d in optionsBasis:
				for i in range(len(optionsBasis[d])):
					(ignoreTicker, s, pps, strike, expire) = optionsBasis[d][i]
					if strike == optionStrike and expire == optionExpire:
						basisVal += s * pps
						basisShares += s
			
			if basisShares == 0:
				return 0
			else:
				return basisVal / basisShares

		def expireOptions(ticker, optionStrike, optionExpire):
			for d in optionsBasis:
				for i in range(len(optionsBasis[d])):
					(thisTicker, s, pps, strike, expire) = optionsBasis[d][i]
					if strike == optionStrike and expire == optionExpire:
						if s < 0:
							# Sell to open
							twrr.coverShares(thisTicker, abs(s) * 100, optionStrike)
							twrr.removeSharesNoPrice(thisTicker + "income", abs(s))
						else:
							# Buy to open
							twrr.removeShares(thisTicker, abs(s), 0)
						removeFromOptionsBasis(thisTicker, s, strike, expire)

		def checkOptionsExpiration(ticker, date):
			# Return True if expired an option
			expired = False
			
			for d in optionsBasis:
				i = 0
				while i < len(optionsBasis[d]):
					(thisTicker, s, pps, strike, expire) = optionsBasis[d][i]
					# Expire the day after
					date2 = datetime.datetime(date.year, date.month, date.day)
					expire2 = datetime.datetime(expire.year, expire.month, expire.day)
					if date2 >= expire2:
						expired = True
						removeFromOptionsBasis(thisTicker, s, strike, expire)
						if s > 0:
							# Buy to open
							twrr.removeShares(thisTicker, abs(s), 0)
						elif s < 0:
							# Sell to open
							twrr.coverShares(thisTicker, abs(s) * 100, strike)
							twrr.removeSharesNoPrice(thisTicker + "income", abs(s))
					else:
						i += 1
			
			return expired
		
		def removeFromOptionsBasis(ticker, remove, strike, expire):
			for d in optionsBasis:
				i = 0
				while d in optionsBasis and i < len(optionsBasis[d]):
					(ignoreTicker, s, pps, str, e) = optionsBasis[d][i]
					if str != strike or e != expire:
						continue
					
					if s > remove:
						optionsBasis[d][i] = (ignoreTicker, s - remove, pps, str, e)
						remove = 0
	
						# Update combined basis
						d = datetime.datetime(t.date.year, t.date.month, t.date.day)
						if not d in combinedBasis:
							combinedBasis[d] = 0.0
						else:
							combinedBasis[d] -= abs(remove * pps)
						i += 1
					else:
						# Remove all of basis
						del optionsBasis[d][i]
						remove -= s
	
						# Update combined basis
						d = datetime.datetime(t.date.year, t.date.month, t.date.day)
						if not remove in combinedBasis:
							combinedBasis[d] = 0.0
						else:
							combinedBasis[d] -= abs(s * pps)
			if abs(remove) > 1.0e-6:
				if update:
					update.addError("Could not finish options basis for %s remove %f strike %f expire %s basis %f" % (ticker, remove, strike, expire, optionsBasis))
		
		if self.isBank():
			self.rebuildBankPositionHistory(update)
			return

		# Only allow one thread to update a portfolio at a time
		appGlobal.getApp().beginBigTask('rebuilding a portfolio', update)
		
		self.readFromDb()
		stockData.updatePortfolioStocks(self, update)
		
		# Begin update
		self.db.beginTransaction()
		try:
			# Delete auto transactions and position history
			self.db.delete("transactions", {"auto": "True"})
			self.db.delete("positionHistory")
	
			if self.isCombined():
				self.rebuildCombinedTransactions(update)
			
			self.readFromDb()
			
			# Nothing to do if no transactions and not benchmark
			if not self.getTransactions() and not self.isBenchmark():
				if update:
					update.addMessage("No transactions found")
					update.setSubTask(100)
				self.portPrefs.setDirty(False)
				self.db.commitTransaction()
				appGlobal.getApp().endBigTask()
				return
			
			if self.isBenchmark():
				if update:
					update.setSubTask(60)
				self.rebuildBenchmarkTransactions(stockData, update)
				self.readFromDb()
				if update:
					update.finishSubTask()
	
			if update:
				update.setSubTask(100)
	
			# Get last second of today's date
			now = datetime.datetime.now()
			now = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)
	
			# Get first date
			portfolioFirstDate = self.getStartDate()
			if not portfolioFirstDate:
				self.db.rollbackTransaction()
				appGlobal.getApp().endBigTask()
				return
	
			# Total combined value indexed by date
			combinedValue = {}
			
			# Basis dictionary key is ticker, dictionary of date, content is list of (shares, price per share)
			basis = {}
			
			# Options basis key is date, content is list of (shares, price per share, strike, expire)
			optionsBasis = {}
	
			# Total combined basis indexed by date
			# First pass through = individual basis adjustments
			combinedBasis = {}
	
			tickers = self.getTickers(includeAllocation = True)
	
			# Check for spinoffs or changeTickers.  Move these to back.  Check for situations like A->B, B->C, D->C
			moveBack = {}
			for ticker in tickers:
				transactions = self.getTransactions(ticker, ascending = True)
				for t in transactions:
					if t.type in [Transaction.spinoff, Transaction.tickerChange] and ticker == t.ticker2:
						if not t.ticker2 in moveBack:
							moveBack[t.ticker2] = []
						moveBack[t.ticker2].append(t.ticker)
			# Now do a weird kind of bubble sort putting each ticker behind each other one
			# This is not perfect but it's pretty good
			for ticker in tickers[:]:
				if not ticker in moveBack:
					continue
				
				# Keep moving back by one until it is behind everything it needs
				moveIt = True
				while moveIt:
					# Check if don't need to move
					numBefore = 0
					for ticker2 in tickers:
						if ticker == ticker2:
							moveIt = numBefore != len(moveBack[ticker])
							break
						elif ticker2 in moveBack[ticker]:
							numBefore += 1
					
					if moveIt:
						# Move ticker back one
						index = tickers.index(ticker)
						tickers = tickers[:index] + [tickers[index + 1], ticker] + tickers[index + 2:]
	
			count = 0
			for ticker in tickers:
				if update:
					update.setStatus("Rebuilding " + ticker, 20 + 80 * count / len(tickers))
					if update.canceled:
						break
				count += 1
				
				if update:
					if ticker == "__CASH__":
						update.addMessage("Computing cash position")
					else:
						update.addMessage("Computing position " + ticker)
				transactions = self.getTransactions(ticker, ascending = True)
				
				# Reset optionsBasis for each ticker
				optionsBasis = {}
				
				# See if we have a portfolio check value for this ticker
				# If so, compute the number of shares at the first portfolio check
				# If the shares is less, add some at the beginning
				# If the shares is more, error
				checks = self.getPositionCheck(ticker)
				if checks:
					check = checks[-1]
					
					# We will make 3 passes, 0, 1 and 2 days after the check
					# At least 1 of those days must match
					foundMatch = False
					closest = 1e12
					for i in (2, 1, 0):
						shares = 0
						targetDate = check.date + datetime.timedelta(days = i)
	
						# First sum up number of computed shares until check
						if ticker == "__CASH__":
							for t in transactions:
								# Only use check if it's valid
								if t.date > targetDate:
									continue
		
								if t.type in [Transaction.deposit, Transaction.dividend, Transaction.adjustment, Transaction.withdrawal, Transaction.expense]:
									shares += t.getTotal()
								else:
									if update:
										update.addError("Unknown cash transaction when updating position check %s" % t)
						else:
							for t in transactions:
								# Only use check if it's valid
								if t.date > targetDate:
									continue
								
								if t.type in [Transaction.buy, Transaction.short, Transaction.dividendReinvest, Transaction.transferIn, Transaction.buyToClose, Transaction.buyToOpen]:
									shares += abs(t.shares)
								elif t.type in [Transaction.sell, Transaction.cover, Transaction.transferOut, Transaction.sellToOpen, Transaction.sellToOpen]:
									shares -= abs(t.shares)
								elif t.type in [Transaction.stockDividend, Transaction.split]:
									if t.type == Transaction.stockDividend:
										adjustShares = t.shares
									else:
										# 2-1 split total is 2.0
										adjustShares = shares * (t.getTotal() - 1.0)
			
									shares += adjustShares
								elif t.type == Transaction.spinoff and t.ticker2 == ticker:
									shares += abs(t.shares)
	
						# Check for match
						# If no match, check how close we got in the best case
						if abs(check.shares - shares) < 1.0e-6:
							foundMatch = True
							break
						elif abs(check.shares - shares) < abs(closest):
							closest = check.shares - shares
	
					# Now compare.  Add deposit for __CASH__, transfer for stock
					if not foundMatch:
						# Add shares based on the first date
						# Get us to the closest point of matching the check
						# Because we looped over multiple windows
						addShares = closest
						if update:
							update.addMessage("Beginning %s with %.2f shares" % (ticker, addShares))
						
						if ticker == "__CASH__":
							t = Transaction(
								False,
								ticker,
								portfolioFirstDate,
								Transaction.adjustment,
								addShares,
								auto = True)
							transactions.insert(0, t)
							t.save(self.db)
						else:
							# Get stock value on date
							# If not found, continue on to next days for up to one week
							lookupPrice = portfolioFirstDate
							price = False
							count = 0
							while not price and count < 7:
								price = stockData.getPrice(ticker, lookupPrice)
								lookupPrice += datetime.timedelta(days = 1)
								count += 1
							if price:
								cash = price["close"] * addShares
								
								# Add deposit to cash transactions
								t = Transaction(
									False,
									"__CASH__",
									portfolioFirstDate,
									Transaction.deposit,
									cash,
									auto = True)
								t.save(self.db)
								
								t = Transaction(
									False,
									ticker,
									portfolioFirstDate,
									Transaction.buy,
									cash,
									shares = addShares,
									pricePerShare = price["close"],
									auto = True)
								transactions.insert(0, t)
								t.save(self.db)
							else:
								if update:
									update.addMessage("No data found for %s for position check on %s" % (ticker, check.date.strftime("%B %d, %Y")))
					elif check.shares < shares - 1.0e-6:
						if update:
							update.addError("ERROR TOO MANY SHARES should be % fbut is %f" % (check.shares, shares))
				
				# Check for negative cash
				# If negative, add deposits as needed
				if ticker == "__CASH__":
					currentCash = 0.0
					added = False
					for t in transactions:
						currentCash += t.getCashMod()
						if currentCash < 0:
							added = True
							
							# Add deposit
							depositAmount = -currentCash
							currentCash += depositAmount

							# Add deposit to cash transactions
							t = Transaction(
								False,
								"__CASH__",
								t.date,
								Transaction.deposit,
								depositAmount,
								auto = True)
							t.save(self.db)
					if added:
						self.readFromDb()
						transactions = self.getTransactions(ticker, ascending = True)
				
				# If no transactions for a stock, skip
				# The cash position may have no transactions if all we have is a transfer in
				if not transactions and ticker != "__CASH__":
					if update:
						update.addError("No transactions for " + ticker)
					continue
	
				# Get stock data
				if ticker == "__CASH__":
					prices = {}
					prices[0] = {}
					prices[0]["close"] = 1.0
					#for t in transactions:
					#	print t
				else:
					prices = stockData.getPrices(ticker, startDate = transactions[0].date)
					if not prices:
						# No prices print error
						if update:
							update.addError("No stock data found for %s" % ticker)
					self.addUserAndTransactionPrices(ticker, prices, transactions)
					if not prices:
						# Still no data, ignore
						continue
	
				# Loop through first date until now
				currentTrans = 0
				currentPrice = 0
				# Begin on first transaction.  Always begin cash on portfolio first date.
				if transactions and ticker != "__CASH__":
					date = transactions[0].getDate()
				else:
					date = portfolioFirstDate
				date = datetime.datetime(date.year, date.month, date.day, 23, 59, 59)
				price = False
				shares = 0.0
				value = 0.0
				adjustedValue = 0.0
				totalFees = 0
				totalDividends = 0
				totalProfit = 0 # Profit after fees
				yieldCount = 0
				doneWithTicker = False
				twrr = Twrr() # Time weighted rate of return
				if ticker == "__CASH__":
					twrr.addShares("__CASH__", 0, 1)
				while date < now and not doneWithTicker:
					yieldCount += 1
					if yieldCount == 100:
						yieldCount = 0
						if update:
							update.appYield()
							if update.canceled:
								break
					totalTrans = 0
					todayDividends = 0
					twrr.beginTransactions()
					while currentTrans < len(transactions) and transactions[currentTrans].getDate() <= date and not doneWithTicker:
						t = transactions[currentTrans]
						
						# Check that first transaction is a buy or transferIn (if not cash), or a spinoff or tickerChange and we are ticker2
						if currentTrans == 0 and ticker != "__CASH__":
							if not t.type in [Transaction.buy, Transaction.short, Transaction.buyToOpen, Transaction.sellToOpen, Transaction.transferIn] and ((t.type != Transaction.spinoff and t.type != Transaction.tickerChange) or t.ticker2 != ticker):
								if update:
									update.addError("The first transaction for %s does not add to its shares.  Ignoring position." % ticker)
								doneWithTicker = True
								break
						currentTrans += 1
						totalTrans += 1
	
						if t.type == Transaction.deposit:
							shares += t.getTotal()
							twrr.addShares(ticker, t.getTotal(), 1)
						elif t.type == Transaction.withdrawal:
							shares += t.getTotal()
							twrr.removeShares(ticker, -t.getTotal(), 1)
						elif t.type == Transaction.buy or t.type == Transaction.transferIn:
							# Lookup price if unavailable
							if t.pricePerShare < 1.0e-6:
								p = stockData.getPrice(ticker, t.date)
								if p:
									t.pricePerShare = p["close"]
									t.setTotal(t.pricePerShare * abs(t.shares) - t.getFee())
								else:
									if update:
										update.addError("Buy transaction has no price per share", t)
									continue
	
							shares += abs(t.shares)
							totalProfit -= abs(t.total)
							twrr.addShares(ticker, t.getShares(), t.pricePerShare)
							
							# Add to basis tracker
							addToBasis(ticker, t.date, t.shares, t.pricePerShare)
						elif t.type == Transaction.buyToOpen:
							totalProfit -= abs(t.total)
							# Use formatTicker() because it includes strike, option
							twrr.addShares(t.formatTicker(), t.getShares(), t.pricePerShare)
							
							# Add to basis tracker
							addToOptionsBasis(t.formatTicker(), t.date, t.shares, t.pricePerShare, t.optionStrike, t.optionExpire)
						elif t.type == Transaction.sell:
							shares -= abs(t.shares)
							totalProfit += t.getTotal()
							twrr.removeShares(ticker, t.getShares(), t.pricePerShare)
							
							# Remove t.shares from basis tracker
							removeFromBasis(ticker, abs(t.shares))
						elif t.type == Transaction.sellToClose:
							totalProfit += t.getTotal()
							twrr.removeShares(t.formatTicker(), t.getShares(), t.pricePerShare)
							
							# Remove t.shares from basis tracker
							removeFromOptionsBasis(t.formatTicker(), abs(t.shares), t.optionStrike, t.optionExpire)
						elif t.type == Transaction.short:
							# Lookup price if unavailable
							if not t.pricePerShare:
								if update:
									update.addError("Transaction has no price per share %s" % t)
								continue
	
							# Shorts reduce shares and add to basis
							shares -= abs(t.shares)
							totalProfit += t.getTotal()
							twrr.shortShares(ticker, t.getShares(), t.pricePerShare)
							
							# Add to basis tracker
							addToBasis(ticker, t.date, -abs(t.shares), t.pricePerShare)
						elif t.type == Transaction.cover:
							# Cover adds to shares and removes from basis
							shares += abs(t.shares)
							twrr.coverShares(ticker, t.getShares(), t.pricePerShare)
							
							# Remove t.shares from basis tracker
							totalProfit += t.getTotal()
							removeFromBasis(ticker, -abs(t.shares))
						elif t.type == Transaction.sellToOpen:
							# Shorts reduce shares and add to basis
							shares -= abs(t.shares)
							totalProfit += t.getTotal()
							
							# For sellToOpen we track 2 positions: One is exposure to the underlying stock,
							# the other is the value of the options.  Assume 100 shares per option.
							twrr.shortShares(t.formatTicker(), t.getShares() * 100, t.optionStrike)
							
							twrr.addShares(t.formatTicker() + "income", abs(t.getShares()), 0)
							twrr.setValue(t.formatTicker() + "income", t.pricePerShare)
							
							# Add to basis tracker
							addToOptionsBasis(t.formatTicker(), t.date, -abs(t.shares), t.pricePerShare, t.optionStrike, t.optionExpire)
						elif t.type == Transaction.buyToClose:
							finalIncome = getSpecificOptionsBasis(t.optionStrike, t.optionExpire) - t.pricePerShare
							# buyToClose adds to shares and removes from basis
							shares += abs(t.shares)
							twrr.coverShares(t.formatTicker(), t.getShares() * 100, t.optionStrike)
							twrr.removeShares(t.formatTicker() + "income", abs(t.getShares()), abs(finalIncome))
							
							# Remove t.shares from basis tracker
							totalProfit += t.getTotal()
							removeFromOptionsBasis(t.formatTicker(), -abs(t.shares), t.optionStrike, t.optionExpire)
						elif t.type in [Transaction.assign, Transaction.exercise, Transaction.expire]:
							expireOptions(t.formatTicker(), t.optionStrike, t.optionExpire)
						elif t.type == Transaction.dividend:
							todayDividends += t.getTotalIgnoreFee()
							twrr.addDividend(t.getTotalIgnoreFee())
							if ticker == "__CASH__":
								twrr.addShares(ticker, t.getTotalIgnoreFee(), 1)
							# Fee will be subtracted from todayDividends later
							if t.getFee():
								todayDividends += t.getFee()
						elif t.type == Transaction.expense:
							# Note: Fees for all transactions are handled somewhere else
							# Here we only keep track of fees from the total
							if t.total:
								if t.fee:
									thisFee = abs(t.total) - abs(t.fee)
								else:
									thisFee = abs(t.total)
								totalFees += thisFee
								totalProfit -= thisFee
							else:
								totalProfit -= t.getFee()
						elif t.type == Transaction.dividendReinvest:
							if t.pricePerShare < 1.0e-6:
								if t.getTotalIgnoreFee() > 0:
									t.pricePerShare = t.getTotalIgnoreFee() / t.shares
								else:
									p = stockData.getPrice(ticker, t.date)
									if p:
										t.pricePerShare = p["close"]
									else:
										if update:
											update.addError("Dividend reinvest transaction has no price per share", t)
										continue
							
							# Add to today's dividends, but don't count as profit
							# Because we are increasing share count
							shares += abs(t.shares)
							todayDividends += t.getTotalIgnoreFee()
							totalProfit -= t.getTotalIgnoreFee()
							twrr.addDividendReinvest(ticker, t.getShares(), t.pricePerShare)
	
							# Add to basis tracker
							addToBasis(ticker, t.date, t.shares, t.pricePerShare)
						elif t.type == Transaction.transferOut:
							if t.pricePerShare < 1.0e-6:
								if t.getTotalIgnoreFee() > 0:
									t.pricePerShare = t.getTotalIgnoreFee() / t.shares
								elif price:
									# Use last price data
									t.pricePerShare = price
								else:
									p = stockData.getPrice(ticker, t.date)
									if p:
										t.pricePerShare = p["close"]
									else:
										if update:
											update.addError("transaction has no price per share %s" % t)
										continue
							
							shares -= abs(t.shares)
							totalProfit += t.getTotal()
							twrr.removeShares(ticker, t.getShares(), t.pricePerShare)
							
							# Remove t.shares from basis tracker
							# TODO: Handle for options?
							removeFromBasis(ticker, abs(t.shares))
						elif t.type in [Transaction.stockDividend, Transaction.split]:
							if t.type == Transaction.stockDividend:
								adjustShares = t.shares
							elif t.getTotal() > 0:
								# A 2-1 split has a value of 2.0
								adjustShares = math.floor(shares * (t.getTotal() - 1.0))
							else:
								raise Exception("Invalid split value for %s" % t)
							shares += adjustShares
							adjustBasisStockDividend(ticker, adjustShares)
							twrr.addShares(ticker, adjustShares, 0)
						elif t.type == Transaction.adjustment:
							adjustedValue += t.getTotal()
							twrr.addAdjustment(t.getTotal())
						elif t.type == Transaction.spinoff:
							# Determine price per share
							if t.pricePerShare:
								pps = t.pricePerShare
							else:
								if update:
									update.addError("Transaction has no price per share: %s" % t)
								continue
	
							# Dividend if ticker, buy if ticker2
							if t.ticker == ticker:
								spinoffValue = t.shares * pps
								if value > 0:
									basisValue = getBasisValue(ticker)
									totalProfit += spinoffValue
									twrr.adjustBasis(ticker, spinoffValue)
									
									# Adjust basis
									percent = (basisValue - spinoffValue) / basisValue
									if percent < 0:
										percent = 0
									if percent >= 0:
										adjustBasisValue(ticker, percent)
									elif update:
										update.addError("adjust basis for spinoff, percent less than 0: %f - %f" % (basisValue, spinoffValue))
							else:
								shares += abs(t.shares)
								totalProfit -= pps
								twrr.addShares(ticker, t.getShares(), pps)
								
								# TODO: Handle for options?
								addToBasis(ticker, t.date, t.shares, pps)
						elif t.type == Transaction.tickerChange:
							if ticker == t.ticker:
								# Old ticker
								# TODO: Handle for options?
								removeFromBasis(ticker, shares)
								shares = 0
								
								# Force exit from loop, this stock no longer exists
								doneWithTicker = True
							else:
								# New ticker, get stock data of original ticker
								if currentTrans != 1:
									if update:
										update.addMessage("The ticker change transaction from %s to %s is not the first transaction for %s." % (t.ticker, t.ticker2, t.ticker2))
									continue
								pos = self.getPositionOnDate(t.ticker, t.date - datetime.timedelta(1))
								if not pos:
									if update:
										update.addMessage("The ticker change transaction from %s to %s does not have data" % (t.ticker, t.ticker2))
									continue
								
								# Start calculating based off of the position data
								# First use given transaction shares, if not, use position shares
								if t.shares > 0:
									shares = abs(t.shares)
								elif pos["shares"] > 0:
									shares = abs(pos["shares"])
								if shares > 0:
									pps = pos["value"] / shares
									# TODO: Handle for options?
									addToBasis(ticker, t.date, shares, pps)
						elif update:
							update.addError("Did not use transaction %s for rebuilding" % t)
						
						# Adjust for fee
						if t.fee:
							totalFees += t.fee
						if t.getFee():
							twrr.addFee(t.getFee())
							if ticker == "__CASH__":
								twrr.removeShares(ticker, t.getFee(), 1)
								shares -= t.getFee()
								value -= t.getFee()
					
					expired = checkOptionsExpiration(ticker, date)
					if expired:
						totalTrans += 1
					
					try:
						twrr.endTransactions()
					except Exception, e:
						if update:
							update.addException()

					# Build current value based on shares and price
					if currentPrice < len(prices):
						# Advance to next price if not cash
						if ticker != "__CASH__":
							while currentPrice < len(prices) - 1 and prices[currentPrice + 1]["date"] <= date:
								currentPrice += 1

						price = prices[currentPrice]["close"]
						if ticker == "__CASH__":
							value = shares
						elif getShares(ticker) >= 0:
							value = getShares(ticker) * price + adjustedValue
						else:
							# Short
							value = (price - getBasis(ticker)) * getShares(ticker) + adjustedValue
						
						twrr.setValue(ticker, price)
						
						# Use yesterday's value or today's value if position was opened today
						if todayDividends > 0:
							totalProfit += todayDividends
							totalDividends += todayDividends

							if ticker == "__CASH__":
								shares += todayDividends
								value += todayDividends

						# Adjust fee factor for fees today's fees
						# Use today's value or yesterday's value if position was closed today
					elif price:
						# Use last price
						value = getShares(ticker) * price + adjustedValue
					
					# Update value based on options
					optionsShares = getOptionsShares(ticker)
					optionsPrice = getOptionsBasis(ticker)
					if optionsShares > 0:
						value += optionsShares * optionsPrice
					elif optionsShares < 0:
						# Short
						value += (optionsPrice - getOptionsBasis(ticker)) * optionsShares
					
					if ticker == "__CASH__":
						profitFee = totalProfit
					else:
						profitFee = value + totalProfit
					
					profitDividend = profitFee + totalFees
					profitSplit = profitDividend - totalDividends

					if (abs(shares) + abs(getOptionsShares(ticker)) > 1.0e-6 or totalTrans > 0 or currentTrans < len(transactions) or ticker == "__CASH__") and not doneWithTicker:
						self.db.insert("positionHistory", {
							"date": date.strftime("%Y-%m-%d 00:00:00"),
							"ticker": ticker,
							"shares": getShares(ticker),
							"options": getOptionsShares(ticker),
							"value": value,
							"normSplit": twrr.getReturnSplit(),
							"normDividend": twrr.getReturnDiv(),
							"normFee": twrr.getReturnFee(),
							"profitSplit": profitSplit,
							"profitDividend": profitDividend,
							"profitFee": profitFee})
	
					d = datetime.datetime(date.year, date.month, date.day)				
					if d in combinedValue:
						combinedValue[d] += value
					else:
						combinedValue[d] = value
	
					date += datetime.timedelta(1)

			# Now build combined position
			if update:
				update.addMessage("Computing combined portfolio")
			allTransactions = self.getTransactions(ascending = True)
			cashTransactions = self.getTransactions("__CASH__", ascending = True, buysToCash = False)
			currentAllTrans = 0
			currentCashTrans = 0
			lastValue = 0.0
			cashNorm = 0.0
			cashNormSplit = 0.0
			normDividendFactor = 1
			normFeeFactor = 1
			cashIn = 0
			totalDividends = 0
			totalFees = 0
			normFee = 1.0
			normSplit = 1.0
			dates = sorted(combinedValue.keys())
			for date in dates:
				endOfDay = datetime.datetime(date.year, date.month, date.day, 23, 59, 59)
				value = combinedValue[date]
	
				# Update deposited/withdrawn money
				cashInToday = 0
				todayDividends = 0
				todayFees = 0
				while currentCashTrans < len(cashTransactions) and cashTransactions[currentCashTrans].date <= endOfDay:
					t = cashTransactions[currentCashTrans]
					if t.type in [Transaction.deposit, Transaction.transferIn]:
						cashIn += t.getTotal()
						cashInToday += t.getTotal()
					elif t.type in [Transaction.withdrawal, Transaction.transferOut]:
						cashIn += t.getTotal()
						cashInToday += t.getTotal()
					elif t.type in [Transaction.dividend, Transaction.adjustment, Transaction.expense]:
						# Dividends/adjustments are not cash in/out
						pass
					else:
						cashIn -= abs(t.total)
						cashInToday -= abs(t.total)
					currentCashTrans += 1
				
				# Update todayFees, todayDividends
				while currentAllTrans < len(allTransactions) and allTransactions[currentAllTrans].date <= endOfDay:
					t = allTransactions[currentAllTrans]
					if t.type == Transaction.expense:
						todayFees += abs(t.total) + abs(t.fee)
					elif t.fee and value > 0:
						todayFees += abs(t.fee)
					
					if t.type in [Transaction.dividend, Transaction.dividendReinvest] and value > 0:
						todayDividends += abs(t.total)
						if t.fee:
							todayDividends += abs(t.fee)
					
					currentAllTrans += 1

				if cashNorm == 0:
					cashNorm = cashInToday / normFee
					#print date, cashNorm
				elif cashInToday != 0 and lastValue != 0.0:
					#print date, cashNorm, "->",
					if value - cashInToday > 0:
						cashNorm *= value / (value - cashInToday)
					elif lastValue > 0:
						cashNorm *= (lastValue + cashInToday) / lastValue
					elif update:
						update.addError("cashIn but no value")
					#print cashNorm
					if value == 0:
						#print cashInToday, lastValue
						normFee *= -cashInToday / lastValue

				# Update cashNorms (normalized cash in)
				# Normalizes all future deposits and withdrawals
				if cashNormSplit == 0 and cashInToday != 0:
					# First deposit or a deposit when value has gone back to 0
					# Solve for cashNormSplit such that the old normSplit = cashInToday * cashNormSplit
					# Note first time through normFee is 1
					cashNormSplit = cashInToday / normSplit
				elif cashInToday != 0:
					if value - cashInToday != 0 and value != 0:
						cashNormSplit = (value - totalDividends) / (value - totalDividends - cashInToday) * cashNormSplit
					else:
						# Value goes to 0, update norm based on how much went out
						# Then set cashNormSplit to 0
						normSplit = -cashInToday / cashNormSplit
						cashNormSplit = 0
				
				if todayFees > 0:
					totalFees += todayFees
					if value > 0 and value - todayFees > 0:
						normFeeFactor *= (value + todayFees) / value
					elif lastValue > 0 and lastValue - todayFees > 0:
						normFeeFactor *= lastValue / (lastValue - todayFees)
					elif update:
						update.addError("Fee but no value")

				if todayDividends > 0:
					totalDividends += todayDividends
					if lastValue > 0:
						normDividendFactor *= (lastValue + todayDividends) / lastValue
					elif value > 0:
						normDividendFactor *= (value + todayDividends) / value
					elif update:
						update.addError("Dividend but no value")
	
				# Base performance on value divided by normalized cash
				if cashNorm > 0.0 and value > 0:
					normFee = value / cashNorm
				
				normDividend = normFee * normFeeFactor
				#print date, normFee, "*", normFeeFactor, "=", normDividend

				if cashNormSplit > 0 and value + totalFees - totalDividends > 0:
					normSplit = (value + totalFees - totalDividends) / cashNormSplit

				profitFee = value - cashIn
				profitDividend = profitFee + totalFees
				profitSplit = profitDividend - totalDividends
				
				self.db.insert("positionHistory", {
					"date": date.strftime("%Y-%m-%d 00:00:00"),
					"ticker": "__COMBINED__",
					"shares": value,
					"value": value,
					"normSplit": normSplit,
					"normDividend": normDividend,
					"normFee": normFee,
					"profitSplit": profitSplit,
					"profitDividend": profitDividend,
					"profitFee": profitFee})
				
				lastValue = value
			
			# Now build benchmark
			if update:
				update.addMessage("Computing benchmark")
			currentCashTrans = 0
			dates = sorted(combinedValue.keys())
			first = True
			if not self.isBenchmark():
				benchmark = Portfolio(self.getBenchmark())

				benchmarkShares = 0
				totalCashIn = 0
				benchmarkValues = benchmark.getPositionHistory("__COMBINED__")
				for date in dates:
					endOfDay = datetime.datetime(date.year, date.month, date.day, 23, 59, 59)
					
					# Update deposited/withdrawn money
					cashInToday = 0
					while currentCashTrans < len(cashTransactions) and cashTransactions[currentCashTrans].date <= endOfDay:
						t = cashTransactions[currentCashTrans]
						if t.type in [Transaction.deposit, Transaction.transferIn]:
							cashInToday += abs(t.total)
						elif t.type in [Transaction.withdrawal, Transaction.transferOut]:
							cashInToday -= abs(t.total)
						elif t.type in [Transaction.dividend, Transaction.adjustment, Transaction.expense]:
							# Dividends/adjustments are not cash in/out
							pass
						else:
							cashIn -= abs(t.total)
						currentCashTrans += 1
					
					# Buy or sell shares
					if cashInToday != 0:
						totalCashIn += cashInToday
						if date in benchmarkValues and benchmarkValues[date]['value'] != 0:
							benchmarkShares += cashInToday / benchmarkValues[date]['value']
					
					# Update values
					if date in benchmarkValues:
						value = benchmarkShares * benchmarkValues[date]['value']
						
						if first:
							first = False
							firstNormSplit = benchmarkValues[date]['normSplit']
							firstNormDividend = benchmarkValues[date]['normDividend']
							firstNormFee = benchmarkValues[date]['normFee']

						self.db.insert("positionHistory", {
							"date": date.strftime("%Y-%m-%d 00:00:00"),
							"ticker": "__BENCHMARK__",
							"shares": benchmarkShares,
							"value": value,
							"normSplit": benchmarkValues[date]['normSplit'] / firstNormSplit,
							"normDividend": benchmarkValues[date]['normDividend'] / firstNormDividend,
							"normFee": benchmarkValues[date]['normFee'] / firstNormFee,
							"profitSplit": value - totalCashIn,
							"profitDividend": value - totalCashIn,
							"profitFee": value - totalCashIn})

			self.portPrefs.setDirty(False)
			self.db.commitTransaction()
			appGlobal.getApp().endBigTask()
			if update:
				update.finishSubTask("Finished rebuilding " + self.name)
		except Exception:
			# An error occurred.  Rollback this update.
			self.db.rollbackTransaction()
			appGlobal.getApp().endBigTask()
			if update:
				update.addException()
				update.setFinished()
			else:
				raise
		
	def chartByType(self, chartBase, type):
		year = datetime.datetime.now() - datetime.timedelta(days = 365)
		threeMonths = datetime.datetime.now() - datetime.timedelta(days = 90)
		month = datetime.datetime.now() - datetime.timedelta(days = 30)

		stockData = appGlobal.getApp().stockData
		
		# Generate movers
		if type in [chart.oneMonthMovers, chart.threeMonthMovers, chart.oneYearMovers]:
			if type == chart.oneMonthMovers:
				period = month
			elif type == chart.threeMonthMovers:
				period = threeMonths
			elif type == chart.oneYearMovers:
				period = year
			period = datetime.datetime(period.year, period.month, period.day)
			
			tickers = self.getTickers()
			movers = []
			for t in tickers:
				if t == "__CASH__":
					continue
				firstLast = self.getPositionFirstLast(t)
				if not firstLast:
					continue
				(first, last) = firstLast
				
				# TODO: Skip if shares==0
				
				# Check that position is relatively recent
				if datetime.datetime.now() - last > datetime.timedelta(days = 90):
					continue
				
				(ret, years) = self.calculatePerformanceProfit(t, period, last, format = False)
				if ret == "n/a":
					continue
				movers.append([t, ret])
			if len(movers) > 5:
				def moverSort(a, b):
					# Sort by magnitude of profit change
					diff = abs(a[1]) - abs(b[1])
					if diff < 0:
						return 1
					elif diff > 0:
						return -1
					else:
						return 0
	
				movers.sort(moverSort)
				movers = movers[0:5]
			def moverSort2(a, b):
				# Sort by positive to negative
				diff = a[1] - b[1]
				if diff < 0:
					return 1
				elif diff > 0:
					return -1
				else:
					return 0
			#movers.sort(moverSort2)
			# Now remove the tuple, keep only the ticker
			movers2 = movers
			movers = []
			for m in movers2:
				movers.append(m[0])

		if type == chart.oneYearVsBenchmark:
			if self.isBenchmark():
				benchmark = False
				title = "One Year"
			else:
				benchmark = True
				title = "One Year vs. Benchmark"

			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.oneYear,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark,
				title = title)
		elif type == chart.oneYearVsBenchmarkCash:
			if self.isBenchmark():
				benchmark = False
				title = "One Year"
			else:
				benchmark = True
				title = "One Year vs. Benchmark"

			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.oneYear,
				chartType = "value",
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark,
				title = title)
		elif type == chart.threeMonthsVsBenchmark:
			if self.isBenchmark():
				benchmark = False
				title = "Three Months"
			else:
				benchmark = True
				title = "Three Months vs. Benchmark"

			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.threeMonths,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark,
				title = title)
		elif type == chart.threeMonthsVsBenchmarkCash:
			if self.isBenchmark():
				benchmark = False
				title = "Three Months"
			else:
				benchmark = True
				title = "Three Months vs. Benchmark"

			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.threeMonths,
				chartType = "value",
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark,
				title = title)
		elif type == chart.inceptionVsBenchmark:
			if self.isBenchmark():
				benchmark = False
				title = "Since Inception"
			else:
				benchmark = True
				title = "Since Inception vs. Benchmark"

			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.portfolioInception,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark,
				title = title)
		elif type == chart.inceptionVsBenchmarkCash:
			if self.isBenchmark():
				benchmark = False
				title = "Since Inception"
			else:
				benchmark = True
				title = "Since Inception vs. Benchmark"

			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.portfolioInception,
				chartType = "value",
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark,
				title = title)
		elif type == chart.oneMonthMovers:
			self.drawChart(
				chartBase,
				stockData,
				movers,
				chart.oneMonth,
				doDividend = True,
				title = "One Month Movers")
		elif type == chart.threeMonthMovers:
			self.drawChart(
				chartBase,
				stockData,
				movers,
				chart.threeMonths,
				doDividend = True,
				title = "Three Month Movers")
		elif type == chart.oneYearMovers:
			self.drawChart(
				chartBase,
				stockData,
				movers,
				chart.oneYear,
				doDividend = True,
				title = "One Year Movers")
		elif type == chart.oneMonthSpending:
			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.oneMonth,
				chartType = "monthly spending",
				doGradient = True,
				title = "One Month Spending")
		elif type == chart.threeMonthSpending:
			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.threeMonths,
				chartType = "monthly spending",
				doGradient = True,
				title = "Three Months Spending")
		elif type == chart.oneYearSpending:
			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.oneYear,
				chartType = "monthly spending",
				doGradient = True,
				title = "One Year Spending")
		elif type == chart.inceptionSpending:
			self.drawChart(
				chartBase,
				stockData,
				"__COMBINED__",
				chart.portfolioInception,
				chartType = "monthly spending",
				doGradient = True,
				title = "Spending Since Inception")
	
		chartBase.legend = True

	def drawChart(self, chartBase, stockData, tickers, period = chart.oneYear, chartType = "performance", doSplit = False, doDividend = False, doFee = False, doBenchmark = False, doGradient = False, title = False):
		# No gradient for spending
		if chartType == "spending":
			doGradient = False
		
		chartBase.reset()
		chartBase.title = title
		chartBase.doGradient = doGradient
		
		if self.isBank() and chartType in ["value", "spending", "monthly spending"]:
			chartBase.zeroYAxis = True

		# If only one ticker is supplied turn it into a list
		if type(tickers) != list:
			tickers = [tickers]
		if not tickers:
			return
			
		# No benchmark for banking
		if self.isBank():
			doBenchmark = False
			if chartBase.title:
				chartBase.title = chartBase.title.replace(" vs. Benchmark", "")
		
		if period == chart.oneWeek:
			startDate = datetime.datetime.now() - datetime.timedelta(7)
		elif period == chart.oneMonth:
			startDate = datetime.datetime.now() - datetime.timedelta(31)
		elif period == chart.threeMonths:
			startDate = datetime.datetime.now() - datetime.timedelta(90)
		elif period == chart.oneYear:
			startDate = datetime.datetime.now()
			startDate = datetime.datetime(startDate.year - 1, startDate.month, startDate.day)
		elif period == chart.twoYears:
			startDate = datetime.datetime.now()
			startDate = datetime.datetime(startDate.year - 2, startDate.month, startDate.day)
		elif period == chart.threeYears:
			startDate = datetime.datetime.now()
			startDate = datetime.datetime(startDate.year - 3, startDate.month, startDate.day)
		elif period == chart.fiveYears:
			startDate = datetime.datetime.now()
			startDate = datetime.datetime(startDate.year - 5, startDate.month, startDate.day)
		elif period == chart.tenYears:
			startDate = datetime.datetime.now()
			startDate = datetime.datetime(startDate.year - 10, startDate.month, startDate.day)
		elif period == chart.portfolioInception:
			startDate = self.getStartDate()
		else:
			# Position inception
			startDate = datetime.datetime(1900, 1, 1)
		
		# Bound startDate to the start of the portfolio
		firstLast = self.getPositionFirstLast(tickers[0])
		if firstLast:
			startDate = max(startDate, firstLast[0])
		else:
			startDate2 = self.getStartDate()
			if startDate2:
				startDate = max(startDate, startDate2)
			
		# Determine if we're charting since inception
		isInception = startDate == self.getStartDate()

		colors = [(0.2, 0.2, 1), (0, 0.8, 0), (1, 0, 0), (0.69, 0.28, 0.71), (0.97, 0.81, 0.09)]
		colorIndex = 0

		# Benchmark's don't have benchmarks
		if doBenchmark:
			if self.isBenchmark():
				benchmark = self
			else:
				benchmark = Portfolio(self.getBenchmark())
	
			# Rebuild benchmark if dirty and if auto rebuilding is not enabled
			if benchmark and benchmark.portPrefs.getDirty() and not appGlobal.getApp().prefs.getBackgroundRebuild():
				benchmark.rebuildPositionHistory(stockData)
			if benchmark:
				benchmarkHistory = benchmark.getPositionHistory("__COMBINED__", startDate)
				benchmarkKeys = sorted(benchmarkHistory.keys())
	
			# Check for empty benchmark
			if benchmark and len(benchmarkKeys) == 0:
				return
		
		if chartType in ["value", "profit", "transactions", "spending", "monthly spending"]:
			doDollars = True
		else:
			doDollars = False
		
		if chartType == "transactions":
			doSplit = True
			doDividend = False
			doFee = False

		normDate = False
		firstDate = False
		veryFirstValue = False
		endLoop = self.getEndDate()
		for ticker in tickers:
			# Get price data
			if chartType == "transactions":
				# Base on stock data for transactions chart
				# Build up pricesBase so it looks like position history data
				pricesTemp = stockData.getPrices(ticker, startDate = startDate, splitAdjusted = True)
				pricesBase = {}
				for p in pricesTemp:
					p["transactions"] = p["close"]
					p["value"] = p["close"]
					pricesBase[p["date"]] = p
			else:
				pricesBase = self.getPositionHistory(ticker, startDate)
			prices = pricesBase
	
			# Keys will be a list of all dates
			keys = sorted(prices.keys())
			if len(keys) == 0:
				continue
			firstDate = keys[0]
	
			# Next check for closed position
			d = firstDate
			d = datetime.datetime(d.year, d.month, d.day)
	
			# Now get old prices, fill in up to one week
			while d < endLoop:
				data = stockData.getPrice(ticker, d)
				if not data:
					d += datetime.timedelta(1)
					continue
				d += datetime.timedelta(1)
	
			chartTypes = []
			if chartType == "value":
				chartTypes.append("value")
			elif chartType == "transactions":
				chartTypes.append("transactions")
			elif chartType == "spending":
				chartTypes.append("spending")
			elif chartType == "monthly spending":
				chartTypes.append("monthly spending")
			elif chartType == "profit":
				if doSplit:
					chartTypes.append("profitSplit")
				if doDividend:
					chartTypes.append("profitDividend")
				if doFee:
					chartTypes.append("profitFee")
			else:
				if doSplit:
					chartTypes.append("normSplit")
				if doDividend:
					chartTypes.append("normDividend")
				if doFee:
					chartTypes.append("normFee")

			# Determine first date of first ticker
			# Used for benchmark normalization
			if ticker == tickers[0]:
				for p in keys:
					price = prices[p]["value"]
					if price != 0:
						normDate = p
						break
	
			# Only choose one type for benchmark
			myChartTypes = chartTypes
			if ticker == "__BENCHMARK__":
				if chartType == "profit":
					myChartTypes = ["profitDividend"]
				elif chartType == "value":
					myChartTypes = ["value"]
				else:
					myChartTypes = ["normDividend"]

			# Build X/Y and normalize
			for thisChartType in myChartTypes:
				firstValue = False
				pricesX = []
				pricesY = []
				for p in keys:
					if chartType == "profit":
						price = prices[p][thisChartType]
					elif chartType == "spending" or chartType == "monthly spending":
						break
					elif doDollars:
						price = prices[p]["value"]
					else:
						price = prices[p][thisChartType]

					if firstValue is False:
						if doDollars:
							# Keep track of start profit if not charting since inception
							if startDate and not isInception:
								if chartType == "profit":
									firstValue = price
								else:
									firstValue = 0
								firstValueNorm = 1
							else:
								firstValue = 0
								firstValueNorm = 1
						elif price != 0:
							firstValue = 1.0 / price
					if veryFirstValue is False:
						veryFirstValue = prices[p]["value"]
					if not firstValue is False:
						pricesX.append(p)
						if doDollars:
							pricesY.append(price * firstValueNorm - firstValue)
						else:
							pricesY.append(price * firstValue - 1)
				
				if len(tickers) > (1 + 1 if doBenchmark else 0):
					color = colors[colorIndex]
					colorIndex = (colorIndex + 1) % len(colors)
				elif thisChartType == "transactions":
					color = (0.2, 0.2, 1)
				elif thisChartType == "normSplit" or thisChartType == "profitSplit":
					color = (0.2, 0.2, 1)
				elif thisChartType == "normDividend" or thisChartType == "profitDividend" or thisChartType == "value":
					color = (0, 0.8, 0)
				elif thisChartType == "normFee" or thisChartType == "profitFee":
					color = (1, 0.2, 0.2)
	
				tickerName = ticker
				if tickerName == "__COMBINED__":
					tickerName = "Combined"
				elif tickerName == "__CASH__":
					tickerName = "Cash"
				if len(chartTypes) > 1:
					if thisChartType == "normSplit" or thisChartType == "profitSplit":
						tickerName += " Price"
					elif thisChartType == "normDividend" or thisChartType == "profitDividend":
						tickerName += " Dividends"
					elif thisChartType == "normFee" or thisChartType == "profitFee":
						tickerName += " Fees"

				if pricesX:
					chartBase.addXY(pricesX, pricesY, tickerName, color)
				
				# Add transactions
				if chartType == "transactions":
					buyX = []
					buyY = []
					sellX = []
					sellY = []
					splitX = []
					splitY = []
					dividendX = []
					dividendY = []
					dividendValue = []
					shortX = []
					shortY = []
					coverX = []
					coverY = []
					for t in self.getTransactions(ticker, ascending = True):
						d = t.date
		
						# Check 7 days prior to find a valid date
						found = False
						for j in range(7):
							date = datetime.datetime(d.year, d.month, d.day)
							date -= datetime.timedelta(days = j)
							if date in prices:
								found = True
								if chartType == "transactions":
									val = prices[date][thisChartType]
								elif doDollars:
									val = prices[date][thisChartType] * firstValue
								else:
									val = prices[date][thisChartType] * firstValue - 1
								break

						# Skip transaction if no price for this date
						if not found:
							continue
						
						if t.type == Transaction.buy or t.type == Transaction.transferIn:
							buyX.append(d)
							buyY.append(val)
						elif t.type == Transaction.sell or t.type == Transaction.transferOut:
							sellX.append(d)
							sellY.append(val)
						elif t.type == Transaction.split or t.type == Transaction.stockDividend:
							splitX.append(d)
							splitY.append(val)
						elif t.type == Transaction.dividend or t.type == Transaction.dividendReinvest:
							dividendX.append(d)
							dividendY.append(val)
							dividendValue.append(t.total)
						elif t.type == Transaction.short:
							shortX.append(d)
							shortY.append(val)
						elif t.type == Transaction.cover:
							coverX.append(d)
							coverY.append(val)
						# TODO: Handle options
					
					if buyX:
						chartBase.addBuys(buyX, buyY)
					if sellX:
						chartBase.addSells(sellX, sellY)
					if splitX:
						chartBase.addSplits(splitX, splitY)
					if dividendX:
						chartBase.addDividends(dividendX, dividendY, dividendValue)
					if shortX:
						chartBase.addShorts(shortX, shortY)
					if coverX:
						chartBase.addCovers(coverX, coverY)
		
				# Add spending
				if chartType == "spending":
					spendingX = []
					spendingY = []
					if ticker == "__COMBINED__":
						thisTicker = False
					else:
						thisTicker = ticker
					for t in self.getTransactions(thisTicker, ascending = True):
						d = t.date
						if d >= startDate and t.isBankSpending():
							spendingX.append(d)
							spendingY.append(abs(t.getTotal()))
					
					if spendingX:
						chartBase.addDividends(spendingX, spendingY, spendingY)

				# Add monthly spending
				if chartType == "monthly spending":
					spendingX = []
					spendingY = []
					if ticker == "__COMBINED__":
						thisTicker = False
					else:
						thisTicker = ticker
					transactions = self.getTransactions(thisTicker, ascending = True)
					
					# Add an extra month to start date only if it doesn't extend one month after portfolio
					firstLast = self.getPositionFirstLast(ticker)
					if firstLast:
						startDate = max(startDate - datetime.timedelta(61), firstLast[0] + datetime.timedelta(31))
					else:
						startDate -= datetime.timedelta(61)
					d = startDate
					
					now = datetime.datetime.now() - datetime.timedelta(31)
					now = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)
					spending = {}
					
					while d < now:
						# Add spending
						while len(transactions) > 0 and d >= transactions[0].getDate():
							t = transactions[0]
							if t.isBankSpending() and t.getDate() >= startDate:
								if not t.getDate() in spending:
									spending[t.getDate()] = abs(t.getCashMod())
								else:
									spending[t.getDate()] += abs(t.getCashMod())
							del transactions[0]
						
						# Remove spending if older than one month
						for thisD in spending.keys():
							if d - thisD > datetime.timedelta(31):
								del spending[thisD]

						# Add if later than one month
						if d - startDate >= datetime.timedelta(31):
							spendingX.append(d)
							spendingY.append(sum(spending.values()))

						d += datetime.timedelta(1)
					
					if spendingX:
						chartBase.addXY(spendingX, spendingY, tickerName, color)
						
		if doDollars:
			chartBase.yAxisType = "dollars"
		else:
			chartBase.yAxisType = "percent"
		
		# Benchmark = benchmarkDividend[p] * origPrice / origBenchmarkDividend
		if doBenchmark and firstDate and normDate:
			if doDollars:
				# Include cash transactions to buy/sell benchmark shares
				if ticker == "__COMBINED__" or ticker == "__CASH__":
					moneyIn = self.getTransactions("__CASH__", transType = Transaction.deposit) + self.getTransactions(transType = Transaction.transferIn)
					moneyOut = self.getTransactions("__CASH__", transType = Transaction.withdrawal) + self.getTransactions(transType = Transaction.transferOut)
				else:
					transactions = self.getTransactions(ticker)
					moneyIn = []
					moneyOut = []

					for t in transactions:
                                        	# Non cash buys and sells
                                        	if t.type in [Transaction.buy, Transaction.buyToOpen, Transaction.cover, Transaction.buyToClose, Transaction.transferIn]:
                                                	t2 = copy.deepcopy(t)
                                                	t2.ticker = "__CASH__"
                                                	t2.fee = 0.0
                                                	t2.type = Transaction.deposit
                                                	t2.total = t.getCashMod()
							moneyIn.append(t2)
                                        	elif t.type in [Transaction.sell, Transaction.sellToOpen, Transaction.short, Transaction.sellToClose, Transaction.transferOut]:
                                                	t2 = copy.deepcopy(t)
                                                	t2.ticker = "__CASH__"
                                                	t2.fee = 0.0
                                                	t2.type = Transaction.withdrawal
                                                	t2.total = t.getCashMod()
							moneyOut.append(t2)

				moneyIn.sort(key = operator.attrgetter('date'))
				moneyOut.sort(key = operator.attrgetter('date'))
				moneyInIndex = 0
				moneyOutIndex = 0
	
			pricesX = []
			pricesY = []
			if chartType == "transactions":
				norm = veryFirstValue / benchmarkHistory[benchmarkKeys[0]]["normSplit"]
				for p in benchmarkKeys:
					value = norm * benchmarkHistory[p]["normSplit"]
					pricesX.append(p)
					pricesY.append(value)
			elif chartType in ["profit", "value"]:
				# Determine profit based on shares purchased
				cashIn = 0
				shares = 0
				first = True
				for p in benchmarkKeys:
					# Buy/sell benchmark
					endOfDay = datetime.datetime(p.year, p.month, p.day, 23, 59, 59)
					while moneyInIndex < len(moneyIn) and moneyIn[moneyInIndex].date <= endOfDay:
						cashIn += abs(moneyIn[moneyInIndex].getTotalIgnoreFee())
						shares += abs(moneyIn[moneyInIndex].getTotalIgnoreFee()) / benchmarkHistory[p]["value"]
						moneyInIndex += 1
					while moneyOutIndex < len(moneyOut) and moneyOut[moneyOutIndex].date <= endOfDay:
						cashIn -= abs(moneyOut[moneyOutIndex].getTotalIgnoreFee())
						shares -= abs(moneyOut[moneyOutIndex].getTotalIgnoreFee()) / benchmarkHistory[p]["value"]
						moneyOutIndex += 1
					
					# If first value, buy enough benchmark to match starting value
					if first and not isInception:
						cashIn = veryFirstValue
						shares = veryFirstValue / benchmarkHistory[p]["value"]
						first = False

					# Calculate value.  Subtract of cashIn for profit.
					if moneyInIndex > 0 or moneyOutIndex > 0:
						value = shares * benchmarkHistory[p]["value"]
						if chartType == "profit":
							value -= cashIn
						pricesX.append(p)
						pricesY.append(value)
			else:
				# Determine benchmark normalization
				firstValue = False
				for p in benchmarkKeys:
					if p < normDate:
						continue
					
					firstValue = 1.0 / benchmarkHistory[p]["normDividend"]
					break
	
				# Add based on normalized value
				for p in benchmarkKeys:
					price = benchmarkHistory[p]["normDividend"]
					
					if firstValue:
						pricesX.append(p)
						pricesY.append(price * firstValue - 1)

			# Add data points for combined
			if pricesX and pricesY:
				chartBase.addXY(pricesX, pricesY, benchmark.name, (0.5, 0.5, 0.5))

	def getPerformanceTable(self, doCurrent = True, doDividend = True, type = "performance"):
		tickers = self.getTickers()
		if len(tickers) > 0:
			tickers.append("__COMBINED__")
			tickers.append("__BENCHMARK__")

		firstDayOfYear = datetime.datetime.now()
		firstDayOfYear = datetime.datetime(firstDayOfYear.year, 1, 1)
		oneYear = datetime.datetime.now() - datetime.timedelta(365.25)
		oneYear = datetime.datetime(oneYear.year, oneYear.month, oneYear.day)
		twoYear = datetime.datetime.now() - datetime.timedelta(365.25 * 2)
		twoYear = datetime.datetime(twoYear.year, twoYear.month, twoYear.day)
		threeYear = datetime.datetime.now() - datetime.timedelta(365.25 * 3)
		threeYear = datetime.datetime(threeYear.year, threeYear.month, threeYear.day)
		fiveYear = datetime.datetime.now() - datetime.timedelta(365.25 * 5)
		fiveYear = datetime.datetime(fiveYear.year, fiveYear.month, fiveYear.day)
		
		lastDay = self.getEndDate()

		row = 0
		tooltips = {}
		data = []
		rowMap = {}
		performance = {}
		
		# Iterate through copy of tickers, incase elements re removed
		for t in copy.copy(tickers):
			firstLast = self.getPositionFirstLast(t)
			if not firstLast:
				tickers.remove(t)
				continue
			(first, last) = firstLast
			
			# Check that the position is current
			if last != lastDay and doCurrent:
				tickers.remove(t)
				continue

			performance[t] = {}
			
			if type == "profit":
				performanceFunc = self.calculatePerformanceProfit
			elif type == "value":
				performanceFunc = self.calculatePerformanceValue
			else:
				performanceFunc = self.calculatePerformanceTimeWeighted
			
			# Compute YTD return
			(ret, years) = performanceFunc(t, firstDayOfYear, last, dividend = doDividend)
			performance[t][firstDayOfYear] = (ret, years)
			
			# Compute year return
			(ret, years) = performanceFunc(t, oneYear, last, dividend = doDividend)
			performance[t][oneYear] = (ret, years)

			# Compute two year return
			(ret, years) = performanceFunc(t, twoYear, last, dividend = doDividend)
			performance[t][twoYear] = (ret, years)

			# Compute three year return
			(ret, years) = performanceFunc(t, threeYear, last, dividend = doDividend)
			performance[t][threeYear] = (ret, years)

			# Compute five year return
			(ret, years) = performanceFunc(t, fiveYear, last, dividend = doDividend)
			performance[t][fiveYear] = (ret, years)

			# Compute inception return
			(ret, years) = performanceFunc(t, first, last, dividend = doDividend, isInception = True)
			performance[t][lastDay] = (ret, years)
			
			row += 1
		
		# Check active columns, always include last day
		activeCols = {lastDay: True}
		for t in performance:
			for date in performance[t]:
				(ret, yeras) = performance[t][date]
				if ret != "n/a":
					activeCols[date] = True
		dates = sorted(activeCols.keys())

		# Create columns
		cols = ["Position"]
		for date in dates:
			if date == firstDayOfYear:
				cols.append("YTD")
			elif date == oneYear:
				cols.append("One Year")
			elif date == twoYear:
				cols.append("Two Years")
			elif date == threeYear:
				cols.append("Three Years")
			elif date == fiveYear:
				cols.append("Five Years")
			elif date == lastDay:
				cols.append("Since Inception")

		tickers.sort()
		
		# Add returns
		row = 0
		for t in tickers:
			#name = stockData.getName(t)
			#if name:
			#	grid.getCtrl(row, 0).SetToolTipString(name)

			data.append([])
			rowMap[row] = row
			if t == "__COMBINED__":
				data[row].append("Combined")
			elif t == "__CASH__":
				data[row].append("Cash")
			elif t == "__BENCHMARK__":
				data[row].append(self.getBenchmark())
			else:
				data[row].append(t)

			tooltips[row] = {}
			col = 1
			for date in dates:
				if date in performance[t]:
					ret = performance[t][date][0]
					years = performance[t][date][1]
					
					#color = False
					tooltips[row][col] = ""
					if ret != "n/a":
						#if ret > "0":
						#	color = self.app.positiveTextColor
						#elif ret < "0":
						#	color = self.app.negativeTextColor
						tooltips[row][col] =  "From %d/%d/%d to %d/%d/%d (%.2f years)" % (first.month, first.day, first.year, date.month, date.day, date.year, years)
						#grid.addText(ret, color, tooltip = tooltips[row][col])
						data[row].append(ret)
					else:
						data[row].append("")
				else:
					data[row].append("no")
				
				col += 1
			
			row += 1

		return [cols, data]
	
	def getSpendingTable(self, days = False, categorize = False, doMonthly = True):
		tickers = self.getTickers()

		row = 0
		tooltips = {}
		data = []
		rowMap = {}
		spending = {}
		first = {}
		last = {}
		
		if days:
			firstDate = self.getLastTransactionDate() - datetime.timedelta(days = days)
		else:
			# Inception
			firstDate = self.getFirstTransactionDate()
			days = (self.getLastTransactionDate() - firstDate).days
		
		categories = {}
		
		# Iterate through copy of tickers, incase elements re removed
		for ticker in tickers:
			transactions = self.getTransactions(ticker)

			# Choose category or ticker
			if categorize:
				if not ticker in categories:
					categories[ticker] = self.getCategory(ticker)
				
				thisKey = categories[ticker]
			else:
				thisKey = ticker
			
			if not thisKey in spending:
				spending[thisKey] = 0
				first[thisKey] = False
			
			for t in transactions:
				if days and t.date < firstDate:
					continue
				
				# Update first/last transaction
				if not first[thisKey]:
					first[thisKey] = t.date
					last[thisKey] = t.date
				if t.date > last[thisKey]:
					last[thisKey] = t.date
				if t.date < first[thisKey]:
					first[thisKey] = t.date
				
				if t.isBankSpending():
					spending[thisKey] += abs(t.getTotal())

		# Create columns
		if categorize:
			cols = ["Category", "Spending"]
		else:
			cols = ["Position", "Spending"]
		if doMonthly and days > 31:
			cols.append("Spending/Month")
		
		# Add returns
		row = 0
		for t in spending:
			if spending[t] > 0:
				data.append([])
				data[row].append(t)
				data[row].append(Transaction.formatDollar(spending[t]))
				
				if doMonthly and days > 31:
					months = 12 * (last[t].year - first[t].year) + last[t].month - first[t].month + 1
					data[row].append(Transaction.formatDollar(round(float(spending[t]) / months, 2)))
				
				row += 1

		return [cols, data]

	def getAllocationTable(self):
		allocation = self.getAllocation()
		positions = self.getPositions(current = True)

		total = 0.0
		for p in positions:
			if p != "__COMBINED__" and positions[p]["value"] > 0.0:
				total += positions[p]["value"]
		self.total = total
				
		allTickers = {}
		for t in positions:
			allTickers[t] = True
		for t in allocation:
			allTickers[t] = True
		if "__COMBINED__" in allTickers:
			del allTickers["__COMBINED__"]
		allTickers = sorted(allTickers)
		self.allTickers = allTickers
		
		sumPercent = 0.0
		row = 1
		self.editors = {}
		data = []
		for ticker in allTickers:
			if ticker == "__COMBINED__":
				continue
			
			# Default everything to n/a
			currentRow = []

			if ticker in positions:
				current = positions[ticker]["value"] / total * 100.0
				currentDollar = Transaction.formatDollar(positions[ticker]["value"])
				if ticker in allocation:
					differenceDollar = positions[ticker]["value"] - total * allocation[ticker] / 100.0
				else:
					differenceDollar = positions[ticker]["value"]
				
				if not ticker in allocation:
					allocation[ticker] = 0.0
				
				# Try to delete everything with a 0 allocation
				if allocation[ticker] == 0.0:
					self.saveAllocation(ticker, False)
			else:
				current = 0.0
				currentDollar = Transaction.formatDollar(0.0)
				differenceDollar = -total * allocation[ticker] / 100.0

			sumPercent += allocation[ticker]
			differencePercent = current - allocation[ticker]
			dollarStr = locale.format("%.2f", abs(differenceDollar), True)
			if differenceDollar > 0:
				sign = "+"
			elif differenceDollar < 0:
				sign = "-"
			else:
				sign = ""
			
			currentRow.append(ticker)

			if ticker in allocation:
				currentRow.append("%s" % allocation[ticker])
			else:
				currentRow.append("")
			
			if current != "n/a":
				currentRow.append("%.2f%%" % current)
			
			if currentDollar != "n/a":
				currentRow.append(currentDollar)

			if differencePercent != "n/a":
				currentRow.append("%+.2f%%" % differencePercent)

			if dollarStr != "n/a":				
				currentRow.append("$%s%s" % (sign, dollarStr))
			
			if self.isBrokerage():
				# Get last stock data
				date = appGlobal.getApp().stockData.getLastDate(ticker)
				if date:
					value = appGlobal.getApp().stockData.getPrice(ticker, date)
					cash = positions["__CASH__"]["value"]
					if value:
						if cash > 0 and differenceDollar < -cash:
							differenceDollar = -cash
						shares = differenceDollar / value["close"]
						if shares > 0:
							currentRow.append("Sell %.2f" % shares)
						elif shares < 0:
							# Buy up to cash amount of shares if we can't totally rebalance
							# Or buy rebalancing amount plus remaining balance
							if differenceDollar > -cash:
								currentRow.append("Buy %.2f to %.2f" % (abs(shares), cash / value["close"]))
							else:
								currentRow.append("Buy %.2f" % abs(shares))
						else:
							currentRow.append("")

			row += 1
			data.append(currentRow)

		currentRow = ["Total", "%.2f%%" % sumPercent, "100.0%", "$" + locale.format("%.2f", total, True)]
		data.append(currentRow)
		
		return data
	
	def getSummaryTable(self):
		f = self.getPositionFirstLast("__COMBINED__")
		if not f:
			return
		(firstDate, lastDate) = f
		firstOfYear = datetime.datetime(lastDate.year, 1, 1)
		
		# Check if first of year is valid
		# If not use first portfolio date
		pos = self.getPositionOnDate("__COMBINED__", firstOfYear)
		if not pos:
			firstOfYear = firstDate

		inflow = self.sumInflow(firstOfYear, lastDate)
		divs = self.sumDistributions(firstOfYear, lastDate)
		fees = self.sumFees(firstOfYear, lastDate)
		pos = self.getPositionOnDate("__COMBINED__", firstOfYear)
		posYtd = self.getPositionOnDate("__COMBINED__", lastDate)
		
		valueYtd = "$" + locale.format("%.2f", posYtd["value"], True)
		inflowYtd = "$" + locale.format("%.2f", inflow, True)
		if pos["normDividend"] != 0.0:
			returnYtd = locale.format("%.2f", (posYtd["normDividend"] / pos["normDividend"] - 1.0) * 100.0) + "%"
		else:
			returnYtd = "n/a"
		divsYtd = "$" + locale.format("%.2f", divs, True)
		feesYtd = "$" + locale.format("%.2f", fees, True)
		if fees > 0:
			feesYtd = "-" + feesYtd
		
		table = []
		def addItem(row, col, text, isNumeric = False, isNegative = False, color = False):
			if col == 0:
				table.append([])
			table[row].append(text)

		addItem(0, 0, "")
		addItem(0, 1, str(lastDate.year) + " YTD")

		addItem(1, 0, "Value")
		addItem(1, 1, valueYtd)

		addItem(2, 0, "Inflow")
		addItem(2, 1, inflowYtd)

		addItem(3, 0, "Dividends")
		addItem(3, 1, divsYtd, isNumeric = True)

		addItem(4, 0, "Fees")
		addItem(4, 1, feesYtd, isNumeric = True, isNegative = True)

		addItem(5, 0, "Returns")
		addItem(5, 1, returnYtd, isNumeric = True)
		
		year = lastDate.year - 1
		col = 2
		while 1:
			if self.getSummaryYears() == "thisYear":
				break

			firstOfLastYear = datetime.datetime(year, 1, 1)
			lastYearEndDate = datetime.datetime(year, 12, 31)

			lastPosEnd = self.getPositionOnDate("__COMBINED__", lastYearEndDate)
			
			# No data at end of year
			if not lastPosEnd:
				break

			lastInflowYear = self.sumInflow(firstOfLastYear, lastYearEndDate)
			lastDivsYear = self.sumDistributions(firstOfLastYear, lastYearEndDate)
			lastFeesYear = self.sumFees(firstOfLastYear, lastYearEndDate)
			lastPos = self.getPositionOnDate("__COMBINED__", firstOfLastYear)
					
			lastInflowEnd = "$" + locale.format("%.2f", lastInflowYear, True)
			lastValueEnd = "$" + locale.format("%.2f", lastPosEnd["value"], True)
			if lastPos:
				lastReturnEnd = locale.format("%.2f", (lastPosEnd["normDividend"] / lastPos["normDividend"] - 1.0) * 100.0) + "%"
			else:
				lastReturnEnd = "n/a"
			lastDivsEnd = "$" + locale.format("%.2f", lastDivsYear, True)
			lastFeesEnd = "$" + locale.format("%.2f", lastFeesYear, True)
			if lastFeesYear > 0:
				lastFeesEnd = "-" + lastFeesEnd
			
			table[0].append(str(year))
	
			addItem(1, col, lastValueEnd)
			addItem(2, col, lastInflowEnd)
			addItem(3, col, lastDivsEnd, isNumeric = True)
			addItem(4, col, lastFeesEnd, isNumeric = True, isNegative = True)
			addItem(5, col, lastReturnEnd, isNumeric = True)
	
			year -= 1
			col += 1
			
			if self.getSummaryYears() != "allYears":
				break

		return table
	
	def errorCheck(self, stockData):
		errors = []
		
		# Check for negative cash positions
		cash = self.getPositionHistory("__CASH__")
		for date in sorted(cash.keys()):
			if cash[date]["value"] < 0:
				errors.append(["Cash position is negative", "Severe", "This portfolio's cash position is $%.2f on %d/%d/%d.  This is likely due to a missing or incorrectly entered deposit, sell or dividend transaction." % (cash[date]["value"], date.month, date.day, date.year)])
				break
		
		# Check for first transaction not buy or no transactions
		for ticker in self.getPositions():
			if ticker == "__CASH__" or ticker == "__COMBINED__":
				continue
			
			transactions = self.getTransactions(ticker, limit = 1, ascending = True)
			
			if len(transactions) == 0:
				errors.append(["No transactions", "Minor", "There are no transactions for %s" % ticker])
				continue
			
			if not transactions[0].type in [Transaction.buy, Transaction.transferIn, Transaction.spinoff]:
				errors.append(["First transaction is not buy", "Severe", "The first transaction for %s is not a buy transaction.  This position will not be included in performance calculations.  Add a buy transaction, a transfer transaction or a spinoff transaction for this position." % ticker])
				
		# Check for data not matching positionCheck
		for ticker in self.getPositions():
			didSevere = False
			didMinor = False
			
			# Keep track of the last correct date for this ticker
			lastCorrectDate = False
			
			checks = self.getPositionCheck(ticker)
			for check in checks:
				pos = self.getPositionForCheck(ticker, check)
				
				# If position data is available first check shares, then value
				if pos:
					# Check value difference of more than 5%
					if floatCompare(check.value, pos["value"]) > 1.05 and not didMinor and not didSevere:
						text = "The computed value for %s  on %s is incorect.  The computed value is %s but the correct value is %s.  This could be due to a missing or incorrect transaction or an incorrect stock value." % (ticker, check.date.strftime("%m/%d/%Y"), Transaction.formatDollar(pos["value"]), Transaction.formatDollar(check.value))
						if lastCorrectDate:
							text += "  The last correct date was on %s." % lastCorrectDate.strftime("%m/%d/%Y")
						errors.append(["Computed value is incorrect", "Minor", text])
						didMinor = True
						continue

					if abs(check.shares - pos["shares"]) > 1.0e-6:
						if floatCompare(check.shares, pos["shares"]) < 1.01:
							if not didMinor:
								text = "The computed shares for %s on %s is incorrect.  The computed shares is %s but the correct shares is %s.  This could be due to a missing or incorrect buy, sell or stock split transaction." % (ticker, check.date.strftime("%m/%d/%Y"), Transaction.formatFloat(pos["shares"]), Transaction.formatFloat(check.shares))
								if lastCorrectDate:
									text += "  The last correct date was on %s." % lastCorrectDate.strftime("%m/%d/%Y")
								errors.append(["Computed shares is incorrect", "Minor", text])
								didMinor = True
								continue
						elif not didSevere:
							text = "The computed shares for %s on %s is incorrect.  The computed shares is %s but the correct shares is %s.  This position will not be included in performance calculations.  This could be due to a missing or incorrect buy, sell or stock split transaction." % (ticker, check.date.strftime("%m/%d/%Y"), Transaction.formatFloat(pos["shares"]), Transaction.formatFloat(check.shares))
							if lastCorrectDate:
								text += "  The last correct date was on %s." % lastCorrectDate.strftime("%m/%d/%Y")
							errors.append(["Computed shares is incorrect", "Severe", text])
							didSevere = True
							continue
					
					# Break if did both minor and major
					if didMinor and didSevere:
						break
					
					# Update last correct date if no error yet
					if not didMinor and not didSevere:
						lastCorrectDate = check.date

		# Check for missing splits
		for ticker in self.getPositions():
			(first, last) = self.getPositionFirstLast(ticker)
			dataSplits = stockData.getSplits(ticker, first, last)
			portSplits = self.getTransactions(ticker, transType = Transaction.stockDividend)
			for t in self.getTransactions(ticker, transType = Transaction.split):
				portSplits.append(t)
			
			# Try to match actual splits with portfolio splits
			if dataSplits and portSplits:
				for s in dataSplits:
					for s2 in portSplits:
						diff = abs(s["date"] - s2.date)
						
						if diff < datetime.timedelta(7):
							position = self.getPositionOnDate(ticker, s["date"])
							if position:
								if s2.type == Transaction.stockDividend:
									# Determine shares before ths split
									# TODO: make work with buys/sells/etc
									shares = position["shares"] - position["shares"] / s["value"]
									portShares = s2.shares
									if abs(shares - portShares) > 1.0e-6:
										# Match but incorrect shares
										errors.append(["Incorrect stock dividend for " + ticker, "Moderate", "A stock dividend occurred on %d/%d/%d.  The portfolio transaction has %f shares but the proper number is %f." % (s2.date.month, s2.date.day, s2.date.year, portShares, shares)])
								else:
									if abs(s2.total - s["value"]) > 1.0e-6:
										# Match but incorrect shares
										errors.append(["Incorrect split for " + ticker, "Moderate", "A split occurred on %d/%d/%d.  The portfolio transaction has a value of %s (%.2f) but the proper value is %s (%.2f)." % (s2.date.month, s2.date.day, s2.date.year, Transaction.splitValueToString(s2.total), s2.total, Transaction.splitValueToString(s["value"]), s["value"])])
								dataSplits.remove(s)
								portSplits.remove(s2)
								break
			
			if dataSplits:
				for s in dataSplits:
					date = s["date"]
					
					# Determine split value
					splitVal = "?-?"
					if s["value"] > 1:
						# guess denom from 1-10
						min = 1.0e6
						minDenom = -1
						for denom in range(1, 11):
							num = s["value"] * denom
							diff = abs(num - round(num))
							if diff < min * 0.0001:
								minDenom = denom
								min = diff
						splitVal = "%d-%d" % (int(round(s["value"] * minDenom)), minDenom)
					
					# Determine shares for stock dividend
					shares = "?"
					position = self.getPositionOnDate(ticker, s["date"])
					if position:
						shares = position["shares"] * (s["value"] - 1.0)
						shares = "%.3f" % shares

					errors.append(["Missing split for " + ticker, "Severe", "A %s split occurred on %d/%d/%d.  A Stock Dividend transaction should be added for %s shares." % (splitVal, date.month, date.day, date.year, shares)])
			
			if portSplits:
				for s2 in portSplits:
					errors.append(["Invalid split for " + ticker, "Severe", "This portfolio has a stock dividend on %d/%d/%d although no such stock dividend or stock split exists." % (s2.date.month, s2.date.day, s2.date.year)])
		
		return errors

def checkBenchmarks(prefs):
	def doCheck(name, allocation):
		if not prefs.hasPortfolio(name):
			prefs.addPortfolio(name)
		p = Portfolio(name)
		if not p.isBenchmark():
			p.makeBenchmark()
	
		pAllocation = p.getAllocation()
		if pAllocation != allocation:
			# Delete old allocation
			for a in pAllocation:
				p.saveAllocation(a, "")
			# Add new allocation
			for a in allocation:
				p.saveAllocation("", a, allocation[a])
	
	doCheck("S&P 500", {"VFINX": 100.0})
	doCheck("Aggressive", {"VTSMX": 75.0, "VBMFX": 25.0})
