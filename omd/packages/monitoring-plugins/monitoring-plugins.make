MONITORING_PLUGINS := monitoring-plugins
# also listed in WORKSPACE
MONITORING_PLUGINS_VERS := 2.3.2

MONITORING_PLUGINS_DIR := $(MONITORING_PLUGINS)-$(MONITORING_PLUGINS_VERS)
MONITORING_PLUGINS_INSTALL := $(BUILD_HELPER_DIR)/$(MONITORING_PLUGINS_DIR)-install

# on Centos8 we don't build our own OpenSSL, so we have to inform the build about it
ifeq ($(DISTRO_CODE),el8)
OPTIONAL_BUILD_ARGS := BAZEL_EXTRA_ARGS="--define no-own-openssl=true"
endif

$(MONITORING_PLUGINS_INSTALL):
	# run the Bazel build process which does all the dependency stuff
	$(OPTIONAL_BUILD_ARGS) $(BAZEL_BUILD) @monitoring-plugins//:monitoring-plugins

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
	    "bazel-bin/external/monitoring-plugins/monitoring-plugins/libexec/" \
	    "$(TMP_DIR)/lib/nagios/plugins/"
	# copy locales and 'documentation'
	$(RSYNC) -r --chmod=u+w \
	    "bazel-bin/external/monitoring-plugins/monitoring-plugins/share/" \
	    "$(TMP_DIR)/share/"
	# set RPATH for all ELF binaries we find
	find "$(TMP_DIR)/lib/nagios/plugins/" -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../../../lib"
	ln -sf check_icmp "$(TMP_DIR)/lib/nagios/plugins/check_host"
	$(RSYNC) "$(TMP_DIR)/" "$(DESTDIR)$(OMD_ROOT)/"

	rm -rf $(TMP_DIR)

