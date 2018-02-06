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



import gobject
#import time
import datetime
import gtk

import ntmtools
#from monthdelta import monthdelta


import locale
import gettext
from gtk import glade

import os
import sys



### + ###
# The used sec is allocated to session start time
class MTime():

    ## + ##
    # ntm: NTM
    # tsTime and slotLength in seconds. startPeriod, endPeriod: datetime.date
    # tsTime : time used in the current slot
    def __init__(self, ntm, active, used_sec, total_sec, auto_disconnect,
                 period_length, custom_days, first_day, period_autoupdate):
        self.active = active
        self.used_sec = used_sec
        self.total_sec = total_sec
        self.auto_disconnect = auto_disconnect
        self.period_length = period_length
        self.custom_days = custom_days
        self.first_day = first_day
        self.period_autoupdate = period_autoupdate

        self.ntm = ntm
        self.db_conn = ntm.db_conn
        self.disconnect_handler = ntm.deactiveConnection
        self.gtkb = None

        self.temp_gui_total_sec = total_sec
        self.temp_gui_pref_first_day = first_day
        self.last_state = 0
        self.connStartTime = 0
        self.this_slot_sec = 0 # seconds used in the active slot
        self.now = None
        self.logUpdate = False
        self.disc_msgDialog = False

        self.temp_gui_pref_first_day = None
    ## - ##


    ## + ##
    def makeFromDb(ntm):
        conn = ntm.db_conn

        val_str = ntmtools.readDBVar(conn, "time.active")
        try:
            active = (ntmtools.strToInt(val_str, 1) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time.active' " + _("or is not stored. Default value") + " 'True'")
            active = True
            ntmtools.setDBVar(conn, "time.active", "1")

        val_str = ntmtools.readDBVar(conn, "time.total_sec")
        try:
            total_sec = ntmtools.strToInt(val_str, 30*60*60) # 30h
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time.total_sec' " + _("or is not stored. Default value") + " '30h'")
            total_sec = 30*60*60
            ntmtools.setDBVar(conn, "time.total_sec", total_sec)

        val_str = ntmtools.readDBVar(conn, "time.auto_disconnect")
        try:
            auto_disconnect = (ntmtools.strToInt(val_str, 1) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time.auto_disconnect' " + _("or is not stored. Default value") + " '" +_("True") + "'")
            auto_disconnect = True
            ntmtools.setDBVar(conn, "time.auto_disconnect", "1")


        val_str = ntmtools.readDBVar(conn, "time.period_length")
        try:
            period_length = int(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time.period_length' " + _("or is not stored. Default value") + " '" + _("Month") + "'")
            period_length = 3  # 3 -> Month
            ntmtools.setDBVar(conn, "time.period_length", str(int(period_length)))

        val_str = ntmtools.readDBVar(conn, "time.custom_days")
        try:
            custom_days = int(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time.custom_days' " + _("or is not stored. Default value") + " '30'")
            custom_days = 30
            ntmtools.setDBVar(conn, "time.custom_days", str(int(custom_days)))

        val_str = ntmtools.readDBVar(conn, "time.first_day")
        try:
            first_day = ntmtools.strToDate(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time.first_day' " + _("or is not stored. Default value") + " '2009-10-01'")
            first_day = datetime.date(2009, 10, 01)
            ntmtools.setDBVar(conn, "time.first_day", first_day)

        val_str = ntmtools.readDBVar(conn, "time.period_autoupdate")
        try:
            period_autoupdate = (ntmtools.strToInt(val_str, 1) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time.period_autoupdate' " + _("or is not stored. Default value") + " '" + _("True") + "'")
            period_autoupdate = True
            ntmtools.setDBVar(conn, "time.period_autoupdate", "1")


        last_day = ntmtools.get_last_day(first_day, period_length, custom_days)
        used_sec = MTime.loadTimeUsed(conn, ntmtools.date_to_datetime_start(first_day), ntmtools.date_to_datetime_end(last_day))

        return MTime(ntm, active, used_sec, total_sec, auto_disconnect, period_length, custom_days, first_day, period_autoupdate)
    makeFromDb = staticmethod(makeFromDb)
    ## - ##


    ## + ##
    # return t(slotsUsed, timeUsedInLastSlot:sec)
    def loadTimeUsed(db_conn, start_period, end_period):
        c = db_conn.cursor()
        rows = c.execute("select * from session where start>=? AND start<=?",
                         (start_period, end_period) ) # start session allocation

        used_time = 0
        len = 0
        time = 0

        for r in rows:
            try:
                tsStart = datetime.datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
                tsEnd = datetime.datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S")
                diff = tsEnd - tsStart
                sec_len = diff.days*86400 + diff.seconds
            except:
                ntmtools.dbgMsg(_("Error in the session table. Row:") + " {0} .\n".format(str(r)))
                sec_len = 0

            used_time += sec_len

        return used_time
    loadTimeUsed = staticmethod(loadTimeUsed)
    ## - ##


    ## + ##
    def reloadTimeUsed(self):
        last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
        used_sec = MTime.loadTimeUsed(self.db_conn, ntmtools.date_to_datetime_start(self.first_day), ntmtools.date_to_datetime_end(last_day))
        self.used_sec = used_sec
        self.update_main_gui()
    ## - ##


    ## + ##
    # Return True if first_day<=timestam<=last_day
    def update_period(self, timestamp):
        last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
        date_timestamp = timestamp.date()
        if (date_timestamp < self.first_day):
            return False

        if self.period_autoupdate:
            ch = False
            while date_timestamp > last_day:
                self.first_day = last_day + datetime.timedelta(1)
                last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
                ch = True

            if ch:
                ntmtools.setDBVar(self.db_conn, "time.first_day", self.first_day.isoformat())
                last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
                self.used_sec = MTime.loadTimeUsed(self.ntm.db_conn, ntmtools.date_to_datetime_start(self.first_day), ntmtools.date_to_datetime_end(last_day))
                self.connStartTime = timestamp
                self.this_slot_sec = 0

            return True
        else:
            return (date_timestamp <= last_day)
    ## - ##


    ## + ##
    # timestamp : Time of update [datetime.datetime]; session_start:[datetime.datetime]; update_interval : sec
    # last_rec_traffic, last_tra_traffic : Generated traffic from last update in bytes
    # conn_state : 0 -> offline; 1 -> online
    def update_h(self, timestamp, session_start, update_interval, last_rec_traffic, last_tra_traffic, conn_state):
        if (not self.active): return

        self.now = timestamp
        if not self.update_period(session_start): return

        if (self.last_state == 0):
            if (conn_state == 1): # offline -> online
                last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
                self.used_sec = MTime.loadTimeUsed(self.ntm.db_conn, ntmtools.date_to_datetime_start(self.first_day), ntmtools.date_to_datetime_end(last_day))
                self.connStartTime = timestamp
                self.this_slot_sec = 0
        else: # last_state is online
            self.this_slot_sec = ntmtools.timedelta2sec(self.now - self.connStartTime)
            if (conn_state == 0): # online -> offline
                pass

        self.last_state = conn_state
        self.update_main_gui()

        if self.logUpdate:
            print('Time: {0} of {1}\n'.
                format( self.used_sec + self.this_slot_sec, self.total_sec)
            )

        self.check_limit()
    ## - ##


    ## + ##
    def check_limit(self):
        if (not self.active): return

        if ( (self.used_sec + self.this_slot_sec) >= self.total_sec):
            if (self.last_state == 1) and (not self.disc_msgDialog):
                self.disc_msgDialog = True
                last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
                if self.auto_disconnect:
                    msg = _('Time Limit Reached') + ', {0}. '.format(ntmtools.formatTime(self.total_sec)) + _('Disconnection is done!!\nPeriod: {0} to {1}').format(self.first_day.isoformat(), last_day.isoformat())
                    if self.disconnect_handler != None:
                        self.disconnect_handler()
                else:
                    msg = _('Time Limit Reached') + ', {0}.\n'.format(ntmtools.formatTime(self.total_sec)) + _('Period: {0} to {1}').format(self.first_day.isoformat(), last_day.isoformat())

                dialog = gtk.Dialog(
                    _("NTM - Message"), None,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_OK, gtk.RESPONSE_OK)
                )
                icon = gtk.Window().render_icon(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_BUTTON)
                dialog.set_icon(icon)
                label = gtk.Label(msg)
                label.set_padding(8, 8)
                dialog.vbox.pack_start(label)
                dialog.show_all()
                result = dialog.run()
                dialog.destroy()
                self.disc_msgDialog = False
    ## - ##


    ## + ##
    def build_gui(self):
        self.gtkb = gtk.Builder()
        # self.gtkb.set_translation_domain("ntm") # i18n
        self.gtkb.add_from_file("mtime.gui")
        gtkb = self.gtkb

        ## Main
        self.gui_main = gtkb.get_object("main")
        if self.active: self.gui_main.show()
        else: self.gui_main.hide()
        self.gui_main_per = gtkb.get_object("time_topLabel2")
        self.gui_main_used_sec = gtkb.get_object("label_used_time")
        self.gui_main_left_sec = gtkb.get_object("label_left_time")
        self.gui_main_total_sec = gtkb.get_object("label_total_time")
        self.gui_main_period = gtkb.get_object("timeFrame_period")
        # #

        # Preferences #
        self.gui_pref = gtkb.get_object("preferences")
        self.gui_pref_time_active = gtkb.get_object("pref_time_active")

        self.gui_pref_total_time = gtkb.get_object("pref_total_time")
        self.gui_pref_total_time.connect('clicked', self.gui_pref_total_time_hclicked)

        self.gui_pref_auto_disconnect = gtkb.get_object("pref_auto_disconnect")

        self.gui_pref_period_autoupdate = gtkb.get_object("pref_period_autoupdate")

        self.gui_pref_period_length = gtkb.get_object("pref_period_length") # Combo Box
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        entries = [_('Custom'), _('Day'), _('Week'), _('Month'), _('Year')]
        for entry in entries:
            liststore.append([entry])
        self.gui_pref_period_length.set_model(liststore)
        cell = gtk.CellRendererText()
        self.gui_pref_period_length.pack_start(cell, True)
        self.gui_pref_period_length.add_attribute(cell, 'text', 0)
        self.gui_pref_period_length.connect("changed", self.pref_period_length_hchanged)

        self.gui_pref_label_days = gtkb.get_object("pref_label_days")
        self.gui_pref_days = gtkb.get_object("pref_days")
        self.gui_pref_days.set_range(1, 999999)
        self.gui_pref_days.set_increments(1, 10)

        self.gui_pref_first_day = gtkb.get_object("pref_first_day")
        self.gui_pref_first_day.connect('clicked', self.gui_pref_first_day_hclicked)

        ## Date Dialog
        self.gui_date_dialog = gtkb.get_object("date_dialog")
        self.gui_date_dialog.connect("delete_event", self.date_dialog_hdelete)
        self.gui_date_dialog_title = gtkb.get_object("date_dialog_title")
        self.gui_date_dialog_calendar = gtkb.get_object("date_dialog_calendar")
        self.gui_date_dialog_calendar.select_month(self.first_day.month-1, self.first_day.year)
        self.gui_date_dialog_calendar.select_day(self.first_day.day)
        self.temp_gui_pref_first_day = self.first_day

        ## TimeLen Dialog
        self.gui_time_len_dialog = gtkb.get_object("time_len_dialog")
        self.gui_time_len_dialog.connect("delete_event", self.gui_time_len_dialog_hdelete)
        self.gui_time_len_dialog_hour = gtkb.get_object("time_len_dialog_hour")
        self.gui_time_len_dialog_hour.set_range(0, 999999)
        self.gui_time_len_dialog_hour.set_increments(1, 10)
        self.gui_time_len_dialog_minute = gtkb.get_object("time_len_dialog_minute")
        self.gui_time_len_dialog_minute.set_range(0, 999999)
        self.gui_time_len_dialog_minute.set_increments(1, 10)
        self.gui_time_len_dialog_second = gtkb.get_object("time_len_dialog_second")
        self.gui_time_len_dialog_second.set_range(0, 59)
        self.gui_time_len_dialog_second.set_increments(1, 10)
        (h, m, s) = ntmtools.sec_to_hms(self.total_sec)
        self.gui_time_len_dialog_hour.set_value(h)
        self.gui_time_len_dialog_minute.set_value(m)
        self.gui_time_len_dialog_second.set_value(s)
        self.temp_gui_total_sec = self.total_sec

        ## i18n
        ntmtools.translate_control_markup(gtkb.get_object("label2"))
        ntmtools.translate_control_markup(gtkb.get_object("label5"))
        # print(gtkb.get_object("label5").get_label())
        ntmtools.translate_control_markup(gtkb.get_object("label6"))
        ntmtools.translate_control_markup(gtkb.get_object("time_topLabel"))
        ntmtools.translate_control_markup(gtkb.get_object("date_dialog_title"))
        ntmtools.translate_control_label(gtkb.get_object("pref_time_active"))

        ntmtools.translate_control_text(gtkb.get_object("pref_label5"))
        ntmtools.translate_control_label(gtkb.get_object("pref_auto_disconnect"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label12"))
        ntmtools.translate_control_label(gtkb.get_object("pref_period_autoupdate"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label1"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label2"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label_days"))
        ntmtools.translate_control_markup(gtkb.get_object("title"))

        ntmtools.translate_control_text(gtkb.get_object("tld_label1"))
        ntmtools.translate_control_text(gtkb.get_object("tld_label2"))
        ntmtools.translate_control_text(gtkb.get_object("tld_label3"))
        
        ntmtools.translate_control_label(gtkb.get_object("time_len_dialog_cancel"))
        ntmtools.translate_control_label(gtkb.get_object("time_len_dialog_ok"))
    ## - ##


    ## + ##
    def date_dialog_hdelete(self, widget, event, data=None):
        self.gui_date_dialog.hide()
        return True
    ## - ##


    ## + ##
    def gui_time_len_dialog_hdelete(self, widget, event, data=None):
        self.gui_time_len_dialog.hide()
        return True
    ## - ##


    ## + ##
    def pref_period_length_hchanged(self, widget, data=None):
        length = self.gui_pref_period_length.get_active()
        if (length == 0):
            self.gui_pref_label_days.show()
            self.gui_pref_days.show()
        else:
            self.gui_pref_label_days.hide()
            self.gui_pref_days.hide()
    ## - ##


    ## + ##
    def gui_pref_total_time_hclicked(self, data = None):
        result = self.gui_time_len_dialog.run()
        if result == 1: # OK
            hour = self.gui_time_len_dialog_hour.get_value()
            minute = self.gui_time_len_dialog_minute.get_value()
            second = self.gui_time_len_dialog_second.get_value()
            self.temp_gui_total_sec = int(round(second + minute*60 + hour*60*60))
            if (self.temp_gui_total_sec == 0):
                self.ntm.ntmgui.showDialog(_("NTM - Warning!"), _("The total time must be > 0 sec. Default value is 1h"))
                self.temp_gui_total_sec = 1*60*60
            self.gui_pref_total_time.set_label(ntmtools.formatTime(self.temp_gui_total_sec))
        self.gui_time_len_dialog.hide()
    ## - ##


    ## + ##
    def gui_pref_first_day_hclicked(self, data = None):
        self.gui_date_dialog_title.set_markup("<b>" + _("First Day") + "</b>")
        result = self.gui_date_dialog.run()
        if result == 1:
            dSel = self.gui_date_dialog_calendar.get_date()
            self.temp_gui_pref_first_day = datetime.date(dSel[0], dSel[1] + 1, dSel[2])
            self.gui_pref_first_day.set_label(self.temp_gui_pref_first_day.isoformat())
        self.gui_date_dialog.hide()
    ## - ##


    ## + ##
    def update_main_gui(self):
        if self.gtkb == None:
            print("MMTime.update_main_gui(): " + _("Gui not builded") + ".\n")
            return

        total_used_sec = self.used_sec + self.this_slot_sec
        (h, m, s) = ntmtools.sec_to_hms(total_used_sec)
        out_str = """<span color='#900000'>{0}h{1}'<small>{2}"</small></span>""".format(h, m, s)
        self.gui_main_used_sec.set_markup(out_str)

        (h, m, s) = ntmtools.sec_to_hms(self.total_sec - total_used_sec)
        out_str = """<span color='#009000'>{0}h{1}'<small>{2}"</small></span>""".format(h, m, s)
        self.gui_main_left_sec.set_markup(out_str)

        (h, m, s) = ntmtools.sec_to_hms(self.total_sec)
        out_str = """{0}h{1}'<small>{2}"</small>""".format(h, m, s)
        self.gui_main_total_sec.set_markup(out_str)

        total_used_sec = self.used_sec + self.this_slot_sec
        if self.total_sec == 0:
            print _("Warning! mtime.py: total sec is 0.")
            per = 100.0
        else: per = 100.0 * total_used_sec / self.total_sec

        last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)

        if self.now != None:
            period_len_total = ntmtools.timedelta2sec(ntmtools.date_to_datetime_end(last_day) - ntmtools.date_to_datetime_start(self.first_day))
            period_len_used = ntmtools.timedelta2sec(self.now - ntmtools.date_to_datetime_start(self.first_day))
            if period_len_used != 0:
                estimate = total_used_sec * period_len_total / period_len_used
                (h, m, s) = ntmtools.sec_to_hms(estimate)
                estimate_str = '''{0}h{1}'{2}"'''.format(h, m, s)
            else: estimate_str = "--"
        else: estimate_str = "--"

        self.gui_main_per.set_markup("""<small>({0:.1f}%) [{1}]</small>""".format(per, estimate_str))

        self.gui_main_period.set_markup("<small><small>" + _("Period") + ": {0} - {1}</small></small>".format(self.first_day, last_day))
    ## - ##


    ## + ##
    def getSummaryMessage(self):
        total_used_sec = self.used_sec + self.this_slot_sec
        return _("Used {0} of {1}").format(ntmtools.formatTime(total_used_sec), ntmtools.formatTime(self.total_sec))
    ## - ##


    ## + ##
    def update_preferences_gui(self):
        if self.gtkb == None:
            print("MMTime.update_preferences_gui(*): " + _("Gui not builded") + ".\n")
            return

        self.gui_pref_time_active.set_active(self.active)
        self.gui_pref_total_time.set_label(ntmtools.formatTime(self.total_sec))
        self.gui_pref_auto_disconnect.set_active(self.auto_disconnect)

        self.gui_pref_period_length.set_active(self.period_length)
        self.gui_pref_days.set_value(self.custom_days)
        self.gui_pref_first_day.set_label(self.first_day.isoformat())
        self.temp_gui_pref_first_day  = self.first_day
        self.gui_pref_period_autoupdate.set_active(self.period_autoupdate)
    ## - ##


    ## + ##
    def set_preferences_from_gui(self):
        if self.gtkb == None:
            print("MMTime.set_preferences_from_gui(): " + _("Gui not builded") + ".\n")
            return

        active = self.gui_pref_time_active.get_active()
        total_sec = self.temp_gui_total_sec
        auto_disconnect = self.gui_pref_auto_disconnect.get_active()
        period_length = self.gui_pref_period_length.get_active()
        custom_days = self.gui_pref_days.get_value()
        period_autoupdate = self.gui_pref_period_autoupdate.get_active()

        self.setPreferences(active, total_sec, auto_disconnect, period_length, custom_days, self.temp_gui_pref_first_day, period_autoupdate)
    ## - ##


    ## + ##
    def setPreferences(self, active, total_sec, auto_disconnect, period_length, custom_days, first_day, period_autoupdate):
        update_time = False
        if (self.active != active):
            self.active = active
            ntmtools.setDBVar(self.db_conn, "time.active", ntmtools.boolToStrInt(active))
            update_time = True

        if (self.total_sec != total_sec):
            self.total_sec = total_sec
            ntmtools.setDBVar(self.db_conn, "time.total_sec", str(total_sec))

        if (self.auto_disconnect != auto_disconnect):
            self.auto_disconnect = auto_disconnect
            ntmtools.setDBVar(self.db_conn, "time.auto_disconnect", ntmtools.boolToStrInt(auto_disconnect))

        if (self.period_length != period_length):
            self.period_length = period_length
            ntmtools.setDBVar(self.db_conn, "time.period_length", str(int(period_length)))
            update_time = True

        if (self.custom_days != custom_days):
            self.custom_days = custom_days
            ntmtools.setDBVar(self.db_conn, "time.custom_days", str(int(custom_days)))
            if (period_length == 0): update_timeslot = True

        if (self.first_day != first_day):
            self.first_day = first_day
            ntmtools.setDBVar(self.db_conn, "time.first_day", first_day.isoformat())
            update_time = True

        if (self.period_autoupdate != period_autoupdate):
            self.period_autoupdate = period_autoupdate
            ntmtools.setDBVar(self.db_conn, "time.period_autoupdate", ntmtools.boolToStrInt(period_autoupdate))
            if self.period_autoupdate:
                self.update_period(self.now)
            update_time = True

        if (update_time):
            last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
            self.used_sec = MTime.loadTimeUsed(self.db_conn, ntmtools.date_to_datetime_start(self.first_day), ntmtools.date_to_datetime_end(last_day))

        if self.active:
            self.gui_main.show()
            self.update_main_gui()
            self.check_limit()
        else:
            self.gui_main.hide()
    ## - ##


    ## + ##
    def get_main_gui(self):
        if self.gtkb == None:
            self.build_gui()
        self.update_main_gui()
        return self.gui_main
    ## - ##


    ## + ##
    def get_preferences_gui(self):
        if self.gtkb == None:
            self.build_gui()
        self.update_preferences_gui()
        return self.gui_pref
    ## - ##

### - ###

