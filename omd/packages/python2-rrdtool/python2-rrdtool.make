PYTHON2_RRDTOOL := python2-rrdtool
# Note: We actually use the snapshot f1edd121a from 2017-06-11
PYTHON2_RRDTOOL_VERS := 1.7.1
PYTHON2_RRDTOOL_DIR := $(PYTHON2_RRDTOOL)-$(PYTHON2_RRDTOOL_VERS)

PYTHON2_RRDTOOL_UNPACK := $(BUILD_HELPER_DIR)/$(PYTHON2_RRDTOOL_DIR)-unpack
PYTHON2_RRDTOOL_PATCHING := $(BUILD_HELPER_DIR)/$(PYTHON2_RRDTOOL_DIR)-patching
PYTHON2_RRDTOOL_CONFIGURE := $(BUILD_HELPER_DIR)/$(PYTHON2_RRDTOOL_DIR)-configure
PYTHON2_RRDTOOL_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON2_RRDTOOL_DIR)-build
PYTHON2_RRDTOOL_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON2_RRDTOOL_DIR)-install

#PYTHON2_RRDTOOL_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON2_RRDTOOL_DIR)
PYTHON2_RRDTOOL_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON2_RRDTOOL_DIR)
PYTHON2_RRDTOOL_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON2_RRDTOOL_DIR)

PYTHON2_RRDTOOL_CONFIGUREOPTS  := \
	--prefix=$(OMD_ROOT) \
	--disable-ruby \
	--disable-libwrap \
	--disable-perl \
	--disable-tcl \
	--disable-lua \
	--enable-python \
	--disable-rrdcached \
	--disable-rrdcgi \
	--with-systemdsystemunitdir=no

$(PYTHON2_RRDTOOL_UNPACK): $(PACKAGE_DIR)/$(PYTHON2_RRDTOOL)/rrdtool-$(PYTHON2_RRDTOOL_VERS).tar.gz
	$(RM) -r $(PACKAGE_BUILD_DIR)/$(PYTHON2_RRDTOOL_DIR)
	$(MKDIR) -p $(PACKAGE_BUILD_DIR)/$(PYTHON2_RRDTOOL_DIR)
	$(TAR_GZ) $< -C $(PACKAGE_BUILD_DIR)/$(PYTHON2_RRDTOOL_DIR) --strip-components=1

	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(PYTHON2_RRDTOOL_CONFIGURE): $(PYTHON2_RRDTOOL_PATCHING)
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export top_builddir="."; \
	export LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 $(PACKAGE_PYTHON_LDFLAGS)" ; \
	export CPPFLAGS="$(shell pkg-config --cflags gthread-2.0)" ; \
	export CFLAGS="-I$(PACKAGE_PYTHON2_INCLUDE_PATH)" ; \
	cd $(PYTHON2_RRDTOOL_BUILD_DIR) && \
        ./configure $(PYTHON2_RRDTOOL_CONFIGUREOPTS)
	$(TOUCH) $@

$(PYTHON2_RRDTOOL_BUILD): $(PYTHON2_RRDTOOL_CONFIGURE) $(PYTHON_CACHE_PKG_PROCESS) $(PYTHON_MODULES_INTERMEDIATE_INSTALL)
	set -e ; \
	unset DESTDIR MAKEFLAGS ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export top_builddir="."; \
	export LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 $(PACKAGE_PYTHON_LDFLAGS)" ; \
	export CPPFLAGS="$(shell pkg-config --cflags gthread-2.0)" ; \
	export CFLAGS="-I$(PACKAGE_PYTHON2_INCLUDE_PATH)" ; \
	$(MAKE) -C $(PYTHON2_RRDTOOL_BUILD_DIR)/bindings all
	$(TOUCH) $@

$(PYTHON2_RRDTOOL_INSTALL): $(PYTHON2_RRDTOOL_BUILD)
	set -e ; \
	unset DESTDIR MAKEFLAGS ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	$(MAKE) DESTDIR=$(DESTDIR) -C $(PYTHON2_RRDTOOL_BUILD_DIR)/bindings install
# clean up perl man pages which end up in wrong location
# clean up systemd init files. Note that on RPM based distros this
# seem to be located in /usr/lib and on debian /lib.
	if [ -n "$(DESTDIR)" ]; then \
	    $(RM) -r $(DESTDIR)/usr/local ; \
	    $(RM) -r $(DESTDIR)/usr/share ; \
	    $(RM) -r $(DESTDIR)/lib ; \
	fi
	$(TOUCH) $@
