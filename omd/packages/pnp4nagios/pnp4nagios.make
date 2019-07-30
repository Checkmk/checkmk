PNP4NAGIOS := pnp4nagios
PNP4NAGIOS_VERS := 0.6.26
PNP4NAGIOS_DIR = $(PNP4NAGIOS)-$(PNP4NAGIOS_VERS)

PNP4NAGIOS_BUILD := $(BUILD_HELPER_DIR)/$(PNP4NAGIOS_DIR)-build
PNP4NAGIOS_INSTALL := $(BUILD_HELPER_DIR)/$(PNP4NAGIOS_DIR)-install
PNP4NAGIOS_PATCHING := $(BUILD_HELPER_DIR)/$(PNP4NAGIOS_DIR)-patching

.PHONY: $(PNP4NAGIOS) $(PNP4NAGIOS)-install $(PNP4NAGIOS)-clean 

$(PNP4NAGIOS): $(PNP4NAGIOS_BUILD)

$(PNP4NAGIOS)-install: $(PNP4NAGIOS_INSTALL)

# Unset CONFIG_SITE
CONFIG_SITE = ''

# Configure options for PNP4Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
PNP4NAGIOS_CONFIGUREOPTS = \
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

$(PNP4NAGIOS_BUILD): $(PNP4NAGIOS_PATCHING)
	cd $(PNP4NAGIOS_DIR) ; ./configure $(PNP4NAGIOS_CONFIGUREOPTS)
	$(MAKE) -C $(PNP4NAGIOS_DIR) all
	$(TOUCH) $@

$(PNP4NAGIOS_INSTALL): $(PNP4NAGIOS_BUILD)
	$(MKDIR) $(DESTDIR)$(APACHE_CONF_DIR)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(PNP4NAGIOS_DIR) install
	# Fixup wrong man page installation path
	# (There is a --mandir configure option, but it does not work)
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/man/man8
	mv $(DESTDIR)$(OMD_ROOT)/man/man8/npcd.8 $(DESTDIR)$(OMD_ROOT)/share/man/man8/npcd.8
	rmdir $(DESTDIR)$(OMD_ROOT)/man/man8
	rmdir $(DESTDIR)$(OMD_ROOT)/man
	# Remove installer
	rm $(DESTDIR)$(OMD_ROOT)/share/pnp4nagios/htdocs/install.php
	rm -rf $(DESTDIR)$(OMD_ROOT)/etc/pnp4nagios
	rm -rf $(DESTDIR)$(OMD_ROOT)/var/pnp4nagios
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	install -m 644 $(PNP4NAGIOS_DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	install -m 644 $(PNP4NAGIOS_DIR)/COPYING $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	install -m 644 $(PNP4NAGIOS_DIR)/AUTHORS $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	install -m 644 $(PNP4NAGIOS_DIR)/THANKS $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios
	
	# Install the diskspace cleanup plugin
	install -m 644 $(PACKAGE_DIR)/$(PNP4NAGIOS)/diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/pnp4nagios
	
	# Move default config files to skel
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/etc/pnp4nagios
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/var/pnp4nagios/stats
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/var/pnp4nagios/perfdata
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/var/pnp4nagios/log
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/var/pnp4nagios/spool
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/tmp/pnp4nagios/run
	
	# Install the facelift theme for pnp4nagios
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/pnp4nagios/htdocs/media/css/ui-facelift/images
	install -m 644 $(PACKAGE_DIR)/$(PNP4NAGIOS)/ui-facelift/jquery-ui.css $(DESTDIR)$(OMD_ROOT)/share/pnp4nagios/htdocs/media/css/ui-facelift
	install -m 644 $(PACKAGE_DIR)/$(PNP4NAGIOS)/ui-facelift/images/* $(DESTDIR)$(OMD_ROOT)/share/pnp4nagios/htdocs/media/css/ui-facelift/images

	# Install Hooks
	install -m 755 $(PACKAGE_DIR)/$(PNP4NAGIOS)/PNP4NAGIOS $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(TOUCH) $@

$(PNP4NAGIOS)-skel:

$(PNP4NAGIOS)-clean:
	rm -rf $(PNP4NAGIOS_DIR) $(BUILD_HELPER_DIR)/$(PNP4NAGIOS_DIR)*
