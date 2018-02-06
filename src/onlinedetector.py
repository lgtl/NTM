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



import globaldef
import ntmtools
from event import Event
import dbus
import gobject
import re
import subprocess


### + ###
class OnlineDetector():

    ## + ##
    # mode: 0-> NetworkManager (ALL); 1-> Ping; 2 -> N.M. Local; 3 -> N.M. Site; 4 -> N.M. Global
    def __init__(self, mode):


            
        self.mode = None

        self.online_event = Event()
        self.offline_event = Event()

        # Active mainloop
        from dbus.mainloop.glib import DBusGMainLoop
        DBusGMainLoop(set_as_default=True)

        # Create object for using system bus from d-bus
        bus = dbus.SystemBus()

        nm_ver = ntmtools.getNMVersion(bus)
        if nm_ver == None:
            nm_ver = "0.8"
        if ntmtools.versionCompare(nm_ver, "0.8.995") < 0:
            self.NTM_MAP_STATE_UNKNOWN = [0]
            self.NTM_MAP_STATE_CONNECTING = [2]
            self.NTM_MAP_STATE_DISCONNECTING = []
            self.NTM_MAP_STATE_CONNECTED = [3]
            self.NTM_MAP_STATE_DISCONNECTED = [1, 4]
        else:
            self.NTM_MAP_STATE_UNKNOWN = [0]
            self.NTM_MAP_STATE_CONNECTING = [40]
            self.NTM_MAP_STATE_DISCONNECTING = [30]
            if mode == 2:
                self.NTM_MAP_STATE_CONNECTED = [50]  # LOCAL
            elif mode == 3:
                self.NTM_MAP_STATE_CONNECTED = [60]  # SITE
            elif mode == 4:
                self.NTM_MAP_STATE_CONNECTED = [70]  # GLOBAL
            else:
                self.NTM_MAP_STATE_CONNECTED = [50, 60, 70]  # LOCAL, SITE, GLOBAL
                
            self.NTM_MAP_STATE_DISCONNECTED = [10, 20]            

        # Handler of StateChanged signal
        bus.add_signal_receiver(self.nm_hStateChanged, dbus_interface="org.freedesktop.NetworkManager", signal_name="StateChanged")

        self.ping_test_url = 'google.com'
        self.check_line = re.compile(r"(\d) received")

        if mode in [0, 2, 3]:
            proxy = bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
            iface = dbus.Interface(proxy, dbus_interface='org.freedesktop.DBus.Properties')
            active_connections = iface.Get('org.freedesktop.NetworkManager', 'ActiveConnections')
            self.online = (len(active_connections) > 0)
        elif mode == 1:
            status = self.get_ping_test()
            self.online = (status)
        else:
            ntmtools.dbgMsg(_("Wrong value for online check mode") + ".\n") 
            self.online = False

        self.changeMode(mode)
    ## - ##

    ## + ##
    def changeMode(self, mode):
        if self.mode != mode:
            self.mode = mode
            if mode == 1:
                gobject.timeout_add(2000, self.ping_test)
    ## - ##

    ## + ##
    def add_online_handler(self, handler):
        self.online_event += handler
    ## - ##

    ## + ##
    def add_offline_handler(self, handler):
        self.offline_event += handler
    ## - ##

    ## + ##
    def set_online(self):
        if not self.online:
            self.online = True
            self.online_event()
    ## - ##

    ## + ##
    def set_offline(self):
        if self.online:
            self.online = False
            self.offline_event()
    ## - ##

    ## + ##
    def nm_hStateChanged(self, new_state):
        if self.mode != 0: return
        
        if new_state in self.NTM_MAP_STATE_UNKNOWN:
            ntmtools.dbgMsg(_("Unknown state") + ": " + str(new_state))
        elif new_state in self.NTM_MAP_STATE_CONNECTING:
            pass
        elif new_state in self.NTM_MAP_STATE_DISCONNECTING:
            pass
        elif new_state in self.NTM_MAP_STATE_CONNECTED:
            self.set_online()
        elif new_state in self.NTM_MAP_STATE_DISCONNECTED:
            self.set_offline()
        else:
            ntmtools.dbgMsg(_("Unknown state") + ": " + str(new_state))
    ## - ##

    ## + ##
    def get_ping_test(self):
        ret = subprocess.call("ping -q -w2 -c1 " + self.ping_test_url,
                        shell=True,
                        stdout=open('/dev/null', 'w'),
                        stderr=subprocess.STDOUT)
        
        if ret == 0:
            return True # Online
        else:
            return False # Offline
    ## - ##

    ## + ##
    def ping_test(self):
        if self.mode != 1: return

        status = self.get_ping_test()        

        if status:
            self.set_online()
        else: 
            self.set_offline()
        
        gobject.timeout_add(2000, self.ping_test)
    ## - ##

    
