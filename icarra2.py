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
import uuid
import time
import datetime
import mutex
import traceback
import locale

locale.setlocale(locale.LC_ALL, "")

# Check that all required components are available
try:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
	from PyQt4.QtWebKit import *
	from PyQt4.QtNetwork import *
except:
	print "Icarra requires PyQt version 4.4 or higher"
	sys.exit(-1)

try:
	import keyring
except:
	# Ignore missing keyring, not critical
	pass

try:
	import sgmlop 
except:
	print "Icarra requires the sgmlop library"
	sys.exit(-1)

try:
	import json
	import jsonrpc
except:
	print "Icarra requires the jsonrpc library"
	sys.exit(-1)

try:
	import feedparser
except:
	print "Icarra requires the feedparser library"
	sys.exit(-1)

# For chart director
if sys.platform.startswith("darwin"):
	sys.path.append("lib/darwin")
if sys.platform.startswith("win"):
	if not hasattr(sys, "frozen"):
		sys.path.append(os.path.join(sys.path[0], "lib\win32"))
if sys.platform.startswith("linux"):
	sys.path.append("lib/linux32")

from editGrid import *
from prefs import *
from portfolio import *
from stockData import *
from statusUpdate import *
from pluginManager import *
from helpFrame import *
from splashScreenFrame import *
from newPortfolioFrame import *
from newVersionFrame import *
from ofxDebugFrame import *
from prefsFrame import *
import tutorial

import appGlobal
import autoUpdater

# For dependencies when building standalone apps
import plugin
import feedparser
import chartWidget
import webBrowser

class ToolSelectorDelegate(QItemDelegate):
	def __init__(self, parent):
		QItemDelegate.__init__(self, parent)
		self.myHint = False
	
	def sizeHint(self, option, index):
		if self.myHint:
			return self.myHint
		
		# Increase height by 10
		self.myHint = QItemDelegate.sizeHint(self, option, index)
		self.myHint.setHeight(self.myHint.height() + 10)
		return self.myHint

class ToolSelector(QListView):
	def __init__(self, parent = None):
		QWidget.__init__(self, parent)

		self.tools = []
		self.setEditTriggers(QAbstractItemView.NoEditTriggers)
		self.setSelectionMode(QListView.SingleSelection)
		self.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding))

		self.setSpacing(0)
		self.selectorDelegate = ToolSelectorDelegate(self)
		self.setItemDelegate(self.selectorDelegate)

		if appGlobal.getApp().isOSX:
			font = self.font()
			font.setPointSize(13)
			font.setBold(True)
			self.setFont(font)

			self.setStyleSheet("QListView::item { color: #444444; background: white; border: 1px solid white; } QListView::item:selected:active { background: #d8d8ff; border: 1px solid gray; }")
		elif appGlobal.getApp().isWindows:
			font = self.font()
			font.setBold(True)
			self.setFont(font)

			self.setStyleSheet("QListView::item { color: #444444; background: white; } QListView::item:selected { background: #d8d8ff; }")
		else:
			self.setStyleSheet("QListView::item { color: #444444; background: white; } QListView::item:selected{ background: #d8d8ff; }")
	
	def rebuild(self):
		self.tools = []
		for plugin in getApp().plugins.getPlugins():
			if appGlobal.getApp().portfolio.isBank() and plugin.forBank():
				self.addTool(plugin.name())
			elif not appGlobal.getApp().portfolio.isBank() and plugin.forInvestment():
				self.addTool(plugin.name())
		self.finishAdd()
	
	def addTool(self, name):
		self.tools.append(name)
	
	def finishAdd(self):
		self.myModel = QStringListModel(self.tools)
		self.setModel(self.myModel)
		self.connect(self.selectionModel(), SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.newSelection)
	
	def newSelection(self, old, new):
		row = self.selectedIndexes()[0].row()
		self.loadTool(self.tools[row])
	
	def selectTool(self, name):
		try:
			index = self.model().index(self.tools.index(name))
		except:
			index = self.model().index(self.tools.index("Summary"))
		self.selectionModel().setCurrentIndex(index, QItemSelectionModel.ClearAndSelect)
	
	def getSelectedTool(self):
		return self.tools[self.selectionModel().currentIndex().row()]
	
	def loadTool(self, tool):
		# Check for rebuilding portfolio if it's dirty
		# Don't rebuild if background rebuilding is enabled
		app = appGlobal.getApp()
		app.main.setCursor(Qt.WaitCursor)
		if app.portfolio.portPrefs.getDirty() and not tool in ["Transactions", "Settings", "News"] and not app.prefs.getBackgroundRebuild():
			p =  app.portfolio

			# Only show update window if app is started
			if app.started:
				update = StatusUpdate(app.main, modal = False, closeOnFinish = True)

				update.setStatus("Rebuilding " + p.name)
				update.setSubTask(100)
			else:
				update = False

			p.rebuildPositionHistory(app.stockData, update)
			if update:
				update.finishSubTask("Finished rebuilding " + p.name)

		app.prefs.setLastTab(tool)
		app.tool = app.plugins.getPlugin(tool)
	
		# Remove old tool
		if app.toolWidget:
			app.toolWidget.deleteLater()
			app.main.toolLayout.removeWidget(app.toolWidget)

		# Add new tool
		try:
			app.toolWidget = app.tool.createWidget(app.main)
		except Exception, inst:
			app.toolWidget = QLabel("Error while loading plugin: %s\n%s" % (inst, "".join(traceback.format_exc())))
		if app.toolWidget:
			app.main.toolLayout.addWidget(app.toolWidget)
		app.main.splitter.setSizes([200, app.prefs.getWidth() - 200])
		app.main.setCursor(Qt.ArrowCursor)
		app.checkThreadSafeError()

