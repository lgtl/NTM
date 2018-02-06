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


import pygtk
pygtk.require("2.0")
import gtk
import globaldef
import ntmtools
import datetime
import os
import gobject
from monthdelta import monthdelta
import pynotify
import sqlite3
import webkit

import locale
import gettext
from gtk import glade


### + ###
class NtmGui(object):

    ## Init ##
    def __init__(self, ntmo):
        self.ntmo = ntmo

        self.mtraffic = None
        self.mtimeslot = None
        self.mtime = None

        self.last_conn_state = None

        self.unity_panel = self.ntmo.sys_info["unity.panel"]
        if self.unity_panel:
            try:
                import appindicator
            except:
                self.unity_panel = False
        

        # Status Icon
        self.statusIcon = gtk.StatusIcon()
        
        ## i18n
        # self.i18n_APP_NAME = "ntm"
        # self.i18n_DIR = "i18n/locale"
        # print(_("i18n setup: done!")) # TEST

        ## Open xml
        self.gtkb = gtk.Builder()
        # self.gtkb.set_translation_domain("ntm") # i18n
        self.gtkb.add_from_file("ntm_main.gui")        

        ##

        ## Windows Menu

        #self.butMenu = self.gtkb.get_object("button_menu")
        #self.butMenu.connect('clicked', self.butMenu_hClicked)


        ## Menu
        self.statusIconMenu = self.gtkb.get_object("menu_statusIcon")

        menuItem = self.gtkb.get_object("menuitem_show_win")
        menuItem.connect('activate', self.menuShowWin_hActivate)
        menuItem.get_children()[0].set_label(_("Show Window"))

        menuItem = self.gtkb.get_object("menuitem_report")
        menuItem.connect('activate', self.menuReport_hActivate)
        menuItem.get_children()[0].set_label(_("Report"))

        menuItem = self.gtkb.get_object("menuitem_preferences")
        menuItem.connect('activate', self.menuPreferences_hActivate)
        menuItem.get_children()[0].set_label(_("Preferences"))

        menuItem = self.gtkb.get_object("menuitem_info")
        menuItem.connect('activate', self.menuInfo_hActivate)
        menuItem.get_children()[0].set_label(_("Info & News"))

        menuItem = self.gtkb.get_object("menuitem_about")
        menuItem.connect('activate', self.menuAbout_hActivate)
        menuItem.get_children()[0].set_label(_("About"))

        menuItem = self.gtkb.get_object("menuitem_quit")
        menuItem.connect('activate', self.menuQuit_hActivate)
        menuItem.get_children()[0].set_label(_("Quit"))

        # menuItem = self.gtkb.get_object("menuitem_test")
        # menuItem.connect('activate', self.menuTest_hActivate)
        ##

        ## Status Icon
        self.statusIcon.set_from_file(globaldef.NTM_ICON)
        self.statusIcon.set_tooltip(_("Network Traffic Monitor\n-Left click: show the counters\n-Rigth click: show menu"))
        self.statusIcon.connect('activate', self.tryIcon_hActivate)
        self.statusIcon.connect('popup-menu', self.tryIcon_hPopup_menu, self.statusIconMenu)
        ##


        ## Main Window
        self.mainWindow = self.gtkb.get_object("ntmMainWindow")

        self.mainWindow.connect("delete_event", self.windowMain_hDelete)
        self.mainWindow.set_icon_from_file(globaldef.NTM_ICON)
        self.mainWindow.set_title(_(self.mainWindow.get_title()))
        self.mainWindow.hide()
        self.mainWindow_Show = False
        (self.winposx, self.winposy) = self.mainWindow.get_position()
        (self.winsizex, self.winsizey) = self.mainWindow.get_size()

        self.status_bar = self.gtkb.get_object("statusbar")
        ##


        ## Report Windows
        self.view_rep = webkit.WebView()

        self.gtkb_report = gtk.Builder()
        self.gtkb_report.add_from_file("report.gui")

        self.report_date_dialog = self.gtkb_report.get_object("date_dialog")
        self.report_date_dialog_calendar = self.gtkb_report.get_object("date_dialog_calendar")
        self.report_date_dialog_title = self.gtkb_report.get_object("date_dialog_title")

        self.report_window = gtk.Window()
        icon = self.report_window.render_icon(gtk.STOCK_FILE, gtk.ICON_SIZE_BUTTON)
        self.report_window.set_icon(icon)
        self.report_window.resize(300, 400)
        self.report_window.set_position(gtk.WIN_POS_CENTER)
        self.report_window.set_title("NTM - Report")

        vbox = gtk.VBox(False, 0)

        self.report_top_bar = self.gtkb_report.get_object("top_bar")
        vbox.pack_start(self.report_top_bar, False, False, 0)
        vbox.pack_start(self.view_rep, True, True, 0)

        self.report_window.add(vbox)
        self.report_window.show_all()
        self.report_window.hide()
        self.report_window_Show = False
        self.report_window.connect("delete_event", self.report_window_hDelete)

        self.report_first_day = self.gtkb_report.get_object("from_button")
        self.temp_report_first_day = datetime.date.today() - monthdelta(1)
        self.report_first_day.set_label(self.temp_report_first_day.isoformat())
        self.report_first_day.connect('clicked', self.report_first_day_hclicked)

        self.report_last_day = self.gtkb_report.get_object("to_button")
        self.temp_report_last_day = datetime.date.today()
        self.report_last_day.set_label(self.temp_report_last_day.isoformat())
        self.report_last_day.connect('clicked', self.report_last_day_hclicked)

        self.report_all_days = self.gtkb_report.get_object("all_days")

        report_update = self.gtkb_report.get_object("update")
        report_update.connect('clicked', self.report_update_hClicked)

        self.report_type = self.gtkb_report.get_object("report_type") # Combo Box
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        entries = [_('Total'), _('Daily')] # , 'Days of Week']
        for entry in entries: liststore.append([entry])
        self.report_type.set_model(liststore)
        cell = gtk.CellRendererText()
        self.report_type.pack_start(cell, True)
        self.report_type.add_attribute(cell, 'text', 0)
        self.report_type.set_active(0)

        # i18n
        ntmtools.translate_control_text(self.gtkb_report.get_object("label1"))
        ntmtools.translate_control_text(self.gtkb_report.get_object("label2"))
        ntmtools.translate_control_label(self.gtkb_report.get_object("all_days"))
        ntmtools.translate_control_text(self.gtkb_report.get_object("label3"))
        ntmtools.translate_control_label(self.gtkb_report.get_object("update"))
        ntmtools.translate_control_markup(self.gtkb_report.get_object("date_dialog_title"))
        ntmtools.translate_control_label(self.gtkb_report.get_object("dateWindow_cancelButton"))
        ntmtools.translate_control_label(self.gtkb_report.get_object("dateWindow_okButton"))

        self.update_report()
        ##


        ## Window Preferences

        self.windowPreferences = self.gtkb.get_object("preferencesWindow")
        icon = self.windowPreferences.render_icon(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_BUTTON)
        self.windowPreferences.set_icon(icon)
        self.windowPreferences.connect("delete_event", self.windowPreferences_hDelete)
        self.windowPreferences.hide()
        self.windowPreferences_Show = False

        # General

        self.entry_interface = self.gtkb.get_object("preferencesEntry_interface")

        self.spinButton_updateInterval = self.gtkb.get_object("preferencesSpinbutton_updateInterval")
        self.spinButton_updateInterval.set_range(1, 999)
        self.spinButton_updateInterval.set_increments(1, 10)

        self.prefKeepAbove = self.gtkb.get_object("preferences_general_keepAbove")

        self.preferences_opacity = self.gtkb.get_object("preferences_opacity")
        self.preferences_opacity.set_range(0, 100)
        self.preferences_opacity.set_increments(1, 10)

        self.prefAutorun = self.gtkb.get_object("preferences_general_autorun")

        self.preferences_online_check = self.gtkb.get_object("preferences_online_check")
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        entries = ['NetworkManager', 'Ping Mode']
        for entry in entries:
            liststore.append([entry])
        self.preferences_online_check.set_model(liststore)
        cell = gtk.CellRendererText()
        self.preferences_online_check.pack_start(cell, True)
        self.preferences_online_check.add_attribute(cell, 'text', 0)

        self.preferences_tray_activate_action = self.gtkb.get_object("preferences_tray_activate_action")
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        entries = [_('Show Main Window'), _('Show Notify')]
        for entry in entries: liststore.append([entry])
        self.preferences_tray_activate_action.set_model(liststore)
        cell = gtk.CellRendererText()
        self.preferences_tray_activate_action.pack_start(cell, True)
        self.preferences_tray_activate_action.add_attribute(cell, 'text', 0)

        but_cancel = self.gtkb.get_object("preferences_delete_data")
        but_cancel.connect('clicked', self.preferencesDeleteData_hClicked)

        # Data

        but = self.gtkb.get_object("preferences_data_import")
        but.connect('clicked', self.preferencesDataImport_hClicked)

        but = self.gtkb.get_object("preferences_data_export")
        but.connect('clicked', self.preferencesDataExport_hClicked)

        but = self.gtkb.get_object("preferences_data_selfile")
        but.connect('clicked', self.preferencesDataSelfile_hClicked)

        self.entry_data_file = self.gtkb.get_object("preferences_data_file")

        # Bottom

        but_cancel = self.gtkb.get_object("preferencesButton_cancel")
        but_cancel.connect('clicked', self.preferencesButtonCancel_hClicked)

        but_apply = self.gtkb.get_object("preferencesButton_apply")
        but_apply.connect('clicked', self.preferencesButtonApply_hClicked)
        ##

        self.notify_ok = pynotify.init ("summary-body")


        self.aboutActive = False
        self.quitActive = False

        ## i18n
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label_01"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label_02"))
        ntmtools.translate_control_label(self.gtkb.get_object("preferences_general_keepAbove"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label_03"))
        ntmtools.translate_control_label(self.gtkb.get_object("preferences_general_autorun"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label_04"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label_05"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label_06"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label1"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label_1"))
        ntmtools.translate_control_label(self.gtkb.get_object("preferences_data_import"))
        ntmtools.translate_control_label(self.gtkb.get_object("preferences_data_export"))
        ntmtools.translate_control_label(self.gtkb.get_object("preferences_data_selfile"))
        ntmtools.translate_control_text(self.gtkb.get_object("label1"))
        ntmtools.translate_control_label(self.gtkb.get_object("preferences_delete_data"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label_data"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label2"))
        ntmtools.translate_control_text(self.gtkb.get_object("preferences_label3"))
        ntmtools.translate_control_text(self.gtkb.get_object("label_time_page"))
        ntmtools.translate_control_label(self.gtkb.get_object("preferencesButton_cancel"))
        ntmtools.translate_control_label(self.gtkb.get_object("preferencesButton_apply"))

        self.indIcontype = 0
        if not self.unity_panel:
            self.statusIcon.set_visible(True)
            self.indIcontype = 1
        else:
            self.statusIcon.set_visible(False)    
            self.appind = appindicator.Indicator("ntm-ai","nk.ntm_off", appindicator.CATEGORY_APPLICATION_STATUS)
            self.appind.set_status(appindicator.STATUS_ACTIVE)
            self.appind.set_menu(self.statusIconMenu)
            self.indIcontype = 2

    ## - __init__ ##

    ### + ###
    def showNotify(self):
        if self.notify_ok:            
            if self.ntmo.online: smsg = "Online"
            else: smsg = "Offline"

            message = ""
            first = True
            if self.mtraffic != None:
                message += _("Traffic") + ": {0}".format(self.mtraffic.getSummaryMessage())
                first = False

            if self.mtimeslot != None:
                if not first: message += "\n"
                first = False
                message += _("Time Slot") + ": {0}".format(self.mtimeslot.getSummaryMessage())

            if self.mtime != None:
                if not first: message += "\n"
                first = False
                message += _("Time") + ': {0}"'.format(self.mtime.getSummaryMessage())

            self.notify_new_slot = pynotify.Notification ("NTM: {0} - {1}".format(self.ntmo.interface, smsg), message)
            self.notify_new_slot.show()
    ### - ###


    ### Report Window Delete Handler ###
    def report_window_hDelete(self, widget, event, data=None):
        self.report_window.hide()
        self.report_window_Show = False
        return True
    ### - ###


    ## + ##
    def report_first_day_hclicked(self, data = None):
        self.report_date_dialog_title.set_markup("<b>" + _("First Day") + "</b>")
        result = self.report_date_dialog.run()
        if result == 1:
            dSel = self.report_date_dialog_calendar.get_date()
            self.temp_report_first_day = datetime.date(dSel[0], dSel[1] + 1, dSel[2])
            self.report_first_day.set_label(self.temp_report_first_day.isoformat())
        self.report_date_dialog.hide()
    ## - ##


    ## + ##
    def report_last_day_hclicked(self, data = None):
        self.report_date_dialog_title.set_markup("<b>" + _("Last Day") + "</b>")
        result = self.report_date_dialog.run()
        if result == 1:
            dSel = self.report_date_dialog_calendar.get_date()
            self.temp_report_last_day = datetime.date(dSel[0], dSel[1] + 1, dSel[2])
            self.report_last_day.set_label(self.temp_report_last_day.isoformat())
        self.report_date_dialog.hide()
    ## - ##


    ## + ##
    def update_report(self):
        all_days = self.report_all_days.get_active();
        if all_days: rep_res = self.ntmo.get_report_from_db(None, None, all_days)
        else:
            first_day = self.temp_report_first_day
            last_day = self.temp_report_last_day
            rep_res = self.ntmo.get_report_from_db(first_day, last_day)

        rep_type = self.report_type.get_active()
        if rep_type == 0:
            self.set_report_total(rep_res)
        elif rep_type == 1:
            self.set_report_daily(rep_res[0])
        elif rep_type == 2:
            self.set_report_stat()
    ## - ##


    ## + ##
    def report_update_hClicked(self, data = None):
        self.update_report()
    ## - ##

    ## + ##
    #def butMenu_hClicked(self, button, data = None):
    #    self.statusIconMenu.popup(None, None, None, 3, 0, None)
    ## - ##

    ## + ##
    def showMainWindow(self):
        if (not self.mainWindow_Show):
            self.mainWindow.move(self.winposx, self.winposy)
            self.mainWindow.resize(self.winsizex, self.winsizey)
            self.mainWindow.show()
            self.mainWindow_Show = True
        self.mainWindow.present()
    ## - ##

    ## + ##
    def hideMainWindow(self):
        if (self.mainWindow_Show):
            (self.winposx, self.winposy) = self.mainWindow.get_position()
            (self.winsizex, self.winsizey) = self.mainWindow.get_size()
            self.mainWindow.hide()
            self.mainWindow_Show = False
    ## - ##

    ## TryIcon Handler ##
    # Activate
    def tryIcon_hActivate(self, data = None):
        if self.ntmo.general_pref_tray_activate_action == 0:
            self.showMainWindow()
        elif self.ntmo.general_pref_tray_activate_action == 1:
            self.showNotify()
    ## - ##


    ## Right Click ##
    def tryIcon_hPopup_menu(self, widget, button, time, data = None):
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, None, 3, time)
        pass
    ## - ##


    ## Menu Handlers ##
    def menuShowWin_hActivate(self, widget):
        self.showMainWindow()
    ## - ##


    ## Menu Handlers ##
    def menuReport_hActivate(self, widget):
        self.report_window.show()
        self.report_window_Show = True
    ## - ##


    ## + ##
    def menuPreferences_hActivate(self, widget):
        self.prefKeepAbove.set_active(self.ntmo.ntmMainWindow_keep_above)
        self.preferences_opacity.set_value(self.ntmo.ntmMainWindow_opacity)
        self.prefAutorun.set_active(self.ntmo.general_pref_autorun)
        self.set_general_preferences(
            self.ntmo.interface, self.ntmo.update_interval,
            self.ntmo.ntmMainWindow_keep_above, self.ntmo.ntmMainWindow_opacity,
            self.ntmo.general_pref_autorun, self.ntmo.general_pref_online_check,
            self.ntmo.general_pref_tray_activate_action,
            self.ntmo.importexport_file
        )
        self.windowPreferences.show()
        self.windowPreferences_Show = True
    ## - ##


    ## + ##
    def menuInfo_hActivate(self, widget):
        #if self.ntmo.online:
        #    self.ntmo.info_win.load()
        self.ntmo.info_win.show()
    ## - ##


    ## + ##
    def menuAbout_hActivate(self, widget):
        if self.aboutActive: return
        self.aboutActive = True

        about = gtk.AboutDialog()
        icon = about.render_icon(gtk.STOCK_ABOUT, gtk.ICON_SIZE_BUTTON)
        about.set_icon(icon)
        about.set_name("NTM")
        about.set_version(globaldef.VERSION)
        about.set_copyright("Copyleft 2010 - Luigi Tullio")
        about.set_license(globaldef.LICENSE)
        about.set_website("http://netramon.sourceforge.net")
        about.set_authors(["Luigi Tullio <tluigi@gmail.com>\nhttp://luigit.altervista.org"])

        try:
            about.set_logo(gtk.gdk.pixbuf_new_from_file(globaldef.NTM_ICON))
        except:
            ntmtools.dbgMsg(_("Error: set_logo in ") + "menuAbout_hActivate.")

        about.set_comments("(" + globaldef.VERSION_NN + ")\n" + _("Monitors your internet traffic."))
        about.run()
        about.destroy()

        self.aboutActive = False
    ## - ##


    ## + ##
    def menuQuit_hActivate(self, widget):
        if self.quitActive: return
        self.quitActive = True

        dialog = gtk.Dialog(
            "NTM - Quit", self.statusIconMenu.get_toplevel(),
             gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
             (gtk.STOCK_YES, gtk.RESPONSE_YES,
              gtk.STOCK_NO, gtk.RESPONSE_NO)
        )
        icon = self.mainWindow.render_icon(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_BUTTON)
        dialog.set_icon(icon)
        label = gtk.Label(_('Do you really want to exit from NTM?'))
        label.set_padding(8, 8)
        dialog.vbox.pack_start(label)
        dialog.show_all()
        result = dialog.run()
        dialog.destroy()
        if result == gtk.RESPONSE_YES:
            self.hideMainWindow()
            self.ntmo.quit()

        self.quitActive = False
    ## - ##


    ## + TEST ##
    #def menuTest_hActivate(self, widget):
    #    print("Test:")
    ## - ##


    ## Main Window Handler ##

    ## + ##
    def windowMain_hDelete(self, widget, event, data=None):
        # print("windowMain_hDelete")

        #if self.env_des == "kde":
        #    self.menuQuit_hActivate(None)
        #else:
            
        self.hideMainWindow()
        return True
    ## - ##


    ## Report Window Handler ##
    def report_window_hDelete(self, widget, event, data=None):
        # print("<<windowReport_hDelete>>")
        self.report_window.hide()
        self.report_window_show = False
        return True
    ## - ##


    ## Preferences Window Handler ##
    def windowPreferences_hDelete(self, widget, event, data=None):
        # print("delete event occurred")
        self.windowPreferences.hide()
        self.windowPreferences_Show = False
        return True
    ## - ##


    ## + ##
    def preferencesDeleteData_hClicked(self, data = None):
        dialog = gtk.Dialog(
            _("NTM - Delete All Data"), self.statusIconMenu.get_toplevel(),
             gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
             (gtk.STOCK_YES, gtk.RESPONSE_YES,
              gtk.STOCK_NO, gtk.RESPONSE_NO)
        )
        #icon = self.report_window.render_icon(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_BUTTON)
        icon = self.mainWindow.render_icon(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_BUTTON)
        dialog.set_icon(icon)
        label = gtk.Label(_('Do you really want to remove all data (report and counters)?\nThe general preferences will be not deleted.'))
        label.set_padding(8, 8)
        dialog.vbox.pack_start(label)
        dialog.show_all()
        result = dialog.run()
        dialog.destroy()
        if result == gtk.RESPONSE_YES:
            self.ntmo.removeAllData()
    ## - ##


    ## + ##
    def preferencesDataImport_hClicked(self, data = None):
        #print("preferencesDataImport_hClicked(self, data = None)")
        filename = self.entry_data_file.get_text()
        if os.path.exists(filename):
            dbc_s = sqlite3.connect(filename)
            self.ntmo.substituteData(dbc_s)
        else:
            dialog = gtk.Dialog(
                _("NTM - Import Data"), self.statusIconMenu.get_toplevel(),
                 gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                 (gtk.STOCK_OK, gtk.RESPONSE_OK)
            )
            icon = self.mainWindow.render_icon(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_BUTTON)
            dialog.set_icon(icon)
            label = gtk.Label(_("No such file") + ": {0}".format(filename))
            label.set_padding(8, 8)
            dialog.vbox.pack_start(label)
            dialog.show_all()
            result = dialog.run()
            dialog.destroy()
    ## - ##


    ## + ##
    def preferencesDataExport_hClicked(self, data = None):
        #print("preferencesDataExport_hClicked(self, data = None)")
        filename = self.entry_data_file.get_text()

        dbc_d = sqlite3.connect(filename)
        self.ntmo.createTables(dbc_d)
        self.ntmo.copyData(self.ntmo.db_conn, dbc_d)
    ## - ##


    ## + ##
    def preferencesDataSelfile_hClicked(self, data = None):
        # print("preferencesDataSelfile_hClicked(self, data = None)")
        chooser = gtk.FileChooserDialog(
            title = None, action = gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        )
        filename = self.entry_data_file.get_text()
        chooser.set_filename(filename)
        res = chooser.run()
        if res == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
            self.entry_data_file.set_text(filename)
        chooser.destroy()
    ## - ##


    ## + ##
    def preferencesButtonCancel_hClicked(self, data = None):
        self.windowPreferences.hide()
        self.windowPreferences_Show = False
    ## - ##


    ## + ##
    def preferencesButtonApply_hClicked(self, data = None):
        self.mtraffic.set_preferences_from_gui()
        self.mtimeslot.set_preferences_from_gui()
        self.mtime.set_preferences_from_gui()

        interface = self.entry_interface.get_text()
        update_interval = self.spinButton_updateInterval.get_value()
        online_check = self.preferences_online_check.get_active()
        tray_activate_action = self.preferences_tray_activate_action.get_active()

        self.ntmo.setPreferences(
            interface, update_interval,
            self.prefKeepAbove.get_active(),
            self.preferences_opacity.get_value(),
            self.prefAutorun.get_active(),
            online_check, tray_activate_action,
            self.entry_data_file.get_text()
        )

        self.windowPreferences.hide()
        self.windowPreferences_Show = False
    ## - ##


    ## + ##
    def dateWindow_hDelete(self, widget, event, data=None):
        self.dateWindow.hide()
        return True
    ## - ##


    ## + ##
    def applyProp(self, keep_above, opacity):
        self.mainWindow.set_keep_above(keep_above)
        self.mainWindow.set_opacity(0.01 * opacity)
    ## - ##


    ## updateInterval : sec;  ##
    def set_general_preferences(self, interface, updateInterval, keep_above, opacity, autorun, online_check, tray_activate_action, importexport_file):
        self.entry_interface.set_text(interface)
        self.spinButton_updateInterval.set_value(updateInterval)
        self.prefKeepAbove.set_active(keep_above)
        self.preferences_opacity.set_value(int(opacity))
        self.prefAutorun.set_active(autorun)
        self.preferences_online_check.set_active(online_check)
        self.preferences_tray_activate_action.set_active(tray_activate_action)
        self.entry_data_file.set_text(importexport_file)
    ## - ##


    ## + ##
    def set_icon_tooltip(self, string):
        self.statusIcon.set_tooltip(string)
    ## - ##


    ## rows: db cursor #
    def set_report_daily(self, rows):
        data_head = '''<html><head><title>''' + _("Daily Traffic Report") + '''</title></head><body><p align="center">
            <table class="bodyText" border="0" cellpadding="0" cellspacing="0" width="272">
            <tbody><tr><td>
            <table id="1" class="setfont" style="background-color: LightGrey;" border="0" cellpadding="2" cellspacing="1" width="100%">
              <tbody>
                <tr style="background-color: WhiteSmoke;">
                  <th colspan="5" align="center">''' + _("Daily Traffic") + '''<br>
                    <span class="red" style="font-size: 11px; width: 100%;"><b>''' + _("All value are listed in MiB") + '''.</b></span>
                  </th>
                </tr>
                <tr style="font-style: italic; background-color: White;" align="center">
                  <td></td>
                  <td><b>''' + _("Total") + '''</b></td>
                  <td><b>''' + _("In") + '''</b></td>
                  <td><b>''' + _("Out") + '''</b></td>
                </tr>'''
        data_foot = '</tbody></table></td></tr></tbody></table></p></body></html>'
        data_row = '''<tr style="background-color: {0};" align="right">
          <td><b><b>{1}</b></b></td> <td><span>{2:.2f}</span></td>
          <td><span>{3:.2f}</span></td> <td><span>{4:.2f}</span></td></tr>'''

        data = data_head
        i = 0
        for r in rows:
            t_in = r[1] / (1024.0*1024.0)
            t_out = r[2] / (1024.0*1024.0)
            if i == 0:
                data += data_row.format("#F0F0F0", str(r[0]), t_in+t_out, t_in, t_out)
                i = 1
            else:
                data += data_row.format("#FFFFFF", str(r[0]), t_in+t_out, t_in, t_out)
                i = 0

        data += data_foot

        self.view_rep.load_html_string(data, "file:///")
    ## - end-def #


    ## rows: db cursor #
    def set_report_total(self, rep_res):
        template = '''<html><head><title>''' + _("Daily Traffic Report") + '''</title>
        </head>
        <body><p><h2 align="center">''' + _("Report - Total") + '''</h2></p>
        <p align="center">
        <table class="bordered" style="border-collapse: collapse; border: 1px solid #a0a0a0; margin: 10px 0px 10px 0px;"><tbody>
        <tr><th rowspan="1" colspan="2" style="border: 1px solid #a0a0a0;">''' + _("Traffic") + '''</th></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Days with traffic") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{0}</td></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Total") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{1:.2f} MiB</td></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Received") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{2:.2f} MiB</td></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Transmitted") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{3:.2f} MiB</td></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Max in one day") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{4:.2f} MiB</td></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Min in one day") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{5:.2f} MiB</td></tr>
        </tbody></table>
        </p>
        <p align="center">
        <table class="bordered" style="border-collapse: collapse; border: 1px solid #a0a0a0; margin: 10px 0px 10px 0px;"><tbody>
        <tr><th rowspan="1" colspan="2" style="border: 1px solid #a0a0a0;">Sessions</th></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("N. sessions") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{6}</td></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Total Time") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{7}</td></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Max session length") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{8}</td></tr>
        <tr><td style="border: 1px solid #a0a0a0;">''' + _("Min session length") + '''</td><td style="border: 1px solid #a0a0a0; text-align: right;">{9}</td></tr>
        </tbody></table>
        </p>
        </body></html>
        '''
        mbytes = 1.0 / (1024.0 * 1024.0)
        data = template.format(rep_res[2], mbytes*(rep_res[3]+rep_res[4]), mbytes*rep_res[3],
                    mbytes*rep_res[4], mbytes*rep_res[5], mbytes*rep_res[6], rep_res[7],
                    ntmtools.formatTime(rep_res[8]), ntmtools.formatTime(rep_res[9]), ntmtools.formatTime(rep_res[10]))

        self.view_rep.load_html_string(data, "file:///")
    ## - end-def #


    ## rows: db cursor #
    def set_report_stat(self):
        template = '''<html><head><title>''' + _("Daily Traffic Report") + '''</title></head>
        <body><p><h2 align="center">''' + _("Report - Statistic") + '''</h2></p>
        <p align="center">''' + _("Coming soon...") + '''</p></body></html>'''
        data = template

        self.view_rep.load_html_string(data, "file:///")
    ## - end-def #


    ## + ##
    def set_traffic_module(self, mtraffic):
        self.mtraffic = mtraffic

        self.container_traffic_main = self.gtkb.get_object("main_container_traffic")
        self.container_traffic_main.add(mtraffic.get_main_gui())

        pref_container_traffic = self.gtkb.get_object("pref_container_traffic")
        ret = mtraffic.get_preferences_gui()
        pref_container_traffic.add(ret)
    ## - ##


    ## + ##
    def set_timeslot_module(self, mtimeslot):
        self.mtimeslot = mtimeslot

        self.container_timeslot_main = self.gtkb.get_object("main_container_timeslot")
        self.container_timeslot_main.add(mtimeslot.get_main_gui())

        pref_container_timeslot = self.gtkb.get_object("pref_container_timeslot")
        ret = mtimeslot.get_preferences_gui()
        pref_container_timeslot.add(ret)
    ## - ##


    ## + ##
    def set_time_module(self, mtime):
        self.mtime = mtime

        self.container_time_main = self.gtkb.get_object("main_container_time")
        self.container_time_main.add(mtime.get_main_gui())

        pref_container_time = self.gtkb.get_object("pref_container_time")
        ret = mtime.get_preferences_gui()
        pref_container_time.add(ret)
    ## - ##


    ## + ##
    # timestamp : Time of update [datetime.datetime]; session_start:[datetime.datetime]; update_interval : sec
    # last_rec_traffic, last_tra_traffic : Generated traffic from last update in bytes
    # conn_state : 0 -> offline; 1 -> online
    def update_h(self, timestamp, session_start, update_interval, last_rec_traffic, last_tra_traffic, conn_state):
        if conn_state != self.last_conn_state:
            if conn_state == 0:
                self.status_bar.push(self.status_bar.get_context_id("ntm"), "{0}: ".format(self.ntmo.interface) + _("Offline"))
                self.statusIcon.set_from_file(globaldef.NTM_ICON)
                if self.unity_panel:
                    self.appind.set_icon("nk.ntm_off")
            elif conn_state == 1:
                self.status_bar.push(self.status_bar.get_context_id("ntm"), "{0}: ".format(self.ntmo.interface) + _("Online"))
                self.statusIcon.set_from_file(globaldef.NTM_ICON_ACTIVE)
                if self.unity_panel:
                    self.appind.set_icon("nk.ntm_on")
            self.last_conn_state = conn_state
    ## - ##


    ## + ##
    def showDialog(self, title, message):
        dialog = gtk.Dialog(
            title, self.statusIconMenu.get_toplevel(),
             gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
             (gtk.STOCK_YES, gtk.RESPONSE_YES,
              gtk.STOCK_NO, gtk.RESPONSE_NO)
        )
        icon = self.mainWindow.render_icon(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_BUTTON)
        dialog.set_icon(icon)
        label = gtk.Label(message)
        label.set_padding(8, 8)
        dialog.vbox.pack_start(label)
        dialog.show_all()
        result = dialog.run()
        dialog.destroy()

        return result
    ## - ##

### - Class ###


