NAGIOS := nagios
NAGIOS_DIR := $(NAGIOS)

NAGIOS_BUILD := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-build
NAGIOS_INSTALL := $(BUILD_HELPER_DIR)/$(NAGIOS_DIR)-install

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.

$(NAGIOS_BUILD):
	$(BAZEL_BUILD) @$(NAGIOS)//:$(NAGIOS)
	$(BAZEL_BUILD) @$(NAGIOS)//:skel

$(NAGIOS_INSTALL): $(NAGIOS_BUILD)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN)/$(NAGIOS)/$(NAGIOS)/ $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=u+w $(BAZEL_BIN)/$(NAGIOS)/bin $(DESTDIR)$(OMD_ROOT)/
	patchelf --set-rpath "\$$ORIGIN/../lib" $(DESTDIR)$(OMD_ROOT)/bin/nagios
	$(RSYNC) --chmod=u+w $(BAZEL_BIN)/$(NAGIOS)/share $(DESTDIR)$(OMD_ROOT)/
	# Fix permissions as they don't come out of bazel correctly yet
	chmod 755 $(DESTDIR)$(OMD_ROOT)/bin/nagios
	chmod 755 $(DESTDIR)$(OMD_ROOT)/bin/nagiostats
	chmod 644 $(DESTDIR)$(OMD_ROOT)/lib/nagios/p1.pl
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/doc/nagios/*
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/diskspace/nagios
	$(TOUCH) $@
