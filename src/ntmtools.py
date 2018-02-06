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



import math
import time
import datetime
import platform
import os
import string
from monthdelta import monthdelta
import commands
import subprocess
import dbus


GNOME_AUTORUN_TYPE_DES = ["gnome", "ubuntu", "ubuntu-2d", "xfce", "lxde"] 
KDE_AUTORUN_TYPE_DES = ["kde"]

## + ##
def getNMVersion(bus):
    version = None
    
    proxy = bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
    iface = dbus.Interface(proxy, dbus_interface='org.freedesktop.DBus.Properties')

    try:
        version = iface.Get('org.freedesktop.NetworkManager', 'Version')
    except:
        version = "0.8.3"
    
    return version
## - ##


### return = 0:ugual; 1:ver1>ver2; -1:ver1<ver2 ###
def versionCompare(ver1, ver2):
    sv1 = string.split(ver1, '.')
    sv2 = string.split(ver2, '.')

    if len(sv2) > len(sv1):
        min = len(sv1)
    else:
        min = len(sv2)

    i = 0
    while i < min:
        val1 = int(sv1[i])
        val2 = int(sv2[i])

        if val1 > val2: return 1
        if val1 < val2: return -1
        i += 1

    if len(sv1) > len(sv2): return 1
    elif len(sv1) < len(sv2):   return -1
    else: return 0
### - ###

import globaldef


## get the bytes value then return a string with a compact representation (ex.
##  '123 bytes', '1.234 KiB', '12.51 MiB', '123.4 GiB')
def formatBytes(val):
    tv = 1024.0
    if (val < tv):
        return "{0} bytes".format(int(val))
    tv *= 1024.0
    if (val < tv):
        val2 = 1024.0 * val / tv
        if val2 < 10: return "{0:.3f} KiB".format(val2)
        elif val2 < 100: return "{0:.2f} KiB".format(val2)
        else: return "{0:.1f} KiB".format(val2)
    tv *= 1024.0
    if (val < tv): 
        val2 = 1024.0 * val / tv
        if val2 < 10: return "{0:.3f} MiB".format(val2)
        elif val2 < 100: return "{0:.2f} MiB".format(val2)
        else: return "{0:.1f} MiB".format(val2)
    val2 = 1.0 * val / tv
    if val2 < 10: return "{0:.3f} GiB".format(val2)
    elif val2 < 100: return "{0:.2f} GiB".format(val2)
    else: return "{0:.1f} GiB".format(val2)
## end-def ##


## get the seconds then return a string with a compact representation (ex.
##  ' 13" ', ' 2'34" ', ' 3h2'1" ')
def formatTime(val):
    (h, m, s) = sec_to_hms(val)
    if h>0: return "{0}h{1}\'{2}\"".format(h, m, s)
    elif m>0: return "{0}'{1}\"".format(m, s)
    else: return "{0}\"".format(s)
## end-def ##


## get the timedelta then return a string with a compact representation (ex.
##  ' 13" ', ' 2'34" ', ' 3h2'1" ')
def formatTime_td(timedelta_val):
    return formatTime(timedelta2sec(timedelta_val))
## end-def ##


## get the seconds then return (hour, minute, sec)
def sec_to_hms(tot_sec):
    ival = int(round(tot_sec))
    s = ival % 60
    ival = math.trunc(ival / 60)
    m = ival % 60
    ival = math.trunc(ival / 60)
    h = ival
    return (h, m, s)
## end-def ##


## + ##
def timedelta2sec(val):
    return val.days * (24*60*60) + val.seconds + int(round(0.000001*val.microseconds))
## end-def ##


## + ##
def readDBVar(conn, name):
    c = conn.cursor()
    c.execute("select * from vars where name=?", (name,))
    r = c.fetchone()
    if r != None: return r[1]
    else: return None
## end-def ##


## + ##
def setDBVar(conn, name, val, commit=True):
    if readDBVar(conn, name) == None:
        conn.execute("insert into vars values (?, ?)", (name, val) )
    else:
        conn.execute("update vars set value=? where name=?", (val, name) )
    if commit: conn.commit()
## end-def ##

## + ##
# str ex. "2010-06-19"
def strToDate(str):
    ris = time.strptime(str, "%Y-%m-%d")
    return datetime.date(ris.tm_year, ris.tm_mon, ris.tm_mday)
## - ##


## + ##
# str ex. "2010-06-19 16:42:02.123456"
def strToDateTime(str):
    return datetime.datetime.strptime(str, "%Y-%m-%d %H:%M:%S.%f")
