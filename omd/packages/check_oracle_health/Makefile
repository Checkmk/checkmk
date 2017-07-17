include ../../Makefile.omd

NAME = check_oracle_health
VERSION = 3.0.1
DIR = $(NAME)-$(VERSION)

.PHONY: skel

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
CONFIGUREOPTS = ""

build:
	tar xzf $(DIR).tar.gz
	for i in configure.ac aclocal.m4 configure Makefile.am Makefile.in ; do \
	  test -f $(DIR)/$$i && touch $(DIR)/$$i ; \
	done
	cd $(DIR) ; ./configure $(CONFIGUREOPTS)
	$(MAKE) -C $(DIR)

install:
	[ -d $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins ] || mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	install -m 755 $(DIR)/plugins-scripts/check_oracle_health $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins

skel:

clean:
	rm -rf $(DIR)
