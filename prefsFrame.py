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

import prefs
import appGlobal

from editGrid import *

class PrefsFrame(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self)
		self.setWindowTitle("Icarra Preferences")
		self.app = appGlobal.getApp()
		
		grid = QGridLayout(self)
		
		self.showCash = QCheckBox("Show cash total in Transactions")
		if self.app.prefs.getShowCashInTransactions():
			self.showCash.setChecked(True)
		grid.addWidget(self.showCash, 0, 0, 1, 1)

		self.ofxDebug = QCheckBox("Enable OFX Debugging")
		if self.app.prefs.getOfxDebug():
			self.ofxDebug.setChecked(True)
		grid.addWidget(self.ofxDebug, 1, 0, 1, 1)
		
  		buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
  		grid.addWidget(buttons, 2, 0, 2, 1)
  		self.connect(buttons.button(QDialogButtonBox.Cancel), SIGNAL("clicked()"), SLOT("reject()"))
  		self.connect(buttons.button(QDialogButtonBox.Ok), SIGNAL("clicked()"), self.onOk)

		self.exec_()

	def onOk(self):
		if self.ofxDebug.isChecked() != self.app.prefs.getOfxDebug():
			self.app.prefs.setOfxDebug(self.ofxDebug.isChecked())

		if self.showCash.isChecked() != self.app.prefs.getShowCashInTransactions():
			self.app.prefs.setShowCashInTransactions(self.showCash.isChecked())

		self.close()