include ../../Makefile.omd

NAME = nrpe
VERSION = 2.13
DIR = $(NAME)-$(VERSION)

.PHONY: skel

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
CONFIGUREOPTS = ""

build:
	tar xzf $(DIR).tar.gz
	set -e ; for p in patches/*.dif ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(DIR) < $$p ; \
	done
	cd $(DIR) ; ./configure $(CONFIGUREOPTS)
	$(MAKE) -C $(DIR) all

install:
	install -m 755 $(DIR)/src/check_nrpe $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	
	mkdir $(DESTDIR)$(OMD_ROOT)/share/doc/nrpe
	install -m 644 $(DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/nrpe
	install -m 644 $(DIR)/LEGAL $(DESTDIR)$(OMD_ROOT)/share/doc/nrpe
	install -m 644 $(DIR)/SECURITY $(DESTDIR)$(OMD_ROOT)/share/doc/nrpe

skel:

clean:
	rm -rf $(DIR)
