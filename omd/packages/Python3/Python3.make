# Package definition
PYTHON3 := Python3
PYTHON3_VERS := 3.7.4
PYTHON3_DIR := Python-$(PYTHON3_VERS)
# Increase this to enforce a recreation of the build cache
PYTHON3_BUILD_ID := 0

PYTHON3_UNPACK := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-unpack
PYTHON3_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-build
PYTHON3_COMPILE := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-compile
PYTHON3_BUILD_TMP_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-install-for-build
PYTHON3_CACHE_PKG_UPLOAD := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-cache-pkg-upload
PYTHON3_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-install-intermediate
PYTHON3_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-install

PYTHON3_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON3_DIR)
PYTHON3_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON3_DIR)

# HACK!
PYTHON3_PACKAGE_DIR := $(PACKAGE_DIR)/$(PYTHON3)
PYTHON3_SITECUSTOMIZE_SOURCE := $(PYTHON3_PACKAGE_DIR)/sitecustomize.py
PYTHON3_SITECUSTOMIZE_WORK := $(PYTHON3_WORK_DIR)/sitecustomize.py
PYTHON3_SITECUSTOMIZE_COMPILED := $(PYTHON3_WORK_DIR)/__pycache__/sitecustomize.cpython-37.pyc

.PHONY: $(PYTHON3) $(PYTHON3)-install $(PYTHON3)-skel $(PYTHON3)-clean upstream

.NOTPARALLEL: $(PYTHON3_INSTALL)

$(PYTHON3): $(PYTHON3_BUILD)

$(PYTHON3)-install: $(PYTHON3_INSTALL)

$(PYTHON3_BUILD): $(PYTHON3_SITECUSTOMIZE_COMPILED)
	$(TOUCH) $@

PYTHON3_CACHE_PKG_PATH := $(call cache_pkg_path,$(PYTHON3_DIR),$(PYTHON3_BUILD_ID))

$(PYTHON3_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PYTHON3_DIR),$(PYTHON3_BUILD_ID),$(PYTHON3_INTERMEDIATE_INSTALL))

$(PYTHON3_CACHE_PKG_UPLOAD): $(PYTHON3_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PYTHON3_CACHE_PKG_PATH),$(PYTHON3_DIR))
	$(call upload_pkg_archive,$(PYTHON3_CACHE_PKG_PATH),$(PYTHON3_DIR),$(PYTHON3_BUILD_ID))
	$(TOUCH) $@

$(PYTHON3_UNPACK): $(PACKAGE_DIR)/$(PYTHON3)/$(PYTHON3_DIR).tar.xz
	$(RM) -r $*
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TAR_XZ) $<
	$(TOUCH) $@

$(PYTHON3_COMPILE): $(PYTHON3_UNPACK)
# The build with PGO/LTO enabled is mainly sequential, so a high build
# parallelism doesn't really help. Therefore we use just -j2.
	cd $(PYTHON3_DIR) ; \
	$(TEST) "$(DISTRO_NAME)" = "SLES" && sed -i 's,#include <panel.h>,#include <ncurses/panel.h>,' Modules/_curses_panel.c ; \
	./configure \
	    --prefix="" \
	    --enable-shared \
	    --with-ensurepip=install \
	    $(PYTHON_ENABLE_OPTIMIZATIONS) \
	    LDFLAGS="-Wl,--rpath,$(OMD_ROOT)/lib"
	cd $(PYTHON3_DIR) ; $(MAKE) -j2
	$(TOUCH) $@

$(PYTHON3_BUILD_TMP_INSTALL): $(PYTHON3_COMPILE)
# Install python files (needed by dependent packages like mod_python,
# python-modules, ...) during compilation and install targets.
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	$(MAKE) -j1 -C $(PYTHON3_DIR) DESTDIR=$(PACKAGE_PYTHON3_DESTDIR) install
	$(TOUCH) $@

$(PYTHON3_SITECUSTOMIZE_COMPILED): $(PYTHON3_SITECUSTOMIZE_SOURCE) $(PYTHON3_BUILD_TMP_INSTALL)
	$(MKDIR) $(PYTHON3_WORK_DIR)
	install -m 644 $(PYTHON3_SITECUSTOMIZE_SOURCE) $(PYTHON3_SITECUSTOMIZE_WORK)
	export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_PYTHONPATH)" ; \
	export LDFLAGS="$(PACKAGE_PYTHON3_LDFLAGS)" ; \
	export LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH)" ; \
	$(PACKAGE_PYTHON3_EXECUTABLE) -m py_compile $(PYTHON3_SITECUSTOMIZE_WORK)

$(PYTHON3_INTERMEDIATE_INSTALL): $(PYTHON3_BUILD)
# Install python files (needed by dependent packages like mod_python,
# python-modules, ...) during compilation and install targets.
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	$(MAKE) -j1 -C $(PYTHON3_DIR) DESTDIR=$(PYTHON3_INSTALL_DIR) install
# Fix python interpreter
	$(SED) -i '1s|^#!.*/python3\.7$$|#!/usr/bin/env python3|' $(addprefix $(PYTHON3_INSTALL_DIR)/bin/,2to3-3.7 easy_install-3.7 idle3.7 pip3 pip3.7 pydoc3.7 python3.7m-config pyvenv-3.7)
# Fix pip3 configuration
	$(SED) -i '/^import re$$/i import os\nos.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "True"\nos.environ["PIP_TARGET"] = os.path.join(os.environ["OMD_ROOT"], "local/lib/python3")' $(addprefix $(PYTHON3_INSTALL_DIR)/bin/,pip3 pip3.7)
	install -m 644 $(PYTHON3_SITECUSTOMIZE_SOURCE) $(PYTHON3_INSTALL_DIR)/lib/python3.7/
	install -m 644 $(PYTHON3_SITECUSTOMIZE_COMPILED) $(PYTHON3_INSTALL_DIR)/lib/python3.7/__pycache__
	$(TOUCH) $@

$(PYTHON3_INSTALL): $(PYTHON3_CACHE_PKG_UPLOAD)
	$(RSYNC) $(PYTHON3_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@

$(PYTHON3)-clean:
	$(RM) -r $(DIR) $(BUILD_HELPER_DIR)/$(PYTHON3)* $(PACKAGE_PYTHON3_DESTDIR)
