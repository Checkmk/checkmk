include $(REPO_PATH)/defines.make

# Package definition
PYTHON := Python
PYTHON_DIR := $(PYTHON)-$(PYTHON_VERSION)

PYTHON_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-build
PYTHON_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install-intermediate
PYTHON_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_DIR)-install
PYTHON_SYSCONFIGDATA := _sysconfigdata__linux_x86_64-linux-gnu.py

PYTHON_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)

# Used by other OMD packages
PACKAGE_PYTHON_DESTDIR         := $(PYTHON_INSTALL_DIR)
PACKAGE_PYTHON_PYTHONPATH      := $(PACKAGE_PYTHON_DESTDIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)
PACKAGE_PYTHON_LDFLAGS         := -L$(PACKAGE_PYTHON_DESTDIR)/lib -L$(PACKAGE_PYTHON_PYTHONPATH)/config
PACKAGE_PYTHON_LD_LIBRARY_PATH := $(PACKAGE_PYTHON_DESTDIR)/lib
PACKAGE_PYTHON_INCLUDE_PATH    := $(PACKAGE_PYTHON_DESTDIR)/include/python$(PYTHON_MAJOR_DOT_MINOR)
PACKAGE_PYTHON_BIN             := $(PACKAGE_PYTHON_DESTDIR)/bin
PACKAGE_PYTHON_EXECUTABLE      := $(PACKAGE_PYTHON_BIN)/python$(PYTHON_VERSION_MAJOR)
PACKAGE_PYTHON_SYSCONFIGDATA := $(PACKAGE_PYTHON_PYTHONPATH)/$(PYTHON_SYSCONFIGDATA)

$(PYTHON_BUILD):
	$(BAZEL_BUILD) @python//:python

$(PYTHON_INTERMEDIATE_INSTALL): $(PYTHON_BUILD)
	mkdir -p "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)"
	# This will leave us with some strange file permissions, but works for now, see
	# https://stackoverflow.com/questions/75208034
	$(RSYNC) -r --chmod=u+w "$(BAZEL_BIN_EXT)/python/python/" \
	    "$(PYTHON_INSTALL_DIR)/"
	# remove executable bit from libraries
	find "$(PYTHON_INSTALL_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)" -type f | xargs chmod -x
	# Fix sysconfigdata
	$(SED) -i "s|/replace-me|$(PACKAGE_PYTHON_DESTDIR)|g" $(PACKAGE_PYTHON_SYSCONFIGDATA)
	# set RPATH for all ELF binaries we find
	find "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)" -maxdepth 2 -type f -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../lib"
	find "$(INTERMEDIATE_INSTALL_BASE)/$(PYTHON_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/lib-dynload" -name "*.so" -exec file {} \; \
	    | grep ELF | cut -d ':' -f1 \
	    | xargs patchelf --set-rpath "\$$ORIGIN/../.."

$(PYTHON_INSTALL): $(PYTHON_INTERMEDIATE_INSTALL)
	$(RSYNC) -rl --perms $(PYTHON_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(SED) -i "s|$(PACKAGE_PYTHON_DESTDIR)|$(OMD_ROOT)|g" \
	    $(DESTDIR)/$(OMD_ROOT)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/$(PYTHON_SYSCONFIGDATA)
	# pre-compile pyc files enforcing `checked-hash` invalidation
	# note: this is a workaround and should be handled in according Bazel project
	$(PACKAGE_PYTHON_EXECUTABLE) -m compileall \
	    -f \
	    --invalidation-mode=checked-hash \
	    -s "$(DESTDIR)/$(OMD_ROOT)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/" \
	    -x "bad_coding|badsyntax|test/test_lib2to3/data" \
	    "$(DESTDIR)/$(OMD_ROOT)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/"

