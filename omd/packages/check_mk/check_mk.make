CHECK_MK := check_mk
CHECK_MK_DIR := $(CHECK_MK)-$(CMK_VERSION)

CHECK_MK_BUILD := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-build
CHECK_MK_INSTALL := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-install
CHECK_MK_SKEL := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-skel
CHECK_MK_PATCHING := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-patching

.PHONY: $(CHECK_MK) $(CHECK_MK)-install $(CHECK_MK)-skel $(CHECK_MK)-clean

$(CHECK_MK): $(CHECK_MK_BUILD)

$(CHECK_MK)-install: $(CHECK_MK_INSTALL)
$(CHECK_MK)-skel: $(CHECK_MK_SKEL)

# This step creates a tar archive containing the sources
# which are need for the build step
$(REPO_PATH)/$(CHECK_MK_DIR).tar.gz:
	    $(MAKE) -C $(REPO_PATH) $(CHECK_MK_DIR).tar.gz ; \

# The build step just extracts the archive
# which was created in the step before
$(CHECK_MK_BUILD): $(REPO_PATH)/$(CHECK_MK_DIR).tar.gz
	$(MAKE) -C $(REPO_PATH)/locale all
	$(TAR_GZ) $(REPO_PATH)/$(CHECK_MK_DIR).tar.gz
	cd $(CHECK_MK_DIR) ; \
	  $(MKDIR) bin ; \
	  cd bin ; \
	  $(TAR_GZ) ../bin.tar.gz ; \
	  $(MAKE)
	cd $(CHECK_MK_DIR) ; \
	  $(MKDIR) active_checks ; \
	  cd active_checks ; \
	  $(TAR_GZ) ../active_checks.tar.gz ; \
	  $(MAKE)
	$(TOUCH) $@

$(CHECK_MK_INSTALL): $(CHECK_MK_BUILD)
	export bindir='$(OMD_ROOT)/bin' ; \
	export sharedir='$(OMD_ROOT)/share/check_mk' ; \
	export checksdir='$(OMD_ROOT)/share/check_mk/checks' ; \
	export modulesdir='$(OMD_ROOT)/share/check_mk/modules' ; \
	export web_dir='$(OMD_ROOT)/share/check_mk/web' ; \
	export mibsdir='$(OMD_ROOT)/share/snmp/mibs' ; \
	export docdir='$(OMD_ROOT)/share/doc/check_mk' ; \
	export checkmandir='$(OMD_ROOT)/share/check_mk/checkman' ; \
	export agentsdir='$(OMD_ROOT)/share/check_mk/agents' ; \
	export agentslibdir='/usr/lib/check_mk_agent' ; \
	export nagios_binary='$(OMD_ROOT)/bin/nagios' ; \
	export check_icmp_path='$(OMD_ROOT)/lib/nagios/plugins/check_icmp' ; \
	export pnptemplates='$(OMD_ROOT)/share/check_mk/pnp-templates' ; \
	export livebackendsdir='$(OMD_ROOT)/share/check_mk/livestatus' ; \
	export libdir='$(OMD_ROOT)/lib/check_mk' ; \
	export python_lib_dir='$(OMD_ROOT)/lib/python' ; \
	export confdir='$(OMD_ROOT)/skel/etc/check_mk' ; \
	export pnpconfdir='$(OMD_ROOT)/skel/etc/pnp4nagios' ; \
	export pnprraconf='$(OMD_ROOT)/share/check_mk/pnp-rraconf' ; \
	export apache_config_dir='/REMOVE/skel/etc/apache' ; \
	export agentsconfdir='/etc/check_mk' ; \
	export vardir='/REMOVE/var/lib/check_mk' ; \
	export nagios_config_file='/REMOVE/etc/nagios/nagios.cfg' ; \
	export nagconfdir='/REMOVE/etc/nagios/conf.d' ; \
	export htpasswd_file='/REMOVE/etc/nagios/htpasswd' ; \
	export nagios_startscript='/REMOVE/etc/init.d/nagios' ; \
	export nagpipe='/REMOVE/var/run/nagios/rw/nagios.cmd' ; \
	export rrddir='/REMOVE/var/lib/nagios/rrd' ; \
	export nagios_status_file='/REMOVE/var/spool/nagios/status.dat' ; \
	export livesock='/REMOVE/var/run/nagios/rw/live' ; \
	export checkmk_web_uri='/nag01/check_mk' ; \
	export nagiosurl='/nag01/nagios' ; \
	export cgiurl='/nag01/nagios/cgi-bin' ; \
	export pnp_url='/nag01/pnp4nagios/' ; \
	export enable_livestatus='no' ; \
	export nagios_auth_name='Nagios Access' ; \
	export nagiosuser='nagios' ; \
	export wwwgroup='nagios' ; \
	cd $(CHECK_MK_DIR) ; DESTDIR=$(DESTDIR) ./setup.sh --yes

	# Delete files we do not want to package
	$(RM) -r $(DESTDIR)/REMOVE
	$(RM) $(DESTDIR)$(OMD_ROOT)/skel/etc/check_mk/*-*.mk

	# Binaries
	install -m 755 $(CHECK_MK_DIR)/bin/* $(DESTDIR)$(OMD_ROOT)/bin
	$(RM) $(DESTDIR)$(OMD_ROOT)/bin/Makefile $(DESTDIR)$(OMD_ROOT)/bin/*.cc

	# Install the diskspace cleanup plugin
	install -m 644 $(PACKAGE_DIR)/$(CHECK_MK)/diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/check_mk

	# Install active checks
	install -m 755 $(CHECK_MK_DIR)/active_checks/* \
	    $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	$(RM) $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/Makefile
	$(RM) $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/*.cc
	chmod 755 $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/*

	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/de/LC_MESSAGES
	install -m 644 $(REPO_PATH)/locale/de/LC_MESSAGES/multisite.mo $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/de/LC_MESSAGES
	install -m 644 $(REPO_PATH)/locale/de/alias $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/de
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/ro/LC_MESSAGES
	install -m 644 $(REPO_PATH)/locale/ro/LC_MESSAGES/multisite.mo $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/ro/LC_MESSAGES
	install -m 644 $(REPO_PATH)/locale/ro/alias $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/ro

	# Install hooks
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MKEVENTD $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MKEVENTD_SNMPTRAP $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MKEVENTD_SYSLOG $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MKEVENTD_SYSLOG_TCP $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MULTISITE_AUTHORISATION $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MULTISITE_COOKIE_AUTH $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/update-pre-hooks
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/cmk.update-pre-hooks $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/update-pre-hooks

	# GUI-Test (in doc/helpers)
	#$(TAR_GZ) $(CHECK_MK_DIR)/doc.tar.gz -C $(DESTDIR)$(OMD_ROOT)/bin \
	#    --strip-components 1 helpers/guitest
	#chmod +x $(DESTDIR)$(OMD_ROOT)/bin/*
	$(TOUCH) $@

$(CHECK_MK_SKEL): $(CHECK_MK_INSTALL)
	$(RM) $(SKEL)/etc/check_mk/main.mk-*
	$(RM) $(SKEL)/etc/check_mk/multisite.mk-*
	$(TOUCH) $@

$(CHECK_MK)-clean:
	$(RM) -r check_mk-*.*.*[0-9] werks ChangeLog $(BUILD_HELPER_DIR)/$(CHECK_MK)*
