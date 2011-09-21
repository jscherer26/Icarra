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

class EditCategories(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		self.setWindowTitle("Edit Categories")
		self.portfolio = appGlobal.getApp().portfolio
		self.account = ""
		
		vert = QVBoxLayout(self)
		self.vert = vert
		
		buttons1 = QHBoxLayout()
		vert.addLayout(buttons1)

		add = QPushButton("Add Category")
		self.connect(add, SIGNAL("clicked()"), self.addCategory)
		buttons1.addWidget(add)

		self.remove = QPushButton("Remove Category")
		self.connect(self.remove, SIGNAL("clicked()"), self.doRemove)
		self.remove.setDisabled(True)
		buttons1.addWidget(self.remove)

		buttons1.addStretch(1000)

		self.listView = False
		self.rebuildCategories()
		
		buttons = QHBoxLayout()
		buttons.setAlignment(Qt.AlignRight)
		buttons.addStretch(1000)
		vert.addLayout(buttons)

		self.ok = QPushButton("OK")
		self.ok.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		self.ok.setDefault(True)
		buttons.addWidget(self.ok)
		self.connect(self.ok, SIGNAL("clicked()"), self.onOk)

		self.exec_()
	
	def rebuildCategories(self):
		if self.listView is False:
			# First time in dialog
			self.listView = QListView(self)
			self.listView.setEditTriggers(QAbstractItemView.NoEditTriggers)
			self.listView.setSelectionMode(QListView.SingleSelection)
			self.listModel = QStringListModel(self.portfolio.getCategories())
			self.listView.setModel(self.listModel)
			self.listView.connect(self.listView.selectionModel(), SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.newSelection)
			self.vert.addWidget(self.listView)
		else:
			self.listModel.setStringList(self.portfolio.getCategories())
	
	def newSelection(self, old, new):
		self.remove.setEnabled(True)
		self.selectedCategoryIndex = self.listView.selectedIndexes()[0].row()
	
	def doRemove(self):
		self.portfolio.removeCategory(self.portfolio.getCategories()[self.selectedCategoryIndex])
		self.rebuildCategories()
		self.remove.setDisabled(True)
	
	def onOk(self):
		self.accept()
	
	def addCategory(self):
		(newCategory, success) = QInputDialog.getText(self, "Add Category", "New Category:")
		if success:
			self.portfolio.addCategory(str(newCategory))
			self.rebuildCategories()

class NewRule(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		self.setWindowTitle("New Rule")
		self.success = False
		self.newRule = False
		self.newCategory = False
		
		vbox = QVBoxLayout(self)
		
		vbox.addWidget(QLabel("Enter a rule.  For example, the rule \"joe\" without\nquotes will match any payee with joe in the\nname such as \"TRADER JOES\" and \"joe's crabshack.\""))
		vbox.addSpacing(20)
		
		layout = QGridLayout()
		vbox.addLayout(layout)
		
		layout.addWidget(QLabel("Rule:"), 0, 0)
		self.rule = QLineEdit(self)
		layout.addWidget(self.rule, 0, 1)

		layout.addWidget(QLabel("Category:"), 1, 0)
		
		self.category = QComboBox()
		self.category.addItems(appGlobal.getApp().portfolio.getCategories())
		layout.addWidget(self.category, 1, 1)

		buttons = QHBoxLayout()
		buttons.setAlignment(Qt.AlignRight)
		buttons.addStretch(1000)
		vbox.addLayout(buttons)

		self.cancel = QPushButton("Cancel")
		self.cancel.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		buttons.addWidget(self.cancel)
		self.connect(self.cancel, SIGNAL("clicked()"), SLOT("reject()"))

		self.ok = QPushButton("OK")
		self.ok.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		self.ok.setDefault(True)
		buttons.addWidget(self.ok)
		self.connect(self.ok, SIGNAL("clicked()"), self.onOk)

		self.exec_()
	
	def onOk(self):
		portfolio = appGlobal.getApp().portfolio
		rule = str(self.rule.text()).strip()
		# Check empty rule or rule already exists
		if rule == "":
			QMessageBox(QMessageBox.Information, "Invalid Rule", "Please enter a rule").exec_()
			return
		for r in portfolio.getRules():
			if rule == r[0]:
				QMessageBox(QMessageBox.Information, "Invalid Rule", "That rule already exists").exec_()
				return
		
		# Get category
		category = portfolio.getCategories()[self.category.currentIndex()]
		
		self.success = True
		self.newRule = rule
		self.newCategory = category
		self.accept()
		
class EditRules(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		self.setWindowTitle("Edit Rules")
		self.portfolio = appGlobal.getApp().portfolio
		self.account = ""
		
		vert = QVBoxLayout(self)
		self.vert = vert
		
		buttons1 = QHBoxLayout()
		vert.addLayout(buttons1)

		add = QPushButton("Add Rule")
		self.connect(add, SIGNAL("clicked()"), self.addRule)
		buttons1.addWidget(add)

		self.remove = QPushButton("Remove Rule")
		self.connect(self.remove, SIGNAL("clicked()"), self.doRemove)
		self.remove.setDisabled(True)
		buttons1.addWidget(self.remove)

		buttons1.addStretch(1000)

		self.listView = False
		self.rebuildRules()
		
		buttons = QHBoxLayout()
		buttons.setAlignment(Qt.AlignRight)
		buttons.addStretch(1000)
		vert.addLayout(buttons)

		self.ok = QPushButton("OK")
		self.ok.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		self.ok.setDefault(True)
		buttons.addWidget(self.ok)
		self.connect(self.ok, SIGNAL("clicked()"), self.onOk)

		self.exec_()
	
	def rebuildRules(self):
		if self.listView is False:
			# First time in dialog
			self.listView = QListView(self)
			self.listView.setEditTriggers(QAbstractItemView.NoEditTriggers)
			self.listView.setSelectionMode(QListView.SingleSelection)

			rules = []
			for r in self.portfolio.getRules():
				rules.append(r[0] + " -> " + r[1])
			self.listModel = QStringListModel(rules)

			self.listView.setModel(self.listModel)
			self.listView.connect(self.listView.selectionModel(), SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.newSelection)
			self.vert.addWidget(self.listView)
		else:
			rules = []
			for r in self.portfolio.getRules():
				rules.append(r[0] + " -> " + r[1])
			self.listModel.setStringList(rules)
	
	def newSelection(self, old, new):
		self.remove.setEnabled(True)
		self.selectedRuleIndex = self.listView.selectedIndexes()[0].row()
	
	def doRemove(self):
		self.portfolio.removeRule(self.portfolio.getRules()[self.selectedRuleIndex][0])
		self.rebuildRules()
		self.remove.setDisabled(True)
	
	def onOk(self):
		self.accept()
	
	def addRule(self):
		nr = NewRule(self)
		if nr.success:
			self.portfolio.addRule(nr.newRule, nr.newCategory)
			self.rebuildRules()

class CategoriesModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		self.showCategorized = False

	def rebuildCategories(self):
		self.portfolio = appGlobal.getApp().portfolio

		table = self.portfolio.getSpendingTable(doMonthly = False)

		# Add category
		table[0].append("Category");
		for row in table[1]:
			c = self.portfolio.getCategory(row[0])
			row.append(c)

		# Remove categorized payees
		rowIndex = 0
		while rowIndex < len(table[1]):
			row = table[1][rowIndex]
			if row[-1] == "Uncategorized" or self.showCategorized:
				rowIndex += 1
			else:
				del table[1][rowIndex]

		self.setColumns(table[0])
		self.setData(table[1])

	def dataChanged(self, combo, index):
		ticker = self.myData[index.row()][0]
		category = self.portfolio.getCategories()[combo.currentIndex()]
		self.portfolio.setCategory(ticker, category)

class CategoriesWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.model = CategoriesModel(self)
		portfolio = appGlobal.getApp().portfolio
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		
		hor = QHBoxLayout()
		hor.setMargin(0)
		vbox.addLayout(hor)
		
		editCategory = QPushButton("Edit Categories")
		self.connect(editCategory, SIGNAL("clicked()"), self.editCategory)
		hor.addWidget(editCategory)
		
		editRules = QPushButton("Edit Rules")
		self.connect(editRules, SIGNAL("clicked()"), self.editRules)
		hor.addWidget(editRules)

		runRules = QPushButton("Run Rules")
		self.connect(runRules, SIGNAL("clicked()"), self.runRules)
		hor.addWidget(runRules)

		self.showCategorized = QCheckBox("Show Categorized")
		self.connect(self.showCategorized, SIGNAL("stateChanged(int)"), self.newCategorized)
		hor.addWidget(self.showCategorized)
		
		hor.addStretch(1000)

		self.table = EditGrid(self.model)
		self.model.table = self.table

		vbox.addWidget(self.table)

		self.model.rebuildCategories()
		self.table.resizeRowsToContents()
		self.table.resizeColumnsToContents()

		self.addCombos()

		self.table.setStyleSheet("QComboBox { margin: 5px; padding-left: 10px }")

		self.table.resizeRowsToContents()
		self.table.resizeColumnsToContents()
	
	def newCategorized(self, value):
		self.model.showCategorized = value == Qt.Checked
		self.model.rebuildCategories()
		self.addCombos()
		self.table.resizeRowsToContents()
		self.table.resizeColumnsToContents()
	
	def addCombos(self):
		portfolio = appGlobal.getApp().portfolio
		categories = portfolio.getCategories()
		for row in range(self.model.rowCount()):
			index = self.model.createIndex(row, 2)
			e = QComboBox()
			e.myIndex = index
			e.setMinimumSize(e.sizeHint().width() + 50, e.sizeHint().height() + 10)
			e.addItems(portfolio.getCategories())
			ticker = self.model.myData[row][0]
			e.setCurrentIndex(categories.index(portfolio.getCategory(ticker)))
			self.table.connect(e, SIGNAL("currentIndexChanged(int)"), EditGrid.editChangedFactory(self.table, e))
			self.table.setIndexWidget(index, e)
			if not 2 in self.table.editColumns:
				self.table.editColumns[2] = [row]
			else:
				self.table.editColumns[2].append(row)
		self.table.resizeRowsToContents()
		self.table.resizeColumnsToContents()
	
	def editCategory(self):
		ec = EditCategories(self)
		self.model.rebuildCategories()
		self.addCombos()
		self.table.resizeRowsToContents()
		self.table.resizeColumnsToContents()
	
	def editRules(self):
		er = EditRules(self)
		self.addCombos()
	
	def runRules(self):
		appGlobal.getApp().portfolio.runRules()
		self.addCombos()

class Plugin(PluginBase):
	def __init__(self):
		PluginBase.__init__(self)
		
	def name(self):
		return "Categories"
	
	def icarraVersion(self):
		return (0, 0, 0)

	def version(self):
		return (1, 0, 0)
	
	def forInvestment(self):
		return False

	def createWidget(self, parent):
		return CategoriesWidget(parent)
