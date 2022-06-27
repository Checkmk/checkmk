LASSO := lasso
LASSO_VERS := 2.7.0
LASSO_DIR := $(LASSO)-$(LASSO_VERS)
# Increase this to enforce a recreation of the build cache
LASSO_BUILD_ID := 2

LASSO_BUILD := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-build
LASSO_UNPACK := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-unpack
LASSO_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-install-intermediate
LASSO_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-cache-pkg-process
LASSO_INSTALL := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-install

LASSO_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(LASSO_DIR)
LASSO_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(LASSO_DIR)
#LASSO_WORK_DIR := $(PACKAGE_WORK_DIR)/$(LASSO_DIR)

# Aliases for manual execution
$(LASSO): $(LASSO_BUILD) $(LASSO_INTERMEDIATE_INSTALL)
$(LASSO)-unpack: $(LASSO_UNPACK)
$(LASSO)-int: $(LASSO_INTERMEDIATE_INSTALL)

ifeq ($(filter sles%,$(DISTRO_CODE)),)
$(LASSO_BUILD): $(LASSO_UNPACK) $(PYTHON_CACHE_PKG_PROCESS) $(PYTHON3_MODULES_CACHE_PKG_PROCESS)
	cd $(LASSO_BUILD_DIR) \
	&& export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH) \
	&& export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) \
	&& export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" \
	&& export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" \
	&& export CFLAGS="-I$(PACKAGE_PYTHON_INCLUDE_PATH)" \
        && ./configure \
	    --prefix="" \
	    --disable-gtk-doc \
	    --disable-java \
	    --disable-perl \
	    --enable-static-linking \
	    --with-python=$(PACKAGE_PYTHON_EXECUTABLE) \
	&& $(MAKE)
	$(TOUCH) $@
else
$(LASSO_BUILD):
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
endif

LASSO_CACHE_PKG_PATH := $(call cache_pkg_path,$(LASSO_DIR),$(LASSO_BUILD_ID))

$(LASSO_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(LASSO_DIR),$(LASSO_BUILD_ID),$(LASSO_INTERMEDIATE_INSTALL))

ifeq ($(filter sles%,$(DISTRO_CODE)),)
$(LASSO_CACHE_PKG_PROCESS): $(LASSO_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(LASSO_CACHE_PKG_PATH),$(LASSO_DIR))
	$(call upload_pkg_archive,$(LASSO_CACHE_PKG_PATH),$(LASSO_DIR),$(LASSO_BUILD_ID))
	$(TOUCH) $@
else
$(LASSO_CACHE_PKG_PROCESS):
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
endif

$(LASSO_INTERMEDIATE_INSTALL): $(LASSO_BUILD)
ifeq ($(filter sles%,$(DISTRO_CODE)),)
	$(MKDIR) $(LASSO_INSTALL_DIR)
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH) \
	&& export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) \
	&& export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" \
	&& $(MAKE) DESTDIR=$(LASSO_INSTALL_DIR) -C $(LASSO_BUILD_DIR) install
endif
	$(TOUCH) $@

$(LASSO_INSTALL): $(LASSO_CACHE_PKG_PROCESS)
ifeq ($(filter sles%,$(DISTRO_CODE)),)
	$(RSYNC) $(LASSO_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
endif
	$(TOUCH) $@

$(LASSO)_download:
	cd packages/lasso/ \
	&& wget https://repos.entrouvert.org/lasso.git/snapshot/lasso-$(LASSO_VERS).tar.gz
