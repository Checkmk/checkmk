MOD_WSGI := mod_wsgi
MOD_WSGI_VERS := 4.9.0
MOD_WSGI_DIR := $(MOD_WSGI)-$(MOD_WSGI_VERS)
# Increase this to enforce a recreation of the build cache
MOD_WSGI_BUILD_ID := 2

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

MOD_WSGI_UNPACK := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-unpack
MOD_WSGI_PATCHING := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-patching
MOD_WSGI_BUILD := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-build
MOD_WSGI_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-install-intermediate
MOD_WSGI_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-cache-pkg-process
MOD_WSGI_INSTALL := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-install

MOD_WSGI_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(MOD_WSGI_DIR)
MOD_WSGI_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(MOD_WSGI_DIR)
#MOD_WSGI_WORK_DIR := $(PACKAGE_WORK_DIR)/$(MOD_WSGI_DIR)

$(MOD_WSGI_BUILD): $(MOD_WSGI_PATCHING) $(PYTHON_CACHE_PKG_PROCESS)
	set -e ; \
	export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	export CFLAGS="-I$(PACKAGE_PYTHON_INCLUDE_PATH)" ; \
	cd $(MOD_WSGI_BUILD_DIR) ; \
	./configure \
	    --prefix=$(OMD_ROOT) \
	    --with-apxs=$(APXS) \
	    --with-python=$(PACKAGE_PYTHON_EXECUTABLE)
	$(MAKE) -C $(MOD_WSGI_BUILD_DIR)
	$(TOUCH) $@

MOD_WSGI_CACHE_PKG_PATH := $(call cache_pkg_path,$(MOD_WSGI_DIR),$(MOD_WSGI_BUILD_ID))

$(MOD_WSGI_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(MOD_WSGI_DIR),$(MOD_WSGI_BUILD_ID),$(MOD_WSGI_INTERMEDIATE_INSTALL))

$(MOD_WSGI_CACHE_PKG_PROCESS): $(MOD_WSGI_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(MOD_WSGI_CACHE_PKG_PATH),$(MOD_WSGI_DIR))
	$(call upload_pkg_archive,$(MOD_WSGI_CACHE_PKG_PATH),$(MOD_WSGI_DIR),$(MOD_WSGI_BUILD_ID))
	$(TOUCH) $@

$(MOD_WSGI_INTERMEDIATE_INSTALL): $(MOD_WSGI_BUILD)
	$(MKDIR) $(MOD_WSGI_INSTALL_DIR)/lib/apache/modules
	install -m 644 $(MOD_WSGI_BUILD_DIR)/src/server/.libs/mod_wsgi.so $(MOD_WSGI_INSTALL_DIR)/lib/apache/modules/mod_wsgi.so
	$(TOUCH) $@


$(MOD_WSGI_INSTALL): $(MOD_WSGI_CACHE_PKG_PROCESS)
	$(RSYNC) $(MOD_WSGI_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
