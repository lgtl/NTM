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
import cairo
import string

import ntmtools


## + ##
class MTraffic():

    ## + ##
    # ntm: NTM
    # active, auto_disconnect : [True/False]
    # rec_traffic, tra_traffic, traffic_limit : Bytes
    # period_length: 0->Custom Days; 1->Daily; 2->Weekly; 3->Monthly; 4->Yearly;
    # first_day : datetime.date
    def __init__(self, ntm, active, rec_traffic, tra_traffic, traffic_limit, auto_disconnect,
                 period_length, custom_days, first_day, period_autoupdate):
        self.active = active
        self.rec_traffic = rec_traffic
        self.tra_traffic = tra_traffic
        self.traffic_limit = traffic_limit
        self.auto_disconnect = auto_disconnect
        self.period_length = period_length
        self.custom_days = custom_days
        self.first_day = first_day
        self.period_autoupdate = period_autoupdate

        self.ntm = ntm
        self.db_conn = ntm.db_conn
        self.disconnect_handler = ntm.deactiveConnection
        self.gtkb = None

        self.temp_gui_pref_first_day = first_day
        self.last_state = 0
        self.last_rec_traffic = 0
        self.last_tra_traffic = 0
        self.last_speed = 0
        self.disc_msgDialog = False
        self.logTraffic = False
        self.last_update_interval = 1
        self.bwu_max_speed = 50.0*1024  # byte/sec
        self.now = None
    ## - ##


    ## + ##
    def makeFromDb(ntm):
        conn = ntm.db_conn

        res = ntmtools.readDBVar(conn, "traffic.active")  # 0:Disable; Other:Enable;
        try:
            active = (int(res) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'traffic.active' " + _("or is not stored. Default value") + " '1'")
            ntmtools.setDBVar(conn, "traffic.active", "1")
            active = True

        res = ntmtools.readDBVar(conn, "traffic.limit")  # bytes
        try:
            traffic_limit = float(res)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'traffic.limit' " + _("or is not stored. Default value") + " '98MB'")
            ntmtools.setDBVar(conn, "traffic.limit", str(98*1024*1024))
            traffic_limit = 98*1024*1024

        res = ntmtools.readDBVar(conn, "traffic.auto_disconnect")  # 0:Disable; Other:Enable;
        try:
            auto_disconnect = (int(res) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'traffic.auto_disconnect' " + _("or is not stored. Default value") + " '1'")
            ntmtools.setDBVar(conn, "traffic.auto_disconnect", "1")
            auto_disconnect = True

        val_str = ntmtools.readDBVar(conn, "traffic.period_length")
        try:
            period_length = int(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'traffic.period_length' " + _("or is not stored. Default value") + " '" + _("Daily") + "'")
            period_length = 0  # 0 -> Daily
            ntmtools.setDBVar(conn, "traffic.period_length", str(int(period_length)))

        val_str = ntmtools.readDBVar(conn, "traffic.custom_days")
        try:
            custom_days = int(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'traffic.custom_days' " + _("or is not stored. Default value") + " 30")
            custom_days = 30
            ntmtools.setDBVar(conn, "traffic.custom_days", str(int(custom_days)))

        val_str = ntmtools.readDBVar(conn, "traffic.first_day")
        try:
            first_day = ntmtools.strToDate(val_str)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'traffic.first_day' " + _("or is not stored. Default value") + " '2009-10-01'")
            first_day = datetime.date(2009, 10, 01)
            ntmtools.setDBVar(conn, "traffic.first_day", first_day)

        val_str = ntmtools.readDBVar(conn, "traffic.period_autoupdate")
        try:
            period_autoupdate = (ntmtools.strToInt(val_str, 1) != 0)
        except:
            ntmtools.dbgMsg(_("Wrong value for the param") + " 'traffic.period_autoupdate' " + _("or is not stored. Default value") + " '" + _("True") + "'")
            period_autoupdate = True
            ntmtools.setDBVar(conn, "traffic.period_autoupdate", "1")

        last_day = ntmtools.get_last_day(first_day, period_length, custom_days)
        ret = MTraffic.loadTraffic(conn, first_day, last_day)

        return MTraffic(ntm, active, ret[0], ret[1], traffic_limit, auto_disconnect, period_length, custom_days, first_day, period_autoupdate)
    makeFromDb = staticmethod(makeFromDb)
    ## - ##


    ## + ##
    # start_period, end_period: Date
    # return (traffic_Rec_Used, traffic_Tra_Used) : in bytes
    def loadTraffic(conn, start_period, end_period):
        # print("loadTraffic(conn, start_period, end_period)")
        if conn == None:
            print(_('Error in NtmTraffic.loadTraffic: conn is None.'))
            return

        c = conn.cursor()
        rows = c.execute("select * from dailytraffic where date>=? AND date<=?",
                         (start_period, end_period) )

        # print("start_period, end_period = {0} - {1}".format(start_period, end_period))
        trafficRecUsed = 0
        trafficTraUsed = 0

        for r in rows:
            # print("r={0}".format(r))
            # print("r[1]={0} - r[2]={1}".format(r[1], r[2]))
            try:
                # (date, recBytes, traBytes)
                trafficRecUsed += r[1]
                trafficTraUsed += r[2]
            except:
                ntmtools.dbgMsg("Error: NtmTraffic.loadTraffic; some erros in the dailytraffic table.")
            # print("trafficRecUsed, trafficTraUsed = {0} - {1}".format(trafficRecUsed, trafficTraUsed))

        return (trafficRecUsed, trafficTraUsed)
    loadTraffic = staticmethod(loadTraffic)
    ## - ##


    ## + ##
    def reloadTraffic(self):
        print("reloadTraffic(self)")
        last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
        ret = MTraffic.loadTraffic(self.db_conn, self.first_day, last_day)
        print("Days: {0} - {1}".format(self.first_day, last_day))
        print("Traffic : {0}".format(ret))
        self.rec_traffic = ret[0]
        self.tra_traffic = ret[1]
        self.update_main_gui()
    ## - ##


    ## + ##
    # timestamp : (datetime.datetime)
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
                ntmtools.setDBVar(self.db_conn, "traffic.first_day", self.first_day.isoformat())
                ret = MTraffic.loadTraffic(self.ntm.db_conn, self.first_day, last_day)
                self.rec_traffic = ret[0]
                self.tra_traffic = ret[1]

            return True
        else:
            return (date_timestamp <= last_day)
    ## - ##


    ## + ##
    # timestamp : Time of update [datetime.datetime]; session_start:[datetime.datetime]; update_interval : sec
    # last_rec_traffic, last_tra_traffic : Generated traffic from last update in bytes
    # conn_state : 0 -> offline; 1 -> online
    def update_h(self, timestamp, session_start, update_interval, last_rec_traffic, last_tra_traffic, conn_state):
        #print('update_h(self, {0}, {1}, {2}, {3})\n'.format(timestamp, last_rec_traffic, last_tra_traffic, conn_state))

        if (not self.active): return

        self.now = timestamp
        if not self.update_period(session_start): return

        if (self.last_state == 0):
            if (conn_state == 1):
                last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
                ret = MTraffic.loadTraffic(self.db_conn, self.first_day, last_day)
                self.rec_traffic = ret[0]
                self.tra_traffic = ret[1]
        else:
            self.rec_traffic += last_rec_traffic
            self.tra_traffic += last_tra_traffic
            if (conn_state == 1):
                self.last_rec_traffic = last_rec_traffic
                self.last_tra_traffic = last_tra_traffic
            else:
                self.last_rec_traffic = 0
                self.last_tra_traffic = 0

        self.last_state = conn_state
        self.last_update_interval = update_interval

        self.last_speed = (self.last_rec_traffic + self.last_tra_traffic) / self.last_update_interval
        self.update_main_gui()

        if self.logTraffic:
            speed = (last_rec_traffic + last_tra_traffic) / update_interval / 1024
            total = (self.rec_traffic + self.tra_traffic) / 1024
            if speed == 0: bar = '|'
            else: bar = '#' * (1 + int(speed))
            print(
                '{0}\t{1}\t{2}\t{3:.3f}\t\t'.
                    format( total/1024, self.last_rec_traffic / 1024, self.last_tra_traffic / 1024, speed) + bar
            )

        self.check_limit()
    ## - ##


    ## + ##
    def check_limit(self):
        if (not self.active): return

        total = self.rec_traffic + self.tra_traffic
        if (total >= self.traffic_limit) and (self.last_state == 1):
            # print("bbb")
            # self.last_speed = 0
            # self.update_main_gui()
            if not self.disc_msgDialog:
                self.disc_msgDialog = True
                last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
                if self.auto_disconnect:
                    msg = _('Traffic Limit Reached') + ", {0}".format(ntmtools.formatBytes(self.traffic_limit)) + ". " + _("Disconnection is done") + "!!\n" + _("Period: {0} to {1}").format(self.first_day.isoformat(), last_day.isoformat())
                    if self.disconnect_handler != None:
                        self.disconnect_handler()
                else:
                    msg = _('Traffic Limit Reached') + ", {0}".format(ntmtools.formatBytes(self.traffic_limit)) + ".\n" + _('Period: {0} to {1}').format(self.first_day.isoformat(), last_day.isoformat())

                if self.logTraffic: print(msg)

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
        self.gtkb.add_from_file("mtraffic.gui")
        gtkb = self.gtkb

        ## Main
        self.gui_main = gtkb.get_object("main")
        if self.active: self.gui_main.show()
        else: self.gui_main.hide()
        self.gui_main_per = gtkb.get_object("main_per") # label
        self.gui_main_used = gtkb.get_object("trafficFrame_allUsed")
        self.gui_main_in = gtkb.get_object("trafficFrame_in")
        self.gui_main_out = gtkb.get_object("trafficFrame_out")
        self.gui_main_left = gtkb.get_object("trafficFrame_allLeft")
        self.gui_main_total = gtkb.get_object("trafficFrame_allTotal")
        self.gui_main_period = gtkb.get_object("trafficFrame_period")


        # Bandwidth Usage
        gui_main_container_bwu = gtkb.get_object("main_container_bwu")
        self.gui_main_bwu = BandWidthUsage()
        self.gui_main_bwu.show()
        gui_main_container_bwu.add(self.gui_main_bwu)
        ##

        ## Preferences
        self.gui_pref = gtkb.get_object("preferences")
        self.gui_pref_active = gtkb.get_object("pref_active")

        self.gui_pref_limit = gtkb.get_object("pref_limit")
        self.gui_pref_limit.set_range(1, 999999)
        self.gui_pref_limit.set_increments(1, 10)

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
        ##

        ## Date Dialog
        self.gui_date_dialog = gtkb.get_object("date_dialog")
        self.gui_date_dialog.connect("delete_event", self.date_dialog_hdelete)
        self.gui_date_dialog_title = gtkb.get_object("date_dialog_title")
        self.gui_date_dialog_calendar = gtkb.get_object("date_dialog_calendar")
        self.gui_date_dialog_calendar.select_month(self.first_day.month-1, self.first_day.year)
        self.gui_date_dialog_calendar.select_day(self.first_day.day)
        self.temp_gui_pref_first_day = self.first_day

        ## i18n
        ntmtools.translate_control_markup(gtkb.get_object("date_dialog_title"))
        ntmtools.translate_control_label(gtkb.get_object("dateWindow_cancelButton"))
        ntmtools.translate_control_label(gtkb.get_object("dateWindow_okButton"))
        ntmtools.translate_control_markup(gtkb.get_object("label2"))
        ntmtools.translate_control_markup(gtkb.get_object("label3"))
        ntmtools.translate_control_markup(gtkb.get_object("label5"))
        ntmtools.translate_control_markup(gtkb.get_object("label6"))
        ntmtools.translate_control_markup(gtkb.get_object("trafficFrame_dim"))
        ntmtools.translate_control_markup(gtkb.get_object("label4"))
        ntmtools.translate_control_markup(gtkb.get_object("label8"))
        ntmtools.translate_control_markup(gtkb.get_object("trafficFrame_topLabel"))
        ntmtools.translate_control_label(gtkb.get_object("pref_active"))
        ntmtools.translate_control_text(gtkb.get_object("pref_label6"))
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
        self.gui_date_dialog_title.set_markup("<b>" + _("First Day") + "</b>")
        result = self.gui_date_dialog.run()
        if result == 1:
            dSel = self.gui_date_dialog_calendar.get_date()
            self.temp_gui_pref_first_day = datetime.date(dSel[0], dSel[1] + 1, dSel[2])
            self.gui_pref_first_day.set_label(self.temp_gui_pref_first_day.isoformat())
        self.gui_date_dialog.hide()
    ## - ##


    ## traf_in, traf_out, limit: byte; speed: byte/sec; autoDisconnect: boolean ##
    def update_main_gui(self):
        # print("mtraffic.update_main_gui(self)")
        if self.gtkb == None:
            print("MTraffic.update_main_gui(*): Gui not builded.\n")
            return

        mbyte = (1024.0*1024.0)
        traf_tot = (self.rec_traffic + self.tra_traffic)

        per = 100.0 * traf_tot / self.traffic_limit

        self.gui_main_left.set_text("{0:.3f}".format((self.traffic_limit - traf_tot)/mbyte))
        self.gui_main_used.set_text("{0:.3f}".format(traf_tot/mbyte))
        self.gui_main_in.set_text("{0:.3f}".format(self.rec_traffic / mbyte))
        self.gui_main_out.set_text("{0:.3f}".format(self.tra_traffic / mbyte))

        self.gui_main_total.set_text("{0:.0f}".format(self.traffic_limit/mbyte))

        if self.last_speed != None:
            while self.last_speed > self.bwu_max_speed:
                self.bwu_max_speed = self.bwu_max_speed + 10.0
            self.gui_main_bwu.speed = self.last_speed
            self.gui_main_bwu.max_speed = self.bwu_max_speed
            self.gui_main_bwu.queue_draw()

        last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)

        if self.now != None:
            period_len_total = ntmtools.timedelta2sec(ntmtools.date_to_datetime_end(last_day) - ntmtools.date_to_datetime_start(self.first_day))
            period_len_used = ntmtools.timedelta2sec(self.now - ntmtools.date_to_datetime_start(self.first_day))
            if period_len_used != 0: estimate_str = ntmtools.formatBytes(traf_tot * period_len_total / period_len_used)
            else: estimate_str = "--"
        else: estimate_str = "--"

        self.gui_main_per.set_markup("<small>({0:.1f}%) [{1}]</small>".format(per, estimate_str))

        self.gui_main_period.set_markup("<small><small>" + _("Period") + ": {0} - {1}</small></small>".format(self.first_day, last_day))
    ## - ##


    ## + ##
    def getSummaryMessage(self):
        traf_tot = (self.rec_traffic + self.tra_traffic)        
        return _("Used {0} of {1}").format(ntmtools.formatBytes(traf_tot), ntmtools.formatBytes(self.traffic_limit))
    ## - ##


    ## + ##
    def update_preferences_gui(self):
        if self.gtkb == None:
            print("MTraffic.update_preferences_gui(*): Gui not builded.\n")
            return

        self.gui_pref_active.set_active(self.active)
        self.gui_pref_limit.set_value(int(self.traffic_limit/1024/1024))
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
            print("MTraffic.update_preferences_gui(*): Gui not builded.\n")
            return

        active = self.gui_pref_active.get_active()
        traffic_limit = self.gui_pref_limit.get_value() * 1024 * 1024
        auto_disconnect = self.gui_pref_auto_disconnect.get_active()
        period_length = self.gui_pref_period_length.get_active()
        custom_days = self.gui_pref_days.get_value()
        period_autoupdate = self.gui_pref_period_autoupdate.get_active()

        self.setPreferences(active, traffic_limit, auto_disconnect, period_length, custom_days, self.temp_gui_pref_first_day, period_autoupdate)
    ## - ##


    ## + ##
    def setPreferences(self, active, traffic_limit, auto_disconnect, period_length, custom_days, first_day, period_autoupdate):
        #print("mtraffic.setPreferences({0},{1},{2},{3},{4})\n".format(active, traffic_limit, auto_disconnect, period_length, first_day))
        update = False
        if (self.active != active):
            self.active = active
            ntmtools.setDBVar(self.db_conn, "traffic.active", ntmtools.boolToStrInt(active))
            update = True

        if (self.traffic_limit != traffic_limit):
            self.traffic_limit = traffic_limit
            ntmtools.setDBVar(self.db_conn, "traffic.limit", str(int(traffic_limit)))
            update = True

        if (self.auto_disconnect != auto_disconnect):
            self.auto_disconnect = auto_disconnect
            ntmtools.setDBVar(self.db_conn, "traffic.auto_disconnect", ntmtools.boolToStrInt(auto_disconnect))

        update_traffic = False
        if (self.period_length != period_length):
            self.period_length = period_length
            ntmtools.setDBVar(self.db_conn, "traffic.period_length", str(int(period_length)))
            update_traffic = True

        if (self.custom_days != custom_days):
            self.custom_days = custom_days
            ntmtools.setDBVar(self.db_conn, "traffic.custom_days", str(int(custom_days)))
            update_traffic = True

        if (self.first_day != first_day):
            self.first_day = first_day
            ntmtools.setDBVar(self.db_conn, "traffic.first_day", first_day.isoformat())
            update_traffic = True

        if (self.period_autoupdate != period_autoupdate):
            self.period_autoupdate = period_autoupdate
            ntmtools.setDBVar(self.db_conn, "traffic.period_autoupdate", ntmtools.boolToStrInt(period_autoupdate))
            if self.period_autoupdate:
                self.update_period(self.now)
                update_traffic = True

        if update_traffic:
            last_day = ntmtools.get_last_day(self.first_day, self.period_length, self.custom_days)
            ret = MTraffic.loadTraffic(self.db_conn, self.first_day, last_day)
            self.rec_traffic = ret[0]
            self.tra_traffic = ret[1]
            update = True

        if update:
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


    ## + ##
    def to_string(self):
        return ('active:{0}; rec_traffic:{1}; tra_traffic:{2}; traffic_limit:{3}; auto_disconnect:{4}; period_length:{5}; custom_days:{6}; first_day:{7}; period_autoupdate:{8}'.
               format(self.active, self.rec_traffic, self.tra_traffic, self.traffic_limit, self.auto_disconnect,
                      self.period_length, self.custom_days, self.first_day, self.period_autoupdate))
    ## - ##
## - MTraffic ##


## + ##
class BandWidthUsage(gtk.DrawingArea):

    ## + ##
    def __init__(self):
        super(BandWidthUsage, self).__init__()

        # Draw in response to an expose-event
        self.connect("expose_event", self.expose)

        self.speed = 0.0
        self.max_speed = 1.0


    ## + ##
    def expose(self, widget, event):
        context = widget.window.cairo_create()

        # set a clip region for the expose event
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()

        self.draw(context, *self.window.get_size())

        return False


    ## + ##
    def draw(self, cr, width, height):
        # Fill the background with gray
        cr.set_source_rgb(0.9, 0.92, 0.92)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        # Fill the bar
        cr.set_source_rgb(1.0, 0.47, 0.0)
        rap = (0.0 + self.speed) / self.max_speed
        len = rap * (width - 4)
        cr.rectangle(2, 2, len, height - 4)
        cr.fill()

        cr.set_line_width(1.0)
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, width, height)
        cr.stroke()


        # Write speed
        cr.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.set_font_size(14)
        cr.move_to(8, 14)
        cr.show_text(ntmtools.formatBytes(self.speed) + "/s")
    ## - ##

## - BandWidthUsage ##

