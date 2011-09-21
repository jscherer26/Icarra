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

import datetime

from portfolio import *
from editGrid import *
from plugin import *
from chartWidget import *

class Plugin(PluginBase):
	def name(self):
		return "Summary"

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)

	def initialize(self):
		pass

	def createWidget(self, parent):
		return PortfolioSummaryWidget(parent)
	
	def reRender(self, panel, app):
		panel.update()

	def finalize(self):
		pass

class PortfolioSummaryModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		self.app = appGlobal.getApp()
	
	def setSummary(self):
		# Create financial statement
		p = self.app.portfolio

		table = p.getSummaryTable()
		if table:
			self.setColumns(table[0])
			self.setData(table[1:])
			self.setRedGreenRow(2)
			self.setRedGreenRow(3)
			self.setRedGreenRow(4)

class PortfolioSummaryWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.app = appGlobal.getApp()
		self.chart1 = False
		self.chart2 = False
		self.model = False
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		vbox.setAlignment(Qt.AlignTop)
		
		self.chartLayout = QHBoxLayout()
		vbox.addLayout(self.chartLayout)
		
		self.chart1 = ChartWidget()
		self.app.portfolio.chartByType(self.chart1, self.app.portfolio.getSummaryChart1())
		self.chart1.pixelsPerTickY = 30
		self.chart1.pixelsPerTickX = 60
		self.chart1.margin = 10
		self.chart1.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum))
		self.chartLayout.addWidget(self.chart1)
		
		self.chart2 = ChartWidget()
		self.app.portfolio.chartByType(self.chart2, self.app.portfolio.getSummaryChart2())
		self.chart2.pixelsPerTickY = 30
		self.chart2.pixelsPerTickX = 60
		self.chart2.margin = 10
		self.chart2.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum))
		self.chartLayout.addWidget(self.chart2)

		self.model = PortfolioSummaryModel(self)
		self.table = EditGrid(self.model, sorting = False)
		self.table.setRowHeader(True)
		self.table.horizontalHeader().setResizeMode(QHeaderView.Fixed)
		self.table.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
		vbox.addWidget(self.table)
	
	def resizeEvent(self, event):
		w = self.size().width()
		
		if self.chart1:
			self.chart1.setMinimumHeight(w / 3)
		if self.chart2:
			self.chart2.setMinimumHeight(w / 3)

		if self.model:
			self.model.setSummary()
			self.table.resizeToMinimum()
		
		# Hack for older versions, forces to resize properly
		if PYQT_VERSION < 0x040700:
			self.hide()
			self.show()

		QWidget.resizeEvent(self, event)

	def resize(self, event):
		self.update()

