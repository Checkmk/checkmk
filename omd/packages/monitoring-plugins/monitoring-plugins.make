MONITORING_PLUGINS := monitoring-plugins

MONITORING_PLUGINS_INSTALL := $(BUILD_HELPER_DIR)/$(MONITORING_PLUGINS)-install

.PHONY: $(MONITORING_PLUGINS_INSTALL)
$(MONITORING_PLUGINS_INSTALL):
	# run the Bazel build process which does all the dependency stuff
	bazel build @$(MONITORING_PLUGINS)//:$(MONITORING_PLUGINS)

	# THIS IS ALL HACKY WORKAROUND STUFF - BETTER GET RID OF IT BY LETTING
	# BAZEL HANDLE ALL THIS RATHER THAN MODIFYING IT!
	#
	# Basically we create a temporary directory we're allowed to write to,
	# copy all files we want and apply all needed modifications and move
	# them over to "$(DESTDIR)$(OMD_ROOT)/" afterwards
	$(eval TMP_DIR := $(shell mktemp -d))
	# copy over all the plugins we built
	mkdir -p "$(TMP_DIR)/lib/nagios"
	$(RSYNC) -r --chmod=u+w \
	    "$(BAZEL_BIN_EXT)/$(MONITORING_PLUGINS)/$(MONITORING_PLUGINS)/libexec/" \
	    "$(TMP_DIR)/lib/nagios/plugins/"
	# copy locales and 'documentation'
	$(RSYNC) -r --chmod=u+w \
	    "$(BAZEL_BIN_EXT)/$(MONITORING_PLUGINS)/$(MONITORING_PLUGINS)/share/" \
	    "$(TMP_DIR)/share/"
	# set RPATH for all ELF binaries we find
	find "$(TMP_DIR)/lib/nagios/plugins/" -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../../../lib"
	ln -sf check_icmp "$(TMP_DIR)/lib/nagios/plugins/check_host"
	$(RSYNC) "$(TMP_DIR)/" "$(DESTDIR)$(OMD_ROOT)/"

	rm -rf $(TMP_DIR)