class MainWindow(QMainWindow):
	def __init__(self):
		QMainWindow.__init__(self)
	
	def render(self):
		self.setWindowTitle('Icarra 2')
		self.setMinimumSize(QSize(400, 300))
		
		central = QWidget(self)
		vbox = QVBoxLayout(central)
		vbox.setMargin(0)
		vbox.setSpacing(0)
		self.setCentralWidget(central)
		
		# Create splitter
		self.splitter = QSplitter()
		self.splitter.setContentsMargins(10, 10, 10, 10)
		vbox.addWidget(self.splitter)
		#self.setCentralWidget(self.splitter)
		
		# Create menus
		self.fileMenu = QMenu("File")
		self.menuBar().addMenu(self.fileMenu)

		exit = QAction("Exit", self)
		exit.setMenuRole(QAction.QuitRole)
		exit.setShortcut("Ctrl+Q")
		exit.setStatusTip("Exit Icarra2")
		self.fileMenu.addAction(exit)
		self.connect(exit, SIGNAL("triggered()"), self.exit)

		about = QAction("About...", self)
		about.setMenuRole(QAction.AboutRole)
		about.setStatusTip("About Icarra2")
		self.fileMenu.addAction(about)
		self.connect(about, SIGNAL("triggered()"), self.about)

		prefsMenu = QAction("Preferences...", self)
		prefsMenu.setMenuRole(QAction.PreferencesRole)
		prefsMenu.setStatusTip("Preferences")
		self.fileMenu.addAction(prefsMenu)
		self.connect(prefsMenu, SIGNAL("triggered()"), self.preferences)

		help = QAction("Help...", self)
		help.setMenuRole(QAction.ApplicationSpecificRole)
		help.setStatusTip("Icarra Help")
		self.fileMenu.addAction(help)
		self.connect(help, SIGNAL("triggered()"), self.help)

		# Create tool selector
		self.ts = ToolSelector()
		self.splitter.addWidget(self.ts)
		
		# Create tool holder
		self.toolHolder = QWidget(self.splitter)
		self.toolLayout = QVBoxLayout(self.toolHolder)
		self.toolLayout.setMargin(0)

		self.resize(prefs.getWidth(), prefs.getHeight())
	
	def resizeEvent(self, event):
		w = self.size().width()
		h = self.size().height()
		if w != prefs.getWidth() or h != prefs.getHeight():
			prefs.setSize(w, h)

	def exit(self):
		autoUpdater.stop()
		QCoreApplication.exit()

	def closeEvent(self, event):
		autoUpdater.stop()
		QCoreApplication.exit()
	
	def about(self):
		about = QMessageBox.about(self, "About Icarra2", "Icarra version %d.%d.%d\n\nPyQT version %s\n\nby Jesse Liesch" % (appGlobal.gMajorVersion, appGlobal.gMinorVersion, appGlobal.gRelease, PYQT_VERSION_STR))
	
	def help(self):
		help = HelpFrame()

	def preferences(self):
		p = PrefsFrame(self)

