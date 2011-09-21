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
import appGlobal

class EditGridModel(QAbstractTableModel):
	def __init__(self, parent = None, *args): 
		QAbstractTableModel.__init__(self, parent, *args)
		self.myData = []
		self.myColumns = []
		self.redGreenCols = {}
		self.redGreenRows = {}
		self.sortColumn = False
		self.sortOrder = False
		self.rowHeader = False

	# Sort based on column.  Warning: fancy python here.
	@staticmethod
	def mySortKey(*items):
		i = items[0]
		def g(obj):
			val = obj[i]
			if isinstance(val, str):
				val = val.strip("$").strip("%").replace(",", "")
				try:
					val = float(val)
				except:
					pass
			return val
		return g

	def setData(self, data, reset = True):
		self.myData = data

		# Append the index of each element as the last value
		i = 0
		for row in self.myData:
			row.append(i)
			i += 1
		
		if self.sortColumn:
			self.sort(self.sortColumn, self.sortOrder)
		
		if reset:
			self.reset()

	def setColumns(self, columns):
		self.myColumns = columns
		
	def setRedGreenColumn(self, col):
		self.redGreenCols[col] = True
	
	def setRedGreenRow(self, row):
		self.redGreenRows[row] = True
	
	def rowCount(self, parent = None):
		return len(self.myData)
	
	def columnCount(self, parent = None):
		if self.rowHeader:
			return len(self.myColumns) - 1
		else:
			return len(self.myColumns)
	
	def sort(self, column, order):
		self.sortColumn = column
		self.sortOrder = order
		
		def myCmp(a, b):
			if a == "":
				return -1
			elif b == "":
				return 1
			elif a < b:
				return -1
			elif a > b:
				return 1
			else:
				return 0
		
		self.myData.sort(key = self.mySortKey(column), cmp = myCmp)
		if order == Qt.DescendingOrder:
			self.myData.reverse()
			
		self.reset()

	def headerData(self, col, orientation, role):
		if self.rowHeader:
			col += 1
		if orientation == Qt.Horizontal and role == Qt.DisplayRole and col < len(self.myColumns):
			return QVariant(self.myColumns[col])
		elif orientation == Qt.Vertical and role == Qt.DisplayRole and col <= len(self.myData):
			return QVariant(self.myData[col - 1][0])
		return QVariant()
	
	def data(self, index, role):
		row = index.row()
		column = index.column()
		if self.rowHeader:
			column += 1
		
		if not index.isValid():
			return QVariant() 
		elif role == Qt.BackgroundRole:
			if row % 2 == 1:
				return QVariant(appGlobal.getApp().alternateRowColor)
		elif role == Qt.ForegroundRole:
			# Return red/green if it is a red/green column
			if column in self.redGreenCols or row in self.redGreenRows:
				d = self.myData[row]
				if column < len(d):
					val = d[column]
					if val:
						# Try converting to float and return positive/negative
						try:
							val = val.replace('$', '').replace('%', '').replace(',', '')
							val = float(val)
							if val >= 0:
								return QVariant(appGlobal.getApp().positiveColor)
							else:
								return QVariant(appGlobal.getApp().negativeColor)
						except:
							return QVariant()
		elif role != Qt.DisplayRole: 
			return QVariant()
		if row < len(self.myData):
			# Return nothing if it is an editor
			if column in self.myTable.editColumns and row in self.myTable.editColumns[column]:
				return QVariant()

			d = self.myData[row]
			if column < len(d):
				# Return string depending on column
				val = d[column]
				if isinstance(val, datetime.datetime):
					return QVariant(val.strftime("%m/%d/%Y"))
				else:
					return QVariant(val)
		return QVariant()
	
	def dataChanged(self, editor, index):
		# Overload if using editors
		pass

class EditGrid(QTableView):
	def __init__(self, model, parent = None, sorting = False):
		QTableView.__init__(self, parent)
		self.editColumns = {}
		self.editors = []
		model.myTable = self

		self.setModel(model)
		self.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.setSelectionMode(QAbstractItemView.SingleSelection)
		self.verticalHeader().hide()

		if sorting:
			self.setSortingEnabled(True)

	def setRowHeader(self, val):
		# When using row headers data[row][0] is the header and all data is shifted over by one
		self.model().rowHeader = val
		if val:
			self.verticalHeader().show()
		else:
			self.verticalHeader().hide()

	@staticmethod
	def editChangedFactory(self, e):
		# Return a function suitable for processing editor textChanged signals
		def ec(string):
			self.model().dataChanged(e, e.myIndex)
		return ec
	
	def setEdit(self, row, column):
		index = self.model().createIndex(row, column)
		e = QLineEdit()
		e.setText(self.model().myData[row][column])
		e.myIndex = index
		e.setMinimumHeight(e.sizeHint().height() + 10)
		self.setIndexWidget(index, e)
		self.connect(e, SIGNAL("textChanged(QString)"), self.editChangedFactory(self, e))

		# Install style sheet, margin handled by setMinimumHeight
		if len(self.editColumns) == 0:
			self.setStyleSheet("QLineEdit { margin: 5px }")
		
		if not column in self.editColumns:
			self.editColumns[column] = [row]
		else:
			self.editColumns[column].append(row)

	def getEdit(self, row, column):
		index = self.model().createIndex(row, column)
		return self.indexWidget(index)

	def selectRow(self, index):
		# The last element of each row contains the original row number
		i = 0;
		for row in self.model().myData:
			if row[-1] == index:
				QTableView.selectRow(self, i)
			i += 1
	
	def selectedRow(self):
		rows = self.selectionModel().selectedRows()
		if len(rows) > 0:
			# The last element of each row contains the original row number
			sortedRow = rows[0].row()
			return self.model().myData[sortedRow][-1]
		else:
			return -1

	def resizeToMinimum(self):
		self.resizeColumnsToContents()
		
		width = self.horizontalHeader().length() + self.verticalHeader().sizeHint().width() + 4
		self.setMaximumWidth(width)
		
		height = self.horizontalHeader().sizeHint().height() + self.verticalHeader().length() + 4
		sb = self.horizontalScrollBar()
		if sb:
			# Check if scrollbar is shown, then add its height
			sbHeight = sb.sizeHint().height()
			if sbHeight > 0 and self.width() < width:
				height += sbHeight + 1
		self.setMaximumHeight(height)
