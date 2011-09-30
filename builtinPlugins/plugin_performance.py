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

class PerformanceModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		
		self.dividend = True
		self.current = False
		self.type = "performance"

	def rebuildPerformance(self):
		stockData = appGlobal.getApp().stockData
		portfolio = appGlobal.getApp().portfolio

		table = portfolio.getPerformanceTable(self.current, self.dividend, self.type)
		self.setColumns(table[0])
		self.setData(table[1])
		for col in range(len(table[0])):
			if col == 0:
				continue
			self.setRedGreenColumn(col)

		#name = stockData.getName(t)
		#if name:
		#	grid.getCtrl(row, 0).SetToolTipString(name)
		#tooltips[row][col] =  "From %d/%d/%d to %d/%d/%d (%.2f years)" % (first.month, first.day, first.year, date.month, date.day, date.year, years)

class PerformanceWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.model = PerformanceModel(self)
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		
		hor = QHBoxLayout()
		vbox.addLayout(hor)
		
		portfolio = appGlobal.getApp().portfolio
		
		hor.addWidget(QLabel("Type:"))
		self.chartType = QComboBox()
		self.chartTypes = ["Value", "Profit", "Performance", "Internal Rate of Return (IRR)"]
		self.chartType.addItems(self.chartTypes)
		type = portfolio.portPrefs.getChartType()
		if type in self.chartTypes:
			self.chartType.setCurrentIndex(self.chartTypes.index(type))
			self.model.type = type.lower()
		hor.addWidget(self.chartType)
		self.connect(self.chartType, SIGNAL("currentIndexChanged(int)"), self.changeType)

		current = QCheckBox("Current Positions Only")
		if portfolio.portPrefs.getPerformanceCurrent():
			current.setChecked(True)
			self.model.current = True
		hor.addWidget(current)
		
		div = QCheckBox("Dividends")
		if portfolio.portPrefs.getPerformanceDividends():
			div.setChecked(True)
			self.model.dividend = True
		hor.addWidget(div)
		
		# Redraw when checkboxes are changed
		self.connect(current, SIGNAL("stateChanged(int)"), self.changeCurrent)
		self.connect(div, SIGNAL("stateChanged(int)"), self.changeDiv)
		
		hor.addStretch(1000)

		self.table = EditGrid(self.model)

		self.model.rebuildPerformance()
		self.table.resizeColumnsToContents()
		self.table.setSortingEnabled(True)

		vbox.addWidget(self.table)
	
	def changeType(self, event):
		type = self.chartTypes[self.chartType.currentIndex()]
		appGlobal.getApp().portfolio.portPrefs.setChartType(type)
		self.model.type = type.lower()

		self.model.rebuildPerformance()

	def changeCurrent(self, state):
		self.model.current = state != 0
		appGlobal.getApp().portfolio.portPrefs.setPerformanceCurrent(self.model.current)
		self.model.rebuildPerformance()

	def changeDiv(self, state):
		self.model.dividend = state != 0
		appGlobal.getApp().portfolio.portPrefs.setPerformanceDividends(self.model.dividend)
		self.model.rebuildPerformance()

class Plugin(PluginBase):
	def __init__(self):
		PluginBase.__init__(self)
		
	def name(self):
		return "Performance"
	
	def icarraVersion(self):
		return (0, 0, 0)

	def version(self):
		return (1, 0, 0)
	
	def forBank(self):
		return False

	def createWidget(self, parent):
		return PerformanceWidget(parent)
