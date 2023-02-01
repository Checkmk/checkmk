include $(REPO_PATH)/defines.make

PYTHON := Python
# also listed in WORKSPACE

PYTHON_DIR := $(PYTHON)-$(PYTHON_VERSION)
PYTHON_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-build
PYTHON_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install-intermediate
PYTHON_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-cache-pkg-process
PYTHON_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install
PYTHON_SYSCONFIGDATA := _sysconfigdata__linux_x86_64-linux-gnu.py

# externally required variables
PYTHON_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)

# Used by other OMD packages
PACKAGE_PYTHON_DESTDIR         := $(PYTHON_INSTALL_DIR)
PACKAGE_PYTHON_PYTHONPATH      := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)
PACKAGE_PYTHON_LDFLAGS         := -L$(PACKAGE_PYTHON_DESTDIR)/lib -L$(PACKAGE_PYTHON_PYTHONPATH)/config
PACKAGE_PYTHON_LD_LIBRARY_PATH := $(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_INCLUDE_PATH    := $(PACKAGE_PYTHON_DESTDIR)/include/python$(PYTHON_MAJOR_DOT_MINOR)
PACKAGE_PYTHON_BIN             := $(PACKAGE_PYTHON_DESTDIR)/bin
PACKAGE_PYTHON_EXECUTABLE      := $(PACKAGE_PYTHON_BIN)/python3
PACKAGE_PYTHON_SYSCONFIGDATA   := $(PACKAGE_PYTHON_PYTHONPATH)/$(PYTHON_SYSCONFIGDATA)

# Executed from enterprise/core/src/Makefile.am
$(PYTHON)-build-library: $(BUILD_HELPER_DIR) $(PYTHON_CACHE_PKG_PROCESS)

# Used by Python/Python.make
PACKAGE_PYTHON_DESTDIR := $(PYTHON_INSTALL_DIR)
PACKAGE_PYTHON_LDFLAGS := -L$(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_LD_LIBRARY_PATH := $(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_INCLUDE_PATH := $(PACKAGE_PYTHON_DESTDIR)/include/python$(PYTHON_MAJOR_DOT_MINOR)

# on Centos8 we don't build our own OpenSSL, so we have to inform the build about it
ifeq ($(DISTRO_CODE),el8)
OPTIONAL_BUILD_ARGS := BAZEL_EXTRA_ARGS="--define no-own-openssl=true"
endif

# HACK! To be moved to Bazel!
PYTHON_PACKAGE_DIR := $(PACKAGE_DIR)/$(PYTHON)
PYTHON_SITECUSTOMIZE_SOURCE := $(PYTHON_PACKAGE_DIR)/sitecustomize.py

$(PYTHON_BUILD):
	# run the Bazel build process which does all the dependency stuff
	$(OPTIONAL_BUILD_ARGS) $(BAZEL_BUILD) @python//:python
	echo '###Maximum heap size:';
	bazel info peak-heap-size;
	echo '### Server log:';
	cat $$(bazel info server_log) 
	echo '### END Server log:';

$(PYTHON_INTERMEDIATE_INSTALL):  $(PYTHON_BUILD)
	mkdir -p "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)"
	# This will leave us with some strange file permissions, but works for now, see
	# https://stackoverflow.com/questions/75208034
	rsync -r --chmod=u+w "bazel-bin/external/python/python/" \
	    "$(PYTHON_INSTALL_DIR)/"

	cd "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/bin"; \
	    ln -sf 2to3-${PYTHON_MAJOR_DOT_MINOR} 2to3; \
	    ln -sf idle${PYTHON_MAJOR_DOT_MINOR} idle3; \
	    ln -sf pydoc${PYTHON_MAJOR_DOT_MINOR} pydoc3; \
	    ln -sf python${PYTHON_MAJOR_DOT_MINOR} python3; \
	    ln -sf python-config${PYTHON_MAJOR_DOT_MINOR} python3-config
	# Fix sysconfigdata
	$(SED) -i "s|/replace-me|$(OMD_ROOT)|g" $(PACKAGE_PYTHON_SYSCONFIGDATA)
	# set RPATH for all ELF binaries we find
	find "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)" -maxdepth 2 -type f -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../lib"
	find "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/lib-dynload" -name "*.so" -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../.."

$(PYTHON_INSTALL): $(PYTHON_INTERMEDIATE_INSTALL)
	rsync -rl --perms "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/" "$(DESTDIR)$(OMD_ROOT)/"

# legacy stuff
$(PYTHON_CACHE_PKG_PROCESS): $(PYTHON_INTERMEDIATE_INSTALL)

