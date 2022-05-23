NAGVIS := nagvis
NAGVIS_VERS := 1.9.33
NAGVIS_DIR := $(NAGVIS)-$(NAGVIS_VERS)

NAGVIS_PATCHING := $(BUILD_HELPER_DIR)/$(NAGVIS_DIR)-patching
NAGVIS_BUILD := $(BUILD_HELPER_DIR)/$(NAGVIS_DIR)-build
NAGVIS_INSTALL := $(BUILD_HELPER_DIR)/$(NAGVIS_DIR)-install

#NAGVIS_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(NAGVIS_DIR)
NAGVIS_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(NAGVIS_DIR)
#NAGVIS_WORK_DIR := $(PACKAGE_WORK_DIR)/$(NAGVIS_DIR)

$(NAGVIS_BUILD): $(NAGVIS_PATCHING)
	$(TOUCH) $@

$(NAGVIS_INSTALL): $(NAGVIS_BUILD)
	cd $(NAGVIS_BUILD_DIR) ; ./install.sh -q -F -c y -a n \
	 -u $$(id -un) \
	 -g $$(id -gn) \
	 -w $(DESTDIR)$(OMD_ROOT)/etc/apache \
	 -W /WILL_BE_REPLACED/nagvis \
	 -b $(DESTDIR)/usr/bin \
	 -p $(DESTDIR)$(OMD_ROOT)/share/nagvis
	
	# Relocate the NagVis shared directory to have the same path as all the other packages
	$(TEST) -d $(DESTDIR)$(OMD_ROOT)/share/nagvis/share && \
	  $(MV) $(DESTDIR)$(OMD_ROOT)/share/nagvis/share $(DESTDIR)$(OMD_ROOT)/share/nagvis/htdocs
	
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/var/nagvis/profiles
	
	# Move package documentations to have these files in the binary packages
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAGVIS)
	for file in COPYING README ; do \
	  $(MV) $(DESTDIR)$(OMD_ROOT)/share/nagvis/$$file $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAGVIS); \
	done
	
	# Take the sample main configuration file from source package and overwrite the one 
	# installed by the installer.
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis
	cp $(NAGVIS_BUILD_DIR)/etc/nagvis.ini.php-sample $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/nagvis.ini.php
	
	# Move demo config files
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/conf.d
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/maps
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/geomap
	$(RM) $(DESTDIR)$(OMD_ROOT)/share/nagvis/etc/maps/*.cfg
	$(MV) $(DESTDIR)$(OMD_ROOT)/share/nagvis/etc/conf.d/*.ini.php $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/conf.d
	$(MV) $(DESTDIR)$(OMD_ROOT)/share/nagvis/etc/geomap/demo-*.csv $(DESTDIR)$(OMD_ROOT)/skel/etc/nagvis/geomap
	
	# Delete files/directories we do not want to pack
	$(RM) -rf $(DESTDIR)$(OMD_ROOT)/share/nagvis/var
	$(RM) -rf $(DESTDIR)$(OMD_ROOT)/share/nagvis/etc
	$(TOUCH) $@
