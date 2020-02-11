# This package contains the SNAP 7 library (http://snap7.sourceforge.net/)
SNAP7 := snap7
SNAP7_VERS := 1.4.2
SNAP7_DIR := $(SNAP7)-full-$(SNAP7_VERS)
SNAP7_ARCH := $(shell uname -m)

SNAP7_UNPACK := $(BUILD_HELPER_DIR)/$(SNAP7_DIR)-unpack
SNAP7_BUILD := $(BUILD_HELPER_DIR)/$(SNAP7_DIR)-build
SNAP7_INSTALL := $(BUILD_HELPER_DIR)/$(SNAP7_DIR)-install

#SNAP7_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(SNAP7_DIR)
SNAP7_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(SNAP7_DIR)
#SNAP7_WORK_DIR := $(PACKAGE_WORK_DIR)/$(SNAP7_DIR)

.PHONY: $(SNAP7)-repackage

$(SNAP7_BUILD): $(SNAP7_UNPACK)
	$(MAKE) -C $(SNAP7_BUILD_DIR)/build/unix -f $(SNAP7_ARCH)_linux.mk
	$(TOUCH) $@

$(SNAP7_INSTALL): $(SNAP7_BUILD)
	install -m 644 $(SNAP7_BUILD_DIR)/build/bin/$(SNAP7_ARCH)-linux/libsnap7.so $(DESTDIR)$(OMD_ROOT)/lib
	$(TOUCH) $@

# The original 7z file is quite large (20MB), because it contains tons of
# executables, but we don't need any of them. An equivalent .tar.gz would almost
# be 60MB. Furthermore, requiring a 7z command at build time on a ton of
# platforms is annoying (adding repos, varying names, etc.), so we repackage the
# 7z file to a standard gzipped tar file.
# TODO: Do this in the SNAP7_WORK_DIR
$(SNAP7)-repackage: clean
	wget https://sourceforge.net/projects/snap7/files/$(SNAP7_VERS)/$(SNAP7_DIR).7z
	7z x $(SNAP7_DIR).7z
	GZIP=-9 tar cvzf $(SNAP7_DIR).tar.gz $(SNAP7_DIR)/build $(SNAP7_DIR)/src $(SNAP7_DIR)/*.txt