## - ##


## + ##
def strToInt(str, defVal):
    if str == None: return defVal
    else: return int(str)
## end-def ##


## + ##
def getEnvInfo():
    ctime = str(datetime.datetime.today())
    pyVer = platform.python_version()
    plat = platform.platform()
    osi = os.uname()
    arc = platform.architecture()
    return "{0}\t{1}\t{2}\t{3}\t{4}".format(ctime, pyVer, plat, osi[3], arc[0], arc[1])
## - ##


## + ##
def getSysInfo():
    ret = {}

    ret["ctime"] = str(datetime.datetime.today())
    ret["pyver"] = platform.python_version()
    ret["plat"] = platform.platform()
    ret["osi"] = os.uname()
    ret["arc"] = platform.architecture()

    ose = os.environ

    # Desktop Enviroment Graphic Shell
    des_val = None

    if getDicKey(ose, "KDE_FULL_SESSION") == "true":
        des_val = "kde"
    elif getDicKey(ose, "DESKTOP_SESSION") == "gnome":
        des_val = "gnome"
    elif getDicKey(ose, "DESKTOP_SESSION") == "ubuntu":
        des_val = "unity"
    elif getDicKey(ose, "DESKTOP_SESSION") == "ubuntu-2d":
        des_val = "unity-2d"
    elif getDicKey(ose, "DESKTOP_SESSION") == "xubuntu":
        des_val = "xfce"
    elif getDicKey(ose, "DESKTOP_SESSION") == "Lubuntu":
        des_val = "lxde"
    else:
        try:
            info = commands.getoutput('xprop -root _DT_SAVE_MODE')
            if ' = "xfce4"' in info:
                des_val = 'xfce'
        except (OSError, RuntimeError):
            pass
        
    ret["des"] = des_val

    # unity    
    ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
    processes = ps.split('\n')
    
    unity_panel = False
    for row in processes:
        if row.find("unity-") >= 0:
            if row.find("unity-panel-service") >= 0:
                unity_panel = True
                break
            elif row.find("unity-2d-panel") >= 0:
                unity_panel = True
                break
    
    ret["unity.panel"] = unity_panel
    

    return ret
## - ##


## + ##
def autorunSupported(des):
    return des in ["gnome", "ubuntu-2d", "kde", "xfce", "lxde"]
## - ##


## + ##
def getDicKey(dic, key):
    try:
        return dic[key]
    except KeyError:
        return None
## - ##


### + ###
def prop2dic(properties_string):
    linelist = string.split(properties_string, '\n')
    dic = {}

    for l in linelist:
        sl = string.split(l, ':', 1)
        if len(sl) == 2:
            if sl[0] != '':
                dic[string.strip(sl[0])] = string.strip(sl[1])
    return dic
### - ###


### + ###
def dbgMsg(str, lev=1):
    if (lev <= globaldef.DBGMSG_LEVEL):
        print(str)
### - ###


### + ###
def boolToStrInt(val):
    if val: return '1'
    else: return '0'
### - ###


### + ###
# first_day: datetime.date
# period: 0->Custom Days; 1->Day; 2->Week; 3->Month; 4->Year;
def get_last_day(first_day, period, custom_days):
    if period == 0:
        return (first_day + datetime.timedelta(custom_days-1))
    elif period == 1:
        return first_day
    elif period == 2:
        return (first_day + datetime.timedelta(7-1))
    elif period == 3:
        return (first_day + monthdelta(1) - datetime.timedelta(1))
    elif period == 4:
        return (first_day + monthdelta(12) - datetime.timedelta(1))
    else: return None
### - ###


### + ###
# date: (datetime.date)
# return: the start of the day date (datetime.datetime). 
# ex. date=2000.2.15 >> return=2000.2.15 0h0'0"
def date_to_datetime_start(date):
    return datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
### - ###


### + ###
# date: (datetime.date)
# return: the end of the day date (datetime.datetime). 
# ex. date=2000.2.15 >> return=2000.2.15 23h59'59"
def date_to_datetime_end(date):
    return datetime.datetime(date.year, date.month, date.day, 23, 59, 59)
### - ###

### + ###
# for control with set/get text: label
def translate_control_text(control):
    control.set_text(_(control.get_text()))
### - ###

### + ###
# for control with set markup: label
def translate_control_markup(control):
    control.set_markup(_(control.get_label()))
### - ###

### + ###
# for control with set/get label: button
def translate_control_label(control):
    control.set_label(_(control.get_label()))
### - ###

