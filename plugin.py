from PyQt4.QtCore import *
from PyQt4.QtGui import *

class PluginBase(QWidget):
	def __init__(self):
		QWidget.__init__(self)
	
	def name(self):
		'Return the display name of this plugin'
		return '???'

	def icarraVersion(self):
		'Return the latest version of Icarra software that this plugin has been tested with'
		return (0, 2, 0)

	def version(self):
		'Return a 3-tuple of the plugin version'
		return (0, 0, 0)

	def forInvestment(self):
		return True

	def forBank(self):
		return True

	def initialize(self):
		'Called on startup.  Called sequentially for each plugin.  This may not be the first function that is called.'
		pass

	def createWidget(self, parent):
		'Called when the plugin should display its GUI controls.  Should return a QWidget or None.  The QWidget will be returned as the widget argument to reRender.'
		return None

	def reRender(self, widget, app):
		'Called when the plugin should re-display its GUI controls.  Render will always be called first.'
		pass

	def finalize(self):
		'Called when Icarra exits.  Called sequentially for each plugin.'
		pass
