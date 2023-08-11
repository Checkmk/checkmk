# Package definition
PYTHON3 := Python3
PYTHON3_VERS := 3.8.17
PYTHON3_DIR := Python-$(PYTHON3_VERS)
# Increase this to enforce a recreation of the build cache
PYTHON3_BUILD_ID := 11

PYTHON3_UNPACK := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-unpack
PYTHON3_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-build
PYTHON3_COMPILE := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-compile
PYTHON3_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-install-intermediate
PYTHON3_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-cache-pkg-process
PYTHON3_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-install
PYTHON3_SYSCONFIGDATA := _sysconfigdata__linux_x86_64-linux-gnu.py

PYTHON3_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON3_DIR)
PYTHON3_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON3_DIR)
PYTHON3_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON3_DIR)

# Used by other OMD packages
PACKAGE_PYTHON3_DESTDIR         := $(PYTHON3_INSTALL_DIR)
PACKAGE_PYTHON3_PYTHONPATH      := $(PACKAGE_PYTHON3_DESTDIR)/lib/python3.8
PACKAGE_PYTHON3_LDFLAGS         := -L$(PACKAGE_PYTHON3_DESTDIR)/lib -L$(PACKAGE_PYTHON3_PYTHONPATH)/config
PACKAGE_PYTHON3_LD_LIBRARY_PATH := $(PACKAGE_PYTHON3_DESTDIR)/lib
PACKAGE_PYTHON3_INCLUDE_PATH    := $(PACKAGE_PYTHON3_DESTDIR)/include/python3.8
PACKAGE_PYTHON3_BIN             := $(PACKAGE_PYTHON3_DESTDIR)/bin
PACKAGE_PYTHON3_EXECUTABLE      := $(PACKAGE_PYTHON3_BIN)/python3
PACKAGE_PYTHON3_SYSCONFIGDATA := $(PACKAGE_PYTHON3_PYTHONPATH)/$(PYTHON3_SYSCONFIGDATA)

# HACK!
PYTHON3_PACKAGE_DIR := $(PACKAGE_DIR)/$(PYTHON3)
PYTHON3_SITECUSTOMIZE_SOURCE := $(PYTHON3_PACKAGE_DIR)/sitecustomize.py
PYTHON3_SITECUSTOMIZE_WORK := $(PYTHON3_WORK_DIR)/sitecustomize.py
PYTHON3_SITECUSTOMIZE_COMPILED := $(PYTHON3_WORK_DIR)/__pycache__/sitecustomize.cpython-38.pyc
PYTHON3_PIP_WRAPPER_SOURCE := $(PYTHON3_PACKAGE_DIR)/pip
PYTHON3_PREFIX := /replace-me

.NOTPARALLEL: $(PYTHON3_INSTALL)

python3-install: $(PYTHON3_INSTALL)

$(PYTHON3_BUILD): $(PYTHON3_SITECUSTOMIZE_COMPILED)
	$(TOUCH) $@

PYTHON3_CACHE_PKG_PATH := $(call cache_pkg_path,$(PYTHON3_DIR),$(PYTHON3_BUILD_ID))

$(PYTHON3_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PYTHON3_DIR),$(PYTHON3_BUILD_ID),$(PYTHON3_INTERMEDIATE_INSTALL))

$(PYTHON3_CACHE_PKG_PROCESS): $(PYTHON3_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PYTHON3_CACHE_PKG_PATH),$(PYTHON3_DIR))
	$(call upload_pkg_archive,$(PYTHON3_CACHE_PKG_PATH),$(PYTHON3_DIR),$(PYTHON3_BUILD_ID))
# Ensure that the rpath of the python binary and dynamic libs always points to the current version path
	for i in $(PACKAGE_PYTHON3_EXECUTABLE) \
	         $(PACKAGE_PYTHON3_LD_LIBRARY_PATH)/libpython3.8.so.1.0 \
	         $(PACKAGE_PYTHON3_LD_LIBRARY_PATH)/libpython3.so \
	         $(PACKAGE_PYTHON3_PYTHONPATH)/lib-dynload/*.so ; do \
	    chrpath -r "$(OMD_ROOT)/lib" $$i; \
	done
# Native modules built based on this version need to use the correct rpath
	$(SED) -i 's|--rpath,/omd/versions/[^/]*/lib|--rpath,$(OMD_ROOT)/lib|g' $(PACKAGE_PYTHON3_SYSCONFIGDATA)
	$(SED) -i "s|$(PYTHON3_PREFIX)|$(PACKAGE_PYTHON3_DESTDIR)|g" $(PACKAGE_PYTHON3_SYSCONFIGDATA)
	LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH)" \
	    $(PACKAGE_PYTHON3_EXECUTABLE) -m py_compile \
	    $(PACKAGE_PYTHON3_SYSCONFIGDATA)
	rm -r $(PACKAGE_PYTHON3_PYTHONPATH)/test
	$(TOUCH) $@

