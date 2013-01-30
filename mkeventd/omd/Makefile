# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

include ../../Makefile.omd

NAME = mkeventd
VERSION = foobar
DIR = $(NAME)-$(VERSION)

build:
	tar xzf $(DIR).tar.gz
	cd $(DIR)/src ; make

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(DIR)/bin/* $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(DIR)/src/mkevent $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(DIR)/src/mkeventd_open514 $(DESTDIR)$(OMD_ROOT)/bin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	install -m 755 $(DIR)/lib/* $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/checks
	install -m 644 $(DIR)/checks/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/checks
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/web
	cp -pr $(DIR)/web/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/web

clean:
	rm -rf mk-eventd-*.*.*

