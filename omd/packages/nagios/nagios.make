NAGIOS := nagios
NAGIOS_VERS := 3.5.1
NAGIOS_DIR := $(NAGIOS)-$(NAGIOS_VERS)
# Increase this to enforce a recreation of the build cache
NAGIOS_BUILD_ID := 3-$(EDITION_SHORT)

NAGIOS_UNPACK := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-unpack
NAGIOS_PATCHING := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-patching
NAGIOS_BUILD := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-build
NAGIOS_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-install-intermediate
NAGIOS_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-cache-pkg-process
NAGIOS_INSTALL := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-install

NAGIOS_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(NAGIOS_DIR)
NAGIOS_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(NAGIOS_DIR)
#NAGIOS_WORK_DIR := $(PACKAGE_WORK_DIR)/$(NAGIOS_DIR)

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
NAGIOS_CONFIGUREOPTS := \
    --prefix="" \
    --sbindir=$(OMD_ROOT)/lib/nagios/cgi-bin \
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

NAGIOS_CACHE_PKG_PATH := $(call cache_pkg_path,$(NAGIOS_DIR),$(NAGIOS_BUILD_ID))

$(NAGIOS_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(NAGIOS_DIR),$(NAGIOS_BUILD_ID),$(NAGIOS_INTERMEDIATE_INSTALL))

$(NAGIOS_CACHE_PKG_PROCESS): $(NAGIOS_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(NAGIOS_CACHE_PKG_PATH),$(NAGIOS_DIR))
	$(call upload_pkg_archive,$(NAGIOS_CACHE_PKG_PATH),$(NAGIOS_DIR),$(NAGIOS_BUILD_ID))
	$(TOUCH) $@

$(NAGIOS_INTERMEDIATE_INSTALL): $(NAGIOS_BUILD)
	$(MAKE) DESTDIR=$(NAGIOS_INSTALL_DIR) -C $(NAGIOS_BUILD_DIR) install-base
	
	$(MKDIR) $(NAGIOS_INSTALL_DIR)/lib/nagios
	install -m 664 $(NAGIOS_BUILD_DIR)/p1.pl $(NAGIOS_INSTALL_DIR)/lib/nagios
	
	# Copy package documentations to have these information in the binary packages
	$(MKDIR) $(NAGIOS_INSTALL_DIR)/share/doc/$(NAGIOS)
	set -e ; for file in README THANKS LEGAL LICENSE ; do \
	   install -m 644 $(NAGIOS_BUILD_DIR)/$$file $(NAGIOS_INSTALL_DIR)/share/doc/$(NAGIOS); \
	done
	
	$(MKDIR) $(NAGIOS_INSTALL_DIR)/bin
	install -m 755 $(PACKAGE_DIR)/$(NAGIOS)/merge-nagios-config $(NAGIOS_INSTALL_DIR)/bin
	
	# Install the diskspace cleanup plugin
	$(MKDIR) $(NAGIOS_INSTALL_DIR)/share/diskspace
	install -m 644 $(PACKAGE_DIR)/$(NAGIOS)/diskspace $(NAGIOS_INSTALL_DIR)/share/diskspace/nagios
	$(MKDIR) $(NAGIOS_INSTALL_DIR)/lib/omd/hooks
	install -m 755 $(PACKAGE_DIR)/$(NAGIOS)/NAGIOS_THEME $(NAGIOS_INSTALL_DIR)/lib/omd/hooks/
	$(TOUCH) $@


$(NAGIOS_INSTALL): $(NAGIOS_CACHE_PKG_PROCESS)
	$(RSYNC) $(NAGIOS_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
