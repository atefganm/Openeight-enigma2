from Screen import Screen
from Components.Language import language
from Screens.ParentalControlSetup import ProtectedScreen
from enigma import eConsoleAppContainer, eDVBDB, eTimer

from Components.ActionMap import ActionMap, NumberActionMap
from Components.config import config, ConfigSubsection, ConfigText
from Components.PluginComponent import plugins
from Components.PluginList import *
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Language import language
from Components.ServiceList import refreshServiceList
from Components.Harddisk import harddiskmanager
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo, hassoftcaminstalled
from Components import Opkg
from Components.config import config, ConfigSubsection, ConfigYesNo, getConfigListEntry, configfile, ConfigText
from Components.ConfigList import ConfigListScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

from time import time
import os

config.misc.pluginbrowser = ConfigSubsection()
config.misc.pluginbrowser.plugin_order = ConfigText(default="")

config.pluginfilter = ConfigSubsection()
config.pluginfilter.openeight = ConfigYesNo(default=True)
config.pluginfilter.kernel = ConfigYesNo(default=False)
config.pluginfilter.drivers = ConfigYesNo(default=True)
config.pluginfilter.extensions = ConfigYesNo(default=True)
config.pluginfilter.e2_locales = ConfigYesNo(default=True)
config.pluginfilter.m2k = ConfigYesNo(default=True)
config.pluginfilter.picons = ConfigYesNo(default=True)
config.pluginfilter.pli = ConfigYesNo(default=False)
config.pluginfilter.security = ConfigYesNo(default=True)
config.pluginfilter.settings = ConfigYesNo(default=True)
config.pluginfilter.skins = ConfigYesNo(default=True)
config.pluginfilter.display = ConfigYesNo(default=True)
config.pluginfilter.softcams = ConfigYesNo(default=True)
config.pluginfilter.systemplugins = ConfigYesNo(default=True)
config.pluginfilter.vix = ConfigYesNo(default=False)
config.pluginfilter.weblinks = ConfigYesNo(default=True)
config.pluginfilter.userfeed = ConfigText(default='http://', fixed_size=False)


def languageChanged():
	plugins.clearPluginList()
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))


def Check_Softcam():
	found = False
	for x in os.listdir('/etc'):
		if x.find('.emu') > -1:
			found = True
			break
	return found


def CreateFeedConfig():
	fileconf = "/etc/opkg/user-feed.conf"
	feedurl = "src/gz user-feeds %s\n" % config.pluginfilter.userfeed.getValue()
	f = open(fileconf, "w")
	f.write(feedurl)
	f.close()
	container = eConsoleAppContainer()
	container.execute('opkg update')
	del container


config.misc.pluginbrowser = ConfigSubsection()
config.misc.pluginbrowser.plugin_order = ConfigText(default="")


class PluginBrowserSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")
		self["desc"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, name, desc):
		self["entry"].text = name
		self["desc"].text = desc


