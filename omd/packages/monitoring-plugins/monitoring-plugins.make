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

	# copy over all the plugins we built
	$(RSYNC) -r --chmod=u+w \
	    "bazel-bin/external/monitoring-plugins/monitoring-plugins/libexec/" \
	    "$(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/"

	# copy locales and 'documentation'
	$(RSYNC) -r --chmod=u+w \
	    "bazel-bin/external/monitoring-plugins/monitoring-plugins/share/" \
	    "$(DESTDIR)$(OMD_ROOT)/share/"

	# set RPATH for all ELF binaries we find
	find "$(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/" -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../../../lib"

	ln -sf check_icmp "$(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/check_host"

