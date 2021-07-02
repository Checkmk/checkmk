PYTHON3_MODULES := python3-modules
# Use some pseudo version here. Don't use OMD_VERSION (would break the package cache)
PYTHON3_MODULES_VERS := 1.1
PYTHON3_MODULES_DIR := $(PYTHON3_MODULES)-$(PYTHON3_MODULES_VERS)
# Increase the number before the "-" to enforce a recreation of the build cache
PYTHON3_MODULES_BUILD_ID := 1-$(md5sum $(REPO_PATH)/Pipfile.lock | cut -d' ' -f1)

PYTHON3_MODULES_UNPACK:= $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-unpack
PYTHON3_MODULES_PATCHING := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-patching
PYTHON3_MODULES_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-build
PYTHON3_MODULES_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-install-intermediate
PYTHON3_MODULES_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-cache-pkg-process
PYTHON3_MODULES_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-install

PYTHON3_MODULES_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON3_MODULES_DIR)
PYTHON3_MODULES_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON3_MODULES_DIR)
PYTHON3_MODULES_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON3_MODULES_DIR)

# Used by other OMD packages
PACKAGE_PYTHON3_MODULES_DESTDIR    := $(PYTHON3_MODULES_INSTALL_DIR)
PACKAGE_PYTHON3_MODULES_PYTHONPATH := $(PACKAGE_PYTHON3_MODULES_DESTDIR)/lib/python3.8/site-packages

$(PYTHON3_MODULES_BUILD): $(PYTHON3_CACHE_PKG_PROCESS) $(OPENSSL_INTERMEDIATE_INSTALL) $(FREETDS_INTERMEDIATE_INSTALL) $(POSTGRESQL_INTERMEDIATE_INSTALL) $(PYTHON3_MODULES_PATCHING)
	$(RM) -r $(PYTHON3_MODULES_BUILD_DIR)
	$(MKDIR) $(PYTHON3_MODULES_BUILD_DIR)
	$(MKDIR) $(BUILD_HELPER_DIR)
# rpath: Create some dummy rpath which has enough space for later replacement
# by the final rpath
	set -e ; cd $(PYTHON3_MODULES_BUILD_DIR) ; \
	    unset DESTDIR MAKEFLAGS ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH)" ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_PYTHONPATH)" ; \
	    export CPATH="$(PACKAGE_FREETDS_DESTDIR)/include:$(PACKAGE_OPENSSL_INCLUDE_PATH):$(PACKAGE_POSTGRESQL_INCLUDE_PATH)" ; \
	    export LDFLAGS="-Wl,--rpath,/omd/versions/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/lib $(PACKAGE_PYTHON3_LDFLAGS) $(PACKAGE_FREETDS_LDFLAGS) $(PACKAGE_OPENSSL_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH):$(PACKAGE_OPENSSL_LD_LIBRARY_PATH):$(PACKAGE_POSTGRESQL_LD_LIBRARY_PATH)" ; \
	    export PATH="$(PACKAGE_PYTHON3_BIN):$(PACKAGE_POSTGRESQL_BIN):$$PATH" ; \
	    PIPENV_PIPFILE="$(REPO_PATH)/Pipfile" \
	    `: rrdtool module is built with rrdtool omd package` \
		pipenv lock -r | grep -v rrdtool > requirements-dist.txt ; \
	    $(PACKAGE_PYTHON3_EXECUTABLE) -m pip install \
		`: dont use precompiled things, build with our build env ` \
		--no-binary=":all:" \
		--no-deps \
		--compile \
		--isolated \
		--ignore-installed \
		--no-warn-script-location \
		--prefix="$(PYTHON3_MODULES_INSTALL_DIR)" \
		-r requirements-dist.txt
# For some highly obscure unknown reason some files end up world-writable. Fix that!
	chmod -R o-w $(PYTHON3_MODULES_INSTALL_DIR)/lib/python3.8/site-packages
# Cleanup some unwanted files (example scripts)
	find $(PYTHON3_MODULES_INSTALL_DIR)/bin -name \*.py ! -name snmpsimd.py -exec rm {} \;
# These files break the integration tests on the CI server. Don't know exactly
# why this happens only there, but should be a working fix.
	$(RM) -r $(PYTHON3_MODULES_INSTALL_DIR)/snmpsim
# Fix python interpreter for kept scripts
	$(SED) -i '1s|^#!.*/python3$$|#!/usr/bin/env python3|' $(PYTHON3_MODULES_INSTALL_DIR)/bin/[!_]*
	$(TOUCH) $@

$(PYTHON3_MODULES_PATCHING): $(PYTHON3_MODULES_UNPACK)
	$(TOUCH) $@

$(PYTHON3_MODULES_UNPACK):
	$(TOUCH) $@

$(PYTHON3_MODULES_INTERMEDIATE_INSTALL): $(PYTHON3_MODULES_BUILD)
	$(TOUCH) $@

PYTHON3_MODULES_CACHE_PKG_PATH := $(call cache_pkg_path,$(PYTHON3_MODULES_DIR),$(PYTHON3_MODULES_BUILD_ID))

$(PYTHON3_MODULES_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PYTHON3_MODULES_DIR),$(PYTHON3_MODULES_BUILD_ID),$(PYTHON3_MODULES_INTERMEDIATE_INSTALL))

$(PYTHON3_MODULES_CACHE_PKG_PROCESS): $(PYTHON3_MODULES_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PYTHON3_MODULES_CACHE_PKG_PATH),$(PYTHON3_MODULES_DIR))
	$(call upload_pkg_archive,$(PYTHON3_MODULES_CACHE_PKG_PATH),$(PYTHON3_MODULES_DIR),$(PYTHON3_MODULES_BUILD_ID))
# Ensure that the rpath of the python binary and dynamic libs always points to the current version path
	set -e ; for F in $$(find $(PYTHON3_MODULES_INSTALL_DIR) -name \*.so); do \
	    chrpath -r "$(OMD_ROOT)/lib" $$F; \
	    echo -n "Test rpath of $$F..." ; \
		if chrpath "$$F" | grep "=$(OMD_ROOT)/lib" >/dev/null 2>&1; then \
		    echo OK ; \
		else \
		    echo "ERROR ($$(chrpath $$F))"; \
		    exit 1 ; \
		fi \
	done
	$(TOUCH) $@

$(PYTHON3_MODULES_INSTALL): $(PYTHON3_MODULES_CACHE_PKG_PROCESS)
	$(RSYNC) -v $(PYTHON3_MODULES_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
