CHECK_MK := check_mk
CHECK_MK_DIR := $(CHECK_MK)-$(CMK_VERSION)

CHECK_MK_BUILD := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-build
CHECK_MK_INSTALL := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-install
CHECK_MK_PATCHING := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-patching

#CHECK_MK_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(CHECK_MK_DIR)
CHECK_MK_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(CHECK_MK_DIR)
#CHECK_MK_WORK_DIR := $(PACKAGE_WORK_DIR)/$(CHECK_MK_DIR)

CHECK_MK_LANGUAGES := de ro nl fr it ja pt_PT es

# This step creates a tar archive containing the sources
# which are need for the build step
$(REPO_PATH)/$(CHECK_MK_DIR).tar.gz:
	$(MAKE) -C $(REPO_PATH) $(CHECK_MK_DIR).tar.gz

# The build step just extracts the archive
# which was created in the step before
$(CHECK_MK_BUILD): $(REPO_PATH)/$(CHECK_MK_DIR).tar.gz
	$(MKDIR) $(CHECK_MK_BUILD_DIR)
	$(MAKE) -C $(REPO_PATH)/locale mo
	$(TAR_GZ) $(REPO_PATH)/$(CHECK_MK_DIR).tar.gz -C $(PACKAGE_BUILD_DIR)
	cd $(CHECK_MK_BUILD_DIR) ; \
	  $(MKDIR) bin ; \
	  cd bin ; \
	  $(TAR_GZ) ../bin.tar.gz ; \
	  $(MAKE)
	cd $(CHECK_MK_BUILD_DIR) ; \
	  $(MKDIR) active_checks ; \
	  cd active_checks ; \
	  $(TAR_GZ) ../active_checks.tar.gz ; \
	  $(MAKE)
	$(TOUCH) $@

$(CHECK_MK_INSTALL): $(CHECK_MK_BUILD) $(PACKAGE_PYTHON3_MODULES_PYTHON_DEPS)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/werks
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/werks.tar.gz -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/werks

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/checks
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/checks.tar.gz -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/checks

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/active_checks.tar.gz -C $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/notifications
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/notifications.tar.gz -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/notifications

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/inventory
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/inventory.tar.gz -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/inventory

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/web
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/web.tar.gz -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/web

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/doc.tar.gz -C $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/checkman
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/checkman.tar.gz -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/checkman

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents
	$(TAR_GZ) $(CHECK_MK_BUILD_DIR)/agents.tar.gz -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents

	# Binaries
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(CHECK_MK_BUILD_DIR)/bin/* $(DESTDIR)$(OMD_ROOT)/bin
	$(RM) $(DESTDIR)$(OMD_ROOT)/bin/Makefile $(DESTDIR)$(OMD_ROOT)/bin/*.cc

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/python3
	tar -xz -C $(DESTDIR)$(OMD_ROOT)/lib/python3 -f $(CHECK_MK_BUILD_DIR)/lib.tar.gz
	# cmk needs to be a namespace package (CMK-3979)
	rm \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/special_agents/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/check_legacy_includes/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/plugins/agent_based/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/plugins/agent_based/utils/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/post_rename_site/__init__.py \
    	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/post_rename_site/plugins/__init__.py \
    	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/post_rename_site/plugins/actions/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/dashboard/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/config/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/cron/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/userdb/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/bi/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/webapi/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/watolib/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/openapi/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/openapi/endpoints/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/sidebar/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/views/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/views/icons/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/views/perfometers/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/visuals/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/metrics/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/wato/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/wato/check_parameters/__init__.py

	# After installing all python modules, ensure they are compiled
	$(PACKAGE_PYTHON3_MODULES_PYTHON) -m compileall $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk

	# Provide the externally documented paths for Checkmk plugins
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib
	$(LN) -s python3/cmk $(DESTDIR)$(OMD_ROOT)/lib/check_mk
	# ... and ensure the same for the local hierarchy
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/skel/local/lib/python3/cmk
	$(LN) -s python3/cmk $(DESTDIR)$(OMD_ROOT)/skel/local/lib/check_mk
	# Create the plugin namespaces
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/skel/local/lib/python3/cmk/base/plugins/agent_based
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/skel/local/lib/python3/cmk/special_agents

	# Install the diskspace cleanup plugin
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/diskspace
	install -m 644 $(PACKAGE_DIR)/$(CHECK_MK)/diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/check_mk

	# Install active checks
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/nagios
	install -m 755 $(CHECK_MK_BUILD_DIR)/active_checks/* \
	    $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	$(RM) $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/Makefile
	$(RM) $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/*.cc
	chmod 755 $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/*

	# Install localizations
	for lang in $(CHECK_MK_LANGUAGES) ; do \
		$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/$$lang/LC_MESSAGES ; \
		install -m 644 $(REPO_PATH)/locale/$$lang/LC_MESSAGES/multisite.mo $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/$$lang/LC_MESSAGES ; \
		install -m 644 $(REPO_PATH)/locale/$$lang/alias $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/$$lang ; \
	done

	# Install hooks
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/AGENT_RECEIVER $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/AGENT_RECEIVER_PORT $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MKEVENTD $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MKEVENTD_SNMPTRAP $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MKEVENTD_SYSLOG $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MKEVENTD_SYSLOG_TCP $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MULTISITE_AUTHORISATION $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/MULTISITE_COOKIE_AUTH $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-create
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/post-create/01_create-sample-config.py $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-create/

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/update-pre-hooks
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/scripts/update-pre-hooks/01_mkp-disable-outdated $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/update-pre-hooks/
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/scripts/update-pre-hooks/02_cmk-update-config $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/update-pre-hooks/
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-mv
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/scripts/post-mv/01_cmk-post-rename-site $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-mv/
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-cp
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/scripts/post-cp/01_cmk-post-rename-site $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-cp/
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-restore
	install -m 755 $(PACKAGE_DIR)/$(CHECK_MK)/scripts/post-restore/01_cmk-post-rename-site $(DESTDIR)$(OMD_ROOT)/lib/omd/scripts/post-restore/

	$(TOUCH) $@
