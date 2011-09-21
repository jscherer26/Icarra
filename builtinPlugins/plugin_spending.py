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
import copy

from editGrid import *
from plugin import *
from portfolio import *
import appGlobal

class SpendingModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		self.days = 30
		self.categorized = True

	def rebuildSpending(self):
		portfolio = appGlobal.getApp().portfolio

		table = portfolio.getSpendingTable(days = self.days, categorize = self.categorized)
		self.setColumns(table[0])
		self.setData(table[1])

class SpendingWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.model = SpendingModel(self)
		portfolio = appGlobal.getApp().portfolio
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		
		hor = QHBoxLayout()
		hor.setMargin(0)
		vbox.addLayout(hor)

		hor.addWidget(QLabel("Period:"))

		self.periods = ["One Week", "One Month", "Three Months", "One Year", "Two Years", "Three Years", "Five Years", "Ten Years", "Portfolio Inception"]
		value = portfolio.portPrefs.getPositionPeriod()
		self.period = QComboBox()
		self.period.addItems(self.periods)
		if value in self.periods:
			self.period.setCurrentIndex(self.periods.index(value))
		else:
			self.period.setCurrentIndex(self.periods.index("Portfolio Inception"))
		hor.addWidget(self.period)
		self.connect(self.period, SIGNAL("currentIndexChanged(int)"), self.newPeriod)
		
		showCategorized = QCheckBox("Show Categorized")
		if True or portfolio.portPrefs.getPerformanceCurrent():
			showCategorized.setChecked(True)
			self.model.categorized = True
		hor.addWidget(showCategorized)
		
		# Redraw when checkbox is changed
		self.connect(showCategorized, SIGNAL("stateChanged(int)"), self.changeCategorized)
		
		hor.addStretch(1000)
		
		self.table = EditGrid(self.model)

		self.newPeriod()

		vbox.addWidget(self.table)

		self.table.setSortingEnabled(True)
		self.table.sortByColumn(1, Qt.DescendingOrder)
		self.table.resizeColumnsToContents()
	
	def newPeriod(self):
		period = self.periods[self.period.currentIndex()]
		appGlobal.getApp().portfolio.portPrefs.setPositionPeriod(period)

		period = self.periods[self.period.currentIndex()]
		if period == "One Week":
			self.model.days = 7
		elif period == "One Month":
			self.model.days = 30
		elif period == "Three Months":
			self.model.days = 91
		elif period == "One Year":
			self.model.days = 365
		elif period == "Two Years":
			self.model.days = 365 * 2
		elif period == "Three Years":
			self.model.days = 365 * 3
		elif period == "Five Years":
			self.model.days = 365 * 5 + 1
		elif period == "Ten Years":
			self.model.days = 365 * 10 + 2
		else:
			self.model.days = 365 * 100 # 100 years

		self.model.rebuildSpending()
		self.table.resizeColumnsToContents()

	def changeCategorized(self, state):
		self.model.categorized = state != 0
		#appGlobal.getApp().portfolio.portPrefs.setPerformanceCurrent(self.model.current)
		self.model.rebuildSpending()
		self.table.resizeColumnsToContents()

class Plugin(PluginBase):
	def __init__(self):
		PluginBase.__init__(self)
		
	def name(self):
		return "Spending"
	
	def icarraVersion(self):
		return (0, 0, 0)

	def version(self):
		return (1, 0, 0)
	
	def forInvestment(self):
		return False

	def createWidget(self, parent):
		return SpendingWidget(parent)
