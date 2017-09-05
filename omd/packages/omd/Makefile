include ../../Makefile.omd

NAME = omd
VERSION = $(OMD_VERSION)
SHELL = /bin/bash

ifeq ($(DISTRO_NAME),SLES)
    DEFAULT_RUNLEVELS=2 3 5
else
    DEFAULT_RUNLEVELS=2 3 4 5
endif

build:

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 omd $(DESTDIR)$(OMD_ROOT)/bin
	sed -i 's|###OMD_VERSION###|$(OMD_VERSION)|g' $(DESTDIR)$(OMD_ROOT)/bin/omd
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/omd/htdocs
	install -m 644 index.py $(DESTDIR)$(OMD_ROOT)/share/omd/htdocs
	install -m 644 logout.php $(DESTDIR)$(OMD_ROOT)/share/omd/htdocs
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/man/man8
	install -m 644 omd.8 $(DESTDIR)$(OMD_ROOT)/share/man/man8
	gzip $(DESTDIR)$(OMD_ROOT)/share/man/man8/omd.8
	install -m 755 omd.init $(DESTDIR)$(OMD_ROOT)/share/omd/omd.init
	sed -i 's|###DEFAULT_RUNLEVELS###|$(DEFAULT_RUNLEVELS)|g' $(DESTDIR)$(OMD_ROOT)/share/omd/omd.init
	install -m 644 omd.service $(DESTDIR)$(OMD_ROOT)/share/omd/omd.service
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME)
	install -m 644 README COPYING $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME)
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/omd
	install -m 644 init_profile $(DESTDIR)$(OMD_ROOT)/lib/omd/
	install -m 755 port_is_used $(DESTDIR)$(OMD_ROOT)/lib/omd/
	install -m 644 omd_bash_completion $(DESTDIR)$(OMD_ROOT)/lib/omd/
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-create

skel:
	mkdir -p $(SKEL)/etc/bash_completion.d

clean:
