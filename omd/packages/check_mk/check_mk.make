CHECK_MK := check_mk
CHECK_MK_DIR := $(CHECK_MK)-$(CMK_VERSION)

CHECK_MK_BUILD := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-build
CHECK_MK_INSTALL := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-install
CHECK_MK_PATCHING := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-patching

#CHECK_MK_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(CHECK_MK_DIR)
CHECK_MK_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(CHECK_MK_DIR)
#CHECK_MK_WORK_DIR := $(PACKAGE_WORK_DIR)/$(CHECK_MK_DIR)

CHECK_MK_LANGUAGES := de ro nl fr it ja pt_PT es

CHECK_MK_TAROPTS := --owner=root --group=root --exclude=.svn --exclude=*~ \
                    --exclude=.gitignore --exclude=*.swp --exclude=.f12 \
                    --exclude=__pycache__ --exclude=*.pyc

# It is used from top-level Makefile and this makefile as an intermediate step.
# We should end up with one central place to care for packaging our files
# without the need to have shared logic between like this.
include ../artifacts.make

$(CHECK_MK_RAW_PRECOMPILED_WERKS) $(REPO_PATH)/ChangeLog:
	$(MAKE) -C $(REPO_PATH) $@

# RPM/DEB build are currently working on the same working directory and would
# influence each other. Need to be cleaned up later
.NOTPARALLEL: $(SOURCE_BUILT_AGENTS)

$(SOURCE_BUILT_AGENTS) $(JAVASCRIPT_MINI) $(THEME_RESOURCES):
ifneq ($(CI),)
	@echo "ERROR: Should have been built by source stage (top level: 'make dist')" ; exit 1
endif
	$(MAKE) -C $(REPO_PATH) $@

$(CHECK_MK_BUILD): $(CHECK_MK_RAW_PRECOMPILED_WERKS) $(REPO_PATH)/ChangeLog $(JAVASCRIPT_MINI) $(THEME_RESOURCES)
	$(MKDIR) $(CHECK_MK_BUILD_DIR)
	$(MAKE) -C $(REPO_PATH)/locale mo
	$(MAKE) -C $(REPO_PATH)/bin
	$(MAKE) -C $(REPO_PATH)/active_checks
	$(MAKE) -C $(REPO_PATH)/doc/plugin-api html
	$(TOUCH) $@

EDITION_EXCLUDE=
ifeq ($(EDITION),raw)
	EDITION_EXCLUDE += \
	    --exclude "enterprise" \
	    --exclude "cee" \
	    --exclude "cee.py"
endif
ifneq ($(EDITION),managed)
	EDITION_EXCLUDE += \
	    --exclude "managed" \
	    --exclude "cme" \
	    --exclude "cme.py"
endif
ifneq ($(EDITION),plus)
	EDITION_EXCLUDE += \
	    --exclude "plus" \
	    --exclude "cpe" \
	    --exclude "cpe.py"
endif

$(CHECK_MK_INSTALL): $(SOURCE_BUILT_AGENTS) $(CHECK_MK_BUILD) $(PACKAGE_PYTHON3_MODULES_PYTHON_DEPS)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/werks
	install -m 644 $(CHECK_MK_RAW_PRECOMPILED_WERKS) $(DESTDIR)$(OMD_ROOT)/share/check_mk/werks

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/checks
	install -m 664 $(REPO_PATH)/checks/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/checks

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/notifications
	install -m 775 $(REPO_PATH)/notifications/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/notifications

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/web
	tar -c -C $(REPO_PATH)/web \
	    $(CHECK_MK_TAROPTS) \
            app \
            htdocs/openapi \
            htdocs/css \
            htdocs/images \
            htdocs/jquery \
            $(patsubst $(REPO_PATH)/web/%,%,$(JAVASCRIPT_MINI)) \
            $(patsubst $(REPO_PATH)/web/%,%.map,$(JAVASCRIPT_MINI)) \
            htdocs/sounds \
            $(patsubst $(REPO_PATH)/web/%,%,$(THEME_RESOURCES)) \
	    | tar -x -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/web

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk
	install -m 644 $(REPO_PATH)/{COPYING,AUTHORS,ChangeLog} $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk
	tar -c -C $(REPO_PATH)/doc $(CHECK_MK_TAROPTS) --exclude plugin-api \
	    . | tar -x -C $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk/
	tar -c -C $(REPO_PATH)/doc \
	    --transform "s/^plugin-api\/build/plugin-api/" \
	    plugin-api/build/html | tar -x -C $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk/
	tar -c -C $(REPO_PATH)/livestatus/api \
	    $(CHECK_MK_TAROPTS) \
	    . | tar -x -C $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk/livestatus/

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/checkman
	install -m 664 $(REPO_PATH)/checkman/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/checkman

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents
	tar -c -C $(REPO_PATH)/agents \
	    $(CHECK_MK_TAROPTS) \
	    --exclude __init__.py \
	    --exclude check_mk_agent.spec \
	    --exclude special/lib \
	    --exclude plugins/Makefile \
	    --exclude plugins/*.checksum \
	    --exclude plugins/__init__.py \
	    cfg_examples \
	    plugins \
	    sap \
	    scripts \
	    special \
	    z_os \
	    check-mk-agent_$(CMK_VERSION)-1_all.deb \
	    check-mk-agent-$(CMK_VERSION)-1.noarch.rpm \
	    check_mk_agent.aix \
	    check_mk_agent.freebsd \
	    check_mk_agent.hpux \
	    check_mk_agent.linux \
	    check_mk_agent.macosx \
	    check_mk_agent.netbsd \
	    check_mk_agent.openbsd \
	    check_mk_agent.openvms \
	    check_mk_agent.openwrt \
	    check_mk_agent.solaris \
	    check_mk_caching_agent.linux \
	    CONTENTS \
	    mk-job \
	    waitmax \
	    linux \
	    windows/cfg_examples \
	    windows/check_mk_agent.msi \
	    windows/unsign-msi.patch \
	    windows/python-3.cab \
	    windows/python-3.4.cab \
	    windows/check_mk.user.yml \
	    windows/OpenHardwareMonitorLib.dll \
	    windows/OpenHardwareMonitorCLI.exe \
	    windows/CONTENTS \
	    windows/mrpe \
	    windows/plugins \
	    | tar -x -C $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	tar -c -C $(REPO_PATH)/bin \
	    $(CHECK_MK_TAROPTS) \
	    --exclude Makefile \
	    --exclude *.cc \
	    . | tar -x -C $(DESTDIR)$(OMD_ROOT)/bin

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/python3
	tar -C $(REPO_PATH) -c \
	    $(CHECK_MK_TAROPTS) \
	    $(EDITION_EXCLUDE) \
	    cmk | tar -x -C $(DESTDIR)$(OMD_ROOT)/lib/python3

	# cmk needs to be a namespace package (CMK-3979)
	rm -f \
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
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/raw/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/raw/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/dashboard/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/config/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/cron/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/userdb/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/bi/__init__.py \
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
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/plugins/wato/check_parameters/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/update_config/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/update_config/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/update_config/plugins/actions/__init__.py \
	    \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/dcd/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/dcd/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/dcd/plugins/connectors/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/post_rename_site/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/post_rename_site/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/post_rename_site/plugins/actions/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/update_config/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/update_config/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/cee/update_config/plugins/actions/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/cee/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/cee/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/cee/plugins/bakery/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/cee/bakery/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/cee/bakery/core_bakelets/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/cee/bakery/core_bakelets/cpe/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cee/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cee/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cee/plugins/sla/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cee/plugins/reporting/__init__.py \
	    \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cpe/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cpe/plugins/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cpe/plugins/wato/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cpe/plugins/wato/check_parameters/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/gui/cpe/plugins/wato/watolib/__init__.py \
	    $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk/base/cpe/plugins/agent_based/__init__.py

	# After installing all python modules, ensure they are compiled
	$(PACKAGE_PYTHON3_MODULES_PYTHON) -m compileall $(DESTDIR)$(OMD_ROOT)/lib/python3/cmk

	# Provide the externally documented paths for Checkmk plugins
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib
	$(LN) -sf python3/cmk $(DESTDIR)$(OMD_ROOT)/lib/check_mk
	# ... and ensure the same for the local hierarchy
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/skel/local/lib/python3/cmk
	$(LN) -sf python3/cmk $(DESTDIR)$(OMD_ROOT)/skel/local/lib/check_mk
	# Create the plugin namespaces
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/skel/local/lib/python3/cmk/base/plugins/agent_based
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/skel/local/lib/python3/cmk/special_agents

	# Install the diskspace cleanup plugin
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/diskspace
	install -m 644 $(PACKAGE_DIR)/$(CHECK_MK)/diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/check_mk

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	tar -c -C $(REPO_PATH)/active_checks \
	    $(CHECK_MK_TAROPTS) \
	    --exclude Makefile \
	    --exclude *.cc \
	    . | tar -x -C $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins

	# Install localizations
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale
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
