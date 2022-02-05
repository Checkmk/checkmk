OMD := omd
OMD_VERS := $(OMD_VERSION)
OMD_DIR := $(OMD)-$(OMD_VERS)

ifeq ($(DISTRO_NAME),SLES)
    DEFAULT_RUNLEVELS=2 3 5
else
    DEFAULT_RUNLEVELS=2 3 4 5
endif

OMD_BUILD := $(BUILD_HELPER_DIR)/$(OMD_DIR)-build
OMD_INSTALL := $(BUILD_HELPER_DIR)/$(OMD_DIR)-install

$(OMD_BUILD):
	$(TOUCH) $@

$(OMD_INSTALL): omdlib-install
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(PACKAGE_DIR)/$(OMD)/omd.bin $(DESTDIR)$(OMD_ROOT)/bin/omd
	sed -i 's|###OMD_VERSION###|$(OMD_VERSION)|g' $(DESTDIR)$(OMD_ROOT)/bin/omd
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/man/man8
	install -m 644 $(PACKAGE_DIR)/$(OMD)/omd.8 $(DESTDIR)$(OMD_ROOT)/share/man/man8
	gzip -f $(DESTDIR)$(OMD_ROOT)/share/man/man8/omd.8
	install -m 755 $(PACKAGE_DIR)/$(OMD)/omd.init $(DESTDIR)$(OMD_ROOT)/share/omd/omd.init
	sed -i 's|###DEFAULT_RUNLEVELS###|$(DEFAULT_RUNLEVELS)|g' $(DESTDIR)$(OMD_ROOT)/share/omd/omd.init
	install -m 644 $(PACKAGE_DIR)/$(OMD)/omd.service $(DESTDIR)$(OMD_ROOT)/share/omd/omd.service
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME)
	install -m 644 $(PACKAGE_DIR)/$(OMD)/README $(PACKAGE_DIR)/$(OMD)/COPYING $(DESTDIR)$(OMD_ROOT)/share/doc/$(NAME)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd
	install -m 644 $(PACKAGE_DIR)/$(OMD)/init_profile $(DESTDIR)$(OMD_ROOT)/lib/omd/
	install -m 755 $(PACKAGE_DIR)/$(OMD)/port_is_used $(DESTDIR)$(OMD_ROOT)/lib/omd/
	install -m 644 $(PACKAGE_DIR)/$(OMD)/bash_completion $(DESTDIR)$(OMD_ROOT)/lib/omd/
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-create
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-update
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	install -m 755 $(PACKAGE_DIR)/$(OMD)/hooks/* $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(MKDIR) $(SKEL)/etc/bash_completion.d
	$(TOUCH) $@

omdlib-install: $(PACKAGE_PYTHON3_MODULES_PYTHON_DEPS)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/python3/omdlib
	install -m 644 $(PACKAGE_DIR)/$(OMD)/omdlib/*.py $(DESTDIR)$(OMD_ROOT)/lib/python3/omdlib/
	sed -i 's|###OMD_VERSION###|$(OMD_VERSION)|g' $(DESTDIR)$(OMD_ROOT)/lib/python3/omdlib/__init__.py
	$(PACKAGE_PYTHON3_MODULES_PYTHON) -m py_compile $(DESTDIR)$(OMD_ROOT)/lib/python3/omdlib/*.py
