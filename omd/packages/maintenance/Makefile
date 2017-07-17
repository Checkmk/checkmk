include ../../Makefile.omd

NAME = maintenance 
VERSION = $(OMD_VERSION)
SHELL = /bin/bash

build:

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 merge-crontabs $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 diskspace $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 logrotate $(DESTDIR)$(OMD_ROOT)/bin
	
	# Create directory for the diskspace plugin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/diskspace
	
	install -m 644 wato_omd_configuration.py $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/wato/omd_configuration.py

skel:

clean:
