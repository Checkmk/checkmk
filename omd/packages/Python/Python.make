# Package definition
PYTHON := Python
PYTHON_VERS := 2.7.17
PYTHON_DIR := $(PYTHON)-$(PYTHON_VERS)
# Increase this to enforce a recreation of the build cache
PYTHON_BUILD_ID := 2

PYTHON_PATCHING := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-patching
PYTHON_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-build
PYTHON_COMPILE := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-compile
PYTHON_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install-intermediate
PYTHON_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-cache-pkg-process
PYTHON_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install

PYTHON_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)
PYTHON_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON_DIR)
PYTHON_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON_DIR)

# Used by other OMD packages
PACKAGE_PYTHON_DESTDIR         := $(PYTHON_INSTALL_DIR)
PACKAGE_PYTHON_PYTHONPATH      := $(PACKAGE_PYTHON_DESTDIR)/lib/python2.7
PACKAGE_PYTHON_LDFLAGS         := -L$(PACKAGE_PYTHON_DESTDIR)/lib -L$(PACKAGE_PYTHON_PYTHONPATH)/config
PACKAGE_PYTHON_LD_LIBRARY_PATH := $(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_BIN             := $(PACKAGE_PYTHON_DESTDIR)/bin
PACKAGE_PYTHON_EXECUTABLE      := $(PACKAGE_PYTHON_BIN)/python

# HACK!
PYTHON_PACKAGE_DIR := $(PACKAGE_DIR)/$(PYTHON)
PYTHON_SITECUSTOMIZE_SOURCE := $(PYTHON_PACKAGE_DIR)/sitecustomize.py
PYTHON_SITECUSTOMIZE_WORK := $(PYTHON_WORK_DIR)/sitecustomize.py
PYTHON_SITECUSTOMIZE_COMPILED := $(PYTHON_WORK_DIR)/sitecustomize.pyc
PYTHON_TMP_BIN_DIR := $(PYTHON_WORK_DIR)/python-bin

# Is needed to find the temporary links created by the targets
# $(PYTHON_TMP_BIN_DIR)/gcc and $(PYTHON_TMP_BIN_DIR)/g++
PYTHON_TMP_BIN_PATH_VAR := PATH="$(PYTHON_TMP_BIN_DIR):$$PATH"

PYTHON_CC_COMPILERS = gcc-9 clang-9 clang-8 gcc-8 gcc-7 clang-6.0 clang-5.0 gcc-6 clang-4.0 gcc-5 clang-3.9 clang-3.8 clang-3.7 clang-3.6 clang-3.5 gcc-4.9 gcc clang
PYTHON_CXX_COMPILERS := g++-9 clang++-9 clang++-8 g++-8 clang++-7 g++-7 clang++-6.0 clang++-5.0 g++ clang++

.PHONY:  $(PYTHON)-upstream

.NOTPARALLEL: $(PYTHON_INSTALL)

$(PYTHON_BUILD): $(PYTHON_SITECUSTOMIZE_COMPILED)
	$(TOUCH) $@

PYTHON_CACHE_PKG_PATH := $(call cache_pkg_path,$(PYTHON_DIR),$(PYTHON_BUILD_ID))

$(PYTHON_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PYTHON_DIR),$(PYTHON_BUILD_ID),$(PYTHON_INTERMEDIATE_INSTALL))

$(PYTHON_CACHE_PKG_PROCESS): $(PYTHON_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PYTHON_CACHE_PKG_PATH),$(PYTHON_DIR))
	$(call upload_pkg_archive,$(PYTHON_CACHE_PKG_PATH),$(PYTHON_DIR),$(PYTHON_BUILD_ID))
# Ensure that the rpath of the python binary and dynamic libs always points to the current version path
	chmod +w $(PACKAGE_PYTHON_LD_LIBRARY_PATH)/libpython2.7.so.1.0
	for i in $(PACKAGE_PYTHON_EXECUTABLE) \
	         $(PACKAGE_PYTHON_LD_LIBRARY_PATH)/libpython2.7.so.1.0 \
	         $(PACKAGE_PYTHON_PYTHONPATH)/lib-dynload/*.so ; do \
	    chrpath -r "$(OMD_ROOT)/lib" $$i; \
	done
	chmod -w $(PACKAGE_PYTHON_LD_LIBRARY_PATH)/libpython2.7.so.1.0
# Native modules built based on this version need to use the correct rpath
	sed -i 's|--rpath,/omd/versions/[^/]*/lib|--rpath,$(OMD_ROOT)/lib|g' \
	    $(PACKAGE_PYTHON_PYTHONPATH)/_sysconfigdata.py
	LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" \
	    $(PACKAGE_PYTHON_EXECUTABLE) -m py_compile $(PACKAGE_PYTHON_PYTHONPATH)/_sysconfigdata.py
	$(TOUCH) $@

$(PYTHON_COMPILE): $(PYTHON_PATCHING) $(PYTHON_TMP_BIN_DIR)/gcc $(PYTHON_TMP_BIN_DIR)/g++
# Things are a bit tricky here: For PGO/LTO we need a rather recent compiler,
# but we don't want to bake paths to our build system into _sysconfigdata and
# friends. Workaround: Find a recent compiler to be used for building and make a
# symlink for it under a generic name. :-P Furthermore, the build with PGO/LTO
# enables is mainly sequential, so a high build parallelism doesn't really
# help. Therefore we use just -j2.
#
# rpath: Create some dummy rpath which has enough space for later replacement
# by the final rpath
	cd $(PYTHON_BUILD_DIR) ; $(PYTHON_TMP_BIN_PATH_VAR) ; \
	$(TEST) "$(DISTRO_NAME)" = "SLES" && sed -i 's,#include <panel.h>,#include <ncurses/panel.h>,' Modules/_curses_panel.c ; \
	./configure \
	    --prefix="" \
	    --enable-shared \
	    --enable-unicode=ucs4 \
	    --with-ensurepip=install \
	    $(PYTHON_ENABLE_OPTIMIZATIONS) \
	    LDFLAGS="-Wl,--rpath,/omd/versions/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/lib"
	cd $(PYTHON_BUILD_DIR) ; $(PYTHON_TMP_BIN_PATH_VAR) ; $(MAKE) -j2
	$(TOUCH) $@

