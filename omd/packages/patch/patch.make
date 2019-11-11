PATCH := patch
PATCH_VERS := 2.7.6
PATCH_DIR := $(PATCH)-$(PATCH_VERS)
# Increase this to enforce a recreation of the build cache
PATCH_BUILD_ID := 0

PATCH_BUILD := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-build
PATCH_BUILD_UNCACHED := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-build-uncached
PATCH_BUILD_PKG_UPLOAD := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-build-pkg-upload
PATCH_INSTALL := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-install
PATCH_UNPACK := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-unpack

.PHONY: $(PATCH) $(PATCH)-install $(PATCH)-skel $(PATCH)-clean

$(PATCH): $(PATCH_BUILD)

$(PATCH)-install: $(PATCH_INSTALL)

$(PATCH_BUILD): $(PATCH_BUILD_PKG_UPLOAD)
	$(TOUCH) $@

PATCH_BUILD_PKG_PATH := $(call build_pkg_path,$(PATCH_DIR),$(PATCH_BUILD_ID))

$(PATCH_BUILD_PKG_PATH):
	$(call build_pkg_archive,$@,$(PATCH_DIR),$(PATCH_BUILD_ID),$(PATCH_BUILD_UNCACHED))

$(PATCH_BUILD_PKG_UPLOAD): $(PATCH_BUILD_PKG_PATH)
	$(call unpack_pkg_archive,$(PATCH_BUILD_PKG_PATH),$(PATCH_DIR))
	$(call upload_pkg_archive,$(PATCH_BUILD_PKG_PATH),$(PATCH_DIR),$(PATCH_BUILD_ID))
	$(TOUCH) $@

$(PATCH_BUILD_UNCACHED): $(PATCH_UNPACK)
	cd $(PATCH_DIR) && ./configure --prefix=$(OMD_ROOT)
	$(MAKE) -C $(PATCH_DIR)
	$(TOUCH) $@

$(PATCH_INSTALL): $(PATCH_BUILD)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(PATCH_DIR) install
	$(TOUCH) $@

$(PATCH)-skel:

$(PATCH)-clean:
	rm -rf $(PATCH_DIR) $(BUILD_HELPER_DIR)/$(PATCH)*