global prefs
prefs = Prefs()

class Icarra2(QApplication):
	def __init__(self, *args):
		global prefs
		self.started = False

		self.isOSX = sys.platform.startswith("darwin")
		self.isWindows = sys.platform.startswith("win")
		self.isLinux = sys.platform.startswith("linux")

		QApplication.__init__(self, *args)
		self.setApplicationName('Icarra2')
		self.setQuitOnLastWindowClosed(False)

		# Set global app and path
		if hasattr(sys, "frozen"):
			appPath = os.path.dirname(sys.argv[0])
		else:
			appPath = os.getcwd()
		appGlobal.setApp(self, appPath)
		
		# For thread safe errors
		self.errorMutex = threading.Lock()
		self.errorList = []
		
		# For checking tables
		self.checkTableMutex = threading.Lock()
		
		# For starting and ending big tasks
		self.bigTask = False
		self.bigTaskCondition = threading.Condition()
		
		# The current statusUpdate dialog, if any
		self.statusUpdate = False

		# Initialize members
		self.prefs = prefs
		self.stockData = StockData()
		self.ofxDebugFrame = False
		self.portfolio = False
		self.tool = False
		self.toolWidget = False

		self.positiveColor = QColor(0, 153, 0)
		self.negativeColor = QColor(204, 0, 0)
		self.alternateRowColor = QColor(216, 216, 255)

		# Make sure benchmarks have been created
		checkBenchmarks(prefs)
		
		# Nothing else if regression
		if "--regression" in args[0] or "--broker-info" in args[0] or "--rebuild" in args[0] or "--import" in args[0]:
			return
		
		timesRun = prefs.getTimesRun()
		splashTime = datetime.datetime.now()
		if timesRun > 0:
			# Start updater now so we can get stock data
			autoUpdater.start(self.stockData, self.prefs)

			self.splash = SplashScreenFrame()
		else:
			self.createSamplePortfolio()
			
			# Set all stocks as not having been downloaded
			# This is important incase the startup process failed
			self.stockData.db.query("update stockInfo set lastDownload='1900-01-01 00:00:00'")

			# Start after creating sample portfolio
			autoUpdater.start(self.stockData, self.prefs)

			# Load initial data, make sure we got it
			self.splash = SplashScreenFrame(firstTime = True)
			if not self.splash.running:
				autoUpdater.stop()
				self.splash.close()
				self.started = False
				message = QMessageBox(QMessageBox.Critical, "Connection error", "Unable to connect to the Icarra web server.  Please check your internet connection and try again.", flags = Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint | Qt.WindowStaysOnTopHint)
				message.exec_()
				return

		self.main = MainWindow()
		self.processEvents()
	
		self.plugins = PluginManager()

		self.main.render()
		self.processEvents()
		
		self.rebuildPortfoliosMenu()

		self.loadPortfolio(prefs.getLastPortfolio())
		self.processEvents()

		if self.prefs.getOfxDebug():
			self.startOfxDebug()

		if self.splash and timesRun == 0:
			self.splash.progress.setValue(100)

		self.checkVersion()

		self.processEvents()

		# Wait up to 2 seconds before hiding splash screen
		elapsedMs = (datetime.datetime.now() - splashTime).microseconds / 1000
		if self.splash and elapsedMs < 3000:
			self.timer = QTimer()
			interval = 3000 - elapsedMs
			self.timer.setInterval(interval)
			self.timer.setSingleShot(True)
			self.timer.start()
			self.connect(self.timer, SIGNAL("timeout()"), self.hideSplash)
		else:
			self.hideSplash()

		self.prefs.incTimesRun()
		appGlobal.getApp().started = True
			
	def checkIntro(self):
		tutorial.check(tutorial.intro)

	def createSamplePortfolio(self):
		# Check that not already created
		if prefs.hasPortfolio("Sample Portfolio"):
			return
		
		prefs.addPortfolio("Sample Portfolio")
		prefs.setLastTab("Summary")
		prefs.setLastPortfolio("Sample Portfolio")
		p = Portfolio("Sample Portfolio")
		p.db.beginTransaction()

		t = Transaction(1, "__CASH__", datetime.datetime(2008, 1, 2), Transaction.deposit, amount = 20000)
		t.save(p.db)

		t = Transaction(2, "AAPL", datetime.datetime(2008, 1, 2), Transaction.buy, amount = 10000, shares = 50, pricePerShare = 200, fee = 0)
		t.save(p.db)

		shares = 107.52688172043
		t = Transaction(3, "XOM", datetime.datetime(2008, 1, 2), Transaction.buy, amount = 10000, shares = shares, pricePerShare = 93, fee = 0)
		t.save(p.db)

		t = Transaction(4, "XOM", datetime.datetime(2008, 2, 7), Transaction.dividend, amount = shares * 0.35)
		t.save(p.db)

		t = Transaction(5, "XOM", datetime.datetime(2008, 3, 9), Transaction.dividend, amount = shares * 0.4)
		t.save(p.db)

		t = Transaction(6, "XOM", datetime.datetime(2008, 8, 11), Transaction.dividend, amount = shares * 0.4)
		t.save(p.db)

		t = Transaction(7, "XOM", datetime.datetime(2008, 11, 7), Transaction.dividend, amount = shares * 0.4)
		t.save(p.db)

		t = Transaction(8, "XOM", datetime.datetime(2009, 3, 11), Transaction.dividend, amount = shares * 0.42)
		t.save(p.db)

		t = Transaction(9, "XOM", datetime.datetime(2009, 8, 11), Transaction.dividend, amount = shares * 0.42)
		t.save(p.db)

		t = Transaction(10, "XOM", datetime.datetime(2009, 11, 9), Transaction.dividend, amount = shares * 0.42)
		t.save(p.db)

		t = Transaction(11, "XOM", datetime.datetime(2010, 2, 8), Transaction.dividend, amount = shares * 0.42)
		t.save(p.db)

		t = Transaction(12, "XOM", datetime.datetime(2010, 3, 11), Transaction.dividend, amount = shares * 0.44)
		t.save(p.db)

		t = Transaction(13, "XOM", datetime.datetime(2010, 8, 11), Transaction.dividend, amount = shares * 0.44)
		t.save(p.db)

		t = Transaction(14, "XOM", datetime.datetime(2010, 11, 9), Transaction.dividend, amount = shares * 0.44)
		t.save(p.db)

		p.db.commitTransaction()
	
	def hideSplash(self):
		if self.splash:
			self.splash.close()
		self.main.show()
		self.main.raise_()
		
		# Set timer for tutorial
		self.tutorialTimer = QTimer()
		self.tutorialTimer.setInterval(500)
		self.tutorialTimer.setSingleShot(True)
		self.connect(self.tutorialTimer, SIGNAL("timeout()"), self.checkIntro)
		self.tutorialTimer.start()
	
	def beginBigTask(self, description, status = False):
		# Get the bigTask mutex
		# Check if we're currently doing anything big
		# If so, wait for it to finish
		self.bigTaskCondition.acquire()
		while self.bigTask:
			if status:
				status.setStatus('Waiting while we finish ' + self.bigTask + '...')
			self.bigTaskCondition.wait(1)
		self.bigTask = description
		self.bigTaskCondition.release()
	
	def endBigTask(self):
		# We're no longer doing anything big
		# Wake up anyone who is waiting
		self.bigTaskCondition.acquire()
		self.bigTask = False
		self.bigTaskCondition.notify()
		self.bigTaskCondition.release()

	def loadPortfolio(self, name):
		global prefs
		prefs.setLastPortfolio(name)
		
		# Remove old portfolio
		if self.portfolio:
			del self.portfolio
			self.portfolio = False

		# Set title and check/uncheck menus
		self.main.setWindowTitle('Icarra - ' + name)
		for a in self.portfoliosMenu.actions():
			a.setChecked(a.text().replace("&&", "&") == name)

		try:
			self.portfolio = Portfolio(name)
			self.portfolio.readFromDb()
	
			self.main.ts.rebuild()

			# Load tool
			self.main.ts.selectTool(prefs.getLastTab())
			
			# Enable or disable Import Transactions menu
			if self.portfolio.isBrokerage() and not self.portfolio.isBank():
				self.importTransactionsAction.setEnabled(True)
			else:
				self.importTransactionsAction.setEnabled(False)
		except Exception, e:
			self.toolWidget = QLabel("Error while loading plugin: %s\n%s" % (e, "".join(traceback.format_exc())))
			self.main.toolLayout.addWidget(self.toolWidget)
	
	def selectPortfolio(self, t):
		# Check for new portfolio using shortcut
		if t.shortcut() == "CTRL+N":
			d = NewPortfolio(self.main)
			d.exec_()
		elif t.shortcut() == "CTRL+I":
			# Import, ignore here
			pass
		elif t.shortcut() == "CTRL+R":
			# Rebuild, ignore here
			pass
		else:
			name = str(t.text())
			name = name.replace("&&", "&")
			self.loadPortfolio(name)

	def importTransactions(self):
		brokerage = self.plugins.getBrokerage(self.portfolio.brokerage)
		if not brokerage:
			print "no brokerage"

		self.plugins.getPlugin("Transactions").doImport()

	def rebuildPortfolio(self):
		p =  self.portfolio
		update = StatusUpdate(app.main, modal = False)
		
		update.setStatus("Rebuilding " + p.name)

		update.setSubTask(100)
		p.rebuildPositionHistory(app.stockData, update)
		update.finishSubTask("Finished rebuilding " + p.name)

	def rebuildPortfoliosMenu(self, load = True):
		global prefs
		portfolios = sorted(prefs.getPortfolios())
		
		# Add or clear menu
		if "portfoliosMenu" in dir(self):
			self.portfoliosMenu.clear()
		else:
			self.portfoliosMenu = QMenu("Portfolio", self.main)
			self.connect(self.portfoliosMenu, SIGNAL("triggered(QAction*)"), self.selectPortfolio)
			self.main.menuBar().addMenu(self.portfoliosMenu)
		
		n = QAction("New Portfolio", self.main)
		n.setShortcut("CTRL+N")
		self.portfoliosMenu.addAction(n)

		self.importTransactionsAction = QAction("Import Transactions", self.main)
		self.importTransactionsAction.setShortcut("CTRL+I")
		if self.portfolio and not self.portfolio.isBrokerage():
			self.importTransactionsAction.setEnabled(False)
		self.portfoliosMenu.addAction(self.importTransactionsAction)
		self.connect(self.importTransactionsAction, SIGNAL("triggered()"), self.importTransactions)

		reb = QAction("Rebuild Portfolio", self.main)
		reb.setShortcut("CTRL+R")
		self.portfoliosMenu.addAction(reb)
		self.portfoliosMenu.addSeparator()
		self.connect(reb, SIGNAL("triggered()"), self.rebuildPortfolio)
		
		benchmarks = []
		addedPort = False
		self.portfolioActions = {}
		for name in portfolios:
			p = Portfolio(name)
			if not p:
				continue
			name = name.replace("&", "&&")
			self.portfolioActions[name] = QAction(name, self)

			a = QAction(name, self.main)
			a.setCheckable(True)
			if p.isBenchmark():
				benchmarks.append(a)
			else:
				self.portfoliosMenu.addAction(a)
				addedPort = True
			if p.name == prefs.getLastPortfolio():
				a.setChecked(True)
		if addedPort and len(benchmarks) > 0:
			self.portfoliosMenu.addSeparator()
		for a in benchmarks:
			self.portfoliosMenu.addAction(a)

	def getUniqueId(self):
		# Create uniqueId
		id = self.prefs.getUniqueId()
		if id == "":
			id = str(uuid.uuid4())
			self.prefs.setUniqueId(id)
		return id

	def checkVersion(self):
		# Check new
		(newMajor, newMinor, newRelease) = self.prefs.getLatestVersion()
		if newMajor > appGlobal.gMajorVersion or (newMajor == appGlobal.gMajorVersion and newMinor > appGlobal.gMinorVersion) or (newMajor == appGlobal.gMajorVersion and newMinor == appGlobal.gMinorVersion and newRelease > appGlobal.gRelease):
			# Remind once per week
			if datetime.datetime.now() < appGlobal.getApp().prefs.getLastVersionReminder() + datetime.timedelta(days = 7):
				return
	
			# Check if skipped
			(skipMajor, skipMinor, skipRelease) = self.prefs.getIgnoreVersion()
			if newMajor != skipMajor or newMinor != skipMinor or newRelease != skipRelease:
				d = NewVersion(newMajor, newMinor, newRelease)

	def startOfxDebug(self):
		if self.ofxDebugFrame:
			return

		self.ofxDebugFrame = OfxDebugFrame()
	
	def addThreadSafeError(self, area, error):
		self.errorMutex.acquire()
		print "THREAD ERRROR:", area, error
		self.errorList.append((area, error))
		self.errorMutex.release()
	
	def checkThreadSafeError(self):
		self.errorMutex.acquire()
		for (area, error) in self.errorList:
			message = QMessageBox(QMessageBox.Critical, area, error).exec_()
		self.errorList = []
		self.errorMutex.release()

