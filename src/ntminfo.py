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
pygtk.require('2.0')
import gtk
import gobject
import globaldef
import webkit

### + ###
class NtmInfo:
    ## + ##
    # load : True-> load the page
    def __init__(self, load_local):
        self.view = webkit.WebView()

        self.info_window = gtk.Window()
        icon = self.info_window.render_icon(gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_BUTTON)
        self.info_window.set_icon(icon)
        self.info_window.resize(800, 600)
        self.info_window.set_position(gtk.WIN_POS_CENTER)
        self.info_window.set_title(_("NTM - Info & News"))
	
        self.scrolledWindow = gtk.ScrolledWindow() 
        self.scrolledWindow.add(self.view)
        self.info_window.add(self.scrolledWindow)

        self.info_url = 'http://netramon.sourceforge.net/news.html'
        self.info_local_url = 'file://' + globaldef.NTM_PATH + '/info.html'

        if load_local: self.view.open(self.info_local_url)
        else: self.view.open(self.info_url)

        self.info_window.show_all()
        self.info_window.hide()
        self.info_window.connect("delete_event", self.delete_event)
    ## - ##
        
    ## + ##
    def load(self):
        self.view.open(self.info_url)
    ## - ##

    ## + ##
    def show(self):
        self.info_window.show()
    ## - ##

    ## + ##
    def delete_event(self, widget, data=None):
        self.info_window.hide()
        return True
    ## - ##
### - ###