$(PYTHON3_UNPACK): $(PACKAGE_DIR)/$(PYTHON3)/$(PYTHON3_DIR).tar.xz
	$(RM) -r $(PACKAGE_BUILD_DIR)/$*
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(TAR_XZ) $< -C $(PACKAGE_BUILD_DIR)
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(PYTHON3_COMPILE): $(PYTHON3_UNPACK) $(OPENSSL_INTERMEDIATE_INSTALL)
# The build with PGO/LTO enabled is mainly sequential, so a high build
# parallelism doesn't really help. Therefore we use just -j2.
#
# We need to build our own OpenSSL because older distribution, that we still
# have to support are not able to build Python 3.8+ (See CMK-3477).
#
# rpath: Create some dummy rpath which has enough space for later replacement
# by the final rpath
	cd $(PYTHON3_BUILD_DIR) ; \
	$(TEST) "$(DISTRO_NAME)" = "SLES" && sed -i 's,#include <panel.h>,#include <ncurses/panel.h>,' Modules/_curses_panel.c ; \
	LD_LIBRARY_PATH="$(PACKAGE_OPENSSL_LD_LIBRARY_PATH)" \
	    ./configure \
	        --prefix=$(PYTHON3_PREFIX) \
	        --enable-shared \
	        --with-ensurepip=install \
	        --with-openssl=$(PACKAGE_OPENSSL_DESTDIR) \
	        $(PYTHON_ENABLE_OPTIMIZATIONS) \
	        LDFLAGS="-Wl,--rpath,/omd/versions/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/lib $(PACKAGE_OPENSSL_LDFLAGS)"
	cd $(PYTHON3_BUILD_DIR) ; \
	    $(MAKE) -j2
	$(TOUCH) $@

$(PYTHON3_SITECUSTOMIZE_COMPILED): $(PYTHON3_SITECUSTOMIZE_SOURCE) $(PYTHON3_COMPILE)
	$(MKDIR) $(PYTHON3_WORK_DIR)
	install -m 644 $(PYTHON3_SITECUSTOMIZE_SOURCE) $(PYTHON3_SITECUSTOMIZE_WORK)
	LD_LIBRARY_PATH="$(PYTHON3_BUILD_DIR)" \
	    $(PYTHON3_BUILD_DIR)/python -m py_compile $(PYTHON3_SITECUSTOMIZE_WORK)

$(PYTHON3_INTERMEDIATE_INSTALL): $(PYTHON3_BUILD)
# Install python files (needed by dependent packages like mod_python,
# python-modules, ...) during compilation and install targets.
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	$(MAKE) -j1 -C $(PYTHON3_BUILD_DIR) DESTDIR=$(PYTHON3_INSTALL_DIR) install
# As we're now setting the prefix during ./configure, we need to clean up here the folder structure to get
# the same one as before.
	$(RSYNC) $(PYTHON3_INSTALL_DIR)$(PYTHON3_PREFIX)/* $(PYTHON3_INSTALL_DIR)
	rm -r $(PYTHON3_INSTALL_DIR)$(PYTHON3_PREFIX)
# Fix shebang of scripts
	$(SED) -i '1s|^#!'$(PYTHON3_PREFIX)'.*|#!/usr/bin/env python3|' $(addprefix $(PYTHON3_INSTALL_DIR)/bin/,2to3-3.8 idle3.8 pydoc3.8)
# Fix pip3 configuration by using own wrapper script
# * PIP_TARGET currently has an issue when installing non-wheel packages, see https://github.com/pypa/pip/issues/8438
# * The workaround is to set the target via the commandline
# * The wrapper script we're using is based on what PipScriptMaker would create, see:
# https://github.com/pypa/pip/blob/83c800d3b8b367b6ae1fbf92fd4f699612cecfc7/src/pip/_internal/operations/install/wheel.py#L422
# * However, we may run into issues in the future again. It seems actually the module invocation (python -m pip) is more solid, see:
# https://github.com/pypa/pip/issues/5599
	install -m 755 --no-target-directory $(PYTHON3_PIP_WRAPPER_SOURCE) $(PYTHON3_INSTALL_DIR)/bin/pip3
	install -m 755 --no-target-directory $(PYTHON3_PIP_WRAPPER_SOURCE) $(PYTHON3_INSTALL_DIR)/bin/pip3.8
	install -m 644 $(PYTHON3_SITECUSTOMIZE_SOURCE) $(PYTHON3_INSTALL_DIR)/lib/python3.8/
	install -m 644 $(PYTHON3_SITECUSTOMIZE_COMPILED) $(PYTHON3_INSTALL_DIR)/lib/python3.8/__pycache__
	$(TOUCH) $@

$(PYTHON3_INSTALL): $(PYTHON3_CACHE_PKG_PROCESS)
	$(RSYNC) $(PYTHON3_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	# Patch for the final destination
	# TODO: It seems $(DESTDIR) is only defined in this target, so it cannot be used outside of this target?
	$(SED) -i "s|$(PACKAGE_PYTHON3_DESTDIR)|$(OMD_ROOT)|g" $(DESTDIR)/$(OMD_ROOT)/lib/python3.8/$(PYTHON3_SYSCONFIGDATA)
	$(TOUCH) $@
