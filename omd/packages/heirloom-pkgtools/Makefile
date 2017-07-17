include ../../Makefile.omd

NAME     = heirloom-pkgtools
VERSION  = 070227
DIR      = $(NAME)-$(VERSION)

.PHONY: skel

build:
	
	tar xjf $(DIR).tar.bz2
	set -e ; for p in patches/*.dif ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(DIR) < $$p ; \
	done
	cd $(DIR) \
	    && find -name Makefile -delete \
	    && $(MAKE) -j 1

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/man/man1
	for F in pkgmk pkgtrans; do \
	    install -m 755 $(DIR)/pkgcmds/$$F/$$F $(DESTDIR)$(OMD_ROOT)/bin/ ; \
	    install -m 644 $(DIR)/man/$$F.1 $(DESTDIR)$(OMD_ROOT)/share/man/man1/; \
	    gzip -f $(DESTDIR)$(OMD_ROOT)/share/man/man1/$$F.1 ; \
	done

skel:

clean:
	rm -rf $(DIR) heirloom-devtools-070527
