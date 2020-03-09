# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

# we have to use legacy msi-update 	
exchange_msi_files: msibuild
	mkdir -p work sources
	cp ../check_mk_agent.exe ../check_mk_agent-64.exe ../check_mk.example.ini sources
	LD_LIBRARY_PATH=$$(pwd)/msitools-0.94/libmsi/.libs \
           ./msi-update-legacy -v vanilla_container.msi sources $(BUILD_VERSION) $(CHECK_MK_VERSION)
	rm -rf work sources
