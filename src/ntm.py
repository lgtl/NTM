#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#
# NTM Copyright (C) 2009-2011 by Luigi Tullio <tluigi@gmail.com>.
#
#   NTM is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
#   NTM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#



__author__="Luigi Tullio"
#__date__ ="$Jul 9, 2009 5:52:10 PM$"

import locale
import gettext
import ntmtools

## + i18n ##
i18n_APP_NAME = "ntm"
i18n_DIR = "/usr/share/locale"


i18n_ok = False

try:
    locale.setlocale(locale.LC_ALL, '')
    locale.bindtextdomain(i18n_APP_NAME, i18n_DIR)
    gettext.bindtextdomain(i18n_APP_NAME, i18n_DIR)
    gettext.textdomain(i18n_APP_NAME)
    i18n_ok = True
except:
    ntmtools.dbgMsg("i18n init: Error!")

if i18n_ok:
    try:
        i18n_lang = gettext.translation(i18n_APP_NAME, i18n_DIR)
    except:
        i18n_DIR = "../i18n/locale" # for no deb install
        try:
            i18n_lang = gettext.translation(i18n_APP_NAME, i18n_DIR)
        except:
            ntmtools.dbgMsg("i18n gettext.translation: Error!")
            i18n_ok = False

if i18n_ok:  
    _ = i18n_lang.gettext
else:
    def _(message): return message
## - i18n ##


from optparse import OptionParser
import sys
import globaldef

parser = OptionParser()
parser.add_option(
    "-v", "--version",
    action="store_true", dest="version", default=False,
    help= _("print the version number")
)
(options, args) = parser.parse_args()
if (options.version):
    print(globaldef.VERSION)
    sys.exit(0)


## + i18n ##
if i18n_ok:  
    ntmtools.dbgMsg(_("i18n setup: done!"))

from gtk import glade

gettext.install(i18n_APP_NAME, i18n_DIR)
for module in glade, gettext :
    module.bindtextdomain(i18n_APP_NAME, i18n_DIR)
    module.textdomain(i18n_APP_NAME)
## - i18n ##

import gobject
import sqlite3
import gtk
import string
import urllib2
import os
import datetime
import time
import dbus

from event import Event
from mtraffic import MTraffic
from mtimeslot import MTimeSlot
from mtime import MTime
import ntmgui
import ntminfo
import onlinedetector


