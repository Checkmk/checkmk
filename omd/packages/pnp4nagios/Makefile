include ../../Makefile.omd

.PHONY: skel

NAME = pnp4nagios
VERSION = 0.6.25
DIR = $(NAME)-$(VERSION)
# Unset CONFIG_SITE
CONFIG_SITE = ''

# Configure options for PNP4Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
CONFIGUREOPTS = \
    --prefix=$(OMD_ROOT) \
    --sysconfdir=$(OMD_ROOT)/etc/pnp4nagios \
    --libexecdir=$(OMD_ROOT)/lib/pnp4nagios \
    --docdir=$(OMD_ROOT)/share/doc/pnp4nagios \
    --datarootdir=$(OMD_ROOT)/share/pnp4nagios/htdocs \
    --localstatedir=$(OMD_ROOT)/var/pnp4nagios \
    --with-perfdata-dir=$(OMD_ROOT)/var/pnp4nagios/perfdata \
    --with-perfdata-spool-dir=$(OMD_ROOT)/tmp/pnp4nagios/spool \
    --with-perfdata-logfile=$(OMD_ROOT)/var/pnp4nagios/log/perfdata.log \
    --with-nagios-user=$$(id -un) \
    --with-nagios-group=$$(id -gn) \
    --with-rrdtool=/bin/true \
    --with-perl_lib_path=$(OMD_ROOT)/lib/perl5/lib/perl5 \
    --with-base-url='/\#\#\#SITE\#\#\#/pnp4nagios'

build:
	tar xzf $(DIR).tar.gz
	for p in patches/*.diff ; do \
		echo "applying $$p..." ; \
		patch -p1 -b -d $(DIR) < $$p ; \
        done
	cd $(DIR) ; ./configure $(CONFIGUREOPTS)
	$(MAKE) -C $(DIR) all

install:
	mkdir -p $(DESTDIR)$(APACHE_CONF_DIR)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install
	# Remove installer 
	rm $(DESTDIR)$(OMD_ROOT)/share/pnp4nagios/htdocs/install.php
	rm -rf $(DESTDIR)$(OMD_ROOT)/etc/pnp4nagios
	rm -rf $(DESTDIR)$(OMD_ROOT)/var/pnp4nagios
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	install -m 644 $(DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	install -m 644 $(DIR)/COPYING $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	install -m 644 $(DIR)/AUTHORS $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	install -m 644 $(DIR)/THANKS $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	
	# Install the diskspace cleanup plugin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/diskspace
	install -m 644 diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/pnp4nagios
	
	# Move default config files to skel
	mkdir -p skel/etc/pnp4nagios
	mkdir -p skel/var/pnp4nagios/stats
	mkdir -p skel/var/pnp4nagios/perfdata
	mkdir -p skel/var/pnp4nagios/log
	mkdir -p skel/var/pnp4nagios/spool
	mkdir -p skel/tmp/pnp4nagios/run

clean:
	rm -rf $(DIR)
