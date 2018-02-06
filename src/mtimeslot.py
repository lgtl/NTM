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
import time
import datetime
import gtk
import pynotify

import ntmtools
from monthdelta import monthdelta

### + ###
class MTimeSlot():

    ## + ##
    # ntm: NTM
    # tsTime and slotLength in seconds. startPeriod, endPeriod: datetime.date
    # tsTime : time used in the current slot
    def __init__(self, ntm, active, slotsUsed, totalSlots, tsTime, slotLength, auto_disconnect,
                 period_length, custom_days, first_day, period_autoupdate):

        self.ntm = ntm
        self.active = active
        self.slotsUsed = slotsUsed
        self.totalSlots = totalSlots
        self.tsTime = tsTime
        self.slotLength = slotLength
        self.auto_disconnect = auto_disconnect
        self.period_length = period_length
        self.custom_days = custom_days
        self.first_day = first_day
        self.period_autoupdate = period_autoupdate

        self.db_conn = ntm.db_conn
        self.disconnect_handler = ntm.deactiveConnection
        self.gtkb = None

        self.temp_gui_pref_first_day = first_day
        self.last_state = 0
        self.connStartTime = 0
        self.tsStartTime = None
        self.now = None
        self.logUpdate = False
        self.disc_msgDialog = False


        self.notify_ok = pynotify.init ("summary-body")
        if self.notify_ok:
            self.notify_new_slot = pynotify.Notification (_("NTM - Time Slot"), _("An additional slot was used"))

        # print(self.toStr()+"\n")
    ## - ##


    ## + ##
    def makeFromDb(ntm):
        conn = ntm.db_conn

        val_str = ntmtools.readDBVar(conn, "time_slot.active")
        try:
            active = (ntmtools.strToInt(val_str, 1) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time_slot.active' " + _("or is not stored. Default value") + " '" + _("True") + "'")
            active = True
            ntmtools.setDBVar(conn, "time_slot.active", "1")

        val_str = ntmtools.readDBVar(conn, "time_slot.total_slots")
        try:
            total_slots = ntmtools.strToInt(val_str, 200)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time_slot.total_slots' " + _("or is not stored. Default value") + " '200'")
            total_slots = 200
            ntmtools.setDBVar(conn, "time_slot.total_slots", total_slots)

        val_str = ntmtools.readDBVar(conn, "time_slot.slot_length")
        try:
            slot_length = ntmtools.strToInt(val_str, 15*60)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time_slot.slot_length' " + _("or is not stored. Default value") + " 15'")
            slot_length = 15*60
            ntmtools.setDBVar(conn, "time_slot.slot_length", slot_length)

        val_str = ntmtools.readDBVar(conn, "time_slot.auto_disconnect")
        try:
            auto_disconnect = (ntmtools.strToInt(val_str, 1) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time_slot.auto_disconnect' " + _("or is not stored. Default value") + " '" + _("True") + "'")
            auto_disconnect = True
            ntmtools.setDBVar(conn, "time_slot.auto_disconnect", "1")


        val_str = ntmtools.readDBVar(conn, "time_slot.period_length")
        try:
            period_length = int(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time_slot.period_length' " + _("or is not stored. Default value") + " '" + _("Month") + "'")
            period_length = 3  # 3 -> Month
            ntmtools.setDBVar(conn, "time_slot.period_length", str(int(period_length)))

        val_str = ntmtools.readDBVar(conn, "time_slot.custom_days")
        try:
            custom_days = int(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time_slot.custom_days' " + _("or is not stored. Default value") + " 30")
            custom_days = 30
            ntmtools.setDBVar(conn, "time_slot.custom_days", str(int(custom_days)))

        val_str = ntmtools.readDBVar(conn, "time_slot.first_day")
        try:
            first_day = ntmtools.strToDate(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time_slot.first_day' " + _("or is not stored. Default value") + " '2009-10-01'")
            first_day = datetime.date(2009, 10, 01)
            ntmtools.setDBVar(conn, "time_slot.first_day", first_day)

        val_str = ntmtools.readDBVar(conn, "time_slot.period_autoupdate")
        try:
            period_autoupdate = (ntmtools.strToInt(val_str, 1) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'time_slot.period_autoupdate' " + _("or is not stored. Default value") + " '" + _("True") + "'")
            period_autoupdate = True
            ntmtools.setDBVar(conn, "time_slot.period_autoupdate", "1")


        last_day = ntmtools.get_last_day(first_day, period_length, custom_days)
        ret = MTimeSlot.loadSessions(conn, ntmtools.date_to_datetime_start(first_day), ntmtools.date_to_datetime_end(last_day), slot_length)
        slots_used  = ret[0]
        ts_time = ret[1]

        return MTimeSlot(ntm, active, slots_used, total_slots, ts_time, slot_length, auto_disconnect, period_length, custom_days, first_day, period_autoupdate)
    makeFromDb = staticmethod(makeFromDb)
    ## - ##


    ## + ##
    # return t(slotsUsed, timeUsedInLastSlot:sec)
    def loadSessions(db_conn, start_period, end_period, slot_length):
        c = db_conn.cursor()
        rows = c.execute("select * from session where start>=? AND start<=?",
                         (start_period, end_period) )

        slotsUsed = 0
        len = 0
        time = 0

        for r in rows:
            try:
                tsStart = datetime.datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
                tsEnd = datetime.datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S")
                diff = tsEnd - tsStart
                len = diff.days*86400 + diff.seconds
            except:
                ntmtools.dbgMsg(_("Error in the session table. Row:") + " {0} .\n".format(str(r)))
                len = 0

            slotsUsed += int(len / slot_length)
            time = (len % slot_length)
            if time > 0:
                slotsUsed += 1

        return (slotsUsed, time)
    loadSessions = staticmethod(loadSessions)
    ## - ##

    
    ## + ##
    def reloadSessions(self):
        last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
        ret = MTimeSlot.loadSessions(self.db_conn, ntmtools.date_to_datetime_start(self.first_day), ntmtools.date_to_datetime_end(last_day), self.slotLength)
        self.slotsUsed = ret[0]
        self.tsTime = ret[1]
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
                ntmtools.setDBVar(self.db_conn, "time_slot.first_day", self.first_day.isoformat())
                ret = MTimeSlot.loadSessions(self.db_conn, ntmtools.date_to_datetime_start(self.first_day), ntmtools.date_to_datetime_end(last_day), self.slotLength)
                self.slotsUsed = ret[0]
                self.tsTime = ret[1]

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
            if (conn_state == 1):
                self.slotsUsed += 1
                self.tsTime = 0
                self.connStartTime = timestamp
                self.tsStartTime = self.connStartTime
        self.last_state = conn_state

        if self.tsStartTime != None:
            diff = ntmtools.timedelta2sec(self.now - self.tsStartTime)
        else: diff = 0
        new_slots = 0
        while diff >= self.slotLength:
            self.slotsUsed += 1
            diff -= self.slotLength
            new_slots += 1

        if new_slots > 0:
            if self.notify_ok:
                self.notify_new_slot.show ()

        self.tsStartTime = self.now - datetime.timedelta(seconds=diff)
        self.tsTime = diff

        self.update_main_gui()

        if self.logUpdate:
            print(_('Timeslot:') + ' {0}/{1}\t{2}"/{3}"\n'.
                format( self.slotsUsed, self.totalSlots, self.tsTime, self.slotLength)
            )

        self.check_limit()
    ## - ##


    ## + ##
    def check_limit(self):
        if (not self.active): return

        if ((self.slotsUsed > self.totalSlots) or
           ( (self.slotsUsed == self.totalSlots) and (self.tsTime + 10 >= self.period_length) )):
            if (self.last_state == 1) and (not self.disc_msgDialog):
                self.disc_msgDialog = True
                last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
                if self.auto_disconnect:
                    msg = _('Timeslot Limit Reached') + ", {0}. ".format(self.totalSlots) + _('Disconnection is done!!') + "\n" + _("Period") + (_(": {0} to {1}")).format(self.first_day.isoformat(), last_day.isoformat())
                    if self.disconnect_handler != None:
                        self.disconnect_handler()
                else:
                    msg = _('Timeslot Limit Reached') + ", {0}. ".format(self.totalSlots) + '\n' + _("Period") + (_(": {0} to {1}")).format(self.first_day.isoformat(), last_day.isoformat())

                dialog = gtk.Dialog(
                    "NTM - Message", None,
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
        self.gtkb.add_from_file("mtimeslot.gui")
        gtkb = self.gtkb

        ## Main
        self.gui_main = gtkb.get_object("main")
        if self.active: self.gui_main.show()
        else: self.gui_main.hide()
        self.gui_main_per = gtkb.get_object("timeSlot_topLabel2")
        self.gui_main_slots_used = gtkb.get_object("label_slots_used")
        self.gui_main_slots_left = gtkb.get_object("label_slots_left")
        self.gui_main_slots_total = gtkb.get_object("label_slots_total")
        self.gui_main_thisSlot_timeUsed = gtkb.get_object("label_thisSlot_timeUsed")
        self.gui_main_thisSlot_timeLeft = gtkb.get_object("label_thisSlot_timeLeft")
        self.gui_main_thisSlot_timeTotal = gtkb.get_object("label_thisSlot_timeTotal")
        self.gui_main_period = gtkb.get_object("timeSlotFrame_period")
        # #

        # Preferences #
        self.gui_pref = gtkb.get_object("preferences")
        self.gui_pref_timeSlot_active = gtkb.get_object("pref_timeSlot_active")

        self.gui_pref_totalSlots = gtkb.get_object("pref_totalSlots")
        self.gui_pref_totalSlots.set_range(1, 999999)
        self.gui_pref_totalSlots.set_increments(1, 10)

        self.gui_pref_slotLength = gtkb.get_object("pref_slotLength")
        self.gui_pref_slotLength.set_range(1, 999999)
        self.gui_pref_slotLength.set_increments(1, 10)

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

        ## i18n
        ntmtools.translate_control_markup(gtkb.get_object("label1"))
        ntmtools.translate_control_markup(gtkb.get_object("label2"))
        ntmtools.translate_control_markup(gtkb.get_object("label4"))
        ntmtools.translate_control_markup(gtkb.get_object("label5"))
        ntmtools.translate_control_markup(gtkb.get_object("label6"))
        ntmtools.translate_control_markup(gtkb.get_object("timeSlot_topLabel"))

        ntmtools.translate_control_markup(gtkb.get_object("date_dialog_title"))
        ntmtools.translate_control_label(gtkb.get_object("date_dialog_cancelButton"))
        ntmtools.translate_control_label(gtkb.get_object("date_dialog_okButton"))

        ntmtools.translate_control_label(gtkb.get_object("pref_timeSlot_active"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label5"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label10"))
        ntmtools.translate_control_label(gtkb.get_object("pref_auto_disconnect"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label12"))
        ntmtools.translate_control_label(gtkb.get_object("pref_period_autoupdate"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label1"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label2"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label_days"))
        ntmtools.translate_control_markup(gtkb.get_object("title"))

    ## - ##


    ## + ##
    def date_dialog_hdelete(self, widget, event, data=None):
        self.gui_date_dialog.hide()
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
    def gui_pref_first_day_hclicked(self, data = None):
        self.gui_date_dialog_title.set_markup("<b>First Day</b>")
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
            print("MTimeSlot.update_main_gui(): " + _("Gui not builded") + ".\n")
            return

        self.gui_main_slots_used.set_text(str(self.slotsUsed))
        self.gui_main_slots_left.set_text(str(self.totalSlots - self.slotsUsed))
        self.gui_main_slots_total.set_text(str(self.totalSlots))

        self.gui_main_thisSlot_timeUsed.set_text(ntmtools.formatTime(self.tsTime))
        secLeft = self.slotLength - self.tsTime
        self.gui_main_thisSlot_timeLeft.set_text(ntmtools.formatTime(secLeft))
        self.gui_main_thisSlot_timeTotal.set_text(ntmtools.formatTime(self.slotLength))

        totalSec = self.totalSlots * self.slotLength
        per = 100.0 * (self.slotsUsed * self.slotLength - secLeft) / totalSec

        last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)

        if self.now != None:
            period_len_total = ntmtools.timedelta2sec(ntmtools.date_to_datetime_end(last_day) - ntmtools.date_to_datetime_start(self.first_day))
            period_len_used = ntmtools.timedelta2sec(self.now - ntmtools.date_to_datetime_start(self.first_day))
            if period_len_used != 0:
                estimate = self.slotsUsed * period_len_total / period_len_used
                estimate_str = '{0}sl.'.format(int(round(estimate)))
            else: estimate_str = "--"
        else: estimate_str = "--"

        self.gui_main_per.set_markup("<small>({0:.1f}%) [{1}]</small>".format(per, estimate_str))

        self.gui_main_period.set_markup(
            "<small><small>" + _("Period") + ": {0} - {1}</small></small>".format(self.first_day, last_day)
        )
    ## - ##


    ## + ##
    def getSummaryMessage(self):
        return _("Used {0} of {1}").format(self.slotsUsed, self.totalSlots) + " " + _("slots")
    ## - ##


    ## + ##
    def update_preferences_gui(self):
        if self.gtkb == None:
            print("MTimeSlot.update_preferences_gui(*): " + _("Gui not builded.\n"))
            return

        self.gui_pref_timeSlot_active.set_active(self.active)
        self.gui_pref_totalSlots.set_value(int(round(self.totalSlots)))
        self.gui_pref_slotLength.set_value(int(round(self.slotLength / 60)))
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
            print("MTimeSlot.update_preferences_gui(*): " + _("Gui not builded.\n"))
            return

        active = self.gui_pref_timeSlot_active.get_active()
        totalSlots = int(round(self.gui_pref_totalSlots.get_value()))
        slotLength = int(round(self.gui_pref_slotLength.get_value() * 60))
        auto_disconnect = self.gui_pref_auto_disconnect.get_active()
        period_length = self.gui_pref_period_length.get_active()
        custom_days = self.gui_pref_days.get_value()
        period_autoupdate = self.gui_pref_period_autoupdate.get_active()

        self.setPreferences(active, totalSlots, slotLength, auto_disconnect, period_length, custom_days, self.temp_gui_pref_first_day, period_autoupdate)
    ## - ##


    ## + ##
    def setPreferences(self, active, totalSlots, slotLength, auto_disconnect, period_length, custom_days, first_day, period_autoupdate):
        update_timeslot = False
        if (self.active != active):
            self.active = active
            ntmtools.setDBVar(self.db_conn, "time_slot.active", ntmtools.boolToStrInt(active))
            update_timeslot = True

        if (self.totalSlots != totalSlots):
            self.totalSlots = totalSlots
            ntmtools.setDBVar(self.db_conn, "time_slot.total_slots", str(int(totalSlots)))

        if (self.slotLength != slotLength):
            self.slotLength = slotLength
            ntmtools.setDBVar(self.db_conn, "time_slot.slot_length", str(int(slotLength)))
            update_timeslot = True

        if (self.auto_disconnect != auto_disconnect):
            self.auto_disconnect = auto_disconnect
            ntmtools.setDBVar(self.db_conn, "time_slot.auto_disconnect", ntmtools.boolToStrInt(auto_disconnect))
            update_timeslot = True

        if (self.period_length != period_length):
            self.period_length = period_length
            ntmtools.setDBVar(self.db_conn, "time_slot.period_length", str(int(period_length)))
            update_timeslot = True

        if (self.custom_days != custom_days):
            self.custom_days = custom_days
            ntmtools.setDBVar(self.db_conn, "time_slot.custom_days", str(int(custom_days)))
            if (period_length == 0): update_timeslot = True

        if (self.first_day != first_day):
            self.first_day = first_day
            ntmtools.setDBVar(self.db_conn, "time_slot.first_day", first_day.isoformat())
            update_timeslot = True

        if (self.period_autoupdate != period_autoupdate):
            self.period_autoupdate = period_autoupdate
            ntmtools.setDBVar(self.db_conn, "time_slot.period_autoupdate", ntmtools.boolToStrInt(period_autoupdate))
            if self.period_autoupdate:
                self.update_period(self.now)
                update_timeslot = True

        if (update_timeslot):
            last_day = ntmtools.get_last_day(first_day, period_length, custom_days)
            ret = MTimeSlot.loadSessions(self.db_conn, ntmtools.date_to_datetime_start(first_day), ntmtools.date_to_datetime_end(last_day), slotLength)
            self.slotsUsed = ret[0]
            self.tsTime = ret[1]

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

