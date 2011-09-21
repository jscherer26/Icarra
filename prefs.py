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

import sys
import os
import shutil
import datetime

from db import *
from appGlobal import *

class Prefs:
	@staticmethod
	def prefsRootPath():
		if sys.platform == "darwin":
			return os.path.expanduser("~/Library/Application Support/Icarra2/")
		elif sys.platform.startswith("win"):
			# not tested
			return os.path.join(os.environ['APPDATA'], "Icarra2")
		else:
			return os.path.expanduser("~/.icarra2/")
		
	@staticmethod
	def getPortfolioPath(name):
		return os.path.join(Prefs.prefsRootPath(), "portfolio_" + name + ".db")

	def __init__(self, customDb = False):
		if customDb:
			self.db = customDb
			self.db.checkTable("prefs", [
				{"name": "name", "type": "text"},
				{"name": "value", "type": "text"}])
		else:
			# Check for ~/.icarra2
			if not os.path.isdir(self.prefsRootPath()):
				os.mkdir(self.prefsRootPath())
			
			self.db = Db(os.path.join(self.prefsRootPath(), "prefs.db"))

			self.db.beginTransaction()

			self.db.checkTable("prefs", [
				{"name": "name", "type": "text"},
				{"name": "value", "type": "text"}])
			
			self.db.checkTable("portfolios", [
				{"name": "portfolioId", "type": "integer primary key autoincrement"},
				{"name": "name", "type": "text"},
				{"name": "brokerage", "type": "text"},
				{"name": "username", "type": "text"},
				{"name": "account", "type": "text"}],
				unique = [{"name": "name", "cols": ["name"]}])
			
			# Check basic defaults
			self.checkDefaults("width", 950)
			self.checkDefaults("height", 550)
			self.checkDefaults("statusWidth", 500)
			self.checkDefaults("statusHeight", 300)
			self.checkDefaults("lastPortfolio", "S&P 500")
			self.checkDefaults("lastTab", "Summary")
			self.checkDefaults("ofxDebug", "False")
			self.checkDefaults("showCashInTransactions", "False")
			self.checkDefaults("backgroundRebuild", "True")
			self.checkDefaults("backgroundImport", "False")
			self.checkDefaults("lastBackgroundImport", "2000-01-01 00:00:00")
			self.checkDefaults("ignoreVersion", "0.0.0")
			self.checkDefaults("lastVersionReminder", "2000-01-01 00:00:00")
			self.checkDefaults("latestVersion", "0.0.0")
			self.checkDefaults("timesRun", "0")
			self.checkDefaults("tutorial", "0")
			self.checkDefaults("uniqueId", "")
			
			self.db.commitTransaction()
			
			# Save global in Prefs
			global prefs
			prefs = self
	
	def checkDefaults(self, name, value):
		cursor = self.db.select("prefs", where = {"name": name})
		if not cursor.fetchone():
			self.db.beginTransaction()
			self.db.insert("prefs", {"name": name, "value": value})
			self.db.commitTransaction()
	
	def getAllPrefs(self):
		res = self.db.select("prefs")
		return res.fetchall()

	def getPreference(self, name):
		cursor = self.db.select("prefs", where = {"name": name})
		row = cursor.fetchone()
		if not row:
			raise Exception("No preference " + name)
		return row["value"]
		
	def getWidth(self):
		return int(self.getPreference("width"))
	
	def getHeight(self):
		return int(self.getPreference("height"))
	
	def getStatusWidth(self):
		return int(self.getPreference("statusWidth"))
	
	def getStatusHeight(self):
		return int(self.getPreference("statusHeight"))

	def getLastPortfolio(self):
		return self.getPreference("lastPortfolio")
	
	def getLastTab(self):
		return self.getPreference("lastTab")
	
	def getOfxDebug(self):
		return self.getPreference("ofxDebug") == "True"
	
	def getShowCashInTransactions(self):
		return self.getPreference("showCashInTransactions") == "True"

	def getBackgroundRebuild(self):
		return self.getPreference("backgroundRebuild") == "True"

	def getBackgroundImport(self):
		return self.getPreference("backgroundImport") == "True"

	def getLastBackgroundImport(self):
		return datetime.datetime.strptime(self.getPreference("lastBackgroundImport"), "%Y-%m-%d %H:%M:%S")

	def getIgnoreVersion(self):
		(newMajor, newMinor, newRelease) = self.getPreference("ignoreVersion").split(".")
		return [int(newMajor), int(newMinor), int(newRelease)]

	def getLatestVersion(self):
		(newMajor, newMinor, newRelease) = self.getPreference("latestVersion").split(".")
		return [int(newMajor), int(newMinor), int(newRelease)]

	def getLastVersionReminder(self):
		return datetime.datetime.strptime(self.getPreference("lastVersionReminder"), "%Y-%m-%d %H:%M:%S")

	def getTimesRun(self):
		return int(self.getPreference("timesRun"))
	
	def getTutorial(self):
		return int(self.getPreference("tutorial"))

	def getUniqueId(self):
		return self.getPreference("uniqueId")

	def setSize(self, width, height):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": width}, {"name": "width"})
		self.db.update("prefs", {"value": height}, {"name": "height"})
		self.db.commitTransaction()
	
	def setStatusSize(self, width, height):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": width}, {"name": "statusWidth"})
		self.db.update("prefs", {"value": height}, {"name": "statusHeight"})
		self.db.commitTransaction()

	def setLastPortfolio(self, last):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": last}, {"name": "lastPortfolio"})
		self.db.commitTransaction()
			
	def setLastTab(self, last):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": last}, {"name": "lastTab"})
		self.db.commitTransaction()

	def setOfxDebug(self, debug):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": debug}, {"name": "ofxDebug"})
		self.db.commitTransaction()
	
	def setShowCashInTransactions(self, show):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": show}, {"name": "showCashInTransactions"})
		self.db.commitTransaction()
	
	def setBackgroundRebuild(self, show):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": show}, {"name": "backgroundRebuild"})
		self.db.commitTransaction()
	
	def setBackgroundImport(self, show):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": show}, {"name": "backgroundImport"})
		self.db.commitTransaction()
	
	def setLastBackgroundImport(self):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, {"name": "lastBackgroundImport"})
		self.db.commitTransaction()

	def setIgnoreVersion(self, major, minor, release):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": "%d.%d.%d" % (major, minor, release)}, {"name": "ignoreVersion"})
		self.db.commitTransaction()

	def updateLatestVersion(self, major, minor, release):
		(major2, minor2, release2) = self.getLatestVersion()
		if major > major2 or (major == major2 and minor > minor2) or (major == major2 and minor == minor2 and release > release2):
			self.db.beginTransaction()
			self.db.update("prefs", {"value": "%d.%d.%d" % (major, minor, release)}, {"name": "latestVersion"})
			self.db.commitTransaction()

	def setLastVersionReminder(self):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, {"name": "lastVersionReminder"})
		self.db.commitTransaction()

	def incTimesRun(self):
		r = int(self.getPreference("timesRun"))
		self.db.beginTransaction()
		self.db.update("prefs", {"value": r + 1}, {"name": "timesRun"})
		self.db.commitTransaction()
	
	def setTutorialBit(self, bit):
		t = int(self.getPreference("tutorial"))
		self.db.beginTransaction()
		self.db.update("prefs", {"value": t | bit}, {"name": "tutorial"})
		self.db.commitTransaction()
	
	def setUniqueId(self, unique):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": unique}, {"name": "uniqueId"})
		self.db.commitTransaction()
	
	def setOfxDebug(self, debug):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": debug}, {"name": "ofxDebug"})
		self.db.commitTransaction()
	
	def setIgnoreVersion(self, major, minor, release):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": "%d.%d.%d" % (major, minor, release)}, {"name": "ignoreVersion"})
		self.db.commitTransaction()

	def updateLatestVersion(self, major, minor, release):
		(major2, minor2, release2) = self.getLatestVersion()
		if major > major2 or (major == major2 and minor > minor2) or (major == major2 and minor == minor2 and release > release2):
			self.db.beginTransaction()
			self.db.update("prefs", {"value": "%d.%d.%d" % (major, minor, release)}, {"name": "latestVersion"})
			self.db.commitTransaction()

	def setLastVersionReminder(self):
		self.db.beginTransaction()
		self.db.update("prefs", {"value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, {"name": "lastVersionReminder"})
		self.db.commitTransaction()

	def addPortfolio(self, name):
		self.db.beginTransaction()
		self.db.insertOrUpdate("portfolios", {"name": name})
		self.db.commitTransaction()
	
	def addPortfolio(self, name):
		self.db.beginTransaction()
		self.db.insert("portfolios", {"name": name})
		self.db.commitTransaction()
	
	def hasPortfolio(self, name):
		cursor = self.db.select("portfolios", where = {"name": name})
		return cursor.fetchone() != None
	
	def deletePortfolio(self, name):
		self.db.beginTransaction()
		self.db.delete("portfolios", {"name": name})
		self.db.commitTransaction()
	
	def updatePortfolio(self, name, brokerage, username, account = ""):
		data = {
			"name": name,
			"brokerage": brokerage,
			"username": username,
			"account": account
		}
		self.db.beginTransaction()
		self.db.insertOrUpdate("portfolios", data,
			{"name": name})
		self.db.commitTransaction()
	
	def getPortfolios(self):
		# Read portfolios from db
		cursor = self.db.select("portfolios")
		portfolios = []
		for row in cursor.fetchall():
			portfolios.append(row["name"])

		# Also look in the data directory
		files = os.listdir(self.prefsRootPath())
		for f in files:
			if f[:10] == "portfolio_":
				name = f[10:]
				if name[-3:] == ".db":
					name = name[:-3]
					if not name in portfolios:
						portfolios.append(name)

		return portfolios
	
	def getPortfolioInfo(self, name):
		# First get info from prefs
		cursor = self.db.select("portfolios", where = {"name": name})
		row = cursor.fetchone()
		if row:
			return row
		
		# Next check if it is iin the local directory
		files = os.listdir(self.prefsRootPath())
		for f in files:
			if f == "portfolio_" + name + ".db":
				return {"portfolioId": -1, "name": name, "brokerage": "", "username": "", "account": ""}
		
		# Not found
		return False
	
	def changePortfolioName(self, old, new):
		# Unload current portfolio
		getApp().portfolio.close()
		
		# First try to move portfolio.  If that fails exit.
		# Then update the portfolio
		try:
			shutil.move(self.getPortfolioPath(old), self.getPortfolioPath(new))
		except Exception, e:
			# TODO: Print error
			print "could not move", e
			return True
		
		self.db.beginTransaction()
		self.db.update("portfolios",
			{"name": new}, 
			{"name": old})
		self.db.update("prefs", {"value": new}, {"name": "lastPortfolio"})
		self.db.commitTransaction()

		# Now reload portfolio with new name
		getApp().portfolio.open(new)

		return False
		
prefs = False
