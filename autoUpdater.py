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

import threading
import time
import datetime
import traceback

import appGlobal
import portfolio

try:
	import keyring
	haveKeyring = True
	from ofxToolkit import *
except:
	haveKeyring = False

global updater
updater = False

class AutoUpdater(threading.Thread):
	def __init__(self, stockData, prefs):
		self.stockData = stockData
		self.prefs = prefs
		self.running = True
		self.finished = False
		self.sleeping = False
		self.rebuilding = False # rebuilding portfolios
		self.tickerCount = 0
		self.tickersToImport = 1
		
		# Set to true when we want to run an entire loop
		# For example, when notifying to wake up
		self.freshLoop = False
		
		self.sleepCond = threading.Condition()
		
		threading.Thread.__init__(self, name = "autoUpdater")
	
	def run(self):
		app = appGlobal.getApp()
		while self.running:
			self.freshStart = False
			now = datetime.datetime.now()

			#print "Check for new stock data at %s" % now.strftime("%Y-%m-%d %H:%M:%S")

			# Determine the cutoff date for downloading new stock data
			# If before 7pm EST then go back to 7pm EST of the previous day
			# Go back by one day until we hit a week day
			# Then zero out H:M:S
			cutoffTime = datetime.datetime.utcnow() - datetime.timedelta(hours = 5)
			if cutoffTime.hour < 19:
				cutoffTime -= datetime.timedelta(days = 1)
			while cutoffTime.weekday() >= 5:
				cutoffTime -= datetime.timedelta(days = 1)
			cutoffTime = datetime.datetime(cutoffTime.year, cutoffTime.month, cutoffTime.day, 0, 0, 0)

			# Load all portfolios
			# Build list of tickers, update stock data
			names = self.prefs.getPortfolios()
			tickers = []
			max = len(names)
			tickerPorts = {}
			ports = {}
			for name in names:
				p = portfolio.Portfolio(name)
				p.readFromDb()
				ports[name] = p
				
			# Auto update
			if app.prefs.getBackgroundImport() and haveKeyring:
				# Import once every 20 hours
				diff = now - app.prefs.getLastBackgroundImport()
				#print "time since last auto import", diff
				if diff > datetime.timedelta(hours = 20):
					print "Background import transactions at %s" % now.strftime("%Y-%m-%d %H:%M:%S")
					for name, p in ports.items():
						if not self.running:
							break

						if p.isBrokerage() and p.brokerage != "" and p.username != "" and p.account != "":
							# check for password and brokerage
							brokerage = app.plugins.getBrokerage(p.brokerage)
							if not brokerage:
								continue
							password = keyring.get_password("Icarra-ofx-" + name, p.username)
							if not password:
								continue
							print "import from", name
							# Get ofx data, update if not empty
							# It may be an error string, in which case it's ignored
							ofx = getOfx(p.username, password, brokerage, p.account)
							if ofx != "":
								(numNew, numOld, newTickers) = p.updateFromFile(ofx, app)
								if numNew > 0 or newTickers:
									p.portPrefs.setDirty(True)
							print "imported"

					# Update time only if not aborted
					if self.running:
						app.prefs.setLastBackgroundImport()

			# Build list of tickers
			for name, p in ports.items():
				pTickers = p.getTickers(includeAllocation = True)
				for ticker in pTickers:
					if ticker in ["__CASH__", "__COBMINED__"]:
						continue
					
					# Add to tickerPorts map
					if ticker in tickerPorts:
						tickerPorts[ticker].append(p)
					else:
						tickerPorts[ticker] = [p]
					
					# Add to list of tickers
					if not ticker in tickers:
						tickers.append(ticker)

			# Remove tickers that do not need to be updated
			for ticker in tickers[:]:
				# Check if we do not have data after the cutoffTime
				last = self.stockData.getLastDate(ticker)
				if 0 and last and last >= cutoffTime:
					tickers.remove(ticker)
					continue
				
				# Check if we tried downloading within one hour
				lastDownload = self.stockData.getLastDownload(ticker)
				if lastDownload and datetime.datetime.now() - lastDownload < datetime.timedelta(hours = 1):
					tickers.remove(ticker)
					continue
					
			portsToUpdate = {}
			self.tickersToImport = len(tickers)
			
			# Lump all tickers that are less than 2 weeks old into one request
			updateNow = []
			for ticker in tickers[:]:
				lastDownload = self.stockData.getLastDownload(ticker)
				if lastDownload and datetime.datetime.now() - lastDownload < datetime.timedelta(days = 14):
					updateNow.append(ticker)
					tickers.remove(ticker)
					continue
			
			# Download the 2 week lump 10 tickers at a time
			while updateNow and self.running:
				downloadPart = updateNow[0:10]
				updateNow = updateNow[10:]
				try:
					new = self.stockData.updateStocks(downloadPart)
					appGlobal.setConnected(True)
				except Exception, e:
					print traceback.format_exc()
					appGlobal.setFailConnected(True)
					return
				for ticker in downloadPart:
					self.tickerCount += 1
					if new:
						for p in tickerPorts[ticker]:
							portsToUpdate[p.name] = True

			# Update each remaining ticker while still running
			for ticker in tickers:
				if self.running:
					try:
						new = self.stockData.updateStocks([ticker])
						appGlobal.setConnected(True)
					except Exception, e:
						print traceback.format_exc()
						appGlobal.setFailConnected(True)
						return
					if new:
						for p in tickerPorts[ticker]:
							# Add 3 for every port
							if not p.name in portsToUpdate:
								if app.prefs.getBackgroundRebuild():
									self.tickersToImport += 3
								portsToUpdate[p.name] = True

				self.tickerCount += 1
			
			# Mark every portfolio as dirty
			for name in portsToUpdate:
				ports[name].portPrefs.setDirty(True)
			
			# Next rebuild if the user has it configured
			if app.prefs.getBackgroundRebuild():
				self.rebuilding = True
				# Rebuild benchmarks, portfolios, combined portfolios
				for name, p in ports.items():
					if not self.running:
						break
					if p.portPrefs.getDirty() and p.isBenchmark():
						try:
							ports[name].rebuildPositionHistory(self.stockData)
						except Exception, e:
							print traceback.format_exc()
						self.tickerCount += 3
				for name, p in ports.items():
					if not self.running:
						break
					if p.portPrefs.getDirty() and p.isBrokerage():
						try:
							ports[name].rebuildPositionHistory(self.stockData)
						except Exception, e:
							print traceback.format_exc()
						self.tickerCount += 3
				for name, p in ports.items():
					if not self.running:
						break
					if p.portPrefs.getDirty() and p.isCombined():
						try:
							ports[name].rebuildPositionHistory(self.stockData)
						except Exception, e:
							print traceback.format_exc()
						self.tickerCount += 3
				self.rebuilding = False
			
			# Close all opened portfolios
			for name, p in ports.items():
				p.close()
			
			now = datetime.datetime.now()
			#print "Finished checking for new stock data at %s" % now.strftime("%Y-%m-%d %H:%M:%S")

			# Sleep for up to one hour unless we are notified to wake up
			# Do not sleep if asked to do a fresh start
			if self.running and not self.freshStart:
				self.sleepCond.acquire()
				self.sleeping = True
				self.tickerCount = self.tickersToImport # Percent done = 100%
				self.sleepCond.wait(60 * 60)
				self.sleeping = False
				self.tickerCount = 0
				self.tickersToImport = 1
				self.sleepCond.release()

		self.finished = True
		
	def stop(self):
		self.running = False
		self.wakeUp()
	
	def wakeUp(self, freshStart = False):
		self.sleepCond.acquire()
		# If currently sleeping make sure we are not finished importing
		if self.sleeping:
			# Wake up, make sure we update at least one ticker
			self.tickerCount = 0
			self.tickersToImport = 1
			self.sleeping = False
		if freshStart:
			self.freshStart = True
		self.sleepCond.notify()
		self.sleepCond.release()

	def percentDone(self):
		if self.freshStart:
			return 0
		if self.sleeping:
			return 100
		if self.tickersToImport == 0:
			return 100

		# We are downloading stocks
		return 100 * self.tickerCount / self.tickersToImport

def start(stockData, prefs):
	global updater
	if not updater:
		a = AutoUpdater(stockData, prefs)
		updater = a
		a.start()

def stop(join = True):
	global updater
	if updater:
		updater.stop()
		if join:
			updater.join()

def wakeUp(freshStart = False):
	global updater
	if updater:
		updater.wakeUp(freshStart)

def sleeping():
	global updater
	if updater:
		return updater.sleeping
	else:
		return False

def rebuilding():
	global updater
	if updater:
		return updater.rebuilding
	else:
		return False

def finished():
	global updater
	if updater:
		return updater.finished
	else:
		return False

def percentDone():
	global updater
	if updater:
		return updater.percentDone()
	else:
		return 100
