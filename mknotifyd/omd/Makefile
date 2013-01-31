include ../../Makefile.omd

NAME = mknotifyd
VERSION = foobar
DIR = $(NAME)-$(VERSION)

build:
	tar xzf $(DIR).tar.gz

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(DIR)/bin/* $(DESTDIR)$(OMD_ROOT)/bin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/web
	cp -pr $(DIR)/web/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/web

clean:
#	rm -rf mk-notifyd-*.*.*

