SHELL := bash
.SHELLFLAGS := -o pipefail -c

CHECK_MK := check_mk
CHECK_MK_DIR := $(CHECK_MK)-$(CMK_VERSION)

CHECK_MK_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-install-intermediate
CHECK_MK_INSTALL := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-install
CHECK_MK_PATCHING := $(BUILD_HELPER_DIR)/$(CHECK_MK_DIR)-patching

CHECK_MK_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(CHECK_MK_DIR)
CHECK_MK_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(CHECK_MK_DIR)
CHECK_MK_WORK_DIR := $(PACKAGE_WORK_DIR)/$(CHECK_MK_DIR)

CHECK_MK_TAROPTS := \
	--owner=root --group=root --exclude=.svn --exclude=*~ \
	--exclude=.gitignore --exclude=.editorconfig --exclude=*.swp --exclude=.f12 \
	--exclude=__pycache__ --exclude=*.pyc

# It is used from top-level Makefile and this makefile as an intermediate step.
# We should end up with one central place to care for packaging our files
# without the need to have shared logic between like this.
include ../artifacts.make

# RPM/DEB build are currently working on the same working directory and would
# influence each other. Need to be cleaned up later
.NOTPARALLEL: $(SOURCE_BUILT_AGENTS)

$(SOURCE_BUILT_AGENTS):
ifneq ($(CI),)
	@echo "ERROR: Should have been built by source stage (top level: 'make dist')" ; exit 1
endif
	$(MAKE) -C $(REPO_PATH) $@

ADDITIONAL_EXCLUDE=--exclude "BUILD.*" --exclude "BUILD" --exclude "OWNERS"

EDITION_EXCLUDE=
ifeq ($(EDITION),community)
	EDITION_EXCLUDE += \
	    --exclude "non-free" \
	    --exclude "nonfree" \
	    --exclude "enterprise" \
	    --exclude "pro"
endif
ifneq ($(EDITION),ultimatemt)
	EDITION_EXCLUDE += \
	    --exclude "ultimatemt"
endif
ifeq ($(filter $(EDITION),ultimate cloud ultimatemt),)
	EDITION_EXCLUDE += \
	    --exclude "ultimate"
endif
ifeq ($(filter $(EDITION),cloud),)
	EDITION_EXCLUDE += \
	    --exclude "cloud"
endif

$(CHECK_MK_INTERMEDIATE_INSTALL): $(SOURCE_BUILT_AGENTS)
	$(MKDIR) $(CHECK_MK_INSTALL_DIR)/share/check_mk/agents
	tar -c -C $(REPO_PATH)/agents \
	    $(CHECK_MK_TAROPTS) \
	    --exclude __init__.py \
	    --exclude check_mk_agent.spec \
	    --exclude plugins/Makefile \
	    --exclude plugins/*.checksum \
	    --exclude plugins/__init__.py \
	    $(ADDITIONAL_EXCLUDE) \
	    cfg_examples \
	    plugins \
	    sap \
	    scripts \
	    z_os \
	    check-mk-agent_$(CMK_VERSION)-1_all.deb \
	    check-mk-agent-$(CMK_VERSION)-1.noarch.rpm \
	    linux \
	    windows/cfg_examples \
	    windows/check_mk_agent.msi \
	    windows/unsign-msi.patch \
	    windows/python-3.cab \
	    windows/check_mk.user.yml \
	    windows/robotmk_ext.exe \
	    windows/mk-sql.exe \
	    windows/windows_files_hashes.txt \
	    windows/mrpe \
	    windows/plugins \
	    | tar -x -C $(CHECK_MK_INSTALL_DIR)/share/check_mk/agents/

	$(MKDIR) $(CHECK_MK_INSTALL_DIR)/lib/python3
	tar -c -C $(REPO_PATH) \
	    $(CHECK_MK_TAROPTS) \
	    $(EDITION_EXCLUDE) \
	    $(ADDITIONAL_EXCLUDE) \
	    cmk | tar -x -C $(CHECK_MK_INSTALL_DIR)/lib/python3

	# legacy checks have been moved to checks/ in a dedicated step above.
	rm -rf $(CHECK_MK_INSTALL_DIR)/lib/python3/cmk/base/legacy_checks

	# cmk needs to be a namespace package (CMK-3979)
	grep -Rl 'check_mk.make: do-not-deploy' $(CHECK_MK_INSTALL_DIR)/lib/python3/ | xargs rm

$(CHECK_MK_INSTALL): $(CHECK_MK_INTERMEDIATE_INSTALL)
	$(RSYNC) $(CHECK_MK_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