class PluginBrowser(Screen, ProtectedScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Plugin browser"))
		ProtectedScreen.__init__(self)

		self.firsttime = True

		self["key_red"] = self["red"] = Label(_("Remove plugins"))
		self["key_green"] = self["green"] = Label(_("Download plugins"))
		self.list = []
		self["list"] = PluginList(self.list)
		self["list"].list.sort()

		self["actions"] = ActionMap(["SetupActions", "WizardActions"],
		{
			"ok": self.save,
			"back": self.close,
			"menu": self.menu,
		})
		self["PluginDownloadActions"] = ActionMap(["ColorActions"],
		{
			"red": self.delete,
			"green": self.download
		})
		self["DirectionActions"] = ActionMap(["DirectionActions"],
		{
			"moveUp": self.moveUp,
			"moveDown": self.moveDown
		})
		self["NumberActions"] = NumberActionMap(["NumberActions"],
		{
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		})
		self["HelpActions"] = ActionMap(["HelpActions"],
		{
			"displayHelp": self.showHelp,
		})
		self.help = False

		self.number = 0
		self.nextNumberTimer = eTimer()
		self.nextNumberTimer.callback.append(self.okbuttonClick)

		self.onFirstExecBegin.append(self.checkWarnings)
		self.onShown.append(self.updateList)
		self.onChangedEntry = []
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.saveListsize)
		if config.pluginfilter.userfeed.getValue() != "http://":
				if not os.path.exists("/etc/opkg/user-feed.conf"):
					CreateFeedConfig()

	def menu(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginFilter)

	def exit(self):
		self.close(True)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and (not config.ParentalControl.config_sections.main_menu.value or hasattr(self.session, 'infobar') and self.session.infobar is None) and config.ParentalControl.config_sections.plugin_browser.value

	def exit(self):
		self.close(True)

	def saveListsize(self):
		listsize = self["list"].instance.size()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()

	def createSummary(self):
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["list"].getCurrent()
		if item:
			p = item[0]
			name = p.name
			desc = p.description
		else:
			name = "-"
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def checkWarnings(self):
		if len(plugins.warnings):
			text = _("Some plugins are not available:\n")
			for (pluginname, error) in plugins.warnings:
				text += _("%s (%s)\n") % (pluginname, error)
			plugins.resetWarnings()
			self.session.open(MessageBox, text=text, type=MessageBox.TYPE_WARNING)

	def moveUp(self):
		self.move(-1)

	def moveDown(self):
		self.move(1)

	def move(self, direction):
		if len(self.list) > 1:
			currentIndex = self["list"].getSelectionIndex()
			swapIndex = (currentIndex + direction) % len(self.list)
			if currentIndex == 0 and swapIndex != 1:
				self.list = self.list[1:] + [self.list[0]]
			elif swapIndex == 0 and currentIndex != 1:
				self.list = [self.list[-1]] + self.list[:-1]
			else:
				self.list[currentIndex], self.list[swapIndex] = self.list[swapIndex], self.list[currentIndex]
			self["list"].l.setList(self.list)
			if direction == 1:
				self["list"].down()
			else:
				self["list"].up()
			plugin_order = []
			for x in self.list:
				plugin_order.append(x[0].path[24:])
			config.misc.pluginbrowser.plugin_order.value = ",".join(plugin_order)
			config.misc.pluginbrowser.plugin_order.save()

        def save(self):
		self.run()

	def run(self):
		plugin = self["list"].l.getCurrentSelection()[0]
		plugin(session=self.session)
		self.help = False

	def setDefaultList(self, answer):
		if answer:
			config.misc.pluginbrowser.plugin_order.value = ""
			config.misc.pluginbrowser.plugin_order.save()
			self.updateList()

	def keyNumberGlobal(self, number):
		if number == 0 and self.number == 0:
			if len(self.list) > 0 and config.misc.pluginbrowser.plugin_order.value != "":
				self.session.openWithCallback(self.setDefaultList, MessageBox, _("Sort plugins list to default?"), MessageBox.TYPE_YESNO)
		else:
			self.number = self.number * 10 + number
			if self.number and self.number <= len(self.list):
				if number * 10 > len(self.list) or self.number >= 10:
					self.okbuttonClick()
				else:
					self.nextNumberTimer.start(1400, True)
			else:
				self.resetNumberKey()

	def okbuttonClick(self):
		self["list"].moveToIndex(self.number - 1)
		self.resetNumberKey()
		self.run()

	def resetNumberKey(self):
		self.nextNumberTimer.stop()
		self.number = 0

	def moveUp(self):
		self.move(-1)

	def moveDown(self):
		self.move(1)

	def move(self, direction):
		if len(self.list) > 1:
			currentIndex = self["list"].getSelectionIndex()
			swapIndex = (currentIndex + direction) % len(self.list)
			if currentIndex == 0 and swapIndex != 1:
				self.list = self.list[1:] + [self.list[0]]
			elif swapIndex == 0 and currentIndex != 1:
				self.list = [self.list[-1]] + self.list[:-1]
			else:
				self.list[currentIndex], self.list[swapIndex] = self.list[swapIndex], self.list[currentIndex]
			self["list"].l.setList(self.list)
			if direction == 1:
				self["list"].down()
			else:
				self["list"].up()
			plugin_order = []
			for x in self.list:
				plugin_order.append(x[0].path[24:])
			config.misc.pluginbrowser.plugin_order.value = ",".join(plugin_order)
			config.misc.pluginbrowser.plugin_order.save()

	def updateList(self, showHelp=False):
		self.list = []
		pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)[:]
		for x in config.misc.pluginbrowser.plugin_order.value.split(","):
			plugin = list(plugin for plugin in pluginlist if plugin.path[24:] == x)
			if plugin:
				self.list.append(PluginEntryComponent(plugin[0], self.listWidth))
				pluginlist.remove(plugin[0])
		self.list = self.list + [PluginEntryComponent(plugin, self.listWidth) for plugin in pluginlist]
		if config.usage.menu_show_numbers.value in ("menu&plugins", "plugins") or showHelp:
			for x in enumerate(self.list):
				tmp = list(x[1][1])
				tmp[7] = "%s %s" % (x[0] + 1, tmp[7])
				x[1][1] = tuple(tmp)
		self["list"].l.setList(self.list)

	def showHelp(self):
		if config.usage.menu_show_numbers.value not in ("menu&plugins", "plugins"):
			self.help = not self.help
			self.updateList(self.help)

	def delete(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.REMOVE)

	def download(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.DOWNLOAD, self.firsttime)
		self.firsttime = False

	def PluginDownloadBrowserClosed(self):
		self.updateList()
		self.checkWarnings()

	def openExtensionmanager(self):
		if fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/plugin.py")):
			try:
				from Plugins.SystemPlugins.SoftwareManager.plugin import PluginManager
			except ImportError:
				self.session.open(MessageBox, _("The software management extension is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)
			else:
				self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginManager)


class PluginDownloadBrowser(Screen):
	DOWNLOAD = 0
	REMOVE = 1
	UPDATE = 2
	PLUGIN_PREFIX = 'enigma2-plugin-'
	PLUGIN_PREFIX2 = []
	lastDownloadDate = None

	def __init__(self, session, type=0, needupdate=True):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Downloadable plugins"))

		self.type = type
		self.needupdate = needupdate
		self.createPluginFilter()
		self.LanguageList = language.getLanguageList()

		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun)
		self.setTitle(self.type == self.DOWNLOAD and _("Downloadable new plugins") or _("Remove plugins"))
		self.list = []
		self["list"] = PluginList(self.list)
		self.pluginlist = []
		self.expanded = []
		self.installedplugins = []
		self.plugins_changed = False
		self.reload_settings = False
		self.check_softcams = False
		self.check_settings = False
		self.check_bootlogo = False
		self.install_settings_name = ''
		self.remove_settings_name = ''
		self["text"] = Label(self.type == self.DOWNLOAD and _("Downloading plugin information. Please wait...") or _("Getting plugin information. Please wait..."))
		self.run = 0
		self.remainingdata = ""
		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.go,
			"back": self.requestClose,
		})
		if os.path.isfile('/usr/bin/opkg'):
			self.opkg = '/usr/bin/opkg'
			self.opkg_install = self.opkg + ' install --force-overwrite'
			self.opkg_remove = self.opkg + ' remove --autoremove --force-depends'
		else:
			self.opkg = 'opkg'
			self.opkg_install = 'opkg install --force-overwrite -force-defaults'
			self.opkg_remove = self.opkg + ' remove'

	def createPluginFilter(self):
		#Create Plugin Filter
		self.PLUGIN_PREFIX2 = []
		if config.pluginfilter.openeight.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'openeight')
                if config.pluginfilter.drivers.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'drivers')
		if config.pluginfilter.extensions.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'extensions')
		if config.pluginfilter.e2_locales.getValue():
			self.PLUGIN_PREFIX2.append('enigma2-locale-')
		if config.pluginfilter.m2k.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'm2k')
		if config.pluginfilter.picons.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'picons')
		if config.pluginfilter.pli.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'pli')
		if config.pluginfilter.security.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'security')
		if config.pluginfilter.settings.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'settings')
		if config.pluginfilter.skins.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'skins')
		if config.pluginfilter.display.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'display')
		if config.pluginfilter.softcams.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'softcams')
		if config.pluginfilter.systemplugins.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'systemplugins')
		if config.pluginfilter.vix.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'vix')
		if config.pluginfilter.weblinks.getValue():
			self.PLUGIN_PREFIX2.append(self.PLUGIN_PREFIX + 'weblinks')
		if config.pluginfilter.kernel.getValue():
			self.PLUGIN_PREFIX2.append('kernel-module-')

	def go(self):
		sel = self["list"].l.getCurrentSelection()

		if sel is None:
			return

		sel = sel[0]
		if isinstance(sel, str): # category
			if sel in self.expanded:
				self.expanded.remove(sel)
			else:
				self.expanded.append(sel)
			self.updateList()
		else:
			if self.type == self.DOWNLOAD:
				mbox = self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to download the plugin \"%s\"?") % sel.name)
				mbox.setTitle(_("Download plugins"))
			elif self.type == self.REMOVE:
				mbox = self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to remove the plugin \"%s\"?") % sel.name, default=False)
				mbox.setTitle(_("Remove plugins"))

	def requestClose(self):
		if self.plugins_changed:
			plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		if self.reload_settings:
			self["text"].setText(_("Reloading bouquets and services..."))
			self["text"].show()
			eDVBDB.getInstance().reloadBouquets()
			eDVBDB.getInstance().reloadServicelist()
			from Components.ParentalControl import parentalControl
			parentalControl.open()
			refreshServiceList()
		if self.check_softcams:
			SystemInfo["HasSoftcamInstalled"] = hassoftcaminstalled()
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self.container.appClosed.remove(self.runFinished)
		self.container.dataAvail.remove(self.dataAvail)
		self.close()

	def resetPostInstall(self):
		try:
			del self.postInstallCall
		except:
			pass

	def installDestinationCallback(self, result):
		if result is not None:
			dest = result[1]
			if dest.startswith('/'):
				# Custom install path, add it to the list too
				dest = os.path.normpath(dest)
				extra = '--add-dest %s:%s -d %s' % (dest, dest, dest)
				Opkg.opkgAddDestination(dest)
			else:
				extra = '-d ' + dest
			self.doInstall(self.installFinished, self["list"].l.getCurrentSelection()[0].name + ' ' + extra)
		else:
			self.resetPostInstall()

	def runInstall(self, val):
		if val:
			if self.type == self.DOWNLOAD:
				if self["list"].l.getCurrentSelection()[0].name.startswith("picons-"):
					supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'reiser', 'reiser4', 'jffs2', 'ubifs', 'rootfs'))
					candidates = []
					import Components.Harddisk
					mounts = Components.Harddisk.getProcMounts()
					for partition in harddiskmanager.getMountedPartitions(False, mounts):
						if partition.filesystem(mounts) in supported_filesystems:
							candidates.append((partition.description, partition.mountpoint))
					if candidates:
						from Components.Renderer import Picon
						self.postInstallCall = Picon.initPiconPaths
						self.session.openWithCallback(self.installDestinationCallback, ChoiceBox, title=_("Install picons on"), list=candidates)
					return
				elif self["list"].l.getCurrentSelection()[0].name.startswith("display-picon"):
					supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'reiser', 'reiser4', 'jffs2', 'ubifs', 'rootfs'))
					candidates = []
					import Components.Harddisk
					mounts = Components.Harddisk.getProcMounts()
					for partition in harddiskmanager.getMountedPartitions(False, mounts):
						if partition.filesystem(mounts) in supported_filesystems:
							candidates.append((partition.description, partition.mountpoint))
					if candidates:
						from Components.Renderer import LcdPicon
						self.postInstallCall = LcdPicon.initLcdPiconPaths
						self.session.openWithCallback(self.installDestinationCallback, ChoiceBox, title=_("Install lcd picons on"), list=candidates)
					return
				self.install_settings_name = self["list"].l.getCurrentSelection()[0].name
				self.install_bootlogo_name = self["list"].l.getCurrentSelection()[0].name
				if self["list"].l.getCurrentSelection()[0].name.startswith('settings-'):
					self.check_settings = True
					self.startOpkgListInstalled(self.PLUGIN_PREFIX + 'settings-*')
				elif self["list"].l.getCurrentSelection()[0].name.startswith('bootlogo-'):
					self.check_bootlogo = True
					self.startOpkgListInstalled(self.PLUGIN_PREFIX + 'bootlogo-*')
				else:
					self.runSettingsInstall()
			elif self.type == self.REMOVE:
				if self["list"].l.getCurrentSelection()[0].name.startswith("bootlogo-"):
					self.doRemove(self.installFinished, self["list"].l.getCurrentSelection()[0].name + " --force-remove --force-depends")
				else:
					self.doRemove(self.installFinished, self["list"].l.getCurrentSelection()[0].name)

	def doRemove(self, callback, pkgname):
		if pkgname.startswith('kernel-module-') or pkgname.startswith('enigma2-locale-'):
			self.session.openWithCallback(callback, Console, cmdlist=[self.opkg_remove + Opkg.opkgExtraDestinations() + " " + pkgname, "sync"], skin="Console_Pig", closeOnSuccess=True)
		else:
			pkgname = self.PLUGIN_PREFIX + pkgname
			self.session.openWithCallback(callback, Console, cmdlist=[self.opkg_remove + Opkg.opkgExtraDestinations() + " " + pkgname, "sync"], skin="Console_Pig", closeOnSuccess=True)

	def doInstall(self, callback, pkgname):
		if pkgname.startswith('kernel-module-') or pkgname.startswith('enigma2-locale-'):
			self.session.openWithCallback(callback, Console, cmdlist=[self.opkg_install + " " + pkgname, "sync"], closeOnSuccess=True)
		else:
			self.session.openWithCallback(callback, Console, cmdlist=[self.opkg_install + " " + self.PLUGIN_PREFIX + pkgname, "sync"], skin="Console_Pig", closeOnSuccess=True)

	def runSettingsRemove(self, val):
		if val:
			self.doRemove(self.runSettingsInstall, self.remove_settings_name)

	def runBootlogoRemove(self, val):
		if val:
			self.doRemove(self.runSettingsInstall, self.remove_bootlogo_name + " --force-remove --force-depends")

	def runSettingsInstall(self):
		self.doInstall(self.installFinished, self.install_settings_name)

	def setWindowTitle(self):
		if self.type == self.DOWNLOAD:
			self.setTitle(_("Install plugins"))
		elif self.type == self.REMOVE:
			self.setTitle(_("Remove plugins"))

	def startOpkgListInstalled(self, pkgname=PLUGIN_PREFIX + '*'):
		self.container.execute(self.opkg + Opkg.opkgExtraDestinations() + " list_installed")

	def startOpkgListAvailable(self):
		self.container.execute(self.opkg + Opkg.opkgExtraDestinations() + " list")

	def startRun(self):
		listsize = self["list"].instance.size()
		self["list"].instance.hide()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()
		if self.type == self.DOWNLOAD:
			self.type = self.UPDATE
			self.container.execute(self.opkg + " update")
		elif self.type == self.REMOVE:
			self.run = 1
			self.startOpkgListInstalled()

	def installFinished(self):
		if hasattr(self, 'postInstallCall'):
			try:
				self.postInstallCall()
			except Exception, ex:
				print "[PluginBrowser] postInstallCall failed:", ex
			self.resetPostInstall()
		try:
			os.unlink('/tmp/opkg.conf')
		except:
			pass
		for plugin in self.pluginlist:
			if plugin[3] == self["list"].l.getCurrentSelection()[0].name or plugin[0] == self["list"].l.getCurrentSelection()[0].name:
				self.pluginlist.remove(plugin)
				break
		self.plugins_changed = True
		if self["list"].l.getCurrentSelection()[0].name.startswith("settings-"):
			self.reload_settings = True
		if self["list"].l.getCurrentSelection()[0].name.startswith("softcams-"):
			self.check_softcams = True
		self.expanded = []
		self.updateList()
		self["list"].moveToIndex(0)

	def runFinished(self, retval):
		if self.check_settings:
			self.check_settings = False
			self.runSettingsInstall()
			return
		if self.check_bootlogo:
			self.check_bootlogo = False
			self.runSettingsInstall()
			return
		self.remainingdata = ""
		if self.run == 0:
			self.run = 1
			if self.type == self.UPDATE:
				self.type = self.DOWNLOAD
				self.startOpkgListInstalled()
		elif self.run == 1 and self.type == self.DOWNLOAD:
			self.run = 2
			self.startOpkgListAvailable()
		else:
			if len(self.pluginlist) > 0:
				self.updateList()
				self["list"].instance.show()
				self["text"].hide()
			else:
				if self.type == self.DOWNLOAD:
					self["text"].setText(_("Sorry, feeds are down for maintenance"))
					self["text"].show()
				else:
					self["text"].setText(_("No plugins found"))

	def dataAvail(self, str):
		if self.type == self.DOWNLOAD and str.find('404 Not Found') >= 0:
			self["text"].setText(_("Sorry, feeds are down for maintenance"))
			self.run = 3
			return
		#prepend any remaining data from the previous call
		str = self.remainingdata + str
		#split in lines
		lines = str.split('\n')
		#'str' should end with '\n', so when splitting, the last line should be empty. If this is not the case, we received an incomplete line
		if len(lines[-1]):
			#remember this data for next time
			self.remainingdata = lines[-1]
			lines = lines[0:-1]
		else:
			self.remainingdata = ""

		if self.check_settings:
			self.check_settings = False
			self.remove_settings_name = str.split(' - ')[0].replace(self.PLUGIN_PREFIX, '')
			self.session.openWithCallback(self.runSettingsRemove, MessageBox, _('You already have a channel list installed,\nwould you like to remove\n"%s"?') % self.remove_settings_name)
			return

		if self.check_bootlogo:
			self.check_bootlogo = False
			self.remove_bootlogo_name = str.split(' - ')[0].replace(self.PLUGIN_PREFIX, '')
			self.session.openWithCallback(self.runBootlogoRemove, MessageBox, _('You already have a bootlogo installed,\nwould you like to remove\n"%s"?') % self.remove_bootlogo_name)
			return

		for x in lines:
			plugin = x.split(" - ", 2)
			# 'opkg list_installed' only returns name + version, no description field
			if len(plugin) >= 1:
				if not plugin[0].endswith('-dev') and not plugin[0].endswith('-staticdev') and not plugin[0].endswith('-dbg') and not plugin[0].endswith('-doc') and not plugin[0].endswith('-src'):
					# Plugin filter
					for s in self.PLUGIN_PREFIX2:
						if plugin[0].startswith(s):
							if self.run == 1 and self.type == self.DOWNLOAD:
								if plugin[0] not in self.installedplugins:
									self.installedplugins.append(plugin[0])
							else:
								if plugin[0] not in self.installedplugins:
									if len(plugin) == 2:
										# 'opkg list_installed' does not return descriptions, append empty description
										plugin.append('')
									plugin.append(plugin[0][15:])

									self.pluginlist.append(plugin)

	def updateList(self):
		list = []
		expandableIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/expandable-plugins.png"))
		expandedIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/expanded-plugins.png"))
		verticallineIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/verticalline-plugins.png"))

		self.plugins = {}

		if self.type == self.UPDATE:
			self.list = list
			self["list"].l.setList(list)
			return

		for x in self.pluginlist:
			split = x[3].split('-', 1)
			if x[0][0:14] == 'kernel-module-':
				split[0] = "kernel modules"
			elif x[0][0:15] == 'enigma2-locale-':
				split[0] = "languages"

			if split[0] not in self.plugins:
				self.plugins[split[0]] = []

			if split[0] == "kernel modules":
				self.plugins[split[0]].append((PluginDescriptor(name=x[0], description=x[2], icon=verticallineIcon), x[0][14:], x[1]))
			elif split[0] == "languages":
				for l in self.LanguageList:
					if len(x[3]) > 2:
						tmp = l[0].lower()
						tmp = tmp.replace('_', '-')
						if tmp == x[3]:
							countryIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/" + l[0] + ".png"))
							if countryIcon is None:
								countryIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/missing.png"))
							self.plugins[split[0]].append((PluginDescriptor(name=x[0], description=x[2], icon=countryIcon), l[1][0], x[1]))
							break
					else:
						if l[0][:2] == x[3]:
							countryIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/" + l[1][2].lower() + ".png"))
							if countryIcon is None:
								countryIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/missing.png"))
							self.plugins[split[0]].append((PluginDescriptor(name=x[0], description=x[2], icon=countryIcon), l[1][0], x[1]))
							break
			else:
				if len(split) < 2:
					continue
				self.plugins[split[0]].append((PluginDescriptor(name=x[3], description=x[2], icon=verticallineIcon), split[1], x[1]))

		temp = self.plugins.keys()
		temp.sort()
		for x in temp:
			if x in self.expanded:
				list.append(PluginCategoryComponent(x, expandedIcon, self.listWidth))
				list.extend([PluginDownloadComponent(plugin[0], plugin[1], plugin[2], self.listWidth) for plugin in self.plugins[x]])
			else:
				list.append(PluginCategoryComponent(x, expandableIcon, self.listWidth))
		self.list = list
		self["list"].l.setList(list)


