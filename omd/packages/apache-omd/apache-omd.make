APACHE_OMD := apache-omd
APACHE_OMD_VERS := 1.0
APACHE_OMD_DIR := $(APACHE_OMD)-$(APACHE_OMD_VERS)

APACHE_OMD_INSTALL := $(BUILD_HELPER_DIR)/$(APACHE_OMD_DIR)-install


.PHONY: $(APACHE_OMD_INSTALL)
$(APACHE_OMD_INSTALL):
	bazel build //omd/packages/apache-omd:apache-omd
	tar --strip-components=1 -C $(DESTDIR)$(OMD_ROOT) -xf $(BAZEL_BIN)/omd/packages/apache-omd/apache-omd.tar.gz
	bazel build //omd/packages/apache-omd:skel_dir
	tar -C $(DESTDIR)$(OMD_ROOT) -xf $(BAZEL_BIN)/omd/packages/apache-omd/apache-skel.tar.gz

