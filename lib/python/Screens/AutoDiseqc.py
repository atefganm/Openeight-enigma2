from Screens.Satconfig import NimSelection
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.ConfigList import ConfigListScreen, ConfigList
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ResourceManager import resourcemanager
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, getConfigListEntry, ConfigSelection, ConfigYesNo
from Components.NimManager import nimmanager, InitNimManager
from Components.TuneTest import Tuner
from enigma import eDVBFrontendParametersSatellite, eDVBFrontendParameters, eDVBResourceManager, eTimer


class AutoDiseqc(Screen, ConfigListScreen):
	def __init__(self, session, args = None):
		Screen.__init__(self, session)

		self.feid = args
		self.list = []
		ConfigListScreen.__init__(self, self.list)

		self.enabled = ConfigYesNo(default = True)
		diseqc_modes = {2: _("diseqc_a_b"), 4: _("diseqc_a_b_c_d")}
		self.menu_type = ConfigSelection(choices = diseqc_modes, default = 2)
		self.simple_tone = ConfigYesNo(True)
		self.simple_sat_change = ConfigYesNo(False)

		self.createMenu()

	def createMenu(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Use AutoDiseqc"), self.enabled))
		if self.enabled.value:
			self.list.append(getConfigListEntry(_("Diseqc mode"), self.menu_type))
			self.list.append(getConfigListEntry(_("Set Voltage and 22KHz"), self.simple_tone))
			self.list.append(getConfigListEntry(_("Send DiSEqC only on satellite change"), self.simple_sat_change))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createMenu()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createMenu()

	def run(self):
		if self.enabled.value:
			self.session.open(AutoDiseqcRun, self.feid, self.menu_type.value, self.simple_tone, self.simple_sat_change)
		else:
			if self.feid == 0:
				config.misc.startwizard.autodiseqc_a.value = False
			elif self.feid == 1:
				config.misc.startwizard.autodiseqc_b.value = False
			elif self.feid == 2:
				config.misc.startwizard.autodiseqc_c.value = False
			elif self.feid == 3:
				config.misc.startwizard.autodiseqc_d.value = False


class AutoDiseqcRun(Screen, ConfigListScreen):
	skin = """
		<screen position="c-250,c-100" size="500,250" title=" ">
			<widget source="statusbar" render="Label" position="10,5" zPosition="10" size="e-10,60" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="tunerstatusbar" render="Label" position="10,60" zPosition="10" size="e-10,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="config" position="10,100" size="e-10,100" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="c-140,e-45" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="c+10,e-45" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="c-140,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="c+10,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	diseqc_ports = [
		"A", "B", "C", "D"
	]

	sat_frequencies = [
		# astra 192 zdf
		( 11953, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.FEC_3_4, \
		eDVBFrontendParametersSatellite.Inversion_Off, 192, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		1079, 1, "Astra 1 19.2e"),

		# astra 235 astra ses
		( 12168, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.FEC_3_4, \
		eDVBFrontendParametersSatellite.Inversion_Off, 235, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		3224, 3, "Astra 3 23.5e"),

		# astra 282 bbc
		( 10776, 22000, \
		eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.FEC_Auto, \
		eDVBFrontendParametersSatellite.Inversion_Unknown, 282, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		2045, 2, "Astra 2 28.2e"),

		# hotbird 130 rai
		( 10992, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.FEC_2_3, \
		eDVBFrontendParametersSatellite.Inversion_Off, 130, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		12400, 318, "Hotbird 13.0e"),
	]

	SAT_TABLE_FREQUENCY = 0
	SAT_TABLE_SYMBOLRATE = 1
	SAT_TABLE_POLARISATION = 2
	SAT_TABLE_FEC = 3
	SAT_TABLE_INVERSION = 4
	SAT_TABLE_ORBPOS = 5
	SAT_TABLE_SYSTEM = 6
	SAT_TABLE_MODULATION = 7
	SAT_TABLE_ROLLOFF = 8
	SAT_TABLE_PILOT = 9
	SAT_TABLE_TSID = 10
	SAT_TABLE_ONID = 11
	SAT_TABLE_NAME = 12

	def __init__(self, session, feid, nr_of_ports, simple_tone, simple_sat_change):
		self.skin = AutoDiseqcRun.skin
		Screen.__init__(self, session)

		self["statusbar"] = StaticText(" ")
		self["tunerstatusbar"] = StaticText(" ")

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self["key_red"] = StaticText(" ")
		self["key_green"] = StaticText(" ")

		self.index = 0
		self.port_index = 0
		self.feid = feid
		self.nr_of_ports = nr_of_ports
		self.simple_tone = simple_tone
		self.simple_sat_change = simple_sat_change
		self.found_sats = []

		if not self.openFrontend():
			self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					self.session.pipshown = False
					del self.session.pip
					if not self.openFrontend():
						self.frontend = None

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keySave,
			"save": self.keySave,
			"cancel": self.keyCancel,
		}, -2)

		self.count = 0
		self.state = 0

		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.statusCallback)
		self.tunerStatusTimer = eTimer()
		self.tunerStatusTimer.callback.append(self.tunerStatusCallback)
		self.startStatusTimer()

	def keySave(self):
		if self.state == 99 and len(self.found_sats) > 0:
			self.setupSave()
			self.close()

	def keyCancel(self):
		if self.state == 99:
			self.setupClear()
			self.close()

	def keyOK(self):
		return

	def keyLeft(self):
		return

	def keyRight(self):
		return

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
		return False

	def statusCallback(self):
		if self.state == 0:
			if self.port_index == 0:
				self.clearNimEntries()
				config.Nims[self.feid].diseqcA.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 1:
				self.clearNimEntries()
				config.Nims[self.feid].diseqcB.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 2:
				self.clearNimEntries()
				config.Nims[self.feid].diseqcC.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 3:
				self.clearNimEntries()
				config.Nims[self.feid].diseqcD.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])

			if self.nr_of_ports == 4:
				config.Nims[self.feid].diseqcMode.value = "diseqc_a_b_c_d"
			else:
				config.Nims[self.feid].diseqcMode.value = "diseqc_a_b"

			config.Nims[self.feid].configMode.value = "simple"
			config.Nims[self.feid].simpleDiSEqCSetVoltageTone = self.simple_tone
			config.Nims[self.feid].simpleDiSEqCOnlyOnSatChange = self.simple_sat_change

			self.saveAndReloadNimConfig()
			self.state += 1

		elif self.state == 1:
			InitNimManager(nimmanager)

			self.tuner = Tuner(self.frontend)
			self.tuner.tune(self.sat_frequencies[self.index])

			self["statusbar"].setText(_("AutoDiseqc tuner %d\nDiseqc port %s for %s") % (self.feid, self.diseqc_ports[self.port_index], self.sat_frequencies[self.index][self.SAT_TABLE_NAME]))
			self["tunerstatusbar"].setText(" ")

			self.count = 0
			self.state = 0

			self.startTunerStatusTimer()
			return

		self.startStatusTimer()

	def startStatusTimer(self):
		self.statusTimer.start(100, True)

	def setupConfig(self):
		self["statusbar"].setText(_("AutoDiseqc finished"))
		self["tunerstatusbar"].setText(_("Found %d position(s) of %d total") % (len(self.found_sats), self.nr_of_ports))
		self["key_red"].setText(_("Wrong"))
		if len(self.found_sats) > 0:
			self["key_green"].setText(_("Correct"))

	def setupSave(self):
		if self.feid == 0:
			config.misc.startwizard.autodiseqc_a.value = True
		elif self.feid == 1:
			config.misc.startwizard.autodiseqc_b.value = True
		elif self.feid == 2:
			config.misc.startwizard.autodiseqc_c.value = True
		elif self.feid == 3:
			config.misc.startwizard.autodiseqc_d.value = True
		self.clearNimEntries()
		for x in self.found_sats:
			if x[0] == "A":
				config.Nims[self.feid].diseqcA.value = "%d" % (x[1])
			elif x[0] == "B":
				config.Nims[self.feid].diseqcB.value = "%d" % (x[1])
			elif x[0] == "C":
				config.Nims[self.feid].diseqcC.value = "%d" % (x[1])
			elif x[0] == "D":
				config.Nims[self.feid].diseqcD.value = "%d" % (x[1])
		self.saveAndReloadNimConfig()

	def setupClear(self):
		if self.feid == 0:
			config.misc.startwizard.autodiseqc_a.value = False
		elif self.feid == 1:
			config.misc.startwizard.autodiseqc_b.value = False
		elif self.feid == 2:
			config.misc.startwizard.autodiseqc_c.value = False
		elif self.feid == 3:
			config.misc.startwizard.autodiseqc_d.value = False
		self.clearNimEntries()
		config.Nims[self.feid].diseqcA.value = ""
		config.Nims[self.feid].diseqcB.value = ""
		config.Nims[self.feid].diseqcC.value = ""
		config.Nims[self.feid].diseqcD.value = ""
		config.Nims[self.feid].diseqcMode.value = ""
		config.Nims[self.feid].configMode.value = ""
		config.Nims[self.feid].simpleDiSEqCSetVoltageTone.value = True
		config.Nims[self.feid].simpleDiSEqCOnlyOnSatChange.value = False
		self.saveAndReloadNimConfig()

	def clearNimEntries(self):
		config.Nims[self.feid].diseqcA.value = "3601"
		config.Nims[self.feid].diseqcB.value = "3601"
		config.Nims[self.feid].diseqcC.value = "3601"
		config.Nims[self.feid].diseqcD.value = "3601"

	def saveAndReloadNimConfig(self):
		config.Nims[self.feid].save()
		configfile.save()
		configfile.load()
		nimmanager.sec.update()

	def tunerStatusCallback(self):
		dict = {}
		self.frontend.getFrontendStatus(dict)

		self["tunerstatusbar"].setText(_("Tuner status %s") % (dict["tuner_state"]))

		if dict["tuner_state"] == "LOCKED":
			self.raw_channel.requestTsidOnid(self.gotTsidOnid)

		if dict["tuner_state"] == "LOSTLOCK" or dict["tuner_state"] == "FAILED":
			self.tunerStopScan(False)
			return

		self.count += 1
		if self.count > 10:
			self.tunerStopScan(False)
		else:
			self.startTunerStatusTimer()

	def startTunerStatusTimer(self):
		self.tunerStatusTimer.start(1000, True)

	def gotTsidOnid(self, tsid, onid):
		self.tunerStatusTimer.stop()
		if tsid == self.sat_frequencies[self.index][self.SAT_TABLE_TSID] and onid == self.sat_frequencies[self.index][self.SAT_TABLE_ONID]:
			self.tunerStopScan(True)
		else:
			self.tunerStopScan(False)

	def tunerStopScan(self, result):
		if result:
			self.found_sats.append((self.diseqc_ports[self.port_index], self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS], self.sat_frequencies[self.index][self.SAT_TABLE_NAME]))
			self.index = 0
			self.port_index += 1
		else:
			self.index += 1
			if len(self.sat_frequencies) == self.index:
				self.index = 0
				self.port_index += 1

		if len(self.found_sats) > 0:
			self.list = []
			for x in self.found_sats:
				self.list.append(getConfigListEntry((_("Diseqc port %s: %s") % (x[0], x[2]))))
			self["config"].l.setList(self.list)

		if self.nr_of_ports == self.port_index:
			self.setupConfig()
			self.state = 99
			return

		for x in self.found_sats:
			if x[1] == self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS]:
				self.tunerStopScan(False)
				return

		self.startStatusTimer()