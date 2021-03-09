OMD := omd
OMD_VERS := $(OMD_VERSION)
OMD_DIR := $(OMD)-$(OMD_VERS)

ifeq ($(DISTRO_NAME),SLES)
    DEFAULT_RUNLEVELS=2 3 5
else
    DEFAULT_RUNLEVELS=2 3 4 5
endif

OMD_INSTALL := $(BUILD_HELPER_DIR)/$(OMD_DIR)-install
OMD_SKEL := $(BUILD_HELPER_DIR)/$(OMD_DIR)-skel

.PHONY: $(OMD) $(OMD)-install $(OMD)-skel

$(OMD):

$(OMD)-install: $(OMD_INSTALL)
$(OMD)-skel: $(OMD_SKEL)

$(OMD_INSTALL): omdlib-install
	install -m 755 $(PACKAGE_DIR)/$(OMD)/omd.bin $(DESTDIR)$(OMD_ROOT)/bin/omd
	sed -i 's|###OMD_VERSION###|$(OMD_VERSION)|g' $(DESTDIR)$(OMD_ROOT)/bin/omd
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/omd/htdocs
	install -m 644 $(PACKAGE_DIR)/$(OMD)/logout.php $(DESTDIR)$(OMD_ROOT)/share/omd/htdocs
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
	install -m 755 $(PACKAGE_DIR)/$(OMD)/hooks/* $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(TOUCH) $@

omdlib-install: $(PYTHON_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/python/omdlib
	install -m 644 $(PACKAGE_DIR)/$(OMD)/omdlib/*.py $(DESTDIR)$(OMD_ROOT)/lib/python/omdlib/
	sed -i 's|###OMD_VERSION###|$(OMD_VERSION)|g' $(DESTDIR)$(OMD_ROOT)/lib/python/omdlib/__init__.py
	export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH):$(PACKAGE_PYTHON_PYTHONPATH):$(REPO_PATH)" ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	$(PACKAGE_PYTHON_EXECUTABLE) -m compileall $(DESTDIR)$(OMD_ROOT)/lib/python/omdlib

$(OMD_SKEL): $(OMD_INSTALL)
	$(MKDIR) $(SKEL)/etc/bash_completion.d
	$(TOUCH) $@

$(OMD)-clean:
