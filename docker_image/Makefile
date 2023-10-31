# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include ../defines.make

needed-packages: ../omd/distros/UBUNTU_22.04.mk
	echo -e '.PHONY: needed-packages\nneeded-packages:\n\t@echo \$$(OS_PACKAGES) > needed-packages\n' | \
	    make -f - -f ../omd/distros/UBUNTU_22.04.mk --no-print-directory needed-packages
