NAGIOS := nagios
NAGIOS_VERS := 3.5.1
NAGIOS_DIR := $(NAGIOS)-$(NAGIOS_VERS)

NAGIOS_PATCHING := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-patching
NAGIOS_BUILD := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-build
NAGIOS_INSTALL := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-install

#NAGIOS_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(NAGIOS_DIR)
NAGIOS_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(NAGIOS_DIR)
#NAGIOS_WORK_DIR := $(PACKAGE_WORK_DIR)/$(NAGIOS_DIR)

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
NAGIOS_CONFIGUREOPTS := \
    --sbindir=$(OMD_ROOT)/lib/nagios/cgi-bin \
    --bindir=$(OMD_ROOT)/bin \
    --datadir=$(OMD_ROOT)/share/nagios/htdocs \
    --with-nagios-user=$$(id -un) \
    --with-nagios-group=$$(id -gn) \
    --with-perlcache \
    --enable-embedded-perl \

$(NAGIOS_BUILD): $(NAGIOS_PATCHING)
	find $(NAGIOS_BUILD_DIR)/ -name \*.orig -exec rm {} \;
	cd $(NAGIOS_BUILD_DIR) ; ./configure $(NAGIOS_CONFIGUREOPTS)
	$(MAKE) -C $(NAGIOS_BUILD_DIR) all
	$(TOUCH) $@

$(NAGIOS_INSTALL): $(NAGIOS_BUILD)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(NAGIOS_BUILD_DIR) install-base
	
	install -m 664 $(NAGIOS_BUILD_DIR)/p1.pl $(DESTDIR)$(OMD_ROOT)/lib/nagios
	
	# Copy package documentations to have these information in the binary packages
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAGIOS)
	set -e ; for file in README THANKS LEGAL LICENSE ; do \
	   install -m 644 $(NAGIOS_BUILD_DIR)/$$file $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAGIOS); \
	done
	
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(PACKAGE_DIR)/$(NAGIOS)/merge-nagios-config $(DESTDIR)$(OMD_ROOT)/bin
	
	# Install the diskspace cleanup plugin
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/diskspace
	install -m 644 $(PACKAGE_DIR)/$(NAGIOS)/diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/nagios
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	install -m 755 $(PACKAGE_DIR)/$(NAGIOS)/NAGIOS_THEME $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(TOUCH) $@
