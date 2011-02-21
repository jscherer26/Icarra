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

import os

import appGlobal

intro = 0x00000001
settings = 0x00000002
settingsCombined = 0x00000004
settingsBenchmark = 0x00000008
transactions = 0x00000010
text = {}
text[intro] = "<p><b>Welcome to Icarra!</b></p><p>We have created a Sample Portfolio for you to explore.  It contains the two US stocks with the largest market capitalization: Exxon-Mobil and Apple.</p><p>Have a look around.  You can create a portfolio by navigating to the \"Portfolio\" menu and selecting \"New Portfolio\".  Your first portfolio should be an Investment portfolio.</p>"
text[settings] = "<p><b>New Portfolio</b></p><p>You have just created your first Icarra portfolio.</p><p>In the \"Settings\" tool you may configure your new portfolio.  Configuring the brokerage section will allow you to import transactions directly from your financial institution.</p><p>When you are done editing your portfolio's settings you can use the Transactions tool to import or add transactions.</p>"
text[transactions] = "<p><b>Transactions</b></p><p>In the transactions tool you may import, create, edit and delete transactions.</p><p>Importing transactions is the best way to add transactions to your portfolio.  Icarra will download transactions directly from your brokerage.  Please visit the Icarra forums if you are having trouble importing transactions.</p><p>You may also create and edit new transactions by hand.  This is necessary if your brokerage omits a transaction or provides incorrect data.  We suggest, however, that you import from your brokerage whenever possible.</p>"
text[settingsCombined] = "<p><b>Combined Portfolio</b></p><p>A Combined Portfolio is composed of one or more Investment portfolios.  You may choose which Investment portfolios to include in this combined portfolio by checking their name in the \"Settings\" tool in the components section.  You cannot directly edit its transactions.</p><p>A Combined portfolio behaves just like a regular Investment portfolio.</p>"
text[settingsBenchmark] = "<p><b>Benchmark Portfolio</b></p><p>Benchmark portfolios can be used for performance comparisons.  You may define the benchmark's components in the \"Allocation\" tool.  Click the \"Add Position\" button, set the ticker and choose the target holding percentage.  Continue until the total reaches 100%.</p>"

class Tutorial(QDialog):
	def __init__(self, tutorial):
		app = appGlobal.getApp()
		QDialog.__init__(self, None)
		self.setStyleSheet("background: white")
		
		self.sizer = QVBoxLayout(self)
		self.sizer.setMargin(0)

		pm = QPixmap(os.path.join(appGlobal.getPath(), 'icons/icarra.png'))
		img = QLabel()
		img.setPixmap(pm)
		self.sizer.addWidget(img)
		del pm
		
		label = QLabel(text[tutorial])
		label.setFixedWidth(300)
		label.setWordWrap(True)
		# Labels are too small for some reason
		label.setFixedHeight(label.sizeHint().height() * 1.1)
		self.sizer.addWidget(label, alignment = Qt.AlignCenter)
		
		h = QHBoxLayout()
		self.sizer.addSpacing(20)
		self.sizer.addLayout(h)
		self.sizer.addSpacing(10)
		
		button = QPushButton("OK")
		button.setStyleSheet("background: none")
		button.setDefault(True)
		h.addStretch(1)
		h.addWidget(button, stretch = 1)
		h.addStretch(1)
		self.connect(button, SIGNAL("clicked()"), SLOT("accept()"))

		# Center
		screen = app.desktop().screenGeometry()
		self.move(screen.center() - self.rect().center())
  		
		self.exec_()

def check(value):
	app = appGlobal.getApp()
	
	# Check then show
	if not (app.prefs.getTutorial() & value):
		tut = Tutorial(tutorial = value)
		app.prefs.setTutorialBit(value)
