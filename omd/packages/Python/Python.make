PYTHON := Python
# also listed in WORKSPACE
PYTHON_VERS := 3.11.2

PYTHON_DIR := $(PYTHON)-$(PYTHON_VERS)
PYTHON_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-build
PYTHON_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install-intermediate
PYTHON_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-cache-pkg-process
PYTHON_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install

# externally required variables
PYTHON_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)

# Used by other OMD packages
PACKAGE_PYTHON_DESTDIR         := $(PYTHON_INSTALL_DIR)
PACKAGE_PYTHON_PYTHONPATH      := $(PACKAGE_PYTHON_DESTDIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)
PACKAGE_PYTHON_LDFLAGS         := -L$(PACKAGE_PYTHON_DESTDIR)/lib -L$(PACKAGE_PYTHON_PYTHONPATH)/config
PACKAGE_PYTHON_LD_LIBRARY_PATH := $(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_INCLUDE_PATH    := $(PACKAGE_PYTHON_DESTDIR)/include/python$(PYTHON_MAJOR_DOT_MINOR)
PACKAGE_PYTHON_BIN             := $(PACKAGE_PYTHON_DESTDIR)/bin
PACKAGE_PYTHON_EXECUTABLE      := $(PACKAGE_PYTHON_BIN)/python3
PACKAGE_PYTHON_SYSCONFIGDATA := $(PACKAGE_PYTHON_PYTHONPATH)/$(PYTHON_SYSCONFIGDATA)

# Executed from enterprise/core/src/Makefile.am
$(PYTHON)-build-library: $(BUILD_HELPER_DIR) $(PYTHON_CACHE_PKG_PROCESS)

# Used by Python/Python.make
PACKAGE_PYTHON_DESTDIR := $(PYTHON_INSTALL_DIR)
PACKAGE_PYTHON_LDFLAGS := -L$(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_LD_LIBRARY_PATH := $(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_INCLUDE_PATH := $(PACKAGE_PYTHON_DESTDIR)/include

# on Centos8 we don't build our own OpenSSL, so we have to inform the build about it
ifeq ($(DISTRO_CODE),el8)
OPTIONAL_BUILD_ARGS := BAZEL_EXTRA_ARGS="--define no-own-openssl=true"
endif

$(PYTHON_BUILD):
	# run the Bazel build process which does all the dependency stuff
	$(OPTIONAL_BUILD_ARGS) $(BAZEL_BUILD) @python//:python

$(PYTHON_INTERMEDIATE_INSTALL):  $(PYTHON_BUILD)
	mkdir -p "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)"
	# This will leave us with some strange file permissions, but works for now, see
	# https://stackoverflow.com/questions/75208034
	rsync -r --chmod=u+w "bazel-bin/external/python/python/" \
	    --exclude=__pycache__ \
	    "$(PYTHON_INSTALL_DIR)/"
	cd "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/bin"; \
	    ln -sf 2to3-3.11 2to3; \
	    ln -sf idle3.11 idle3; \
	    ln -sf pydoc3.11 pydoc3; \
	    ln -sf python3.11 python3; \
	    ln -sf python3.11-config python3-config
	# set RPATH for all ELF binaries we find
	find "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)" -maxdepth 2 -type f -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../lib"
	find "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/lib-dynload" -name "*.so" -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../.."

$(PYTHON_INSTALL): $(PYTHON_CACHE_PKG_PROCESS)
	rsync -r --perms "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/" "$(DESTDIR)$(OMD_ROOT)/"

# legacy stuff
$(PYTHON_CACHE_PKG_PROCESS): $(PYTHON_INTERMEDIATE_INSTALL)

