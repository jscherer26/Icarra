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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from prefs import *
import appGlobal

import re

class NewPortfolio(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		self.setWindowTitle("Choose Portfolio Settings")
		self.added = False
		
		vert = QVBoxLayout(self)
		
		horiz = QHBoxLayout()
		vert.addLayout(horiz)

		self.name = QLineEdit(self)
		self.name.setText("New Portfolio")
		horiz.addWidget(QLabel("Portfolio Name:"))
		horiz.addWidget(self.name)
		horiz.addStretch(1000)
		self.name.setFocus()
		self.name.setSelection(0, 200) # Select all
		
		vert.addSpacing(15)
		
		box = QGroupBox("Portfolio Type")
		boxLayout = QVBoxLayout(box)
		boxLayout.setSpacing(15)
		vert.addWidget(box)
		
  		self.brokerage = QRadioButton("Investment: Portfolio for stocks, mutual funds, bonds, etc.")
  		self.brokerage.setChecked(True)
  		boxLayout.addWidget(self.brokerage)
		
  		self.bank = QRadioButton("Bank: Portfolio for banking, credit cards, savings")
  		boxLayout.addWidget(self.bank)

  		self.benchmark = QRadioButton("Benchmark: Benchmark portfolio for investments based on an asset allocation")
  		boxLayout.addWidget(self.benchmark)

  		self.combined = QRadioButton("Combined: Combine several portfolios into a larger portfolio")
  		boxLayout.addWidget(self.combined)
  		
  		buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
  		vert.addWidget(buttons)
  		self.connect(buttons.button(QDialogButtonBox.Cancel), SIGNAL("clicked()"), SLOT("reject()"))
  		self.connect(buttons.button(QDialogButtonBox.Ok), SIGNAL("clicked()"), self.onOk)

	def onOk(self):
		app = appGlobal.getApp()
		self.setCursor(Qt.WaitCursor)
		app.processEvents()

		newName = str(self.name.text())
		if re.search("[/\\.]", newName):
			QMessageBox(QMessageBox.Critical, 'Invalid Name', 'Please do not use any of the following characters: / or \ or .').exec_()
			return
		
		prefs = appGlobal.getApp().prefs
		
		# Check for unique name
		portfolios = prefs.getPortfolios()
		for name in portfolios:
			if name.upper() == newName.upper():
				QMessageBox(QMessageBox.Critical, 'Duplicate Name', 'A portfolio with that name already exists.  Please choose a new name.').exec_()
				return
		
		self.added = True
		
		# Create portfolio, go to settings, and select it
		prefs.addPortfolio(newName)
		prefs.setLastTab("Settings")
		prefs.setLastPortfolio(newName)
		app.main.ts.selectTool("Settings")
		app.loadPortfolio(newName)
		app.rebuildPortfoliosMenu()

		if self.benchmark.isChecked():
			app.portfolio.makeBenchmark()
			app.loadPortfolio(newName)
		elif self.combined.isChecked():
			app.portfolio.makeCombined()
			app.loadPortfolio(newName)
		elif self.bank.isChecked():
			app.portfolio.makeBank()
			app.loadPortfolio(newName)
		else:
			app.loadPortfolio(newName)

		self.setCursor(Qt.ArrowCursor)
		self.close()
