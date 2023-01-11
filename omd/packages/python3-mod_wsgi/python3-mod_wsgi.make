PYTHON3_MOD_WSGI := python3-mod_wsgi
PYTHON3_MOD_WSGI_VERS := 4.9.4
PYTHON3_MOD_WSGI_DIR := $(PYTHON3_MOD_WSGI)-$(PYTHON3_MOD_WSGI_VERS)
# Increase this to enforce a recreation of the build cache
PYTHON3_MOD_WSGI_BUILD_ID := 1

# Try to find the apxs binary
ifneq ("$(wildcard /usr/sbin/apxs)","")
    APXS := /usr/sbin/apxs
endif
ifneq ("$(wildcard /usr/sbin/apxs2)","")
    APXS := /usr/sbin/apxs2
endif
ifneq ("$(wildcard /usr/bin/apxs2)","")
    APXS := /usr/bin/apxs2
endif
# Special case to make compilation work with SLES11. It has apxs2 but we need
# to use the MPM specific apxs2-prefork binary to make compilation find the
# correct mpm.h.
ifneq ("$(wildcard /usr/sbin/apxs2-prefork)","")
    APXS := /usr/sbin/apxs2-prefork
endif
# SLES12SP0 special case
ifneq ("$(wildcard /usr/bin/apxs2-prefork)","")
    APXS := /usr/bin/apxs2-prefork
endif

PYTHON3_MOD_WSGI_UNPACK := $(BUILD_HELPER_DIR)/$(PYTHON3_MOD_WSGI_DIR)-unpack
PYTHON3_MOD_WSGI_PATCHING := $(BUILD_HELPER_DIR)/$(PYTHON3_MOD_WSGI_DIR)-patching
PYTHON3_MOD_WSGI_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON3_MOD_WSGI_DIR)-build
PYTHON3_MOD_WSGI_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MOD_WSGI_DIR)-install-intermediate
PYTHON3_MOD_WSGI_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PYTHON3_MOD_WSGI_DIR)-cache-pkg-process
PYTHON3_MOD_WSGI_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MOD_WSGI_DIR)-install

PYTHON3_MOD_WSGI_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON3_MOD_WSGI_DIR)
PYTHON3_MOD_WSGI_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON3_MOD_WSGI_DIR)
#PYTHON3_MOD_WSGI_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON3_MOD_WSGI_DIR)

# TODO: Can be removed after package python3-mod_wsgi is renamed to mod_wsgi. Then the
# source tar.gz name is equal to the OMD package name again an the generic unpack routine
# from omd/packages/packages.make can be used.
$(PYTHON3_MOD_WSGI_UNPACK): $(PACKAGE_DIR)/python3-mod_wsgi/mod_wsgi-$(PYTHON3_MOD_WSGI_VERS).tar.gz
	$(RM) -r $(PACKAGE_BUILD_DIR)/python3-mod_wsgi-$(PYTHON3_MOD_WSGI_VERS)
	$(MKDIR) -p $(PACKAGE_BUILD_DIR)/python3-mod_wsgi-$(PYTHON3_MOD_WSGI_VERS)
	$(TAR_GZ) $< -C $(PACKAGE_BUILD_DIR)/python3-mod_wsgi-$(PYTHON3_MOD_WSGI_VERS) --strip-components=1

	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(PYTHON3_MOD_WSGI_BUILD): $(PYTHON3_MOD_WSGI_PATCHING) $(PYTHON3_CACHE_PKG_PROCESS)
	set -e ; \
	export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_PYTHONPATH)" ; \
	export LDFLAGS="$(PACKAGE_PYTHON3_LDFLAGS)" ; \
	export LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH)" ; \
	export CFLAGS="-I$(PACKAGE_PYTHON3_INCLUDE_PATH)" ; \
	cd $(PYTHON3_MOD_WSGI_BUILD_DIR) ; \
	./configure \
	    --prefix=$(OMD_ROOT) \
	    --with-apxs=$(APXS) \
	    --with-python=$(PACKAGE_PYTHON3_EXECUTABLE)
	$(MAKE) -C $(PYTHON3_MOD_WSGI_BUILD_DIR)
	$(TOUCH) $@

PYTHON3_MOD_WSGI_CACHE_PKG_PATH := $(call cache_pkg_path,$(PYTHON3_MOD_WSGI_DIR),$(PYTHON3_MOD_WSGI_BUILD_ID))

$(PYTHON3_MOD_WSGI_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PYTHON3_MOD_WSGI_DIR),$(PYTHON3_MOD_WSGI_BUILD_ID),$(PYTHON3_MOD_WSGI_INTERMEDIATE_INSTALL))

$(PYTHON3_MOD_WSGI_CACHE_PKG_PROCESS): $(PYTHON3_MOD_WSGI_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PYTHON3_MOD_WSGI_CACHE_PKG_PATH),$(PYTHON3_MOD_WSGI_DIR))
	$(call upload_pkg_archive,$(PYTHON3_MOD_WSGI_CACHE_PKG_PATH),$(PYTHON3_MOD_WSGI_DIR),$(PYTHON3_MOD_WSGI_BUILD_ID))
	$(TOUCH) $@

$(PYTHON3_MOD_WSGI_INTERMEDIATE_INSTALL): $(PYTHON3_MOD_WSGI_BUILD)
	$(MKDIR) $(PYTHON3_MOD_WSGI_INSTALL_DIR)/lib/apache/modules
	cp $(PYTHON3_MOD_WSGI_BUILD_DIR)/src/server/.libs/mod_wsgi.so $(PYTHON3_MOD_WSGI_INSTALL_DIR)/lib/apache/modules/mod_wsgi_py3.so
	chmod 644 $(PYTHON3_MOD_WSGI_INSTALL_DIR)/lib/apache/modules/mod_wsgi_py3.so
	$(TOUCH) $@


$(PYTHON3_MOD_WSGI_INSTALL): $(PYTHON3_MOD_WSGI_CACHE_PKG_PROCESS)
	$(RSYNC) $(PYTHON3_MOD_WSGI_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
