include ../../Makefile.omd

NAME     = nail
VERSION  = 12.5
DIR      = heirloom-mailx-$(VERSION)

.PHONY: skel

build:
	tar xzf $(DIR).tar.gz
	set -e ; for p in patches/*.dif ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(DIR) < $$p ; \
	done
	cd $(DIR) && $(MAKE) -j 1

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(DIR)/mailx $(DESTDIR)$(OMD_ROOT)/bin/nail
	ln -sfn nail $(DESTDIR)$(OMD_ROOT)/bin/mail
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/man/man1
	install -m 644 $(DIR)/mailx.1 $(DESTDIR)$(OMD_ROOT)/share/man/man1/nail.1
	gzip $(DESTDIR)$(OMD_ROOT)/share/man/man1/nail.1

skel:

clean:
	rm -rf $(DIR)
