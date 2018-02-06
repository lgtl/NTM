#!/bin/bash

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

#ln -s /usr/share/ntm/stf/ntm.svg /usr/share/icons/ubuntu-mono-dark/status/24/ntm.svg
#ln -s /usr/share/ntm/stf/ntm.svg /usr/share/icons/ubuntu-mono-light/status/24/ntm.svg
#ln -s /usr/share/ntm/stf/ntm.svg /usr/share/icons/Humanity/status/24/ntm.svg
#ln -s /usr/share/ntm/stf/ntm.svg /usr/share/icons/Humanity-Dark/status/24/ntm.svg

xdg-icon-resource install --novendor --size 64 ./stf/nk.ntm_on.png nk.ntm_on
xdg-icon-resource install --novendor --size 64 ./stf/nk.ntm_off.png nk.ntm_off

