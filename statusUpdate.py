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

from ofxToolkit import *

import appGlobal
import time

class StatusUpdate(QDialog):
	def __init__(self, parent, modal = True, closeOnFinish = False, cancelable = False, numTextLines = 1):
		QDialog.__init__(self, parent)
		self.finished = False
		self.canceled = False
		self.closeOnFinish = closeOnFinish
		self.cancelable = cancelable
		self.modal = modal
		self.numTextLines = 1
		if modal:
			self.setModal(True)
		self.subTasks = []
		
		layout = QGridLayout(self)
		
		layout.addWidget(QLabel("Status:"), 0, 0)
		if numTextLines == 1:
			label = ""
		else:
			label = ""
			for i in range(numTextLines - 1):
				label += "\n"
		self.status = QLabel(label)
		self.status.setFixedWidth(300)
		self.status.setWordWrap(True)
		self.status.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum))
		layout.addWidget(self.status, 0, 1)
		
		self.progress = QProgressBar()
		self.progress.setFixedWidth(300)
		layout.addWidget(self.progress, 1, 1)
		
		self.messagesLabel = QLabel("Messages:")
		self.messagesLabel.setVisible(False)
		layout.addWidget(self.messagesLabel, 2, 0)
		self.messages = QTextEdit()
		self.messages.setMaximumHeight(80)
		self.messages.setMaximumWidth(300)
		self.messages.setReadOnly(True)
		self.messages.setVisible(False)
		layout.addWidget(self.messages, 2, 1)

		self.errorsLabel = QLabel("Errors:")
		self.errorsLabel.setVisible(False)
		layout.addWidget(self.errorsLabel, 3, 0)
		self.errors = QTextEdit()
		self.errors.setMaximumHeight(80)
		self.errors.setMaximumWidth(300)
		self.errors.setReadOnly(True)
		self.errors.setVisible(False)
		layout.addWidget(self.errors, 3, 1)

		buttons = QHBoxLayout()
		buttons.setAlignment(Qt.AlignRight)
		buttons.addStretch(1000)
		layout.addLayout(buttons, 4, 0, 1, 2)

		if cancelable:
			self.cancel = QPushButton("Cancel")
			self.cancel.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
			buttons.addWidget(self.cancel)
			self.connect(self.cancel, SIGNAL("clicked()"), self.onCancel)
			self.connect(self, SIGNAL('triggered()'), self.closeEvent)

		if not self.closeOnFinish:
			self.ok = QPushButton("OK")
			self.ok.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
			self.ok.setDefault(True)
			self.ok.setDisabled(True)
			buttons.addWidget(self.ok)
			self.connect(self.ok, SIGNAL("clicked()"), SLOT("accept()"))

		self.show()
		self.raise_()
	
	def setSubTask(self, level):
		'Uses level% of the remaining progress bar'
		begin = self.progress.value()
		if begin < 0:
			begin = 0
		if len(self.subTasks) == 0:
			end = level
		else:
			end = begin + round((100 - begin) * level / 100)
		self.subTasks.append((begin, end))

	def finishSubTask(self, status = False):
		(begin, end) = self.subTasks[-1]
		self.subTasks.pop(-1)
		self.setStatus(status, end)
		self.appYield()

	def setStatus(self, status = False, level = False):
		if status:
			self.status.setText(status)
		if level:
			if len(self.subTasks) > 0:
				#print self.subTasks
				(begin, end) = self.subTasks[-1]
				self.progress.setValue(begin + (end - begin) * level / 100)
			else:
				self.progress.setValue(level)
		if self.progress.value() == 100:
			self.setFinished()
		self.appYield()

	def appYield(self):
		appGlobal.getApp().processEvents()
	
	def addMessage(self, message):
		self.messagesLabel.setVisible(True)
		self.messages.setVisible(True)
		if  self.messages.toPlainText():
			self.messages.append("\n" + message)
		else:
			self.messages.setText(message)
		self.appYield()

	def addError(self, error):
		self.errorsLabel.setVisible(True)
		self.errors.setVisible(True)

		oldValue = self.errors.verticalScrollBar().value()
		if  self.errors.toPlainText():
			self.errors.append("\n" + error)
		else:
			self.errors.setText(error)
		if oldValue == 0:
			self.errors.verticalScrollBar().setValue(0)

		self.errors.scrollContentsBy(0, -1000000)
		self.appYield()
	
	def setFinished(self):
		if self.finished:
			return
		self.finished = True
		
		self.progress.setValue(100)
		
		if self.closeOnFinish:
			# If closing on finish, no longer modal, then close and return
			self.appYield()
			time.sleep(1)
			if self.modal:
				self.setModal(False)
			self.close()
			return
		
		self.ok.setEnabled(True)
		if self.cancelable:
			self.cancel.setEnabled(False)
		if self.modal:
			self.exec_()

	def onCancel(self):
		self.canceled = True
		self.reject()
	
	def closeEvent(self, event):
		if not self.finished and not self.cancelable:
			event.ignore()
