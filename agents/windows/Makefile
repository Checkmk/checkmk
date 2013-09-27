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

ifeq ($(shell uname),Linux)
  CXX    = echo -e "\n\nWARNING: MinGW under Linux is broken! Use at your own risk!\n\n" ; i586-mingw32msvc-g++
  CXX_64 = x86_64-w64-mingw32-g++
else
  CXX = mingw32-g++
endif

all: install_agent.exe

test.exe: test.cc
	$(CXX) -s -O2 -o $@ $< -static -lwsock32

install_agent.exe: check_mk_agent.exe crash.exe nowin.exe
	if ! which makensis; then \
	    echo "ERROR: makensis missing. Please install the nsis package." ; \
	    exit 1 ; \
	fi
	makensis installer.nsi
	chmod +x install_agent.exe

install_agent-64.exe: check_mk_agent-64.exe crash.exe nowin.exe
	if ! which makensis; then \
	    echo "ERROR: makensis missing. Please install the nsis package." ; \
	    exit 1 ; \
	fi
	makensis installer-64.nsi
	chmod +x install_agent-64.exe

check_mk_agent.exe: check_mk_agent.cc Makefile
	$(CXX) -s -O2 -Wall -Werror -o $@ $< -static -lwsock32

check_mk_agent-64.exe: check_mk_agent.cc Makefile
	$(CXX_64) -s -O2 -Wall -Werror -o $@ $< -static -lwsock32

crash.exe: crash.cc Makefile
	$(CXX) -o $@ $<

nowin.exe: nowin.cc Makefile
	$(CXX) -o $@ $<

clean:
	rm -f *.o *~ svn-*.tmp

mrproper: clean
	rm -f *.exe

