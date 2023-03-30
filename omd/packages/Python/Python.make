include $(REPO_PATH)/defines.make

# Package definition
PYTHON := Python
PYTHON_DIR := Python-$(PYTHON_VERSION)

PYTHON_DEPS := \
    $(REPO_PATH)/omd/packages/Python/Python.make \
    $(REPO_PATH)/omd/packages/Python/sitecustomize.py

# Increase the number before the "-" to enforce a recreation of the build cache
PYTHON_BUILD_ID := $(call cache_pkg_build_id,5,$(PYTHON_DEPS))

PYTHON_UNPACK := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-unpack
PYTHON_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-build
PYTHON_COMPILE := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-compile
PYTHON_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install-intermediate
PYTHON_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-cache-pkg-process
PYTHON_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install
PYTHON_SYSCONFIGDATA := _sysconfigdata__linux_x86_64-linux-gnu.py

PYTHON_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)
PYTHON_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON_DIR)
PYTHON_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON_DIR)

# Used by other OMD packages
PACKAGE_PYTHON_DESTDIR         := $(PYTHON_INSTALL_DIR)
PACKAGE_PYTHON_PYTHONPATH      := $(PACKAGE_PYTHON_DESTDIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)
PACKAGE_PYTHON_LDFLAGS         := -L$(PACKAGE_PYTHON_DESTDIR)/lib -L$(PACKAGE_PYTHON_PYTHONPATH)/config
PACKAGE_PYTHON_LD_LIBRARY_PATH := $(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_INCLUDE_PATH    := $(PACKAGE_PYTHON_DESTDIR)/include/python$(PYTHON_MAJOR_DOT_MINOR)
PACKAGE_PYTHON_BIN             := $(PACKAGE_PYTHON_DESTDIR)/bin
PACKAGE_PYTHON_EXECUTABLE      := $(PACKAGE_PYTHON_BIN)/python3
PACKAGE_PYTHON_SYSCONFIGDATA := $(PACKAGE_PYTHON_PYTHONPATH)/$(PYTHON_SYSCONFIGDATA)

# HACK!
PYTHON_PACKAGE_DIR := $(PACKAGE_DIR)/$(PYTHON)
PYTHON_SITECUSTOMIZE_SOURCE := $(PYTHON_PACKAGE_DIR)/sitecustomize.py
PYTHON_SITECUSTOMIZE_WORK := $(PYTHON_WORK_DIR)/sitecustomize.py
PYTHON_SITECUSTOMIZE_COMPILED := $(PYTHON_WORK_DIR)/__pycache__/sitecustomize.cpython-$(PYTHON_MAJOR_MINOR).pyc
PYTHON_PIP_WRAPPER_SOURCE := $(PYTHON_PACKAGE_DIR)/pip
PYTHON_PREFIX := /replace-me

.NOTPARALLEL: $(PYTHON_INSTALL)

python-install: $(PYTHON_INSTALL)

$(PYTHON_BUILD): $(PYTHON_SITECUSTOMIZE_COMPILED)
	$(TOUCH) $@

PYTHON_CACHE_PKG_PATH := $(call cache_pkg_path,$(PYTHON_DIR),$(PYTHON_BUILD_ID))

$(PYTHON_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PYTHON_DIR),$(PYTHON_BUILD_ID),$(PYTHON_INTERMEDIATE_INSTALL))

$(PYTHON_CACHE_PKG_PROCESS): $(PYTHON_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PYTHON_CACHE_PKG_PATH),$(PYTHON_DIR))
	$(call upload_pkg_archive,$(PYTHON_CACHE_PKG_PATH),$(PYTHON_DIR),$(PYTHON_BUILD_ID))
# Ensure that the rpath of the python binary and dynamic libs always points to the current version path
	for i in $(PACKAGE_PYTHON_EXECUTABLE) \
	         $(PACKAGE_PYTHON_LD_LIBRARY_PATH)/libpython$(PYTHON_MAJOR_DOT_MINOR).so.1.0 \
	         $(PACKAGE_PYTHON_LD_LIBRARY_PATH)/libpython3.so \
	         $(PACKAGE_PYTHON_PYTHONPATH)/lib-dynload/*.so ; do \
           patchelf --set-rpath "$(OMD_ROOT)/lib" $$i; \
	done
# Native modules built based on this version need to use the correct rpath
	$(SED) -i 's|--rpath,/omd/versions/[^/]*/lib|--rpath,$(OMD_ROOT)/lib|g' $(PACKAGE_PYTHON_SYSCONFIGDATA)
	$(SED) -i "s|$(PYTHON_PREFIX)|$(PACKAGE_PYTHON_DESTDIR)|g" $(PACKAGE_PYTHON_SYSCONFIGDATA)
	LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" \
	    $(PACKAGE_PYTHON_EXECUTABLE) -m py_compile \
	    $(PACKAGE_PYTHON_SYSCONFIGDATA)
	if [ -d "$(PACKAGE_PYTHON_PYTHONPATH)/test" ] ; then \
	    $(RM) -r $(PACKAGE_PYTHON_PYTHONPATH)/test ; \
	fi
	$(TOUCH) $@