$(PYTHON_SITECUSTOMIZE_COMPILED): $(PYTHON_SITECUSTOMIZE_SOURCE) $(PYTHON_COMPILE)
	$(MKDIR) $(PYTHON_WORK_DIR)
	install -m 644 $(PYTHON_SITECUSTOMIZE_SOURCE) $(PYTHON_SITECUSTOMIZE_WORK)
	LD_LIBRARY_PATH="$(PYTHON_BUILD_DIR)" \
	    $(PYTHON_BUILD_DIR)/python -m py_compile $(PYTHON_SITECUSTOMIZE_WORK)

# The compiler detection code below is basically what part of AC_PROC_CXX does.
$(PYTHON_TMP_BIN_DIR)/gcc:
	@CC="" ; \
	for PROG in $(PYTHON_CC_COMPILERS); do \
	    echo -n "checking for $$PROG... "; SAVED_IFS=$$IFS; IFS=: ; \
	    for DIR in $$PATH; do \
	        IFS=$$SAVED_IFS ; \
	        $(TEST) -z "$$DIR" && DIR=. ; \
	        ABS_PROG="$$DIR/$$PROG" ; \
	        $(TEST) -x "$$ABS_PROG" && { CC="$$ABS_PROG"; echo "$$CC"; break 2; } ; \
	    done ; \
	    echo "no"; IFS=$$SAVED_IFS ; \
	done ; \
	$(TEST) -z "$$CC" && { echo "error: no C compiler found" >&2 ; exit 1; } ; \
	$(MKDIR) -p $(PYTHON_TMP_BIN_DIR) ; \
	$(RM) $(PYTHON_TMP_BIN_DIR)/gcc ; \
	$(LN) -s "$$CC" $(PYTHON_TMP_BIN_DIR)/gcc ; \


$(PYTHON_TMP_BIN_DIR)/g++:
	@CXX="" ; \
	for PROG in $(PYTHON_CXX_COMPILERS); do \
	    echo -n "checking for $$PROG... "; SAVED_IFS=$$IFS; IFS=: ; \
	    for DIR in $$PATH; do \
	        IFS=$$SAVED_IFS ; \
	        $(TEST) -z "$$DIR" && DIR=. ; \
	        ABS_PROG="$$DIR/$$PROG" ; \
	        $(TEST) -x "$$ABS_PROG" && { CXX="$$ABS_PROG"; echo "$$CXX"; break 2; } ; \
	    done ; \
	    echo "no"; IFS=$$SAVED_IFS ; \
	done ; \
	$(TEST) -z "$$CXX" && { echo "error: no C++ compiler found" >&2 ; exit 1; } ; \
	$(MKDIR) -p $(PYTHON_TMP_BIN_DIR) ; \
	$(RM) $(PYTHON_TMP_BIN_DIR)/g++ ; \
	$(LN) -s "$$CXX" $(PYTHON_TMP_BIN_DIR)/g++

$(PYTHON_INTERMEDIATE_INSTALL): $(PYTHON_BUILD) $(PYTHON_TMP_BIN_DIR)/gcc $(PYTHON_TMP_BIN_DIR)/g++
# Install python files (needed by dependent packages like mod_python,
# python-modules, ...) during compilation and install targets.
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	$(PYTHON_TMP_BIN_PATH_VAR) ; $(MAKE) -j1 -C $(PYTHON_BUILD_DIR) DESTDIR=$(PYTHON_INSTALL_DIR) install
# Cleanup unused stuff: We ship 2to3 from Python3 and we don't need some example proxy.
	$(RM) $(addprefix $(PYTHON_INSTALL_DIR)/bin/,2to3 smtpd.py)
# Fix python interpreter for kept scripts
	$(SED) -i '1s|^#!.*/python2\.7$$|#!/usr/bin/env python2|' $(addprefix $(PYTHON_INSTALL_DIR)/bin/,easy_install easy_install-2.7 idle pip pip2 pip2.7 pydoc python2.7-config)
# Fix pip configuration
	$(SED) -i '/^import re$$/i import os\nos.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "True"\nos.environ["PIP_TARGET"] = os.path.join(os.environ["OMD_ROOT"], "local/lib/python")' $(addprefix $(PYTHON_INSTALL_DIR)/bin/,pip pip2 pip2.7)
	install -m 644 $(PYTHON_SITECUSTOMIZE_WORK) $(PYTHON_INSTALL_DIR)/lib/python2.7/
	install -m 644 $(PYTHON_SITECUSTOMIZE_COMPILED) $(PYTHON_INSTALL_DIR)/lib/python2.7/
	$(TOUCH) $@

$(PYTHON_INSTALL): $(PYTHON_CACHE_PKG_PROCESS)
	$(RSYNC) $(PYTHON_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@

$(PYTHON)-upstream:
	git rm $(PYTHON_PACKAGE_DIR)/Python-*.tgz || true
	wget -O $(PYTHON_PACKAGE_DIR)/Python-$(PYTHON_VERS).tgz https://www.python.org/ftp/python/$(PYTHON_VERS)/Python-$(PYTHON_VERS).tgz
	git add $(PYTHON_PACKAGE_DIR)/Python-$(PYTHON_VERS).tgz
