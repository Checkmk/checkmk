# Pack the C++ libraries from our build containers. The compiler we use links
# against libraries that are are newer than the target distros libraries. To
# make our executables work as intended, we ship the required libraries with
# Checkmk.

CPP_LIBS := cpp-libs
CPP_LIBS_VERS := 1.0
CPP_LIBS_DIR := $(CPP_LIBS)-$(CPP_LIBS_VERS)

CPP_LIBS_UNPACK := $(BUILD_HELPER_DIR)/$(CPP_LIBS_DIR)-unpack
CPP_LIBS_BUILD := $(BUILD_HELPER_DIR)/$(CPP_LIBS_DIR)-build
CPP_LIBS_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(CPP_LIBS_DIR)-install-intermediate
CPP_LIBS_INSTALL := $(BUILD_HELPER_DIR)/$(CPP_LIBS_DIR)-install

CPP_LIBS_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(CPP_LIBS_DIR)
CPP_LIBS_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(CPP_LIBS_DIR)
#CPP_LIBS_WORK_DIR := $(PACKAGE_WORK_DIR)/$(CPP_LIBS_DIR)

# Used by other OMD packages
#PACKAGE_CPP_LIBS_DESTDIR := $(CPP_LIBS_INSTALL_DIR)

# Paths need to be aligned with
# buildscripts/infrastructure/build-nodes/scripts/install-gnu-toolchain.sh
CPP_LIBS_COMPILER_BASE_DIR := /opt/gcc-$(GCC_VERSION)

$(CPP_LIBS_BUILD):
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(CPP_LIBS_INTERMEDIATE_INSTALL): $(CPP_LIBS_BUILD)
	if [ -d "$(CPP_LIBS_COMPILER_BASE_DIR)" ]; then \
	    $(MKDIR) $(CPP_LIBS_INSTALL_DIR)/lib && \
	    cp -av $(CPP_LIBS_COMPILER_BASE_DIR)/lib64/lib{stdc++,gcc_s}* $(CPP_LIBS_INSTALL_DIR)/lib ; \
	fi
	$(TOUCH) $@

$(CPP_LIBS_INSTALL): $(CPP_LIBS_INTERMEDIATE_INSTALL)
	if [ -d "$(CPP_LIBS_INSTALL_DIR)" ]; then \
	    $(RSYNC) $(CPP_LIBS_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/ ; \
	fi
	$(TOUCH) $@

