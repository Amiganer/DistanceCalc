"""
DistanceCalc a plugin for EDMC
Copyright (C) 2017 Sebastian Bauer

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import sys
import math
import json
import urllib2
from threading import Thread
from functools import partial

import Tkinter as tk
import ttk
from config import config
from ttkHyperlinkLabel import HyperlinkLabel
import myNotebook as nb
from l10n import Locale

this = sys.modules[__name__]  # For holding module globals

this.VERSION = "1.23"
this.PADX = 5
this.WIDTH = 10


class SettingsUiElements(object):
    def __init__(self, systemEntry, xEntry, yEntry, zEntry, edsmButton, hasData=False, success=False, x=0, y=0, z=0, systemName="", errorText=""):
        self.systemEntry = systemEntry
        self.xEntry = xEntry
        self.yEntry = yEntry
        self.zEntry = zEntry
        self.edsmButton = edsmButton
        self.hasData = hasData
        self.success = success
        self.x = x
        self.y = y
        self.z = z
        self.systemName = systemName
        self.statusText = errorText

    def resetResponseData(self):
        self.hasData = False
        self.success = False
        self.x = 0
        self.y = 0
        self.z = 0
        self.systemName = ""
        self.statusText = ""


def plugin_start():
    this.distances = json.loads(config.get("DistanceCalc") or "[]")
    this.coordinates = None
    this.distanceTotal = float(config.getint("DistanceCalc_travelled") or 0) / 1000.0
    this.distanceSession = 0.0
    a, b, c = getSettingsTravelled()
    this.travelledTotalOption = tk.IntVar(value=a and 1)
    this.travelledSessionOption = tk.IntVar(value=b and 1)
    this.travelledSessionSelected = tk.IntVar(value=c and 1)
    this.frame = None
    this.errorLabel = None
    return 'DistanceCalc'


def clearInputFields(system, x, y, z):
    system.delete(0, tk.END)
    x.delete(0, tk.END)
    y.delete(0, tk.END)
    z.delete(0, tk.END)


def getSystemInformationFromEDSM(buttonNumber, systemName):
    # Don't access UI elements from here because of thread safety. Use the regular (int, str, bool) variables and fire an event
    settingsUiElements = this.settingsUiElements[buttonNumber]
    settingsUiElements.resetResponseData()

    edsmUrl = "https://www.edsm.net/api-v1/system?systemName={SYSTEM}&showCoordinates=1".format(SYSTEM=urllib2.quote(systemName))
    try:
        url = urllib2.urlopen(edsmUrl, timeout=15)
        response = url.read()
        edsmJson = json.loads(response)
        if "name" in edsmJson and "coords" in edsmJson:
            settingsUiElements.success = True
            settingsUiElements.systemName = edsmJson["name"]
            settingsUiElements.x = edsmJson["coords"]["x"]
            settingsUiElements.y = edsmJson["coords"]["y"]
            settingsUiElements.z = edsmJson["coords"]["z"]
            settingsUiElements.statusText = "Coordinates filled in for system {0}".format(edsmJson["name"])
        else:
            settingsUiElements.statusText = "Could not get system information for {0} from EDSM".format(systemName)
    except:
        settingsUiElements.statusText = "Could not get system information for {0} from EDSM".format(systemName)
        sys.stderr.write("DistanceCalc: Could not get system information for {0} from EDSM".format(systemName))
    finally:
        settingsUiElements.hasData = True
        this.frame.event_generate("<<DistanceCalc-EDSM-Response>>", when="tail")


def fillSystemInformationFromEdsmAsync(buttonNumber, systemEntry):
    if systemEntry.get() == "":
        this.errorLabel["text"] = "No system name provided."
        this.errorLabel.config(foreground="red")
    else:
        this.settingsUiElements[buttonNumber].edsmButton["state"] = tk.DISABLED
        t = Thread(name="EDSM_caller_{0}".format(buttonNumber), target=getSystemInformationFromEDSM, args=(buttonNumber, systemEntry.get()))
        t.start()


def validate(action, index, value_if_allowed, prior_value, text, validation_type, trigger_type, widget_name):
    if value_if_allowed == "-" or value_if_allowed == "":
        return True
    elif text in "0123456789.," or text == value_if_allowed:
        try:
            t = type(Locale.numberFromString(value_if_allowed))
            if t is float or t is int:
                return True
        except ValueError:
            return False
    return False


def getSettingsTravelled():
    settings = config.getint("DistanceCalc_options")
    settingTotal = settings & 1  # calculate total distance travelled
    settingSession = (settings >> 1) & 1  # calculate for session only
    settingSessionOption = (settings >> 2) & 1  # 1 = calculate for ED session; 0 = calculate for EDMC session
    return settingTotal, settingSession, settingSessionOption


def resetTotalTravelledDistance():
    config.set("DistanceCalc_travelled", 0)
    this.distanceTotal = 0.0


def setStateRadioButtons(travelledSessionEdmc, travelledSessionElite):
    if this.travelledSessionOption.get() == 1:
        travelledSessionEdmc["state"] = "normal"
        travelledSessionElite["state"] = "normal"
    else:
        travelledSessionEdmc["state"] = "disabled"
        travelledSessionElite["state"] = "disabled"


def updatePrefsUI(event=None):
    for settingsUiElement in this.settingsUiElements:
        if settingsUiElement.hasData:
            if settingsUiElement.success:
                clearInputFields(settingsUiElement.systemEntry, settingsUiElement.xEntry, settingsUiElement.yEntry, settingsUiElement.zEntry)
                settingsUiElement.systemEntry.insert(0, settingsUiElement.systemName)
                settingsUiElement.xEntry.insert(0, Locale.stringFromNumber(settingsUiElement.x))
                settingsUiElement.yEntry.insert(0, Locale.stringFromNumber(settingsUiElement.y))
                settingsUiElement.zEntry.insert(0, Locale.stringFromNumber(settingsUiElement.z))
                this.errorLabel["text"] = settingsUiElement.statusText
                this.errorLabel.config(foreground="dark green")
            else:
                this.errorLabel["text"] = settingsUiElement.statusText
                this.errorLabel.config(foreground="red")

            settingsUiElement.edsmButton["state"] = tk.NORMAL
            settingsUiElement.resetResponseData()


def plugin_prefs(parent):
    this.frame = nb.Frame(parent)
    this.frame.bind_all("<<DistanceCalc-EDSM-Response>>", updatePrefsUI)
    frameTop = nb.Frame(this.frame)
    frameTop.grid(row=0, column=0, sticky=tk.W)
    frameBottom = nb.Frame(this.frame)
    frameBottom.grid(row=1, column=0, sticky=tk.SW)

    # headline
    nb.Label(frameTop, text="Systems").grid(row=0, column=0, sticky=tk.EW)
    nb.Label(frameTop, text="X").grid(row=0, column=1, sticky=tk.EW)
    nb.Label(frameTop, text="Y").grid(row=0, column=2, sticky=tk.EW)
    nb.Label(frameTop, text="Z").grid(row=0, column=3, sticky=tk.EW)

    this.errorLabel = nb.Label(frameTop, text="")

    this.settingsUiElements = list()
    vcmd = (frameTop.register(validate), '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

    # create and add fields to enter systems
    for i in range(3):
        systemEntry = nb.Entry(frameTop)
        systemEntry.grid(row=i + 1, column=0, padx=(this.PADX * 2, this.PADX), sticky=tk.W)
        systemEntry.config(width=this.WIDTH * 4)  # set fixed width. columnconfigure doesn't work because it already fits

        xEntry = nb.Entry(frameTop, validate='key', validatecommand=vcmd)
        xEntry.grid(row=i + 1, column=1, padx=this.PADX, sticky=tk.W)
        xEntry.config(width=this.WIDTH)  # set fixed width. columnconfigure doesn't work because it already fits

        yEntry = nb.Entry(frameTop, validate='key', validatecommand=vcmd)
        yEntry.grid(row=i + 1, column=2, padx=this.PADX, sticky=tk.W)
        yEntry.config(width=this.WIDTH)  # set fixed width. columnconfigure doesn't work because it already fits

        zEntry = nb.Entry(frameTop, validate='key', validatecommand=vcmd)
        zEntry.grid(row=i + 1, column=3, padx=this.PADX, sticky=tk.W)
        zEntry.config(width=this.WIDTH)  # set fixed width. columnconfigure doesn't work because it already fits

        clearButton = nb.Button(frameTop, text="Clear", command=partial(clearInputFields, systemEntry, xEntry, yEntry, zEntry))
        clearButton.grid(row=i + 1, column=4, padx=this.PADX, sticky=tk.W)
        clearButton.config(width=7)

        edsmButton = nb.Button(frameTop, text="EDSM")
        edsmButton.grid(row=i + 1, column=5, padx=(this.PADX, this.PADX * 2), sticky=tk.W)
        edsmButton.config(width=7, command=partial(fillSystemInformationFromEdsmAsync, i, systemEntry))

        this.settingsUiElements.append(SettingsUiElements(systemEntry, xEntry, yEntry, zEntry, edsmButton))

    # EDSM result label and information about what coordinates can be entered
    this.errorLabel.grid(row=4, column=0, columnspan=6, padx=this.PADX * 2, sticky=tk.W)
    nb.Label(frameTop, text="You can get coordinates from EDDB or EDSM or enter any valid coordinate.").grid(row=5, column=0, columnspan=6, padx=this.PADX * 2,
                                                                                                             sticky=tk.W)
    ttk.Separator(frameTop, orient=tk.HORIZONTAL).grid(row=6, columnspan=6, padx=this.PADX * 2, pady=8, sticky=tk.EW)

    # total travelled distance
    travelledTotal = nb.Checkbutton(frameBottom, variable=travelledTotalOption, text="Calculate total travelled distance")
    travelledTotal.var = travelledTotalOption
    travelledTotal.grid(row=0, column=0, padx=this.PADX * 2, sticky=tk.W)
    resetButton = nb.Button(frameBottom, text="Reset", command=resetTotalTravelledDistance)
    resetButton.grid(row=1, column=0, padx=this.PADX * 4, pady=5, sticky=tk.W)

    travelledSession = nb.Checkbutton(frameBottom, variable=travelledSessionOption, text="Calculate travelled distance for current session")
    travelledSession.var = travelledSessionOption
    travelledSession.grid(row=2, column=0, padx=this.PADX * 2, sticky=tk.W)

    # radio button value: 1 = calculate for ED session; 0 = calculate for EDMC session
    travelledSessionEdmc = nb.Radiobutton(frameBottom, variable=travelledSessionSelected, value=0, text="EDMC session")
    travelledSessionEdmc.var = travelledSessionSelected
    travelledSessionEdmc.grid(row=3, column=0, padx=this.PADX * 4, sticky=tk.W)

    travelledSessionElite = nb.Radiobutton(frameBottom, variable=travelledSessionSelected, value=1, text="Elite session")
    travelledSessionElite.var = travelledSessionSelected
    travelledSessionElite.grid(row=4, column=0, padx=this.PADX * 4, sticky=tk.W)

    setStateRadioButtons(travelledSessionEdmc, travelledSessionElite)
    travelledSession.config(command=partial(setStateRadioButtons, travelledSessionEdmc, travelledSessionElite))

    nb.Label(frameBottom).grid(row=5)  # spacer
    nb.Label(frameBottom).grid(row=6)  # spacer
    nb.Label(frameBottom, text="Plugin version: {0}".format(this.VERSION)).grid(row=7, column=0, padx=this.PADX, sticky=tk.W)
    HyperlinkLabel(this.frame, text="Open the Github page for this plugin", background=nb.Label().cget("background"), url="https://github.com/Thurion/DistanceCalc/",
                   underline=True).grid(row=8, column=0, padx=this.PADX, sticky=tk.W)
    HyperlinkLabel(this.frame, text="Get estimated coordinates from EDTS", background=nb.Label().cget("background"), url="http://edts.thargoid.space/", underline=True)\
        .grid(row=9, column=0, padx=this.PADX, sticky=tk.W)

    def fillEntries(s, x, y, z, systemEntry, xEntry, yEntry, zEntry):
        systemEntry.insert(0, s)
        xEntry.insert(0, Locale.stringFromNumber(x))
        yEntry.insert(0, Locale.stringFromNumber(y))
        zEntry.insert(0, Locale.stringFromNumber(z))

    row = 0
    if len(this.distances) > 0:
        for var in this.distances:
            settingsUiElement = this.settingsUiElements[row]
            fillEntries(var["system"], var["x"], var["y"], var["z"], settingsUiElement.systemEntry, settingsUiElement.xEntry, settingsUiElement.yEntry, settingsUiElement.zEntry)
            row += 1

    return this.frame


def updateMainUi():
    # labels for distances to systems
    row = 0
    for (system, distance) in this.distanceLabels:
        if len(this.distances) >= row + 1:
            s = this.distances[row]
            system.grid(row=row, column=0, sticky=tk.W)
            system["text"] = "Distance {0}:".format(s["system"])
            distance.grid(row=row, column=1, sticky=tk.W)
            distance["text"] = "? Ly"
            row += 1
        else:
            system.grid_remove()
            distance.grid_remove()

    # labels for total travelled distance
    settingTotal, settingSession, settingSessionOption = getSettingsTravelled()

    for i in range(len(this.travelledLabels)):
        description, distance = this.travelledLabels[i]
        if (i == 0 and settingTotal) or (i == 1 and settingSession):
            description.grid(row=row, column=0, sticky=tk.W)
            description["text"] = "Travelled ({0}):".format("total" if i == 0 else "session")
            distance.grid(row=row, column=1, sticky=tk.W)
            distance["text"] = "{0} Ly".format(Locale.stringFromNumber(this.distanceTotal, 2) if i == 0 else Locale.stringFromNumber(this.distanceSession, 2))
            row += 1
        else:
            description.grid_remove()
            distance.grid_remove()

    if row == 0:
        this.emptyFrame.grid(row=0)
    else:
        this.emptyFrame.grid_remove()


def prefs_changed():
    this.distances = list()
    for settingsUiElement in this.settingsUiElements:
        systemText = settingsUiElement.systemEntry.get()
        xText = settingsUiElement.xEntry.get()
        yText = settingsUiElement.yEntry.get()
        zText = settingsUiElement.zEntry.get()
        if systemText and xText and yText and zText:
            try:
                d = dict()
                d["system"] = systemText.strip()
                d["x"] = Locale.numberFromString(xText.strip())
                d["y"] = Locale.numberFromString(yText.strip())
                d["z"] = Locale.numberFromString(zText.strip())
                this.distances.append(d)
            except:  # error while parsing the numbers
                sys.stderr.write("DistanceCalc: Error while parsing the coordinates for {0}".format(systemText.strip()))
                continue
    config.set("DistanceCalc", json.dumps(this.distances))

    settings = this.travelledTotalOption.get() | (this.travelledSessionOption.get() << 1) | (this.travelledSessionSelected.get() << 2)
    config.set("DistanceCalc_options", settings)

    updateMainUi()
    updateDistances()


def plugin_app(parent):
    frame = tk.Frame(parent)
    this.emptyFrame = tk.Frame(frame)
    frame.columnconfigure(1, weight=1)
    this.distanceLabels = list()
    for i in range(3):
        this.distanceLabels.append((tk.Label(frame), tk.Label(frame)))

    this.travelledLabels = list()
    for i in range(2):
        this.travelledLabels.append((tk.Label(frame), tk.Label(frame)))

    updateMainUi()
    return frame


def calculateDistance(x1, y1, z1, x2, y2, z2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


def updateDistances():
    if not this.coordinates:
        for (_, distance) in this.distanceLabels:
            distance["text"] = "? Ly"
    else:
        for i in range(len(this.distances)):
            system = this.distances[i]
            distance = calculateDistance(system["x"], system["y"], system["z"], *this.coordinates)
            this.distanceLabels[i][1]["text"] = "{0} Ly".format(Locale.stringFromNumber(distance, 2))

    _, distance = this.travelledLabels[0]
    distance["text"] = "{0} Ly".format(Locale.stringFromNumber(this.distanceTotal, 2))
    _, distance = this.travelledLabels[1]
    distance["text"] = "{0} Ly".format(Locale.stringFromNumber(this.distanceSession, 2))


def journal_entry(cmdr, system, station, entry, state):
    if entry["event"] == "FSDJump" or entry["event"] == "Location":
        # We arrived at a new system!
        if "StarPos" in entry:
            this.coordinates = tuple(entry["StarPos"])
        if "JumpDist" in entry:
            distance = entry["JumpDist"]
            if this.travelledTotalOption.get():
                this.distanceTotal += distance
                config.set("DistanceCalc_travelled", int(this.distanceTotal * 1000))
            if this.travelledSessionOption.get():
                this.distanceSession += distance
        updateDistances()
    if entry["event"] == "LoadGame" and this.travelledSessionOption.get() and this.travelledSessionSelected.get():
        this.distanceSession = 0.0
        updateDistances()
