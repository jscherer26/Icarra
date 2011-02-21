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

	def rebuildPerformance(self):		
		stockData = appGlobal.getApp().stockData
		portfolio = appGlobal.getApp().portfolio
		tickers = portfolio.getTickers()
		if len(tickers) > 0:
			tickers.append("__COMBINED__")

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
		
		lastDay = portfolio.getEndDate()
		
		dates = [firstDayOfYear, oneYear, twoYear, threeYear, fiveYear, lastDay]

		row = 0
		tooltips = {}
		data = []
		rowMap = {}
		self.rowMap = rowMap
		performance = {}
		
		# Iterate through copy of tickers, incase elements re removed
		portFirst = False
		for t in copy.copy(tickers):
			firstLast = portfolio.getPositionFirstLast(t)
			if not firstLast:
				tickers.remove(t)
				continue
			(first, last) = firstLast
			
			if t == "__COMBINED__":
				portFirst = first

			# Check that the position is current
			if last != lastDay and self.current:
				tickers.remove(t)
				continue

			performance[t] = {}
			
			# Compute YTD return
			(ret, years) = portfolio.calculatePerformanceTimeWeighted(t, firstDayOfYear, last, dividend = self.dividend)
			performance[t][firstDayOfYear] = (ret, years)
			
			# Compute year return
			(ret, years) = portfolio.calculatePerformanceTimeWeighted(t, oneYear, last, dividend = self.dividend)
			performance[t][oneYear] = (ret, years)

			# Compute two year return
			(ret, years) = portfolio.calculatePerformanceTimeWeighted(t, twoYear, last, dividend = self.dividend)
			performance[t][twoYear] = (ret, years)

			# Compute three year return
			(ret, years) = portfolio.calculatePerformanceTimeWeighted(t, threeYear, last, dividend = self.dividend)
			performance[t][threeYear] = (ret, years)

			# Compute five year return
			(ret, years) = portfolio.calculatePerformanceTimeWeighted(t, fiveYear, last, dividend = self.dividend)
			performance[t][fiveYear] = (ret, years)

			# Compute inception return
			(ret, years) = portfolio.calculatePerformanceTimeWeighted(t, first, last, dividend = self.dividend)
			performance[t][lastDay] = (ret, years)
			
			row += 1
		
		# Do benchmark if benchmark is not included AND we have a first portfolio date
		if not portfolio.getBenchmark() in performance and portFirst:
			t = portfolio.getBenchmark()
			benchmark = Portfolio(t)
			
			if benchmark.portPrefs.getDirty():
				benchmark.rebuildPositionHistory(stockData)
			
			firstLast = benchmark.getPositionFirstLast("__COMBINED__")
			if firstLast:
				(first, last) = firstLast
	
				# Check that the position is current
				tickers.append(t)
				performance[t] = {}
				
				# Compute YTD return
				(ret, years) = benchmark.calculatePerformanceTimeWeighted("__COMBINED__", firstDayOfYear, last, dividend = self.dividend)
				performance[t][firstDayOfYear] = (ret, years)
				
				# Compute year return
				(ret, years) = benchmark.calculatePerformanceTimeWeighted("__COMBINED__", oneYear, last, dividend = self.dividend)
				performance[t][oneYear] = (ret, years)
	
				# Compute two year return
				(ret, years) = benchmark.calculatePerformanceTimeWeighted("__COMBINED__", twoYear, last, dividend = self.dividend)
				performance[t][twoYear] = (ret, years)
	
				# Compute three year return
				(ret, years) = benchmark.calculatePerformanceTimeWeighted("__COMBINED__", threeYear, last, dividend = self.dividend)
				performance[t][threeYear] = (ret, years)
	
				# Compute five year return
				(ret, years) = benchmark.calculatePerformanceTimeWeighted("__COMBINED__", fiveYear, last, dividend = self.dividend)
				performance[t][fiveYear] = (ret, years)
	
				# Compute inception return
				(ret, years) = benchmark.calculatePerformanceTimeWeighted("__COMBINED__", portFirst, last, dividend = self.dividend)
				performance[t][lastDay] = (ret, years)

		# Check active columns, always include last day
		activeCols = {lastDay: True}
		for t in performance:
			for date in performance[t]:
				(ret, yeras) = performance[t][date]
				if ret != "n/a":
					activeCols[date] = True
		dates = sorted(activeCols.keys())

		numCols = 1 + len(dates)

		# Create columns
		cols = ["Position"]
		for date in dates:
			self.setRedGreenColumn(len(cols))
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
		self.setColumns(cols)

		tickers.sort()
		
		# Add returns
		row = 0
		for t in tickers:
			name = stockData.getName(t)
			#if name:
			#	grid.getCtrl(row, 0).SetToolTipString(name)

			data.append([])
			rowMap[row] = row
			data[row].append(t)

			tooltips[row] = {}
			col = 1
			for date in dates:
				if date in performance[t]:
					ret = performance[t][date][0]
					years = performance[t][date][1]
					
					color = False
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
		
		self.setData(data)

class PerformanceWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.model = PerformanceModel(self)
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		
		hor = QHBoxLayout()
		vbox.addLayout(hor)
		
		portfolio = appGlobal.getApp().portfolio
		
		current = QCheckBox("Current Positions Only")
		if portfolio.portPrefs.getPerformanceCurrent():
			current.setChecked(True)
			self.model.current = True
		hor.addWidget(current)
		
		div = QCheckBox("Include Dividends")
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

	def createWidget(self, parent):
		return PerformanceWidget(parent)