$(PYTHON_COMPILE): $(PYTHON_UNPACK) $(OPENSSL_CACHE_PKG_PROCESS)
# The build with PGO/LTO enabled is mainly sequential, so a high build
# parallelism doesn't really help. Therefore we use just -j2.
#
# We need to build our own OpenSSL because older distribution, that we still
# have to support are not able to build Python 3.8+ (See CMK-3477).
#
# rpath: Create some dummy rpath which has enough space for later replacement
# by the final rpath
	cd $(PYTHON_BUILD_DIR) ; \
	$(TEST) "$(DISTRO_NAME)" = "SLES" && sed -i 's,#include <panel.h>,#include <ncurses/panel.h>,' Modules/_curses_panel.c ; \
	LD_LIBRARY_PATH="$(PACKAGE_OPENSSL_LD_LIBRARY_PATH)" \
	    ./configure \
	        --prefix=$(PYTHON_PREFIX) \
	        --enable-shared \
	        --with-ensurepip=install \
	        --with-openssl=$(PACKAGE_OPENSSL_DESTDIR) \
	        $(PYTHON_ENABLE_OPTIMIZATIONS) \
	        LDFLAGS="-Wl,--rpath,/omd/versions/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/lib $(PACKAGE_OPENSSL_LDFLAGS)"
	cd $(PYTHON_BUILD_DIR) ; \
	    $(MAKE) -j2
	$(TOUCH) $@

$(PYTHON_SITECUSTOMIZE_COMPILED): $(PYTHON_SITECUSTOMIZE_SOURCE) $(PYTHON_COMPILE)
	$(MKDIR) $(PYTHON_WORK_DIR)
	install -m 644 $(PYTHON_SITECUSTOMIZE_SOURCE) $(PYTHON_SITECUSTOMIZE_WORK)
	LD_LIBRARY_PATH="$(PYTHON_BUILD_DIR)" \
	    $(PYTHON_BUILD_DIR)/python -m py_compile $(PYTHON_SITECUSTOMIZE_WORK)

$(PYTHON_INTERMEDIATE_INSTALL): $(PYTHON_BUILD)
# Install python files (needed by dependent packages like mod_python,
# python-modules, ...) during compilation and install targets.
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	$(MAKE) -j1 -C $(PYTHON_BUILD_DIR) DESTDIR=$(PYTHON_INSTALL_DIR) install
# As we're now setting the prefix during ./configure, we need to clean up here the folder structure to get
# the same one as before.
	$(RSYNC) $(PYTHON_INSTALL_DIR)$(PYTHON_PREFIX)/* $(PYTHON_INSTALL_DIR)
	rm -r $(PYTHON_INSTALL_DIR)$(PYTHON_PREFIX)
# Fix shebang of scripts
	$(SED) -i '1s|^#!'$(PYTHON_PREFIX)'.*|#!/usr/bin/env python'$(PYTHON_VERSION_MAJOR)'|' $(addprefix $(PYTHON_INSTALL_DIR)/bin/,2to3-$(PYTHON_MAJOR_DOT_MINOR) idle$(PYTHON_MAJOR_DOT_MINOR) pip$(PYTHON_VERSION_MAJOR) pip$(PYTHON_MAJOR_DOT_MINOR) pydoc$(PYTHON_MAJOR_DOT_MINOR))
# Fix pip3 configuration by using own wrapper script
# * PIP_TARGET currently has an issue when installing non-wheel packages, see https://github.com/pypa/pip/issues/8438
# * The workaround is to set the target via the commandline
# * The wrapper script we're using is based on what PipScriptMaker would create, see:
# https://github.com/pypa/pip/blob/83c800d3b8b367b6ae1fbf92fd4f699612cecfc7/src/pip/_internal/operations/install/wheel.py#L422
# * However, we may run into issues in the future again. It seems actually the module invocation (python -m pip) is more solid, see:
# https://github.com/pypa/pip/issues/5599
	install -m 755 --no-target-directory $(PYTHON_PIP_WRAPPER_SOURCE) $(PYTHON_INSTALL_DIR)/bin/pip$(PYTHON_VERSION_MAJOR)
	install -m 755 --no-target-directory $(PYTHON_PIP_WRAPPER_SOURCE) $(PYTHON_INSTALL_DIR)/bin/pip$(PYTHON_MAJOR_DOT_MINOR)
	install -m 644 $(PYTHON_SITECUSTOMIZE_SOURCE) $(PYTHON_INSTALL_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/
	install -m 644 $(PYTHON_SITECUSTOMIZE_COMPILED) $(PYTHON_INSTALL_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/__pycache__
	$(TOUCH) $@

$(PYTHON_INSTALL): $(PYTHON_CACHE_PKG_PROCESS)
	$(RSYNC) $(PYTHON_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	# Patch for the final destination
	# TODO: It seems $(DESTDIR) is only defined in this target, so it cannot be used outside of this target?
	$(SED) -i "s|$(PACKAGE_PYTHON_DESTDIR)|$(OMD_ROOT)|g" $(DESTDIR)/$(OMD_ROOT)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/$(PYTHON_SYSCONFIGDATA)
	$(TOUCH) $@
