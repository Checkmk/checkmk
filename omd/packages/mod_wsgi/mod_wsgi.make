MOD_WSGI := mod_wsgi
MOD_WSGI_VERS := 4.6.4
MOD_WSGI_DIR := $(MOD_WSGI)-$(MOD_WSGI_VERS)

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

MOD_WSGI_PATCHING := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-patching
MOD_WSGI_BUILD := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-build
MOD_WSGI_INSTALL := $(BUILD_HELPER_DIR)/$(MOD_WSGI_DIR)-install

#MOD_WSGI_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(MOD_WSGI_DIR)
MOD_WSGI_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(MOD_WSGI_DIR)
#MOD_WSGI_WORK_DIR := $(PACKAGE_WORK_DIR)/$(MOD_WSGI_DIR)

$(MOD_WSGI_BUILD): $(MOD_WSGI_PATCHING) $(PYTHON_CACHE_PKG_PROCESS)
	set -e ; \
	export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	export CFLAGS="-I$(PACKAGE_PYTHON_DESTDIR)/include/python2.7" ; \
	cd $(MOD_WSGI_BUILD_DIR) ; \
	./configure \
	    --prefix=$(OMD_ROOT) \
	    --with-apxs=$(APXS) \
	    --with-python=$(PACKAGE_PYTHON_EXECUTABLE)
	$(MAKE) -C $(MOD_WSGI_BUILD_DIR)
	$(TOUCH) $@

$(MOD_WSGI_INSTALL): $(MOD_WSGI_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	cp $(MOD_WSGI_BUILD_DIR)/src/server/.libs/mod_wsgi.so $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	chmod 644 $(DESTDIR)$(OMD_ROOT)/lib/apache/modules/mod_wsgi.so
	$(TOUCH) $@
