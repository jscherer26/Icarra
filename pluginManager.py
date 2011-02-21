import sys
import glob

from prefs import *
import appGlobal

class PluginManager:
	def __init__(self):
		self.plugins = {}
		self.brokerages = {}

		# Load all plugins in user plugins path
		prefsRoot = Prefs.prefsRootPath()
		sys.path.append(prefsRoot + 'plugins')
		path = os.path.join(prefsRoot, "plugins/plugin_*.py")
		for file in glob.glob(path):
			plugin = file.replace(prefsRoot + 'plugins', '')
			plugin = plugin.replace('/', '')
			plugin = plugin.replace('\\', '')
			plugin = plugin.replace('.py', '')
			__import__(plugin)
			self.plugins[plugin] = sys.modules[plugin].Plugin()
			self.plugins[plugin].builtin = False

		# Load all plugins in builtin path
		pluginPath = os.path.join(appGlobal.getPath(), 'builtinPlugins')
		sys.path.append(pluginPath)
		for file in glob.glob('builtinPlugins/plugin_*.py'):
			plugin = file.replace('builtinPlugins', '')
			plugin = plugin.replace('/', '')
			plugin = plugin.replace('\\', '')
			plugin = plugin.replace('.py', '')
			__import__(plugin)
			self.plugins[plugin] = sys.modules[plugin].Plugin()
			self.plugins[plugin].builtin = True

		# Check for duplicate names
		names = {}
		for p, plugin in self.plugins.items():
			if plugin.name() in names:
				print "Duplicate plugin name", plugin.name()
				sys.exit()
			names[plugin.name()] = True

		for p, plugin in self.plugins.items():
			plugin.initialize()

		# Check for duplicate names
		names = {}
		for p, plugin in self.plugins.items():
			if plugin.name() in names:
				print "Duplicate plugin name", plugin.name()
				sys.exit()
			names[plugin.name()] = True
		
		# Load all brokerages in user plugins path
		path = os.path.join(prefsRoot, "plugins/brokerage_*.py")
		for file in glob.glob(path):
			brokerage = file.replace(prefsRoot + 'plugins', '')
			brokerage = brokerage.replace('/', '')
			brokerage = brokerage.replace('\\', '')
			brokerage = brokerage.replace('.py', '')
			__import__(brokerage)
			self.brokerages[brokerage] = sys.modules[brokerage].Brokerage()
			self.brokerages[brokerage].builtin = False

		# Load all brokerages in builtin path
		for file in glob.glob('builtinPlugins/brokerage_*.py'):
			brokerage = file.replace('builtinPlugins', '')
			brokerage = brokerage.replace('/', '')
			brokerage = brokerage.replace('\\', '')
			brokerage = brokerage.replace('.py', '')
			__import__(brokerage)
			self.brokerages[brokerage] = sys.modules[brokerage].Brokerage()
			self.brokerages[brokerage].builtin = True

		# Check for duplicate names
		names = {}
		for b, brokerage in self.brokerages.items():
			if brokerage.getName() in names:
				print "Duplicate brokerage name", brokerage.getName()
				sys.exit()
			names[brokerage.getName()] = True

	def __del__(self):
		for p in self.plugins:
			self.plugins[p].finalize()

	def isPlugin(self, name):
		for p, plugin in self.plugins.items():
			if plugin.name() == name:
				return True
		return False

	def getPlugin(self, name):
		for p, plugin in self.plugins.items():
			if plugin.name() == name:
				return plugin
		return None
	
	def getPlugins(self):
		names = []
		for p, plugin in self.plugins.items():
			names.append(p)
		names.sort()

		ret = []
		for n in names:
			ret.append(self.plugins[n])
		return ret
	
	def isBrokerage(self, name):
		for p, brokerage in self.brokeragess.items():
			if brokerage.name == name:
				return True
		return False

	def getBrokerage(self, name):
		for p, brokerage in self.brokerages.items():
			if brokerage.getName() == name:
				return brokerage
		return None
	
	def getBrokerages(self):
		names = []
		for p, brokerage in self.brokerages.items():
			names.append(p)
		names.sort()

		ret = []
		for n in names:
			ret.append(self.brokerages[n])
		return ret

