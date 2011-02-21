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
from brokerage import *
from ofxToolkit import *
from fileFormats import *
from transaction import *
from userprice import *
from positionCheck import *

import prefs
import autoUpdater
import chartWidget

import datetime
import time
import os
import copy
import operator

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
		self.checkDefaults("positionPeriod", "Since Inception")
		self.checkDefaults("performanceCurrent", "False")
		self.checkDefaults("performanceDividends", "True")
		self.checkDefaults("lastImport", "ofx")
		self.checkDefaults("combinedComponents", "")

	def getTransactionId(self):
		id = self.getPreference("nextTransactionId")
		
		self.db.update("prefs", {"value": int(id) + 1}, {"name": "nextTransactionId"})
		
		return id

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
	
	def getPositionPeriod(self):
		return self.getPreference("positionPeriod")

	def getPerformanceCurrent(self):
		return self.getPreference("performanceCurrent") == "True"

	def getPerformanceDividends(self):
		return self.getPreference("performanceDividends") == "True"

	def getLastImport(self):
		return self.getPreference("lastImport")

	def getCombinedComponents(self):
		return self.getPreference("combinedComponents").split(",")

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

class Portfolio:	
	def __init__(self, name, brokerage = "", username = "", account = ""):
		self.open(name)
		
	def open(self, name):
		info = prefs.prefs.getPortfolioInfo(name)
		if not info:
			raise Exception("No portfolio " + name)

		self.name = name
		self.brokerage = info["brokerage"]
		self.username = info["username"]
		self.account = info["account"]
	
		self.db = Db(prefs.Prefs.getPortfolioPath(name))

		self.portPrefs = PortfolioPrefs(self.db)
		self.portPrefs.checkDefaults("nextTransactionId", "1")
		self.portPrefs.checkDefaults("lastTicker", "__COMBINED__")
		self.portPrefs.checkDefaults("benchmark", "S&P 500")
		self.portPrefs.checkDefaults("isBrokerage", "True")
		self.portPrefs.checkDefaults("isBenchmark", "False")
		self.portPrefs.checkDefaults("isCombined", "False")
		self.portPrefs.checkDefaults("summaryYears", "lastYear")
		self.portPrefs.checkDefaults("summaryChart1", chartWidget.oneYearVsBenchmarkCash)
		self.portPrefs.checkDefaults("summaryChart2", chartWidget.oneMonthMovers)

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
			{"name": "edited", "type": "bool not null default False"},
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
			{"name": "value", "type": "float"},
			{"name": "normSplit", "type": "float"},
			{"name": "normDividend", "type": "float"},
			{"name": "normFee", "type": "float"}])
		
		self.db.checkTable("allocation", [
			{"name": "ticker", "type": "text"},
			{"name": "percentage", "type": "float"}],
			index = [{"name": "tickerIndex", "cols": ["ticker"]}])
		
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
		
		return datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
	
	def delete(self, prefs):
		self.db.close()
		os.remove(prefs.getPortfolioPath(self.name))
		prefs.deletePortfolio(self.name)
	
	def updateFromFile(self, data, app, status):
		status.setSubTask(50)
		status.setStatus("Parsing transactions", 10)
		
		if AmeritradeCsv().Guess(data):
			format = AmeritradeCsv()
		elif Ofx().Guess(data):
			format = Ofx()
		elif Ofx2().Guess(data):
			format = Ofx2()
		else:
			status.addError("Unknown file format")
			status.finishSubTask()
			status.setStatus("Aborted", 100)
			return

		(numNew, numOld, newTickers) = format.StartParse(data, self, status)
		
		status.setStatus("Parsing transactions")
		status.finishSubTask()

		# Download new stock data
		autoUpdater.wakeUp()
		if autoUpdater.percentDone() == 100:
			status.setStatus(level = 99)
		else:
			status.setSubTask(99)
			status.setStatus("Downloading stock data\nWarning: This operation may take a while")
			# Wait for downloading to finish
			autoUpdater.wakeUp()
			while not autoUpdater.sleeping():
				status.setStatus(level = autoUpdater.percentDone())
				time.sleep(1)
			status.finishSubTask()
			
		# Check for new positions not in stockData
		if newTickers:
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
				QMessageBox(QMessageBox.Information, "Could not find stock data", message).exec_()

		self.portPrefs.setDirty(True)
		status.setStatus("Finished\nImported %d new transactions.\n%d transactions had already been imported." % (numNew, numOld), 100)
		status.setFinished()

	def readFromDb(self):
		res = self.db.select("transactions")
		
		self.transactions = []
		for row in res.fetchall():
			t = Transaction(
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

	def isBenchmark(self):
		return self.portPrefs.getPreference("isBenchmark") == "True"

	def isCombined(self):
		return self.portPrefs.getPreference("isCombined") == "True"

	def makeBenchmark(self):
		self.db.update("prefs", {"value": "True"}, {"name": "isBenchmark"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBrokerage"})
	
	def makeCombined(self):
		self.db.update("prefs", {"value": "True"}, {"name": "isCombined"})
		self.db.update("prefs", {"value": "False"}, {"name": "isBrokerage"})

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
			return datetime.datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S")
		return False		

	def getEndDate(self):
		cursor = self.db.select("positionHistory", orderBy = "date desc", limit = 1)
		row = cursor.fetchone()
		if row:
			return datetime.datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S")
		return False		

	def getTransactions(self, ticker = False, ascending = False, getDeleted = False, deletedOnly = False, buysToCash = True, limit = False, transType = False):
		retTrans = []
		
		count = 0
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
					elif t.type in [Transaction.buy, Transaction.expense]:
						# Buy transaction treated as withdrawal
						t2 = copy.deepcopy(t)
						t2.type = Transaction.withdrawal
						t2.total = -abs(t2.total)
						t2.fee = 0.0
						retTrans.append(t2)
					elif t.type in [Transaction.sell, Transaction.dividend]:
						# Sell transaction treated as deposit
						t2 = copy.deepcopy(t)
						t2.type = Transaction.deposit
						t2.total = abs(t2.total)
						t2.fee = 0.0
						retTrans.append(t2)
					elif t.type == Transaction.adjustment:
						if t.total < 0:
							# Negative adjustment as withdrawal
							t2 = copy.deepcopy(t)
							t2.type = Transaction.withdrawal
							t2.total = -abs(t2.total)
							t2.fee = 0.0
							retTrans.append(t2)
						else:
							# Positive adjustment as deposit
							t2 = copy.deepcopy(t)
							t2.type = Transaction.deposit
							t2.total = abs(t2.total)
							t2.fee = 0.0
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
				elif (not ticker or t.ticker.upper() == ticker or (t.ticker2 and t.ticker2 != "False" and t.ticker2.upper() == ticker)):
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
		'''Get a dividend nearest to the given ticker and date'''
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
			if t.type in [Transaction.buy, Transaction.sell]:
				# Add to user prices
				# Note there may already be a user price for this date
				
				if t.pricePerShare:
					price = t.pricePerShare
				else:
					price = t.total / t.shares
				userPrices.append(UserPrice(t.date, t.ticker, price))

		# Add user prices and transaction prices to prices array
		for p in userPrices:
			date = self.strToDatetime(p.date, zeroHMS = True)

			# Check if date is already there
			found = False
			for p2 in prices:
				if p2["date"] == date:
					found = True
					break
			if not found:
				prices.append({'volume': 0, 'high': p.price, 'low': p.price, 'date': date, 'close': p.price, 'open': p.price})
		
	
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

		if row['minDate'] == None or row['maxDate'] == None:
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
	def calculatePerformanceTimeWeighted(self, ticker, first, last, divide = True, dividend = True, format = True):
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
		
		if divide:
			ret = val2 / val1
		else:
			ret = val2
		if days > 365:
			ret = pow(ret, 365.0 / days)
		if format:
			ret = "%.2f%%" % (100.0 * ret - 100.0)
		
		#print ticker, ret, val1, val2, years, days, first, last
		return (ret, years)
	
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

			# Compute value if we own shares
			if shares:
				newValue = 0.0
				doNewValue = False
				for ticker in shares:
					# Get current price
					while currentStockPrice[ticker] < len(stockPrices[ticker]) and stockPrices[ticker][currentStockPrice[ticker]]["date"] < date:
						currentStockPrice[ticker] += 1
					if currentStockPrice[ticker] < len(stockPrices[ticker]) and stockPrices[ticker][currentStockPrice[ticker]]["date"] == date:
						val = stockPrices[ticker][currentStockPrice[ticker]]
					
						# Get current dividend
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
					value = newValue
					#print date, newValue
					
			# Rebalance on the first transaction and on the first of every eyar
			if date.year != currentYear:
				stockVal = {}
				for ticker in positions:
					val = stockData.getPrice(ticker, date)
					if currentStockPrice[ticker] < len(stockPrices[ticker]):
						val = stockPrices[ticker][currentStockPrice[ticker]]
						stockVal[ticker] = val
				
				# Rebalance if data is available today (exchanges are open)
				if stockVal:
					currentYear = date.year
					
					if not shares:
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
							
							# amount is > 0 for sell, < 0 for buy
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

	def rebuildPositionHistory(self, stockData, update = False):
		self.db.beginTransaction()
		self.readFromDb()
		
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
			return

		# Total combined value indexed by date
		combinedValue = {}
		
		# Dictionary key is ticker, content is list of (date, shares, price per share)
		basis = {}
		
		# TODO: do not combine individual days
		def addToBasis(ticker, d, s, pps):
			if ticker not in basis:
				basis[ticker] = {}
			if d in basis[ticker]:
				# Update basis for this day
				(oldShares, oldPricePerShare) = basis[ticker][d]
				newShares = s + oldShares
				if newShares == 0:
					return
				newPricePerShare = (oldShares * oldPricePerShare + s * pps) / newShares
				basis[ticker][d] = (newShares, newPricePerShare)
			else:
				basis[ticker][d] = (s, pps)
		
			# Update combined basis
			d = datetime.datetime(d.year, d.month, d.day)
			if not d in combinedBasis:
				combinedBasis[d] = 0.0
			combinedBasis[d] += abs(s * pps)

		def removeFromBasis(ticker, remove):
			remove = abs(remove)
			while len(basis[ticker]) > 0 and remove > 0:
				(s, pricePerShare) = basis[ticker][basis[ticker].keys()[0]]
				if s > remove:
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
			if remove > 1.0e-6:
				print "Could not finish basis for", ticker, remove, basis[ticker]
		
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
			
			print "Computing position", ticker
			self.readFromDb()
			transactions = self.getTransactions(ticker, ascending = True)
			
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
				for i in (2, 1, 0):
					shares = 0
					targetDate = check.date + datetime.timedelta(days = i)

					# First sum up number of computed shares until check
					if ticker == "__CASH__":
						for t in transactions:
							# Only use check if it's valid
							if t.date > targetDate:
								continue
	
							if t.type in [Transaction.deposit, Transaction.dividend, Transaction.adjustment]:
								shares += abs(t.total)
							elif t.type in [Transaction.withdrawal, Transaction.expense]:
								shares -= abs(t.total)
							else:
								print "Unknown cash transaction", t
					else:
						for t in transactions:
							# Only use check if it's valid
							if t.date > targetDate:
								continue
							
							if t.type in [Transaction.buy, Transaction.dividendReinvest, Transaction.transferIn]:
								shares += abs(t.shares)
							elif t.type in [Transaction.sell, Transaction.transferOut]:
								shares -= abs(t.shares)
							elif t.type in [Transaction.stockDividend, Transaction.split]:
								if t.type == Transaction.stockDividend:
									adjustShares = t.shares
								else:
									adjustShares = shares * (t.total - 1.0)
		
								shares += adjustShares
							elif t.type == Transaction.spinoff and t.ticker2 == ticker:
								shares += abs(t.shares)

					# Check for match
					if abs(check.shares - shares) < 1.0e-6:
						foundMatch = True
						break

				# Now compare.  Add deposit for __CASH__, transfer for stock
				if not foundMatch:
					# Add shares based on the first date
					addShares = check.shares - shares
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
							price = stockData.getPrice(ticker, check.date)
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
								update.addMessage("No data found for %s on %s" % (ticker, check.date.strftime("%B %d, %Y")))
							print "no price", portfolioFirstDate, check
				elif check.shares < shares:
					print "ERROR TOO MANY SHARES should be", check.shares, "but is", shares
			
			# If no transactions for a stock, skip
			# The cash position may have no transactions if all we have is a transfer in
			if not transactions and ticker != "__CASH__":
				print "No transactions for", ticker
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
			if transactions:
				date = transactions[0].getDate()
			else:
				date = portfolioFirstDate
			date = datetime.datetime(date.year, date.month, date.day, 23, 59, 59)
			price = False
			shares = 0.0
			value = 0.0
			adjustedValue = 0.0
			normSplit = 1.0
			normDividend = 1.0
			normFee = 1.0
			normSplitFactor = prices[0]["close"]
			normDividendFactor = normSplitFactor
			normFeeFactor = normSplitFactor
			yieldCount = 0
			doneWithTicker = False
			while date < now and not doneWithTicker:
				yieldCount += 1
				if yieldCount == 100:
					yieldCount = 0
					if update:
						update.appYield()
						if update.canceled:
							break
				totalFees = 0
				totalTrans = 0
				while currentTrans < len(transactions) and transactions[currentTrans].getDate() <= date and not doneWithTicker:
					t = transactions[currentTrans]
					
					# Check that first transaction is a buy or transferIn (if not cash), or a spinoff or tickerChange and we are ticker2
					if currentTrans == 0 and ticker != "__CASH__":
						if t.type != Transaction.buy and t.type != Transaction.transferIn and ((t.type != Transaction.spinoff and t.type != Transaction.tickerChange) or t.ticker2 != ticker):
							break
					currentTrans += 1
					totalTrans += 1
					
					if t.type == Transaction.deposit:
						shares += abs(t.total)
					elif t.type == Transaction.withdrawal:
						shares += -abs(t.total)
					elif t.type == Transaction.buy or t.type == Transaction.transferIn:
						# Lookup price if unavailable
						if t.pricePerShare < 1.0e-6:
							p = stockData.getPrice(ticker, t.date)
							if p:
								t.pricePerShare = p["close"]
							else:
								print "buy transactions has no price per share", t
								continue
						
						# First buy should reset the split factor
						if currentTrans == 1:
							normSplitFactor = t.pricePerShare
							normDividendFactor = normSplitFactor
							normFeeFactor = normSplitFactor

						shares += abs(t.shares)
						
						# Add to basis tracker
						addToBasis(ticker, t.date, t.shares, t.pricePerShare)
					elif t.type == Transaction.sell:
						shares -= abs(t.shares)
						
						# Remove t.shares from basis tracker
						removeFromBasis(ticker, t.shares)
					elif t.type == Transaction.dividend:
						if ticker == "__CASH__":
							shares += abs(t.total)
						if value > 0 and t.total > 0:
							normDividendFactor *= value / (value + t.total)
							normFeeFactor *= value / (value + t.total)
						else:
							# error
							pass
					elif t.type == Transaction.expense:
						if ticker == "__CASH__":
							shares -= abs(t.total)
						if value > 0 and t.total > 0:
							normDividendFactor *= value / (value - t.total)
							normFeeFactor *= value / (value - t.total)
						else:
							# error
							pass
					elif t.type in [Transaction.dividendReinvest]:
						if t.pricePerShare < 1.0e-6:
							if t.total > 0:
								t.pricePerShare = t.total / t.shares
							else:
								p = stockData.getPrice(ticker, t.date)
								if p:
									t.pricePerShare = p["close"]
								else:
									print "transaction has no price per share", t
									continue
						
						# Set norm for first transaction if transfer in
						if t.type == Transaction.transferIn and currentTrans == 1:
							normSplitFactor = t.pricePerShare
							normDividendFactor = normSplitFactor
							normFeeFactor = normSplitFactor
						elif value > 0 and t.total > 0:
							normDividendFactor *= value / (value + t.total)
							normFeeFactor *= value / (value + t.total)
						else:
							# error
							pass

						shares += abs(t.shares)
						
						# Add to basis tracker
						addToBasis(ticker, t.date, t.shares, t.pricePerShare)
					elif t.type == Transaction.transferOut:
						if t.pricePerShare < 1.0e-6:
							if t.total > 0:
								t.pricePerShare = t.total / t.shares
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
						
						if value > 0 and t.total > 0:
							normDividendFactor *= (value + t.total) / value
							normFeeFactor *= (value + t.total) / value
						else:
							# error
							pass

						shares -= abs(t.shares)
						print ticker, "shares to", shares
						
						# Remove t.shares from basis tracker
						removeFromBasis(ticker, t.shares)
					elif t.type in [Transaction.stockDividend, Transaction.split]:
						if t.type == Transaction.stockDividend:
							adjustShares = t.shares
						else:
							adjustShares = math.floor(shares * (t.total - 1.0))
						# Note: Could be problem if buy/sell on same day
						if adjustShares > 0 and shares > 1.0e-6:
							normSplitFactor *= shares / (shares + adjustShares)
							normDividendFactor *= shares / (shares + adjustShares)
							normFeeFactor *= shares / (shares + adjustShares)
						else:
							# error
							pass
						shares += adjustShares

					# TODO: Adjust basis
					elif t.type == Transaction.adjustment:
						adjustedValue += t.total
					elif t.type == Transaction.spinoff:
						# Determine price per share
						if t.pricePerShare:
							pps = t.pricePerShare
						else:
							pps = 1
							if t.ticker2 == ticker:
								if currentPrice < len(prices):
									# Stock data is the spinoff ticker
									pps = prices[currentPrice]["close"]
							else:
								# Stock data is the original ticker
								data = stockData.getPrice(t.ticker2, t.date)
								if data:
									pps = data["close"]

						# Dividend if ticker, buy if ticker2
						if t.ticker == ticker:
							spinoffValue = t.shares * pps
							if value > 0:
								print t.date, "normDiv", normDividendFactor
								print value, spinoffValue
								normDividendFactor *= value / (value + spinoffValue)
								normFeeFactor *= value / (value + spinoffValue)
								print "to", normDividendFactor
								
								# TODO: Adjust basis
						else:
							# First buy should reset the split factor
							if currentTrans == 1:
								normSplitFactor = pps
								normDividendFactor = normSplitFactor
								normFeeFactor = normSplitFactor
	
							shares += abs(t.shares)
							
							addToBasis(ticker, t.date, t.shares, pps)
					elif t.type == Transaction.tickerChange:
						if ticker == t.ticker:
							# Old ticker
							removeFromBasis(ticker, shares)
							shares = 0
							
							# Force exit from loop, this stock no longer exists
							doneWithTicker = True
						else:
							# New ticker, get stock data of original ticker
							if currentTrans != 1:
								update.addMessage("The ticker change transaction from %s to %s is not the first transaction for %s." % (t.ticker, t.ticker2, t.ticker2))
								continue
							pos = self.getPositionOnDate(t.ticker, t.date - datetime.timedelta(1))
							if not pos:
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
								normSplitFactor = pps
								normDividendFactor = normSplitFactor
								normFeeFactor = normSplitFactor
								addToBasis(ticker, t.date, shares, pps)
					else:
						print "did not use transaction for rebuilding:", t
					
					# Adjust for fee
					# Should be after calculation of value???
					if t.fee:
						totalFees += t.fee

				# Build current value based on shares and price
				if currentPrice < len(prices):
					price = prices[currentPrice]["close"]
					value = shares * price + adjustedValue
					normSplit = price / normSplitFactor
					normDividend = price / normDividendFactor

					# Adjust fee factor for fees today's fees
					if totalFees > 0 and value > 0:
						normFeeFactor *= (value + totalFees) / value
					if normFeeFactor > 0:
						normFee = price / normFeeFactor

					# Advance to next price if not cash
					if ticker != "__CASH__":
						while currentPrice < len(prices) and prices[currentPrice]["date"] <= date:
							currentPrice += 1
				elif price:
					# Use last price
					value = shares * price + adjustedValue
				
				if (shares > 1.0e-6 or totalTrans > 0 or currentTrans < len(transactions) or ticker == "__CASH__") and not doneWithTicker:
					self.db.insert("positionHistory", {
						"date": date.strftime("%Y-%m-%d 00:00:00"),
						"ticker": ticker,
						"shares": shares,
						"value": value,
						"normSplit": normSplit,
						"normDividend": normDividend,
						"normFee": normFee})

				d = datetime.datetime(date.year, date.month, date.day)				
				if d in combinedValue:
					combinedValue[d] += value
				else:
					combinedValue[d] = value

				date += datetime.timedelta(1)

		# Now build combined position
		allTransactions = self.getTransactions(ascending = True)
		cashTransactions = self.getTransactions("__CASH__", ascending = True, buysToCash = False)
		currentAllTrans = 0
		currentCashTrans = 0
		value = 0.0
		lastValue = 0.0
		cashNorm = 0.0
		normFee = 1.0
		normFeeAdd = 1.0
		normDividendAdd = 1.0
		dates = sorted(combinedValue.keys())
		for date in dates:			
			endOfDay = datetime.datetime(date.year, date.month, date.day, 23, 59, 59)
			value = combinedValue[date]

			# Update deposited/withdrawn money
			cashMod = 0
			while currentCashTrans < len(cashTransactions) and cashTransactions[currentCashTrans].date <= endOfDay:
				t = cashTransactions[currentCashTrans]
				if t.type in [Transaction.deposit, Transaction.transferIn]:
					cashMod += abs(t.total)
				elif t.type in [Transaction.dividend, Transaction.adjustment]:
					# Dividends/adjustments are not cash in/out
					pass
				else:
					cashMod -= abs(t.total)
				currentCashTrans += 1
			
			if cashNorm == 0:
				cashNorm = cashMod
			elif cashMod != 0 and lastValue != 0.0:
				cashNorm = (lastValue + cashMod) / lastValue * cashNorm
			
			# Update normFee
			while currentAllTrans < len(allTransactions) and allTransactions[currentAllTrans].date <= endOfDay:
				t = allTransactions[currentAllTrans]
				if t.fee and value > 0:
					normFeeAdd *= (value + abs(t.fee)) / value
				
				if t.type in [Transaction.dividend, Transaction.dividendReinvest] and value > 0:
					normDividendAdd *= (value  + abs(t.total)) / value
				
				currentAllTrans += 1

			if cashNorm > 0.0:
				normFee = value / cashNorm
			#print date, cashNorm, value, normFee, normDividendAdd
			
			self.db.insert("positionHistory", {
				"date": date.strftime("%Y-%m-%d 00:00:00"),
				"ticker": "__COMBINED__",
				"shares": value,
				"value": value,
				"normSplit": normFee * normFeeAdd / normDividendAdd,
				"normDividend": normFee * normFeeAdd,
				"normFee": normFee})
			
			lastValue = value
		
		self.portPrefs.setDirty(False)
		self.db.commitTransaction()
		if update:
			update.finishSubTask("Finished rebuilding " + self.name)
		
	def chartByType(self, chartWidgetInstance, type):
		inception = self.getStartDate()
		year = datetime.datetime.now() - datetime.timedelta(days = 365)
		threeMonths = datetime.datetime.now() - datetime.timedelta(days = 90)
		month = datetime.datetime.now() - datetime.timedelta(days = 30)
		
		# Generate movers
		if type in [chartWidget.oneMonthMovers, chartWidget.threeMonthMovers, chartWidget.oneYearMovers]:
			if type == chartWidget.oneMonthMovers:
				period = month
			elif type == chartWidget.threeMonthMovers:
				period = threeMonths
			elif type == chartWidget.oneYearMovers:
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
				
				(ret, years) = self.calculatePerformanceTimeWeighted(t, period, last, format = False)
				if ret == "n/a":
					continue
				movers.append([t, ret])
			if len(movers) > 5:
				def moverSort(a, b):
					# Sort by degree away from 1
					diff = abs(a[1] - 1) - abs(b[1] - 1)
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
			movers.sort(moverSort2)
			# Now remove the tuple, keep only the ticker
			movers2 = movers
			movers = []
			for m in movers2:
				movers.append(m[0])

		if type == chartWidget.oneYearVsBenchmark:
			if self.isBenchmark():
				benchmark = False
				title = "One Year"
			else:
				benchmark = True
				title = "One Year vs. Benchmark"

			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				"__COMBINED__",
				year,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark)
			chartWidgetInstance.title = title
		elif type == chartWidget.oneYearVsBenchmarkCash:
			if self.isBenchmark():
				benchmark = False
				title = "One Year"
			else:
				benchmark = True
				title = "One Year vs. Benchmark"

			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				"__COMBINED__",
				year,
				doDollars = True,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark)
			chartWidgetInstance.title = title
		elif type == chartWidget.threeMonthsVsBenchmark:
			if self.isBenchmark():
				benchmark = False
				title = "Three Months"
			else:
				benchmark = True
				title = "Three Months vs. Benchmark"

			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				"__COMBINED__",
				threeMonths,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark)
			chartWidgetInstance.title = title
		elif type == chartWidget.threeMonthsVsBenchmarkCash:
			if self.isBenchmark():
				benchmark = False
				title = "Three Months"
			else:
				benchmark = True
				title = "Three Months vs. Benchmark"

			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				"__COMBINED__",
				threeMonths,
				doDollars = True,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark)
			chartWidgetInstance.title = title
		elif type == chartWidget.inceptionVsBenchmark:
			if self.isBenchmark():
				benchmark = False
				title = "Since Inception"
			else:
				benchmark = True
				title = "Since Inception vs. Benchmark"

			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				"__COMBINED__",
				inception,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark)
			chartWidgetInstance.title = title
		elif type == chartWidget.inceptionVsBenchmarkCash:
			if self.isBenchmark():
				benchmark = False
				title = "Since Inception"
			else:
				benchmark = True
				title = "Since Inception vs. Benchmark"

			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				"__COMBINED__",
				inception,
				doDollars = True,
				doGradient = True,
				doDividend = True,
				doBenchmark = benchmark)
			chartWidgetInstance.title = title
		elif type == chartWidget.oneMonthMovers:
			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				movers,
				month,
				doDividend = True,
				doExtra = False)
			chartWidgetInstance.title = "One Month Movers"
		elif type == chartWidget.threeMonthMovers:
			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				movers,
				threeMonths,
				doDividend = True,
				doExtra = False)
			chartWidgetInstance.title = "Three Month Movers"
		elif type == chartWidget.oneYearMovers:
			self.chart(
				chartWidgetInstance,
				appGlobal.getApp().stockData,
				movers,
				year,
				doDividend = True,
				doExtra = False)
			chartWidgetInstance.title = "One Year Movers"
	
		chartWidgetInstance.legend = True

	def chart(self, chartWidget, stockData, tickers, startDate = False, doTransactions = False, doSplit = False, doDividend = False, doFee = False, doBenchmark = False, doDollars = False, doGradient = False, doExtra = True):
		chartWidget.reset()
		chartWidget.doGradient = doGradient
		
		colors = [(0.2, 0.2, 1), (0, 0.8, 0), (1, 0, 0), (0.69, 0.28, 0.71), (0.97, 0.81, 0.09)]
		colorIndex = 0
		
		# If only one ticker is supplied turn it into a list
		if type(tickers) != list:
			tickers = [tickers]

		benchmark = Portfolio(self.getBenchmark())
		if benchmark.portPrefs.getDirty():
			benchmark.rebuildPositionHistory(stockData)
		benchmarkHistory = benchmark.getPositionHistory("__COMBINED__", startDate)
		benchmarkKeys = sorted(benchmarkHistory.keys())

		firstDate = False
		for ticker in tickers:
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
			endLoop = benchmarkKeys[-1]
	
			# Now get old prices, fill in up to one week
			while d < endLoop:
				data = stockData.getPrice(ticker, d)
				if not data:
					d += datetime.timedelta(1)
					continue
				d += datetime.timedelta(1)
	
			chartTypes = []
			if doSplit:
				chartTypes.append("normSplit")
			if doDividend:
				chartTypes.append("normDividend")
			if doFee:
				chartTypes.append("normFee")
	
			# Build X/Y and normalize
			for chartType in chartTypes:
				firstValue = False
				pricesX = []
				pricesY = []
				for p in keys:
					if doDollars:
						price = prices[p]["value"]
					else:
						price = prices[p][chartType]
					if not firstValue and price != 0:
						if doDollars:
							# Not used
							firstValue = True
						else:
							firstValue = 1.0 / price
					if firstValue:
						pricesX.append(p)
						if doDollars:
							pricesY.append(price)
						else:
							pricesY.append(price * firstValue - 1)
				
				if len(tickers) > 1:
					color = colors[colorIndex]
					colorIndex = (colorIndex + 1) % len(colors)
				elif chartType == "normSplit":
					color = (0.2, 0.2, 1)
				elif chartType == "normDividend":
					color = (0, 0.8, 0)
				elif chartType == "normFee":
					color = (1, 0.2, 0.2)
	
				tickerName = ticker
				if tickerName == "__COMBINED__":
					tickerName = "Combined"
				elif tickerName == "__CASH__":
					tickerName = "Cash"
				if len(chartTypes) > 1:
					if chartType == "normSplit":
						tickerName += " Price"
					elif chartType == "normDividend":
						tickerName += " Dividends"
					elif chartType == "normFee":
						tickerName += " Fees"
				chartWidget.addXY(pricesX, pricesY, tickerName, color)
				
				# Add transactions
				if doTransactions:
					buyX = []
					buyY = []
					sellX = []
					sellY = []
					for t in self.getTransactions(ticker):
						d = t.date
		
						# Check 7 days prior to find a valid date
						found = False
						for j in range(7):
							date = datetime.datetime(d.year, d.month, d.day)
							date -= datetime.timedelta(days = j)
							if date in prices:
								found = True
								if doDollars:
									val = prices[date][chartType] * firstValue
								else:
									val = prices[date][chartType] * firstValue - 1
								break
						if not found:
							# Skip transaction if no price for this date
							continue
						
						if t.type == Transaction.buy or t.type == Transaction.transferIn:
							buyX.append(d)
							buyY.append(val)
						elif t.type == Transaction.sell or t.type == Transaction.transferOut:
							sellX.append(d)
							sellY.append(val)
					
					if buyX:
						chartWidget.addBuys(buyX, buyY)
					if sellX:
						chartWidget.addSells(sellX, sellY)
	
					# Only do transactions once
					doTransactions = False
				
				# Now get old prices, fill in up to one week
				extraPrices = {}
				inMissed = False
				gotMissed = False
				d = firstDate
				norm = False
				while d <= endLoop:
					# Add in price if it's not there
					data = stockData.getPrice(ticker, d)
					if not data:
						inMissed = True
						extraPrices[d] = False
						d += datetime.timedelta(1)
						continue
					if (not d in pricesBase or pricesBase[d]['shares'] <= 0) and norm:
						if inMissed:
							# Fill in data from last 7 days
							fill = d - datetime.timedelta(7)
							last = False
							while fill < d:
								if fill in extraPrices and extraPrices[fill] != False:
									last = extraPrices[fill]
								elif last:
									extraPrices[fill] = last
								fill += datetime.timedelta(1)
						inMissed = False
						
						# Add 2 values so we match with the last value
						# The second one may be over-written
						extraPrices[d] = data['close'] / norm - 1
						extraPrices[d - datetime.timedelta(1)] = data['close'] / norm - 1
						gotMissed = True
					elif d in pricesBase:
						inMissed = True
						# Normalize extraPrices based on normalized value
						norm = data['close'] / (pricesBase[d][chartType] * firstValue)
						extraPrices[d] = False
					d += datetime.timedelta(1)
				
				# If no extra prices on valid days then reset
				if not gotMissed or not doExtra:
					extraPrices = {}
	
				if extraPrices:
					pricesX = extraPrices.keys()
					pricesX.sort()
					pricesY = []
					for x in pricesX:
						pricesY.append(extraPrices[x])
					chartWidget.addXY(pricesX, pricesY, ticker, color, dashed = True)

		if doDollars:
			chartWidget.yAxisType = "dollars"
		else:
			chartWidget.yAxisType = "percent"
		chartWidget.title = False
		
		# Benchmark = benchmarkDividend[p] * origPrice / origBenchmarkDividend
		if doBenchmark and firstDate:
			if doDollars:
				# Include cash transactions to buy/sell benchmark shares
				# Do not include for first date
				firstDatePlus1 = firstDate + datetime.timedelta(1)
				moneyIn = filter(lambda t: firstDatePlus1 < t.date, self.getTransactions("__CASH__", transType = Transaction.deposit))
				moneyIn += filter(lambda t: firstDatePlus1 < t.date, self.getTransactions(transType = Transaction.transferIn))
				moneyOut = filter(lambda t: firstDatePlus1 < t.date, self.getTransactions("__CASH__", transType = Transaction.withdrawal))
				moneyOut += filter(lambda t: firstDatePlus1 < t.date, self.getTransactions(transType = Transaction.transferOut))
				moneyIn.sort(key = operator.attrgetter('date'))
				moneyOut.sort(key = operator.attrgetter('date'))
				moneyInIndex = 0
				moneyOutIndex = 0

			pricesX = []
			pricesY = []
			firstValue = False
			for p in benchmarkKeys:
				price = benchmarkHistory[p]["normDividend"]
				if doDollars and not p in prices:
					continue
				if not firstValue:
					# Normalize on percent or dollars
					if doDollars:
						firstValue = prices[p]["value"] / benchmarkHistory[p]["normDividend"]
					else:
						firstValue = 1.0 / benchmarkHistory[p]["normDividend"]
					#if price > 0:
					#	firstValue = 1.0 / price
				
				# Buy/sell benchmark
				if doDollars:
					while moneyInIndex < len(moneyIn) and moneyIn[moneyInIndex].date <= p:
						firstValue += moneyIn[moneyInIndex].total / benchmarkHistory[p]["normDividend"]
						moneyInIndex += 1
					while moneyOutIndex < len(moneyOut) and moneyOut[moneyOutIndex].date <= p:
						firstValue -= moneyOut[moneyOutIndex].total / benchmarkHistory[p]["normDividend"]
						moneyOutIndex += 1

				if firstValue:
					pricesX.append(p)
					if doDollars:
						pricesY.append(price * firstValue)
					else:
						pricesY.append(price * firstValue - 1)
			chartWidget.addXY(pricesX, pricesY, benchmark.name, (0.4, 0.4, 0.4))

	'''def chartTransactions(self, stockData, tickers, width = 600, height = 400, doSplit = True, doDividend = False, doFee = False, doBenchmark = False, startDate = False, legend = True, title = False, showPercent = True):
		# Create a XYChart object of size 600 x 400 pixels. Use a vertical gradient color
		# from light blue (99ccff) to white (ffffff) spanning the top 100 pixels as
		# background. Set border to grey (888888). Use rounded corners. Enable soft drop
		# shadow.
		c = XYChart(width, height)
		#c.setBackground(c.linearGradientColor(0, 0, 0, 100, 0x99ccff, 0xffffff), 0x888888)
		
		# Add a title using 18 pts Times New Roman Bold Italic font. #Set top margin to 16
		# pixels.
		if title:
			c.addTitle(title, "timesbi.ttf", 16)
		
		left = 60
		chartWidth = width - 70
		if legend:
			top = 45
			chartHeight = height - 75
			if title:
				top += 14
				chartHeight -= 14
		else:
			top = 10
			chartHeight = height - 40
			if title:
				top += 30
				chartHeight -= 30
		
		# Set the plotarea at (60, 80) and of 510 x 275 pixels in size. Use transparent
		# border and dark grey (444444) dotted grid lines
		plotArea = c.setPlotArea(left, top, chartWidth, chartHeight, -1, -1, Transparent, c.dashLineColor(0xaaaaaa, 0x000101), -1)
		
		if legend:
			if title:
				legendTop = 25
			else:
				legendTop = 0
			c.addLegend(55, legendTop, 0, "", 8).setBackground(Transparent)

		# Set x-axis tick density to 75 pixels and y-axis tick density to 30 pixels.
		# ChartDirector auto-scaling will use this as the guidelines when putting ticks on
		# the x-axis and y-axis.
		c.yAxis().setTickDensity(30)
		c.yAxis().setColors(0x666666, 0x000000, 0x00000, 0x666666)

		c.xAxis().setTickDensity(75)
		c.xAxis().setColors(0x666666, 0x000000, 0x00000, 0x666666)
		
		# Set the x-axis margins to 15 pixels, so that the horizontal grid lines can extend
		# beyond the leftmost and rightmost vertical grid lines
		c.xAxis().setMargin(15, 0)
		
		# Set axis label style to 8pts Arial Bold
		c.yAxis().setLabelStyle("arialbd.ttf", 8)
		
		# Add axis title using 10pts Arial Bold Italic font
		c.yAxis().setTitle("Adjusted Returns", "arialbi.ttf", 10)
		
		c.yAxis().setAutoScale(0, 0, 0.00001)
		c.yAxis().setLabelFormat("{={value}-100}%")

		# If only one ticker is supplied turn it into a list
		if type(tickers) != list:
			tickers = [tickers]
		
		def getColor(name):
			if name == "burlywood":
				return 0xdeb887
			elif name == "gold":
				return 0xffd700
			elif name == "saddlebrown":
				return 0x8b4513
			
			try:
				c = QColor(name)
				if not c.isValid():
					return 0x000000
			except:
				return 0x000000
			return (c.red() << 16) | (c.green() << 8) | c.blue()
		
		def darkenColor(color, amount = 0.5):
			red = (color & 0xff0000) >> 16
			green = (color & 0x00ff00) >> 8
			blue = color & 0x0000ff
			
			red = int(red * amount)
			green = int(green * amount)
			blue = int(blue * amount)

			return (red << 16) | (green << 8) | blue
		
		colors = [0x3333ff, 0x00ff00, 0xff0000, getColor("orchid"), getColor("gold"), getColor("burlywood"), getColor("saddlebrown"), getColor("salmon")]
		colorIndex = 0
		color = colors[colorIndex]
		for ticker in tickers:
			ticker = ticker.upper().encode("utf-8")
			transactions = self.getTransactions(ticker, ascending = True)
			
			if width < 200:
				width = 200
			if height < 200:
				height = 200
			
			buyX = []
			buyY = []
			sellX = []
			sellY = []
			
			# Add user price data points
			user = self.getUserPrices(ticker)
			
			# Add User price data points
			#for p in user:
			#	d = p.dateDict()
			#	transX.append(chartTime(**d))
			#	transY.append(p.price)
	
			# Get prices
			pricesX = []
			pricesY = []
			pricesDivX = []
			pricesDivY = []
			pricesFeeX = []
			pricesFeeY = []
			pricesBenchmarkX = []
			pricesBenchmarkY = []
			pricesBase = self.getPositionHistory(ticker, startDate)

			# Trim prices
			interval = len(pricesBase) / float(width)
			if interval < 1.0:
				interval = 1.0
			
			prices = {}
			nextPrice = 0
			nextPriceFloat = 0.0
			i = 0
			for date in sorted(pricesBase.keys()):
				if i == nextPrice:
					prices[date] = pricesBase[date]
					nextPriceFloat += interval
					nextPrice = int(nextPriceFloat)
				
				i += 1

			# Keys will be a list of all dates
			keys = sorted(prices.keys())

			# If no prices, return
			if len(keys) < 2:
				return False

			# Check for start date less than date
			firstDate = keys[0]
			extraPrices = {}
			if startDate and startDate < firstDate:
				d = startDate
			else:
				d = firstDate
			d = datetime.datetime(d.year, d.month, d.day)

			shares = prices[keys[0]]['shares']
			if shares > 0:
				data = stockData.getPrice(ticker, keys[0])
				norm = prices[keys[0]]['value'] / shares * prices[keys[0]]['normSplit']
			else:
				data = stockData.getPrice(ticker, keys[0])
				if data:
					norm = data['close']
				else:
					# Cannot get norm
					print "cannot get norm for ", ticker
					continue

			# Next check for closed position
			benchmark = Portfolio(self.getBenchmark())
			if benchmark.portPrefs.getDirty():
				benchmark.rebuildPositionHistory(stockData)
			benchmarkHistory = benchmark.getPositionHistory("__COMBINED__", startDate)
			if len(benchmarkHistory) > 0:
				benchmarkKeys = sorted(benchmarkHistory.keys())
				endLoop = benchmarkKeys[len(benchmarkKeys) - 1] - datetime.timedelta(1)
			else:
				# No loop, don't fill in prices
				endLoop = d
			
			# Now get old prices, fill in up to one week
			inMissed = False
			gotMissed = False
			while d < endLoop:
				# Add in price if it's not there
				data = stockData.getPrice(ticker, d)
				if not data:
					inMissed = True
					extraPrices[d] = {"normSplit": NoValue, "normDividend": NoValue, "normFee": NoValue}
					d += datetime.timedelta(1)
					continue
				if not d in pricesBase or pricesBase[d]['shares'] <= 0:
					if inMissed:
						# Fill in data from last 7 days
						fill = d - datetime.timedelta(7)
						last = False
						while fill < d:
							if fill in extraPrices and extraPrices[fill]["normSplit"] != NoValue:
								last = extraPrices[fill]
							elif last:
								extraPrices[fill] = last
							fill += datetime.timedelta(1)
					inMissed = False
					close = data['close'] / norm
					extraPrices[d] = {"normSplit":  close, "normDividend": close, "normFee": close}
					gotMissed = True
				else:
					inMissed = True
					if doSplit:
						norm = data['close'] / pricesBase[d]['normSplit']
					elif doDividend:
						norm = data['close'] / pricesBase[d]['normDividend']
					else:
						norm = data['close'] / pricesBase[d]['normFee']
					extraPrices[d] = {"normSplit": NoValue, "normDividend": NoValue, "normFee": NoValue}
				d += datetime.timedelta(1)
			
			# If no extra prices on valid days then reset
			if not gotMissed:
				extraPrices = {}
			
			# Resort keys
			keys = sorted(prices.keys())
			
			first = True
			for p in keys:
				if first:
					normSplit = prices[p]["normSplit"]
					normDividend = prices[p]["normDividend"]
					normFee = prices[p]["normFee"]
					first = False
				
				d = dateDict(p)
				if prices[p]['shares'] <= 0:
					if doSplit:
						pricesX.append(chartTime(**d))
						pricesY.append(NoValue)
					if doDividend:
						pricesDivX.append(chartTime(**d))
						pricesDivY.append(NoValue)
					if doFee:
						pricesFeeX.append(chartTime(**d))
						pricesFeeY.append(NoValue)
				else:
					if doSplit:
						pricesX.append(chartTime(**d))
						pricesY.append(prices[p]["normSplit"] / normSplit * 100.0)
					if doDividend:
						pricesDivX.append(chartTime(**d))
						pricesDivY.append(prices[p]["normDividend"] / normDividend * 100.0)
					if doFee:
						pricesFeeX.append(chartTime(**d))
						pricesFeeY.append(prices[p]["normFee"] / normFee * 100.0)
			
			if not firstDate:
				continue
				
			# Add transaction data points
			for t in transactions:
				d = t.dateDict()

				# Check 7 days prior to find a valid date
				# Multiply 7 by interval (skipped days)
				found = False
				for j in range(int(7 * interval)):
					date = datetime.datetime(d['y'], d['m'], d['d'])
					date -= datetime.timedelta(days = j)
					if date in prices:
						found = True
						if doSplit:
							val = prices[date]["normSplit"] / normSplit * 100
						elif doDividend:
							val = prices[date]["normDividend"] / normDividend * 100
						else:
							val = prices[date]["normFee"] / normFee * 100
						break
				if not found:
					# Skip transaction if no price for this date
					continue
				
				if t.type == Transaction.buy or t.type == Transaction.transferIn:
					buyX.append(chartTime(**d))
					buyY.append(val)
				elif t.type == Transaction.sell or t.type == Transaction.transferOut:
					sellX.append(chartTime(**d))
					sellY.append(val)
				#elif t.type == Transaction.split:
				#	print "split not printed"
				#elif t.type == Transaction.stockDividend:
				#	print "stock dividend not printed"
		
			# Add the transaction images
			if buyX:
				layer = c.addScatterLayer(buyX, buyY, "Buy", TriangleShape, 16, 0x00ff00)
				layer.getDataSet(0).setDataSymbol4([-300, 0, 300, 0, 0, 500], 24)
			
			if sellX:
				layer = c.addScatterLayer(sellX, sellY, "Sell", InvertedTriangleShape, 16, 0xff0000)
				layer.getDataSet(0).setDataSymbol4([-300, 1000, 300, 1000, 0, 500], 24)
	
			# Add stock data
			if ticker == "__COMBINED__":
				ticker = self.name.encode("utf-8")
			
			# Check if to add type after name in legend
			count = 0
			if doSplit:
				count += 1
			if doDividend:
				count += 1
			if doFee:
				count += 1
			addType = count > 1
			
			if pricesX:
				layer2 = c.addLineLayer2()
				if addType:
					title = ticker + " splits"
				else:
					title = ticker
				if len(tickers) > 1:
					color = colors[colorIndex]
					colorIndex = (colorIndex + 1) % len(colors)
				else:
					color = 0x3333ff
				layer2.addDataSet(pricesY, color, title)
				layer2.setXData(pricesX)
				layer2.setLineWidth(2)
				labelIndex = len(pricesY) - 1
				if showPercent:
					tb = layer2.addCustomDataLabel(0, labelIndex, "%.2f%%" % (pricesY[labelIndex] - 100.0), "bold", 12, darkenColor(color))
					tb.setAlignment(BottomRight)
	
			# Add dividend data
			if pricesDivX:
				layer2 = c.addLineLayer2()
				if addType:
					title = ticker + " dividends"
				else:
					title = ticker
				if len(tickers) > 1:
					color = colors[colorIndex]
					colorIndex = (colorIndex + 1) % len(colors)
				else:
					color = 0x00cc00
				layer2.addDataSet(pricesDivY, color, title)
				layer2.setXData(pricesDivX)
				layer2.setLineWidth(2)
				labelIndex = len(pricesDivY) - 1
				if showPercent:
					tb = layer2.addCustomDataLabel(0, labelIndex, "%.2f%%" % (pricesDivY[labelIndex] - 100.0), "bold", 12, darkenColor(color))
					tb.setAlignment(BottomRight)
	
			# Add dividend + fee data
			if pricesFeeX:
				layer2 = c.addLineLayer2()
				if addType:
					title = ticker + " fees"
				else:
					title = ticker
				if len(tickers) > 1:
					color = colors[colorIndex]
					colorIndex = (colorIndex + 1) % len(colors)
				else:
					color = 0xff3333
				layer2.addDataSet(pricesFeeY, color, title)
				layer2.setXData(pricesFeeX)
				layer2.setLineWidth(2)
				labelIndex = len(pricesFeeY) - 1
				if showPercent:
					tb = layer2.addCustomDataLabel(0, labelIndex, "%.2f%%" % (pricesFeeY[labelIndex] - 100.0), "bold", 12, darkenColor(color))
					tb.setAlignment(BottomRight)

			if not legend:
				tb = layer2.addCustomDataLabel(0, labelIndex, ticker, "", 8, darkenColor(color))
				tb.setAlignment(Left)
			
		# Extra prices are before inception or after the position was closed
		keys = sorted(extraPrices.keys())
		if extraPrices:
			extraPricesX = []
			extraPricesY = []
			for d in keys:
				dd = dateDict(d)
				extraPricesX.append(chartTime(**dd))
				val = extraPrices[d]['normSplit']
				if val == NoValue:
					extraPricesY.append(NoValue)
				else:
					extraPricesY.append(100.0 * val)

			if extraPricesX:
				layer2 = c.addLineLayer2()
				name = ticker.upper().encode("utf-8")
				layer2.addDataSet(extraPricesY, c.dashLineColor(0x66ff66, 0x00000101), name)
				layer2.setXData(extraPricesX)
				layer2.setLineWidth(1)
				labelIndex = len(extraPricesY) - 1
				if showPercent:
					tb = layer2.addCustomDataLabel(0, labelIndex, "%.2f%%" % (extraPricesY[labelIndex] - 100.0), "bold", 12, 0x669966)
					tb.setAlignment(BottomRight)

		keys = sorted(benchmarkHistory.keys())
		first = True
		firstValue = False
		if firstDate and doBenchmark:
			for p in keys:
				if p >= keys[0]:
					# Determine first value based on position
					# If can't find first value for ticker just use benchmark
					if first:
						firstValue = 1.0 / benchmarkHistory[firstDate]["normDividend"]
						first = False
					d = dateDict(p)
					pricesBenchmarkX.append(chartTime(**d))
					pricesBenchmarkY.append(benchmarkHistory[p]["normDividend"] * 100.0 * firstValue)

			if pricesBenchmarkX:
				layer2 = c.addLineLayer2()
				name = benchmark.name.encode("utf-8")
				layer2.addDataSet(pricesBenchmarkY, 0x666666, name)
				layer2.setXData(pricesBenchmarkX)
				layer2.setLineWidth(2)
				labelIndex = len(pricesBenchmarkY) - 1
				if showPercent:
					tb = layer2.addCustomDataLabel(0, labelIndex, "%.2f%%" % (pricesBenchmarkY[labelIndex] - 100.0), "bold", 12, 0x000000)
					tb.setAlignment(BottomRight)

		# Output the chart
		c.makeChart("transactions.png")
		return "transactions.png"'''
	
	def errorCheck(self, stockData):
		errors = []
		
		# Check for negative cash positions
		cash = self.getPositionHistory("__CASH__")
		for date in sorted(cash.keys()):
			if cash[date]["value"] < 0:
				errors.append(("Cash position is negative", "Severe", "This portfolio's cash position is $%.2f on %d/%d/%d.  This is likely due to a missing or incorrectly entered deposit, sell or dividend transaction." % (cash[date]["value"], date.month, date.day, date.year)))
				break
		
		# Check for first transaction not buy or no transactions
		for ticker in self.getPositions():
			if ticker == "__CASH__" or ticker == "__COMBINED__":
				continue
			
			transactions = self.getTransactions(ticker, limit = 1, ascending = True)
			
			if len(transactions) == 0:
				errors.append(("No transactions", "Minor", "There are no transactions for %s" % ticker))
			
			if not transactions[0].type in [Transaction.buy, Transaction.transferIn, Transaction.spinoff]:
				errors.append(("First transaction is not buy", "Severe", "The first transaction for %s is not a buy transaction.  This position will not be included in performance calculations.  Add a buy transaction, a transfer transaction or a spinoff transaction for this position." % ticker))
				
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
						errors.append(("Computed value is incorrect", "Minor", text))
						didMinor = True
						continue

					if abs(check.shares - pos["shares"]) > 1.0e-6:
						if floatCompare(check.shares, pos["shares"]) < 1.01:
							if not didMinor:
								text = "The computed shares for %s on %s is incorrect.  The computed shares is %s but the correct shares is %s.  This could be due to a missing or incorrect buy, sell or stock split transaction." % (ticker, check.date.strftime("%m/%d/%Y"), Transaction.formatFloat(pos["shares"]), Transaction.formatFloat(check.shares))
								if lastCorrectDate:
									text += "  The last correct date was on %s." % lastCorrectDate.strftime("%m/%d/%Y")
								errors.append(("Computed shares is incorrect", "Minor", text))
								didMinor = True
								continue
						elif not didSevere:
							text = "The computed shares for %s on %s is incorrect.  The computed shares is %s but the correct shares is %s.  This position will not be included in performance calculations.  This could be due to a missing or incorrect buy, sell or stock split transaction." % (ticker, check.date.strftime("%m/%d/%Y"), Transaction.formatFloat(pos["shares"]), Transaction.formatFloat(check.shares))
							if lastCorrectDate:
								text += "  The last correct date was on %s." % lastCorrectDate.strftime("%m/%d/%Y")
							errors.append(("Computed shares is incorrect", "Severe", text))
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
										errors.append(("Incorrect stock dividend for " + ticker, "Moderate", "A stock dividend occurred on %d/%d/%d.  The portfolio transaction has %f shares but the proper number is %f." % (s2.date.month, s2.date.day, s2.date.year, portShares, shares)))
								else:
									if abs(s2.total - s["value"]) > 1.0e-6:
										# Match but incorrect shares
										errors.append(("Incorrect split for " + ticker, "Moderate", "A split occurred on %d/%d/%d.  The portfolio transaction has a value of %s (%.2f) but the proper value is %s (%.2f)." % (s2.date.month, s2.date.day, s2.date.year, Transaction.splitValueToString(s2.total), s2.total, Transaction.splitValueToString(s["value"]), s["value"])))
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
						splitVal = "%d-%d" % (round(s["value"] * minDenom), minDenom)
					
					# Determine shares for stock dividend
					shares = "?"
					position = self.getPositionOnDate(ticker, s["date"])
					if position:
						shares = position["shares"] * (s["value"] - 1.0)
						shares = "%.3f" % shares

					errors.append(("Missing split for " + ticker, "Severe", "A %s split occurred on %d/%d/%d.  A Stock Dividend transaction should be added for %s shares." % (splitVal, date.month, date.day, date.year, shares)))
			
			if portSplits:
				for s2 in portSplits:
					errors.append(("Invalid split for " + ticker, "Severe", "This portfolio has a stock dividend on %d/%d/%d although no such stock dividend or stock split exists." % (s2.date.month, s2.date.day, s2.date.year)))
		
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

if __name__ == "__main__":
	if 1:
		b = Scottrade()
		p = Portfolio("Scottrade")
		f = open("scottrade.ofx", "r")
		ofx = f.read()
		p.updateFromOfx(ofx, b)
		#doScottrade()
	else:
		p = Portfolio("ameritrade")
		b = Ameritrade()
		
		f = open("ameritrade.ofx", "r")
		ofx = f.read()
		p.updateFromOfx(ofx, b)