class PluginFilter(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = "Setup"
		Screen.setTitle(self, _("Plugin Filter..."))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["status"] = StaticText()
		self["labelExitsave"] = Label("[Exit] = " + _("Cancel") + "              [Ok] =" + _("Save"))

		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)
		self.createSetup()

		self["actions"] = ActionMap(["SetupActions", 'ColorActions', 'VirtualKeyboardActions'],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
			"menu": self.keyCancel,
			"showVirtualKeyboard": self.KeyText
		}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["description"] = Label('')
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def createSetup(self):
		self.editListEntry = None
		self.list = []
		self.list.append(getConfigListEntry(_("openeight"), config.pluginfilter.openeight, _("This allows you to show all specific openeight in downloads")))
		self.list.append(getConfigListEntry(_("drivers"), config.pluginfilter.drivers, _("This allows you to show drivers modules in downloads")))
		self.list.append(getConfigListEntry(_("extensions"), config.pluginfilter.extensions, _("This allows you to show extensions modules in downloads")))
		self.list.append(getConfigListEntry(_("languages"), config.pluginfilter.e2_locales, _("This allows you to show enigma2 languages in downloads")))
		self.list.append(getConfigListEntry(_("systemplugins"), config.pluginfilter.systemplugins, _("This allows you to show systemplugins modules in downloads")))
		if Check_Softcam():
			self.list.append(getConfigListEntry(_("softcams"), config.pluginfilter.softcams, _("This allows you to show softcams modules in downloads")))
		self.list.append(getConfigListEntry(_("skins"), config.pluginfilter.skins, _("This allows you to show skins modules in downloads")))
		self.list.append(getConfigListEntry(_("display"), config.pluginfilter.skins, _("This allows you to show lcd skins in downloads")))
		self.list.append(getConfigListEntry(_("picons"), config.pluginfilter.picons, _("This allows you to show picons modules in downloads")))
		self.list.append(getConfigListEntry(_("settings"), config.pluginfilter.settings, _("This allows you to show settings modules in downloads")))
		self.list.append(getConfigListEntry(_("m2k"), config.pluginfilter.m2k, _("This allows you to show m2k modules in downloads")))
		self.list.append(getConfigListEntry(_("weblinks"), config.pluginfilter.weblinks, _("This allows you to show weblinks modules in downloads")))
		self.list.append(getConfigListEntry(_("pli"), config.pluginfilter.pli, _("This allows you to show pli modules in downloads")))
		self.list.append(getConfigListEntry(_("vix"), config.pluginfilter.vix, _("This allows you to show vix modules in downloads")))
		self.list.append(getConfigListEntry(_("security"), config.pluginfilter.security, _("This allows you to show security modules in downloads")))
		self.list.append(getConfigListEntry(_("kernel modules"), config.pluginfilter.kernel, _("This allows you to show kernel modules in downloads")))
		self.list.append(getConfigListEntry(_("user feed url"), config.pluginfilter.userfeed, _("Please enter your personal feed URL")))

		self["config"].list = self.list
		self["config"].setList(self.list)
		self["config"].list.sort()

	def selectionChanged(self):
		self["status"].setText(self["config"].getCurrent()[2])

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		if config.pluginfilter.userfeed.getValue() != "http://":
			CreateFeedConfig()

	def keySave(self):
		self.saveAll()
		self.close()

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def KeyText(self):
		sel = self['config'].getCurrent()
		if sel:
			self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].getValue())

	def VirtualKeyBoardCallback(self, callback=None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())


language.addCallback(languageChanged)
