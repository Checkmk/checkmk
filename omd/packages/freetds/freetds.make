FREETDS := freetds
FREETDS_VERS := 0.95.95
FREETDS_DIR := $(FREETDS)-$(FREETDS_VERS)
# Increase this to enforce a recreation of the build cache
FREETDS_BUILD_ID := 0

FREETDS_UNPACK := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-unpack
FREETDS_BUILD := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-build
FREETDS_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-install-intermediate
FREETDS_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-cache-pkg-process
FREETDS_INSTALL := $(BUILD_HELPER_DIR)/$(FREETDS_DIR)-install

FREETDS_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(FREETDS_DIR)
FREETDS_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(FREETDS_DIR)
#FREETDS_WORK_DIR := $(PACKAGE_WORK_DIR)/$(FREETDS_DIR)

# Used by python-modules/python3-modules
PACKAGE_FREETDS_DESTDIR := $(FREETDS_INSTALL_DIR)/build
PACKAGE_FREETDS_LDFLAGS := -L$(PACKAGE_FREETDS_DESTDIR)/lib

$(FREETDS_BUILD): $(FREETDS_UNPACK)
	cd $(FREETDS_BUILD_DIR) && \
	    ./configure \
		--enable-msdblib \
		--prefix="" \
		--sysconfdir=/etc/freetds \
		--with-tdsver=7.1 \
		--disable-apps \
		--disable-server \
		--disable-pool \
		--disable-odbc
	$(MAKE) -C $(FREETDS_BUILD_DIR) -j4
	$(TOUCH) $@

FREETDS_CACHE_PKG_PATH := $(call cache_pkg_path,$(FREETDS_DIR),$(FREETDS_BUILD_ID))

$(FREETDS_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(FREETDS_DIR),$(FREETDS_BUILD_ID),$(FREETDS_INTERMEDIATE_INSTALL))

$(FREETDS_CACHE_PKG_PROCESS): $(FREETDS_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(FREETDS_CACHE_PKG_PATH),$(FREETDS_DIR))
	$(call upload_pkg_archive,$(FREETDS_CACHE_PKG_PATH),$(FREETDS_DIR),$(FREETDS_BUILD_ID))
	$(TOUCH) $@

$(FREETDS_INTERMEDIATE_INSTALL): $(FREETDS_BUILD)
# At runtime we need only the libraries.
	$(MKDIR) $(FREETDS_INSTALL_DIR)/runtime
	$(MAKE) -C $(FREETDS_BUILD_DIR)/src/dblib DESTDIR=$(FREETDS_INSTALL_DIR)/runtime install
# Package python-modules needs some stuff during the build.
	$(MKDIR) $(PACKAGE_FREETDS_DESTDIR)
	$(MAKE) -C $(FREETDS_BUILD_DIR)/include DESTDIR=$(PACKAGE_FREETDS_DESTDIR) install
	$(MAKE) -C $(FREETDS_BUILD_DIR)/src/dblib DESTDIR=$(PACKAGE_FREETDS_DESTDIR) install
	$(TOUCH) $@

$(FREETDS_INSTALL): $(FREETDS_CACHE_PKG_PROCESS)
	$(RSYNC) $(FREETDS_INSTALL_DIR)/runtime/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
