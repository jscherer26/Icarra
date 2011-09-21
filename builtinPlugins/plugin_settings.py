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

from portfolio import *
from statusUpdate import *
from editGrid import *
from plugin import *

import appGlobal
import chart
import tutorial

try:
	import keyring
	haveKeyring = True
except:
	haveKeyring = False

class Plugin(PluginBase):
	def name(self):
		return "Settings"

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)

	def initialize(self):
		pass

	def createWidget(self, parent):
		return PortfolioSettingsWidget(parent)
	
	def finalize(self):
		pass

class TestImport(QDialog):
	def __init__(self, parent = None):
		QDialog.__init__(self, parent)
		self.app = appGlobal.getApp()
		self.setWindowTitle("Test login to " + self.app.portfolio.brokerage)
		
		self.ok = False
		self.didImport = False

		layout = QVBoxLayout(self)

		hbox = QHBoxLayout()
		layout.addLayout(hbox)
		
		self.passwordLabel = QLabel("Password: ")
		hbox.addWidget(self.passwordLabel)
		self.password = QLineEdit()
		self.password.setEchoMode(QLineEdit.Password)
		hbox.addWidget(self.password)
		
		# Check for keying, try to load password
		if haveKeyring:
			self.savePassword = QCheckBox("Save Password")
			hbox2 = QHBoxLayout()
			hbox2.addSpacing(20)
			layout.addLayout(hbox2)
			hbox2.addWidget(self.savePassword)
			layout.addSpacing(10)

			password = keyring.get_password("Icarra-ofx-" + self.app.portfolio.name, self.app.portfolio.username)
			if password:
				self.password.setText(password)
				self.savePassword.setChecked(True)
		
		self.password.setFocus()
		
		buttons = QHBoxLayout()
		layout.addLayout(buttons)

		cancel = QPushButton("Cancel")
		buttons.addWidget(cancel)
		self.connect(cancel, SIGNAL("clicked()"), SLOT("reject()"))
		
		ok = QPushButton("Ok")
		ok.setDefault(True)
		buttons.addWidget(ok)
		self.connect(ok, SIGNAL("clicked()"), self.onOk)
	
	def onOk(self):
		portfolio = self.app.portfolio
		brokerage = self.app.plugins.getBrokerage(portfolio.brokerage)
		try:
			status = StatusUpdate(self, cancelable = True, numTextLines = 3)
			status.setStatus("Logging in to " + portfolio.brokerage, 5)

			# Import from ofx
			self.app.portfolio.portPrefs.setLastImport("ofx")
			username = str(portfolio.username)
			password = str(self.password.text())
			account = portfolio.account
			
			if password == "":
				status.setStatus("Login not successful: Please enter a password", 100)
				return
			
			if portfolio.account == "" or portfolio.account == "(optional)" or not portfolio.account or portfolio.account == "None":
				status.setStatus("Retrieving account information", 10)
				(success, account) = getAccount(username, password, brokerage)
				if not success:
					status.setStatus("Login not successful: Could not get account: " + account, 100)
					return
				
				# If multiple accounts are chosen, bring up a selector dialog
				if type(account) == type([]) :
					accountSelector = sys.modules["plugin_transactions"].AccountSelector(status, account)
					account = accountSelector.account
					
					if account:
						portfolio.account = account
						self.app.prefs.updatePortfolio(portfolio.name, portfolio.brokerage, portfolio.username, account)
				else:
					# Single account
					portfolio.account = account
					self.app.prefs.updatePortfolio(portfolio.name, portfolio.brokerage, portfolio.username, account)

			# If still no account, abort
			if portfolio.account == "" or portfolio.account == "(optional)" or not portfolio.account or portfolio.account == "None":
				status.setStatus("Login not successful: Could not get account.", 100)
				return
			
			ofx = getOfx(username, password, brokerage, account, status)
			if ofx.find("did not get account") != -1:
				status.setStatus("Sorry, we could not read your account information.", 100)
				return
			elif ofx.find("could not connect") != -1:
				status.setStatus("We could not connect to %s.  Please check your internet connection." % portfolio.brokerage, 100)
				return
			elif ofx == "":
				status.setStatus("We could not download OFX data.  Please run with OFX Debug enabled.", 100)
				return
			elif ofx.find("Invalid login") != -1:
				status.setStatus("Login not successful: Please check that your username and password are correct.", 100)
				return
			else:
				portfolio.updateFromFile(ofx, self.app, status)
				self.didImport = True

				if haveKeyring:
					if self.savePassword.isChecked():
						keyring.set_password("Icarra-ofx-" + portfolio.name, username, password)
					else:
						keyring.set_password("Icarra-ofx-" + portfolio.name, username, "")
		except Exception, e:
			import traceback
			status.addError('Could not get transactions: %s' % traceback.format_exc())
			status.setFinished()
		
		self.accept()

class PortfolioSettingsWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.app = appGlobal.getApp()

		portfolio = self.app.portfolio
		
		vbox = QVBoxLayout(self)
		vbox.setAlignment(Qt.AlignTop)

		frame = QFrame()
		frame.setFrameStyle(QFrame.Panel)
		frame.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		frame.setStyleSheet("QFrame { background: white }")
		vbox.addWidget(frame)
		
		grid = QGridLayout(frame)
		
		grid.addWidget(QLabel("<b>Name</b>"), 0, 0)
		self.name = QLineEdit()
		self.name.setText(portfolio.name)
		grid.addWidget(self.name, 0, 1)
		self.connect(self.name, SIGNAL("textChanged(QString)"), self.newName)

		if portfolio.isBrokerage() or portfolio.isCombined():
			grid.addWidget(QLabel("<b>Benchmark</b>"), 1, 0)
			portfolios = self.app.prefs.getPortfolios()
			choices = []
			for name in portfolios:
				port = Portfolio(name)
				if port.isBenchmark():
					choices.append(port.name)
			self.benchmarkChoices = choices
			self.benchmark = QComboBox()
			self.benchmark.addItems(choices)
			if portfolio.getBenchmark() in choices:
				self.benchmark.setCurrentIndex(choices.index(portfolio.getBenchmark()))
			grid.addWidget(self.benchmark, 1, 1)
			self.connect(self.benchmark, SIGNAL("currentIndexChanged(int)"), self.newBenchmark)

		row = 2
		if portfolio.isBrokerage():
			brokerFrame = QFrame()
			brokerFrame.setFrameStyle(QFrame.StyledPanel)
			grid.addWidget(brokerFrame, row, 0, 1, 2)
			row += 1
			
			grid2 = QGridLayout(brokerFrame)
			grid2.addWidget(QLabel("<b>Brokerage</b>"), 0, 0)
			
			brokers = self.app.plugins.getBrokerages()
			choices = ["None"]
			text = False
			for b in brokers:
				choices.append(b.getName())
				if b.getName() == portfolio.brokerage:
					text = b.getNotes()
			self.brokerageChoices = choices
			
			self.brokerage = QComboBox()
			self.brokerage.addItems(choices)
			if portfolio.brokerage in choices:
				self.brokerage.setCurrentIndex(choices.index(portfolio.brokerage))
			grid2.addWidget(self.brokerage, 0, 1)
			self.connect(self.brokerage, SIGNAL("currentIndexChanged(int)"), self.newBrokerageInfo)
			
			grid2.addWidget(QLabel("<b>Notes</b>"), 1, 0)
			self.brokerageNotes = QLabel()
			grid2.addWidget(self.brokerageNotes, 1, 1)
				
			self.redoBrokerageNotes()
			
			grid2.addWidget(QLabel("<b>Username</b>"), 2, 0)
			self.username = QLineEdit()
			if portfolio.username:
				self.username.setText(portfolio.username)
			grid2.addWidget(self.username, 2, 1)
			self.connect(self.username, SIGNAL("textChanged(QString)"), self.newBrokerageInfo)

			grid2.addWidget(QLabel("<b>Account</b>"), 3, 0)
			self.account = QLineEdit()
			if portfolio.account:
				self.account.setText(portfolio.account)
			else:
				self.account.setText("(optional)")
			grid2.addWidget(self.account, 3, 1)
			self.connect(self.account, SIGNAL("textChanged(QString)"), self.newBrokerageInfo)
			
			buttonBox = QHBoxLayout()
			grid2.addLayout(buttonBox, 4, 0, 1, 2)
			
			testImport = QPushButton("Change Account")
			self.connect(testImport, SIGNAL("clicked()"), self.changeAccount)
			buttonBox.addWidget(testImport)

			testImport = QPushButton("Test Import")
			self.connect(testImport, SIGNAL("clicked()"), self.testImport)
			buttonBox.addWidget(testImport)
			
			buttonBox.addStretch(1)
		elif portfolio.isCombined():
			combinedFrame = QFrame()
			combinedFrame.setFrameStyle(QFrame.StyledPanel)
			grid.addWidget(combinedFrame, row, 0, 1, 2)
			row += 1

			grid2 = QGridLayout(combinedFrame)
			grid2.addWidget(QLabel("<b>Components</b>"), 0, 0)

			alreadyChecked = portfolio.portPrefs.getCombinedComponents()

			self.checks = {}
			compFrame = QFrame()
			compFrameLayout = QVBoxLayout(compFrame)
			for portName in self.app.prefs.getPortfolios():
				p = Portfolio(portName)
				if p.isBrokerage():
					check = QCheckBox(portName)
					compFrameLayout.addWidget(check)

					# See if already checked
					if portName in alreadyChecked:
						check.setChecked(True)

					self.checks[portName] = check
					self.connect(check, SIGNAL("stateChanged(int)"), self.toggleCombined)
			grid2.addWidget(compFrame, 0, 1)
		
		self.advancedOptions = QCheckBox("Show advanced options")
		self.connect(self.advancedOptions, SIGNAL("clicked()"), self.twiddleAdvanced)
		grid.addWidget(self.advancedOptions, row, 0, 1, 2)
		row += 1

		self.summaryFrame = QFrame()
		self.summaryFrame.setFrameStyle(QFrame.StyledPanel)
		grid.addWidget(self.summaryFrame, row, 0, 1, 2)
		row += 1
		
		grid3 = QGridLayout(self.summaryFrame)

		grid3.addWidget(QLabel("<b>Summary Report</b>"), 0, 0)
		choices = ["Show current year only", "Show last year", "Show all years"]
		if portfolio.getSummaryYears() == "thisYear":
			value = 0
		elif portfolio.getSummaryYears() == "lastYear":
			value = 1
		else: # allYears
			value = 2
		self.reportChoices = choices
		self.report = QComboBox()
		self.report.addItems(choices)
		self.report.setCurrentIndex(value)
		grid3.addWidget(self.report, 0, 1)
		self.connect(self.report, SIGNAL("currentIndexChanged(int)"), self.newReport)

		grid3.addWidget(QLabel("<b>Summary Chart 1</b>"), 1, 0)
		self.summary1 = QComboBox()
		self.chartTypesList = [v for k,v in chart.getSummaryChartTypes(portfolio).items()]
		try:
			index = self.chartTypesList.index(chart.getSummaryChartTypes(portfolio)[portfolio.getSummaryChart1()])
		except:
			index = 0
		self.summary1.addItems(self.chartTypesList)
		self.summary1.setCurrentIndex(index)
		self.connect(self.summary1, SIGNAL("currentIndexChanged(int)"), self.newSummary1)
		grid3.addWidget(self.summary1, 1, 1)

		grid3.addWidget(QLabel("<b>Summary Chart 2</b>"), 2, 0)
		try:
			index = self.chartTypesList.index(chart.getSummaryChartTypes(portfolio)[portfolio.getSummaryChart2()])
		except:
			index = 0
		self.summary2 = QComboBox()
		self.summary2.addItems(self.chartTypesList)
		self.summary2.setCurrentIndex(index)
		self.connect(self.summary2, SIGNAL("currentIndexChanged(int)"), self.newSummary2)
		grid3.addWidget(self.summary2, 2, 1)

		if portfolio.name != "S&P 500":
			self.hasDelete = True
			self.deleteButton = QPushButton("Delete Portfolio")
			self.deleteButton.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
			self.connect(self.deleteButton, SIGNAL("clicked()"), self.delete)
			grid.addWidget(self.deleteButton, row, 0, 1, 2)
			row += 1
		else:
			self.hasDelete = False
		
		self.twiddleAdvanced()

		# Set timer for tutorial
		if portfolio.name != "Sample Portfolio" and portfolio.name != "S&P 500" and portfolio.name != "Aggressive":
			self.tutorialTimer = QTimer()
			self.tutorialTimer.setInterval(500)
			self.tutorialTimer.setSingleShot(True)
			self.connect(self.tutorialTimer, SIGNAL("timeout()"), self.checkTutorial)
			self.tutorialTimer.start()
	
	def twiddleAdvanced(self):
		if self.advancedOptions.isChecked():
			if self.hasDelete:
				self.deleteButton.show()
			self.summaryFrame.show()
		else:
			if self.hasDelete:
				self.deleteButton.hide()
			self.summaryFrame.hide()
	
	def checkTutorial(self):
		portfolio = self.app.portfolio
		if portfolio.isBrokerage():
			tutorial.check(tutorial.settings)
		elif portfolio.isCombined():
			tutorial.check(tutorial.settingsCombined)
		elif portfolio.isBenchmark():
			tutorial.check(tutorial.settingsBenchmark)

	def toggleCombined(self):
		combinedString = ""
		for portName in self.checks:
			if self.checks[portName].isChecked():
				if combinedString != "":
					combinedString += ","
				combinedString += portName
		self.app.portfolio.portPrefs.setCombinedComponents(combinedString)
		self.app.portfolio.portPrefs.setDirty(True)
	
	def redoBrokerageNotes(self, newValue = False):
		# Use portfolio value if nothing is given
		if not newValue:
			newValue = self.app.portfolio.brokerage

		for b in self.app.plugins.getBrokerages():
			if b.getName() == newValue:
				text = ""
				for t in b.getNotes():
					if text:
						text += "\n"
					text += t
				self.brokerageNotes.setText(text)
				break
	
	def newName(self):
		name = str(self.name.text())
		if name != self.app.portfolio.name:
			error = self.app.prefs.changePortfolioName(self.app.portfolio.name, name)
			if not error:
				self.app.prefs.setLastPortfolio(name)
				self.app.main.setWindowTitle(name)
				self.app.rebuildPortfoliosMenu()
	
			self.app.portfolio = Portfolio(name)
			self.app.portfolio.readFromDb()
	
	def newBenchmark(self):
		benchmark = self.benchmarkChoices[self.benchmark.currentIndex()]
		self.app.portfolio.setBenchmark(benchmark)

		self.app.portfolio = Portfolio(self.app.portfolio.name)
		self.app.portfolio.readFromDb()
	
	def newReport(self):
		summ = self.reportChoices[self.report.currentIndex()]
		if summ == "Show current year only":
			self.app.portfolio.setSummaryYears("thisYear")
		elif summ == "Show last year":
			self.app.portfolio.setSummaryYears("lastYear")
		else:
			self.app.portfolio.setSummaryYears("allYears")

		self.app.portfolio = Portfolio(self.app.portfolio.name)
		self.app.portfolio.readFromDb()
	
	def newSummary1(self):
		types = chart.getSummaryChartTypes(self.app.portfolio)
		revTypes = dict((v,k) for k, v in types.iteritems())
		typeName = self.chartTypesList[self.summary1.currentIndex()]
		type = revTypes[typeName]
		self.app.portfolio.setSummaryChart1(type)

	def newSummary2(self):
		types = chart.getSummaryChartTypes(self.app.portfolio)
		revTypes = dict((v,k) for k, v in types.iteritems())
		typeName = self.chartTypesList[self.summary2.currentIndex()]
		type = revTypes[typeName]
		self.app.portfolio.setSummaryChart2(type)

	def newBrokerageInfo(self, ignore = None):
		name = str(self.name.text())
		brokerage = self.brokerageChoices[self.brokerage.currentIndex()]
		username = str(self.username.text())
		account = str(self.account.text())
		
		if brokerage == "None":
			brokerage = ""
		if brokerage != self.app.portfolio.brokerage:
			self.redoBrokerageNotes(brokerage)
		self.app.prefs.updatePortfolio(
			name,
			brokerage,
			username,
			account)

		self.app.portfolio = Portfolio(name)
		self.app.portfolio.readFromDb()

	def changeAccount(self):
		self.app.portfolio.account = ""
		self.testImport(alwaysSetAccount = True)
		
	def testImport(self, alwaysSetAccount = False):
		portfolio = self.app.portfolio
		if not portfolio.brokerage:
			QMessageBox(QMessageBox.Information, "Cannot Test", "Please set Brokerage and Username before logging in").exec_()
			return
		elif not portfolio.username:
			QMessageBox(QMessageBox.Information, "Cannot Test", "Please set your Username before logging in").exec_()
			return

		t = TestImport(self)
		t.exec_()
		if t.didImport and (alwaysSetAccount or self.account.text() == "(optional)" or self.account.text() == "" or not self.account.text() or self.account.text() == "None"):
			self.account.setText(portfolio.account)
	
	def delete(self):
		box = QMessageBox(QMessageBox.Question, "Please confirm", "Are you sure you wish to delete this portfolio?", buttons = QMessageBox.Ok | QMessageBox.Cancel)
		box.setDefaultButton(QMessageBox.Cancel)
		confirm = box.exec_()
		if confirm == QMessageBox.Ok:
			self.app.portfolio.delete(self.app.prefs)
			self.app.loadPortfolio("S&P 500")
			self.app.rebuildPortfoliosMenu()
			ports = self.app.prefs.getPortfolios()
			if len(ports) > 0:
				self.app.loadPortfolio(ports[0])
			else:
				self.app.loadPortfolio("")
