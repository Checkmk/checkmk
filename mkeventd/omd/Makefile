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