############################################
#### Nettwork Traffic Monitor ####
class NTM():
    ## + ##
    def __init__(self):
        self.stop = False
        self.session_start = None
        self.last_traffic_in, self.last_traffic_out = None, None
        self.online = False
        self.timeout_changed = False
        self.versionChecked = False
        self.logTraffic = False
        self.discMsgDialog = False
        self.last_update = None
        
        self.sys_info = ntmtools.getSysInfo()

        #print(self.sys_info)

        self.d_rb, self.d_tb = 0, 0

        self.home_path = os.getenv("HOME")
        self.profile_path = self.home_path + "/" + globaldef.NTM_PROFILE_RELPATH

        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)

        db_file_path = self.profile_path + "/" + globaldef.NTM_DB_NAME
        self.db_conn = sqlite3.connect(db_file_path)

        self.update_event = Event()


        ## Create tables
        self.createTables(self.db_conn)

        res = ntmtools.readDBVar(self.db_conn, "general.interface")
        if res != None:
            self.interface = res
        else:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.interface' " + _("or is not stored. Default value") + " 'ppp0'.")
            ntmtools.setDBVar(self.db_conn, "general.interface", "ppp0")
            self.interface = "ppp0"

        res = ntmtools.readDBVar(self.db_conn, "general.update_interval")   # sec
        try:
            self.update_interval = int(float(res))
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.update_interval' " + _("or is not stored. Default value") + " '5'.")
            ntmtools.setDBVar(self.db_conn, "general.update_interval", "5")
            self.update_interval = 5

        res = ntmtools.readDBVar(self.db_conn, "general.last_version_check")   # datetime
        try:
            self.last_version_check = int(float(res))
            self.versionChecked = ((time.time() - self.last_version_check) < (5*24*60*60))
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.last_version_check' " + _("or is not stored. Default value") + " '" + _("now") + "'.")
            ntmtools.setDBVar(self.db_conn, "general.last_version_check", str(int(time.time())))
            self.last_version_check = int(time.time())
            self.versionChecked = False

        res = ntmtools.readDBVar(self.db_conn, "general.keep_above")   # 0 or 1
        try:
            self.ntmMainWindow_keep_above = ( int(float(res)) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.keep_above' " + _("or is not stored. Default value") + " '0.")
            ntmtools.setDBVar(self.db_conn, "general.keep_above", "0")
            self.ntmMainWindow_keep_above = False

        res = ntmtools.readDBVar(self.db_conn, "general.opacity")   # 0 to 100
        try:
            self.ntmMainWindow_opacity = int(float(res))
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.opacity' " + _("or is not stored. Default value") + " '100.")
            ntmtools.setDBVar(self.db_conn, "general.opacity", "100")
            self.ntmMainWindow_opacity = 100

        res = ntmtools.readDBVar(self.db_conn, "general.autorun")   # 0 or 1
        try:
            self.general_pref_autorun = ( int(float(res)) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.autorun' " + _("or is not stored. Default value") + " '" + _("True") + "'.")
            ntmtools.setDBVar(self.db_conn, "general.autorun", "1")
            self.general_pref_autorun = True
        self.set_autorun(self.general_pref_autorun)

        res = ntmtools.readDBVar(self.db_conn, "general.online_check")   # 0->NetworkManager; 1->Ping
        try:
            self.general_pref_online_check = int(float(res))
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.online_check' " + _("or is not stored. Default value") + " 0 (NetworkManager).")
            self.general_pref_online_check = 0
            ntmtools.setDBVar(self.db_conn, "general.online_check", "0")

        res = ntmtools.readDBVar(self.db_conn, "general.tray_activate_action")   # 0->Show Main Window; 1->Show Nptify;
        try:
            self.general_pref_tray_activate_action = int(float(res))
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.tray_activate_action' " + _("or is not stored. Default value") + _(" 0 (Show Main Window)."))
            self.general_pref_tray_activate_action = 0
            ntmtools.setDBVar(self.db_conn, "general.tray_activate_action", "0")

        res = ntmtools.readDBVar(self.db_conn, "general.importexport_file")
        if res != None:
            self.importexport_file = res
        else:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'general.importexport_file' " + _("or is not stored. Default value") + " ''.")
            ntmtools.setDBVar(self.db_conn, "general.importexport_file", "")
            self.importexport_file = ""


        self.ntmgui = ntmgui.NtmGui(self)

        self.ntmgui.applyProp(self.ntmMainWindow_keep_above, self.ntmMainWindow_opacity)
        self.set_autorun(self.general_pref_autorun)

        self.ntmgui.set_general_preferences(
            self.interface, self.update_interval,
            self.ntmMainWindow_keep_above, self.ntmMainWindow_opacity,
            self.general_pref_autorun, self.general_pref_online_check,
            self.general_pref_tray_activate_action,
            self.importexport_file
        )
        self.update_event += self.ntmgui.update_h

        self.session_start = datetime.datetime.now()

        # Traffic Module
        self.mtraffic = MTraffic.makeFromDb(self)
        self.update_event += self.mtraffic.update_h
        self.ntmgui.set_traffic_module(self.mtraffic)

        # Time Slot Module
        self.mtimeslot = MTimeSlot.makeFromDb(self)
        self.update_event += self.mtimeslot.update_h
        self.ntmgui.set_timeslot_module(self.mtimeslot)

        # Time Module
        self.mtime = MTime.makeFromDb(self)
        self.update_event += self.mtime.update_h
        self.ntmgui.set_time_module(self.mtime)

        # Online detector
        self.online_detector = onlinedetector.OnlineDetector(self.general_pref_online_check)
        self.online_detector.add_online_handler(self.setOnline)
        self.online_detector.add_offline_handler(self.setOffline)


        # Info/News
        self.info_win = ntminfo.NtmInfo(self.online_detector.online)
        self.info_win_load = False


        if self.online_detector.online:
            self.setOnline()
            self.updateCount()
        else: self.setOffline()

        gobject.timeout_add(self.update_interval*1000, self.updateCount)
    ## end-def ##


    ## + ##
    def quit(self):
        self.updateCount()
        self.stop = True
        sys.exit()
    ## end-def ##


    ## + ##
    # fist_day, fast_day: date
    # all_days: boolean
    def get_report_from_db(self, first_day, last_day, all_days=False):
        ctra = self.db_conn.cursor()

        if all_days:
            ctra.execute("select * from dailytraffic")
        else:
            ctra.execute("select * from dailytraffic where (date>=?) AND (date<=?)", (first_day, last_day))

        t_count = 0
        t_in = 0
        t_out = 0
        tot_min = tot_max = 0
        tra_list = []
        for r in ctra:
            t_in += r[1]
            t_out += r[2]
            tot = r[1] + r[2]
            if (t_count == 0):
                tot_min = tot
                tot_max = tot
            else:
                if tot > tot_max: tot_max = tot
                elif tot < tot_min: tot_min = tot
            t_count += 1
            tra_list += [r]

        cses = self.db_conn.cursor()

        if all_days:
            cses.execute("select * from session")
        else:
            cses.execute("select * from session where (start>=?) AND (start<=?)", (first_day, last_day))

        s_count = 0
        tot_time = 0
        s_max = s_min = 0
        ses_list = []
        for r in cses:
            tsStart = datetime.datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
            tsEnd = datetime.datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S")
            diff = ntmtools.timedelta2sec(tsEnd - tsStart)
            tot_time += diff
            if (s_count == 0):
                s_min = diff
                s_max = diff
            else:
                if diff > s_max: s_max = diff
                elif diff < s_min: s_min = diff
            s_count += 1
            ses_list += [r]

        return (tra_list, ses_list, t_count, t_in, t_out, tot_max, tot_min, s_count, tot_time, s_max, s_min)
    ## end-def ##


    ## + ##
    def updateDBDailyTraffic(self, datetime, recbytes, trabytes):

        date = datetime.date()

        c = self.db_conn.cursor()
        c.execute("select * from dailytraffic where date=?", (date,) )
        r = c.fetchone()

        if r != None:
            self.db_conn.execute("update dailytraffic set recbytes=?, trabytes=? where date=?", (r[1] + recbytes, r[2] + trabytes, r[0]))
        else:
            self.db_conn.execute("insert into dailytraffic values (?, ?, ?)", (date, recbytes, trabytes))
        self.db_conn.commit()
    ## end-def ##


    ## + ##
    def updateDBSession(self, commit = True):
        dtStart = self.session_start.replace(microsecond=0).isoformat(' ')
        dtEnd = self.last_update.replace(microsecond=0).isoformat(' ')

        c = self.db_conn.cursor()
        c.execute("select * from session where start=?", (dtStart,) )
        r = c.fetchone()

        if r != None:
            self.db_conn.execute("update session set end=? where start=?", (dtEnd, dtStart))
        else:
            self.db_conn.execute("insert into session values (?, ?)", (dtStart, dtEnd))

        if commit: self.db_conn.commit()
    ## - ##


    ## + ##
    def removeAllData(self):
        self.db_conn.execute("delete from dailytraffic")
        self.db_conn.execute("delete from session")
        self.db_conn.commit()

        self.mtraffic.reloadTraffic()
        self.mtimeslot.reloadSessions()
        self.mtime.reloadTimeUsed()
        self.ntmgui.update_report()
    ## end-def ##


    ## + ##
    def substituteData(self, db_conn):
        self.copyData(db_conn, self.db_conn)
        self.mtraffic.reloadTraffic()
        self.mtimeslot.reloadSessions()
        self.mtime.reloadTimeUsed()
        self.ntmgui.update_report()
    ## end-def ##


    ## + ##
    def copyData(self, dbc_src, dbc_des):
        dbc_d = dbc_des
        dbc_s = dbc_src

        cs = dbc_s.cursor()
        cd = dbc_d.cursor()

        dbc_d.execute("delete from dailytraffic")
        rows_s = cs.execute("select * from dailytraffic")
        for rs in rows_s:
            cd.execute("insert into dailytraffic values (?, ?, ?)", rs)

        dbc_d.execute("delete from session")
        cs = dbc_s.cursor()
        rows_s = cs.execute("select * from session")
        for rs in rows_s:
            cd.execute("insert into session values (?, ?)", rs)
        dbc_d.commit()
    ## end-def ##


    ## + ##
    def createTables(self, dbconn):
        # Create tables
        try:
            dbconn.execute('create table dailytraffic (date text, recbytes integer, trabytes integer)')
            dbconn.commit()
            ntmtools.dbgMsg(_("Create dailytraffic table."))
        except:
            ntmtools.dbgMsg(_("Warning! Create dailytraffic table aborted."))
            pass

        try:
            dbconn.execute("create table vars (name text, value text)")
            dbconn.commit()
            ntmtools.dbgMsg(_("Create vars table."))
        except:
            ntmtools.dbgMsg(_("Warning! Create vars table aborted."))
            pass

        try:
            dbconn.execute("create table session (start datetime, end datetime)")
            dbconn.commit()
            ntmtools.dbgMsg(_("Create session table."))
        except:
            ntmtools.dbgMsg(_("Warning! Create session table aborted."))
            pass
    ## end-def ##


    ## + ##
    def setPreferences(self, interface, updateInterval, keep_above, opacity, autorun, online_check, tray_activate_action, importexport_file):
        ris = self.getProcNetDev(interface)
        if (ris == None) and self.online:
            dia = gtk.Dialog(_('NTM - Interface'),
                              self.ntmgui.statusIconMenu.get_toplevel(),  #the toplevel wgt of your app
                              gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,  #binary flags or'ed together
                              (_("Change the interface"), 77, gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
            dia.vbox.pack_start(gtk.Label(_('The interface "{0}" is not detected.\nDo you want to confirm the change?').format(interface)))
            dia.show_all()
            result = dia.run()
            doChangeInterface = (result == 77)
            dia.destroy()
        else:
            doChangeInterface = True

        if doChangeInterface:
            interface_changed = (self.interface != interface)
            if interface_changed & self.online:
                print(_("Change the interface..."))
                self.setOffline()
                self.interface = interface
                ntmtools.setDBVar(self.db_conn, "general.interface", interface)
                self.setOnline()
                print(_("...done!"))
            else:
                self.interface = interface
                ntmtools.setDBVar(self.db_conn, "general.interface", interface)

        self.ntmMainWindow_keep_above = keep_above
        if self.ntmMainWindow_keep_above:
            ntmtools.setDBVar(self.db_conn, "general.keep_above", "1")
        else:
            ntmtools.setDBVar(self.db_conn, "general.keep_above", "0")

        self.ntmMainWindow_opacity = opacity
        ntmtools.setDBVar(self.db_conn, "general.opacity", opacity)

        self.timeout_changed = (self.update_interval != updateInterval)
        self.update_interval = int(updateInterval)
        ntmtools.setDBVar(self.db_conn, "general.update_interval", str(int(updateInterval)))

        self.general_pref_autorun = autorun
        if autorun: ntmtools.setDBVar(self.db_conn, "general.autorun", "1")
        else: ntmtools.setDBVar(self.db_conn, "general.autorun", "0")
        self.set_autorun(autorun)

        if self.general_pref_online_check != online_check:
            if online_check==0:
                self.general_pref_online_check = 0
                self.online_detector.changeMode(online_check)
                ntmtools.setDBVar(self.db_conn, "general.online_check", "0")
            elif online_check==1:
                self.general_pref_online_check = 1
                self.online_detector.changeMode(online_check)
                ntmtools.setDBVar(self.db_conn, "general.online_check", "1")
            else:
                ntmtools.dbgMsg(_("Error: Invald online_check value.\n"))

        if self.general_pref_tray_activate_action != tray_activate_action:
            if tray_activate_action==0:
                self.general_pref_tray_activate_action = 0
                ntmtools.setDBVar(self.db_conn, "general.tray_activate_action", "0")
            elif tray_activate_action==1:
                self.general_pref_tray_activate_action = 1
                ntmtools.setDBVar(self.db_conn, "general.tray_activate_action", "1")
            else:
                ntmtools.dbgMsg(_("Error: Invald tray_activate_action value.\n"))

        if self.importexport_file != importexport_file:            
            self.importexport_file = importexport_file
            ntmtools.setDBVar(self.db_conn, "general.importexport_file", importexport_file)
    ## - ##


    ## + ##
    def get_autorun(self):
        des = self.sys_info["des"]
        autorun = False
        if des in GNOME_AUTORUN_TYPE_DES:
            autorun = os.path.exists(os.getenv("HOME") + "/.config/autostart/ntm.desktop")
        elif des in KDE_AUTORUN_TYPE_DES:
            autorun = os.path.exists(os.getenv("HOME") + "/.kde/Autostart/ntm.sh")
        return autorun
    ## - ##


    ## + ##
    def set_autorun(self, active):
        try:
            des = self.sys_info["des"]
            if (active):
                if des in GNOME_AUTORUN_TYPE_DES:
                    ar_dir = os.getenv("HOME") + "/.config/autostart"
                    ar_file = ar_dir + "/ntm.desktop"
                    autorun = os.path.exists(ar_file)
                    if not autorun:
                        if not os.path.exists(ar_dir):
                            os.makedirs(ar_dir)
                        src = globaldef.NTM_PATH + "/stf/ntm.desktop"
                        # shutil.copyfile(src, ar_file)
                        os.system("cp {0} {1}".format(src, ar_file))
                elif (des == "kde"):
                    ar_dir = os.getenv("HOME") + "/.kde/Autostart"
                    ar_file = ar_dir + "/ntm.sh"
                    autorun = os.path.exists(ar_file)
                    if not autorun:
                        if not os.path.exists(ar_dir):
                            os.makedirs(ar_dir)
                        src = globaldef.NTM_PATH + "/stf/ntm.sh"
                        # shutil.copyfile(src, ar_file)
                        os.system("cp {0} {1}".format(src, ar_file))
                else:
                    ntmtools.dbgMsg(_("Autostart work only with Gnome and KDE."))
            else:
                if des in GNOME_AUTORUN_TYPE_DES:
                    os.remove(os.getenv("HOME") + "/.config/autostart/ntm.desktop")
                elif des in KDE_AUTORUN_TYPE_DES:
                    os.remove(os.getenv("HOME") + "/.kde/Autostart/ntm.sh")
                else: pass
        except: pass
    ## - ##


    ## + ##
    def setOnline(self):
        self.session_start = datetime.datetime.now()

        self.update_event(self.session_start, self.session_start, self.update_interval, 0, 0, 1)

        ris = self.getProcNetDev(self.interface)
        if ris != None:
            self.last_traffic_in, self.last_traffic_out = ris
        else:
            print(_("The interface ") + self.interface + _(" is not detected."))
            self.last_traffic_in, self.last_traffic_out = 0, 0

        self.online = True
        if self.logTraffic:
            print(_('Total\tReceive\tTransm.\tMean Speed of the last {0}"').format(self.update_interval))
            print('KByte\tKByte\tKByte\tKByte/sec')

        if not self.versionChecked:
            if not self.checkVersion("http://luigit.altervista.org/ntm/ntm_update.php", globaldef.VERSION):
                self.versionChecked = True
                ntmtools.setDBVar(self.db_conn, "general.last_version_check", str(int(time.time())))

        if not self.info_win_load:
            self.info_win.load()
            self.info_win_load = True
    ## end-def ##


    ## + ##
    def setOffline(self):
        self.updateCount()
        self.online = False
        self.update_event(datetime.datetime.now(), self.session_start, self.update_interval, self.d_rb, self.d_tb, 0)
    ## end-def ##


    ## + ##
    def updateCount(self):
        if self.stop:
            return False

        if not self.online:
            return True

        self.last_update = datetime.datetime.now()

        ris = self.getProcNetDev(self.interface)
        if ris != None:
            rb, tb = ris
            self.d_rb = rb - self.last_traffic_in
            self.d_tb = tb - self.last_traffic_out

            ## Update DB
            diff = self.d_rb + self.d_tb
            if diff != 0:
                self.updateDBDailyTraffic(self.session_start, self.d_rb, self.d_tb)
            self.updateDBSession(True)
            ##

            self.last_traffic_in = rb
            self.last_traffic_out = tb
            self.update_event(self.last_update, self.session_start, self.update_interval, self.d_rb, self.d_tb, 1)

        if self.timeout_changed:
            gobject.timeout_add(self.update_interval*1000, self.updateCount)
            self.timeout_changed = False
            return False

        return True
    ## end-def ##


    ### + return False for not error ###
    def checkVersion(self, url, version):
        itime = ntmtools.readDBVar(self.db_conn, "itime")
        try:
            ntmtools.strToDateTime(itime)
        except:
            ntmtools.dbgMsg("itime: " + _("wrong format or absent. rigenerate."))
            itime = str(datetime.datetime.today())
            ntmtools.setDBVar(self.db_conn, "itime", itime)

        envInfo = urllib2.quote("{0}\t{1}".format(itime, ntmtools.getEnvInfo()))

        fullurl = url + "?cver={0}&sys={1}".format(urllib2.quote(version), envInfo)

        dfile = None
        try:
            dfile = urllib2.urlopen(fullurl, timeout=10)
        except:
            ntmtools.dbgMsg(_("Connection Error (") + fullurl + ").")
            return True

        if dfile != None:
            str_data = dfile.read()
            dic_data = ntmtools.prop2dic(str_data)
            newVer = dic_data["lastversion"]
            compare = ntmtools.versionCompare(version, newVer)

            if compare < 0:
                dialog = gtk.Dialog(
                    _("NTM - New Version"), self.ntmgui.statusIconMenu.get_toplevel(),
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_OK, gtk.RESPONSE_OK)
                )
                icon = dialog.render_icon(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_BUTTON)
                dialog.set_icon(icon)

                linkButton = gtk.LinkButton(
                    dic_data["suggestedurl"],
                    _("Your version: {0}.  Last version: {1}\n{2}\n{3}").
                        format( version, newVer, dic_data["updatemessage"], dic_data["extramessage"] )
                )
                dialog.vbox.pack_start(linkButton)

                dialog.show_all()
                dialog.run()
                dialog.destroy()
        else:
            return True

        return False
    ### - ###


    ## + ##
    def deactiveConnection(self):
        bus = dbus.SystemBus()
        proxy = bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
        iface = dbus.Interface(proxy, dbus_interface='org.freedesktop.DBus.Properties')
        active_connections = iface.Get('org.freedesktop.NetworkManager', 'ActiveConnections')

        if len(active_connections) > 0:
            ifaceNM = dbus.Interface(proxy, dbus_interface='org.freedesktop.NetworkManager')
            ifaceNM.DeactivateConnection(active_connections[0])
    ## - ##

    ## + ##
    def getProcNetDev(self, interface):
        for line in open('/proc/net/dev','r'):
            if ':' not in line: continue
            splitline = string.split(line, ':', 1)
            if string.strip(splitline[0]) != interface: continue

            x = splitline[1].split()
            rec_bytes = int(x[0])
            tra_bytes = int(x[8])
            return (rec_bytes, tra_bytes)
        return None
    ## - ##
#### end-class ####



############################################
#### MAIN
############################################
if __name__ == "__main__":

    # for webkit
    gobject.threads_init()

    # Network Traffic Monitor
    ntm = NTM()

    try:
        gobject.MainLoop().run()
    except KeyboardInterrupt:
        ntmtools.dbgMsg(_("Keyboard interrupt."))
        gobject.MainLoop().quit()


