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

skel:

clean:
