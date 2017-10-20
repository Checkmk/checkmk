# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

MSITOOLS      = msitools-0.94
MSITOOLS_FILE = $(MSITOOLS).tar.xz

BUILD_VERSION    = 1
CHECK_MK_VERSION = TESTVERSION

all: exchange_msi_files

clean:
	rm -rf $(MSITOOLS)
	rm -f check_mk_agent.msi
	rm -rf work sources
	rm -f .gsf-save-*

msibuild:
	tar -Jxf $(MSITOOLS_FILE)
	set -e ; for p in patches/*.dif ; do \
	echo "applying $$p..." ; \
	    (cd $(MSITOOLS) ; patch -p1 -b < ../$$p) ; \
	done
	cd $(MSITOOLS) && ./configure
	make -C $(MSITOOLS)/libmsi
	make -C $(MSITOOLS) msibuild msiinfo
	rm msibuild msiinfo
	ln -s $(MSITOOLS)/msibuild $(MSITOOLS)/msiinfo .


exchange_msi_files: msibuild
	mkdir -p work sources
	cp ../check_mk_agent.exe ../check_mk_agent-64.exe ../check_mk.example.ini sources
	LD_LIBRARY_PATH=$$(pwd)/msitools-0.94/libmsi/.libs \
	    ./msi-update -v vanilla_container.msi sources $(BUILD_VERSION) $(CHECK_MK_VERSION)
	rm -rf work sources
