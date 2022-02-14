include $(REPO_PATH)/defines.make
include $(REPO_PATH)/buildscripts/infrastructure/pypi_mirror/pypi_mirror.make

PYTHON3_MODULES := python3-modules
# Use some pseudo version here. Don't use OMD_VERSION (would break the package cache)
PYTHON3_MODULES_VERS := 1.1
PYTHON3_MODULES_DIR := $(PYTHON3_MODULES)-$(PYTHON3_MODULES_VERS)
# Increase the number before the "-" to enforce a recreation of the build cache
PYTHON3_MODULES_BUILD_ID := 10-$(shell md5sum $(REPO_PATH)/Pipfile.lock | cut -d' ' -f1)

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
PACKAGE_PYTHON3_MODULES_PYTHONPATH := $(PACKAGE_PYTHON3_MODULES_DESTDIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/site-packages
# May be used during omd package build time. Call sites have to use the target
# dependency "$(PACKAGE_PYTHON3_MODULES_PYTHON_DEPS)" to have everything needed in place.
PACKAGE_PYTHON3_MODULES_PYTHON         := \
	PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH):$(PACKAGE_PYTHON_PYTHONPATH)" \
	LDFLAGS="$$LDFLAGS $(PACKAGE_PYTHON_LDFLAGS)" \
	LD_LIBRARY_PATH="$$LD_LIBRARY_PATH:$(PACKAGE_PYTHON_LD_LIBRARY_PATH):$(PACKAGE_OPENSSL_LD_LIBRARY_PATH)" \
	$(PACKAGE_PYTHON_EXECUTABLE)
PACKAGE_PYTHON3_MODULES_PYTHON_DEPS    := \
	$(OPENSSL_CACHE_PKG_PROCESS) \
	$(PYTHON_CACHE_PKG_PROCESS) \
	$(PYTHON3_MODULES_CACHE_PKG_PROCESS)

$(PYTHON3_MODULES_BUILD): $(PYTHON_CACHE_PKG_PROCESS) $(OPENSSL_CACHE_PKG_PROCESS) $(FREETDS_CACHE_PKG_PROCESS) $(PYTHON3_MODULES_PATCHING)
	$(RM) -r $(PYTHON3_MODULES_BUILD_DIR)
	$(MKDIR) $(PYTHON3_MODULES_BUILD_DIR)
	$(MKDIR) $(BUILD_HELPER_DIR)
	set -e ; cd $(PYTHON3_MODULES_BUILD_DIR) ; \
	    PIPENV_PIPFILE="$(REPO_PATH)/Pipfile" \
            PIPENV_PYPI_MIRROR=$(PIPENV_PYPI_MIRROR)/simple \
	    `: rrdtool module is built with rrdtool omd package` \
	    `: protobuf module is built with protobuf omd package` \
	    `: fixup git local dependencies` \
		pipenv lock -r | grep -Ev '(protobuf|rrdtool)' | sed 's|-e \.\/\(.*\)|$(REPO_PATH)\/\1|g' > requirements-dist.txt ; \
# rpath: Create some dummy rpath which has enough space for later replacement
# by the final rpath
	set -e ; cd $(PYTHON3_MODULES_BUILD_DIR) ; \
	    unset DESTDIR MAKEFLAGS ; \
	    $(EXPORT_ORIG_GCC) ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH)" ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	    export CPATH="$(PACKAGE_FREETDS_DESTDIR)/include:$(PACKAGE_OPENSSL_INCLUDE_PATH)" ; \
	    export LDFLAGS="-Wl,--rpath,/omd/versions/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/lib $(PACKAGE_PYTHON_LDFLAGS) $(PACKAGE_FREETDS_LDFLAGS) $(PACKAGE_OPENSSL_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH):$(PACKAGE_OPENSSL_LD_LIBRARY_PATH)" ; \
	    export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	    $(PACKAGE_PYTHON_EXECUTABLE) -m pip install \
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
	chmod -R o-w $(PYTHON3_MODULES_INSTALL_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/site-packages
# Cleanup some unwanted files (example scripts)
	find $(PYTHON3_MODULES_INSTALL_DIR)/bin -name \*.py ! -name snmpsimd.py -exec rm {} \;
# These files break the integration tests on the CI server. Don't know exactly
# why this happens only there, but should be a working fix.
	$(RM) -r $(PYTHON3_MODULES_INSTALL_DIR)/snmpsim
# Fix python interpreter for kept scripts
	$(SED) -i '1s|^#!.*/python3$$|#!/usr/bin/env python3|' $(PYTHON3_MODULES_INSTALL_DIR)/bin/[!_]*
# pip is using pip._vendor.distlib.scripts.ScriptMaker._build_shebang() to
# build the shebang of the scripts installed to bin. When executed via our CI
# containers, the shebang exceeds the max_shebang_length of 127 bytes. For this
# case, it adds a #!/bin/sh wrapper in front of the python code o_O to make it
# fit into the shebang. Let's also cleanup this case.
	$(SED) -i -z "s|^#\!/bin/sh\n'''exec.*python3 \"\$$0\" \"\$$@\"\n' '''|#\!/usr/bin/env python3|" $(PYTHON3_MODULES_INSTALL_DIR)/bin/[!_]*
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
	    patchelf --set-rpath "$(OMD_ROOT)/lib" $$F; \
	    echo -n "Test rpath of $$F..." ; \
		if patchelf --print-rpath "$$F" | grep "$(OMD_ROOT)/lib" >/dev/null 2>&1; then \
		    echo OK ; \
		else \
		    echo "ERROR ($$(patchelf --print-rpath $$F))"; \
		    exit 1 ; \
		fi \
	done
	$(TOUCH) $@

$(PYTHON3_MODULES_INSTALL): $(PYTHON3_MODULES_CACHE_PKG_PROCESS)
	$(RSYNC) -v $(PYTHON3_MODULES_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