if "--broker-info" in sys.argv:
	app = Icarra2(sys.argv)

	print "<h2>Notes</h2>"
	for b in app.plugins.getBrokerages():
		if b.getNotes():
			print b.getName()
			print "<ul>"
			for n in b.getNotes():
				print "<li>", n, "</li>"
			print "</ul>"
		else:
			print "<p>", b.getName(), "</p>"
	print "<p>Is your brokerage not supported?  Contact us in the forum &mdash; we would love to help!</p>"
	app.exit()
	sys.exit()

if "--regression" in sys.argv:
	import traceback
	app = Icarra2(sys.argv)
	
	try:
		import regression
		regression.run(sys.argv)
	except Exception, e:
		print "Error running regression:"
		print traceback.format_exc()
	
	app.exit()
	sys.exit()

if "--rebuild" in sys.argv:
	import traceback
	app = Icarra2(sys.argv)
	
	try:
		p = Portfolio(sys.argv[2])
		p.rebuildPositionHistory(app.stockData)
	except Exception, e:
		print "Error running regression:"
		print traceback.format_exc()
	
	app.exit()
	sys.exit()

if "--import" in sys.argv:
	f = open(sys.argv[2], "r")
	if not f:
		print "Could not open", sys.argv[2]
		sys.exit()
	data = f.read()
	
	for format in getFileFormats():
		if format.Guess(data):
			print "Is", format
			(numNew, numOld, newTickers) = format.StartParse(data, False, False)
			print "New: %d, Old: %d, Tickers: %s" % (numNew, numOld, newTickers)
			sys.exit(0)
	print "Did not guess", sys.argv[2]

# Launch and run app
# If exception, stop autoUpdater thread and re-raise exception
try:
	app = Icarra2(sys.argv)
	if app.started:
		app.exec_()
	else:
		app.quit()
except:
	autoUpdater.stop()
	raise
