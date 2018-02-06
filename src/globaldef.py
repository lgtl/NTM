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

import os, sys

VERSION = "1.3.1"
VERSION_NN = "Drunken Monkey"

LICENSE = """This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA."""


NTM_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))

NTM_ICON_SCA = "./stf/ntm.svg"
NTM_ICON = NTM_ICON_SCA
NTM_ICON_ACTIVE = "./stf/ntm_active.svg"

NTM_PROFILE_RELPATH = ".ntm"

NTM_DB_NAME = "ntmdb_2"

DBGMSG_LEVEL = 0

