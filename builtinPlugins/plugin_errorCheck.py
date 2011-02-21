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

from editGrid import *
from plugin import *
import appGlobal

class Plugin(PluginBase):
	def name(self):
		return 'Error Check'

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)

	def initialize(self):
		pass

	def createWidget(self, parent):
		return ErrorCheckWidget(parent)
	
	def reRender(self, panel, app):
		pass

	def finalize(self):
		pass

class ErrorCheckModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		
		self.ticker = False
		self.setColumns(["Error", "Severity", "Recommended Fix"])
	
	def setErrors(self):
		app = appGlobal.getApp()
		
		errors = app.portfolio.errorCheck(app.stockData)
		self.errors = []
		for e in errors:
			self.errors.append(e)
		self.setData(self.errors)

class ErrorCheckWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
	
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)

		self.model = ErrorCheckModel()
		self.table = EditGrid(self.model)
		self.table.horizontalHeader().setResizeMode(0, QHeaderView.ResizeToContents)
		self.table.horizontalHeader().setResizeMode(1, QHeaderView.ResizeToContents)
		self.table.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
		self.table.setWordWrap(True)
		self.table.setTextElideMode(Qt.ElideNone)
		
		self.model.setErrors()
		self.table.resizeRowsToContents()
		vbox.addWidget(self.table)

	def ignore(self):
		for (error, severity, fix) in errors:
			grid.addText(error)
			grid.addText(severity)
			grid.addText(fix)
		self.Layout()
