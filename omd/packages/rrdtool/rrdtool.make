RRDTOOL := rrdtool
RRDTOOL_VERS := 1.7.2
RRDTOOL_DIR := $(RRDTOOL)-$(RRDTOOL_VERS)
# Increase this to enforce a recreation of the build cache
RRDTOOL_BUILD_ID := 2

RRDTOOL_PATCHING := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-patching
RRDTOOL_CONFIGURE := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-configure
RRDTOOL_BUILD := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-build
RRDTOOL_BUILD_LIBRARY := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-build-library
RRDTOOL_BUILD_BINDINGS := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-build-bindings
RRDTOOL_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install-intermediate
RRDTOOL_INTERMEDIATE_INSTALL_LIBRARY := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install-intermediate-library
RRDTOOL_INTERMEDIATE_INSTALL_BINDINGS := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install-intermediate-bindings
RRDTOOL_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-cache-pkg-process
RRDTOOL_CACHE_PKG_PROCESS_LIBRARY := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-cache-pkg-process-library
RRDTOOL_CACHE_PKG_PROCESS_BINDINGS := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-cache-pkg-process-bindings
RRDTOOL_INSTALL := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install
RRDTOOL_INSTALL_LIBRARY := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install-library
RRDTOOL_INSTALL_BINDINGS := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install-bindings

RRDTOOL_INSTALL_DIR_LIBRARY := $(INTERMEDIATE_INSTALL_BASE)/$(RRDTOOL_DIR)-library
RRDTOOL_INSTALL_DIR_BINDINGS := $(INTERMEDIATE_INSTALL_BASE)/$(RRDTOOL_DIR)-bindings
RRDTOOL_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(RRDTOOL_DIR)
RRDTOOL_WORK_DIR := $(PACKAGE_WORK_DIR)/$(RRDTOOL_DIR)

RRDTOOL_WORK_MODULEBUILDRC := $(RRDTOOL_WORK_DIR)/.modulebuildrc

# Used by other OMD packages (e.g. mk-livestatus.make)
PACKAGE_RRDTOOL_DESTDIR := $(RRDTOOL_INSTALL_DIR_LIBRARY)

# Executed from enterprise/core/src/Makefile.am and livestatus/src/Makefile.am
# and enterprise/core/src/.f12
$(RRDTOOL)-build-library: $(BUILD_HELPER_DIR) $(RRDTOOL_CACHE_PKG_PROCESS_LIBRARY)

RRDTOOL_CONFIGUREOPTS  := \
	--prefix="" \
	--disable-ruby \
	--disable-libwrap \
	--enable-perl-site-install \
	--disable-tcl \
	--disable-lua \
	--disable-rrdcgi \
	--with-systemdsystemunitdir=no \
	--with-perl-options="LIB=/lib/perl5/lib/perl5"

$(RRDTOOL_WORK_MODULEBUILDRC):
	$(MKDIR) $(RRDTOOL_WORK_DIR)
	$(ECHO) "install  --install_base  $(DESTDIR)$(OMD_ROOT)/lib/perl5" > $@

$(RRDTOOL_CONFIGURE): $(RRDTOOL_PATCHING)
# TODO: We need to find out which variables here are needed for the configure and which for the make calls
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export top_builddir="."; \
	export LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 $(PACKAGE_PYTHON_LDFLAGS)" ; \
	export CPPFLAGS="$(shell pkg-config --cflags gthread-2.0) -I$(PACKAGE_PYTHON_INCLUDE_PATH)" ; \
	cd $(RRDTOOL_BUILD_DIR) && \
        ./configure $(RRDTOOL_CONFIGUREOPTS)
	$(TOUCH) $@

$(RRDTOOL_BUILD): $(RRDTOOL_BUILD_LIBRARY) $(RRDTOOL_BUILD_BINDINGS)

$(RRDTOOL_BUILD_LIBRARY): $(RRDTOOL_CONFIGURE)
# Build everything except the bindings (which have python and so on as
# dependency which would take a long time to build)
# TODO: We need to find out which variables here are needed for the configure and which for the make calls
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export top_builddir="."; \
	export LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 $(PACKAGE_PYTHON_LDFLAGS)" ; \
	export CPPFLAGS="$(shell pkg-config --cflags gthread-2.0) -I$(PACKAGE_PYTHON_INCLUDE_PATH)" ; \
	$(MAKE) -C $(RRDTOOL_BUILD_DIR)/po all && \
	$(MAKE) -C $(RRDTOOL_BUILD_DIR)/src all && \
	$(MAKE) -C $(RRDTOOL_BUILD_DIR)/tests all && \
	$(MAKE) -C $(RRDTOOL_BUILD_DIR)/etc all
	$(TOUCH) $@

$(RRDTOOL_BUILD_BINDINGS): $(RRDTOOL_CONFIGURE) $(RRDTOOL_BUILD_LIBRARY) $(PYTHON_CACHE_PKG_PROCESS) $(PYTHON3_MODULES_CACHE_PKG_PROCESS) $(RRDTOOL_WORK_MODULEBUILDRC) $(PERL_MODULES_CACHE_PKG_PROCESS)
# TODO: We need to find out which variables here are needed for the configure and which for the make calls
	set -e ; \
	unset DESTDIR MAKEFLAGS ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export PERL5LIB=$(PACKAGE_PERL_MODULES_PERL5LIB); \
	export PERL_MM_OPT=INSTALL_BASE=$(DESTDIR)$(OMD_ROOT)/lib/perl5; \
	export MODULEBUILDRC=$(RRDTOOL_WORK_MODULEBUILDRC); \
	export top_builddir="."; \
	export LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 $(PACKAGE_PYTHON_LDFLAGS)" ; \
	export CPPFLAGS="$(shell pkg-config --cflags gthread-2.0)" ; \
	$(MAKE) -C $(RRDTOOL_BUILD_DIR)/bindings all
	$(TOUCH) $@

$(RRDTOOL_CACHE_PKG_PROCESS): $(RRDTOOL_CACHE_PKG_PROCESS_LIBRARY) $(RRDTOOL_CACHE_PKG_PROCESS_BINDINGS)

RRDTOOL_CACHE_PKG_PATH_LIBRARY := $(call cache_pkg_path,$(RRDTOOL_DIR)-library,$(RRDTOOL_BUILD_ID))

$(RRDTOOL_CACHE_PKG_PATH_LIBRARY):
	$(call pack_pkg_archive,$@,$(RRDTOOL_DIR)-library,$(RRDTOOL_BUILD_ID),$(RRDTOOL_INTERMEDIATE_INSTALL_LIBRARY))

$(RRDTOOL_CACHE_PKG_PROCESS_LIBRARY): $(RRDTOOL_CACHE_PKG_PATH_LIBRARY)
	$(call unpack_pkg_archive,$(RRDTOOL_CACHE_PKG_PATH_LIBRARY),$(RRDTOOL_DIR)-library)
	$(call upload_pkg_archive,$(RRDTOOL_CACHE_PKG_PATH_LIBRARY),$(RRDTOOL_DIR)-library,$(RRDTOOL_BUILD_ID))
	$(TOUCH) $@

RRDTOOL_CACHE_PKG_PATH_BINDINGS := $(call cache_pkg_path,$(RRDTOOL_DIR)-bindings,$(RRDTOOL_BUILD_ID))

$(RRDTOOL_CACHE_PKG_PATH_BINDINGS):
	$(call pack_pkg_archive,$@,$(RRDTOOL_DIR)-bindings,$(RRDTOOL_BUILD_ID),$(RRDTOOL_INTERMEDIATE_INSTALL_BINDINGS))

$(RRDTOOL_CACHE_PKG_PROCESS_BINDINGS): $(RRDTOOL_CACHE_PKG_PATH_BINDINGS)
	$(call unpack_pkg_archive,$(RRDTOOL_CACHE_PKG_PATH_BINDINGS),$(RRDTOOL_DIR)-bindings)
	$(call upload_pkg_archive,$(RRDTOOL_CACHE_PKG_PATH_BINDINGS),$(RRDTOOL_DIR)-bindings,$(RRDTOOL_BUILD_ID))
	$(TOUCH) $@

$(RRDTOOL_INTERMEDIATE_INSTALL): $(RRDTOOL_INTERMEDIATE_INSTALL_LIBRARY) $(RRDTOOL_INTERMEDIATE_INSTALL_BINDINGS)

# TODO: We need to find out which variables here are needed for the configure and which for the make calls
$(RRDTOOL_INTERMEDIATE_INSTALL_LIBRARY): $(RRDTOOL_BUILD_LIBRARY)
	set -e ; \
	unset MAKEFLAGS ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	$(MAKE) DESTDIR=$(RRDTOOL_INSTALL_DIR_LIBRARY) -C $(RRDTOOL_BUILD_DIR)/po install && \
	$(MAKE) DESTDIR=$(RRDTOOL_INSTALL_DIR_LIBRARY) -C $(RRDTOOL_BUILD_DIR)/src install && \
	$(MAKE) DESTDIR=$(RRDTOOL_INSTALL_DIR_LIBRARY) -C $(RRDTOOL_BUILD_DIR)/tests install && \
	$(MAKE) DESTDIR=$(RRDTOOL_INSTALL_DIR_LIBRARY) -C $(RRDTOOL_BUILD_DIR)/etc install
	$(MKDIR) $(RRDTOOL_INSTALL_DIR_LIBRARY)/share/doc/rrdtool
	install -m 644 $(RRDTOOL_BUILD_DIR)/COPYRIGHT $(RRDTOOL_INSTALL_DIR_LIBRARY)/share/doc/rrdtool
	install -m 644 $(RRDTOOL_BUILD_DIR)/CONTRIBUTORS $(RRDTOOL_INSTALL_DIR_LIBRARY)/share/doc/rrdtool
	$(TOUCH) $@

# TODO: We need to find out which variables here are needed for the configure and which for the make calls
$(RRDTOOL_INTERMEDIATE_INSTALL_BINDINGS): $(RRDTOOL_BUILD_BINDINGS) $(PERL_MODULES_CACHE_PKG_PROCESS)
	set -e ; \
	unset MAKEFLAGS ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export PERL5LIB=$(PACKAGE_PERL_MODULES_PERL5LIB); \
	$(MAKE) DESTDIR=$(RRDTOOL_INSTALL_DIR_BINDINGS) -C $(RRDTOOL_BUILD_DIR)/bindings install
# Fixup some library permissions. They need to be owner writable to make
# dh_strip command of deb packaging procedure work
	find $(RRDTOOL_INSTALL_DIR_BINDINGS)/lib/perl5/lib/perl5 -type f -name RRDs.so -exec chmod u+w {} \;
# clean up perl man pages which end up in wrong location
# clean up systemd init files. Note that on RPM based distros this
# seem to be located in /usr/lib and on debian /lib.
	$(RM) -r $(RRDTOOL_INSTALL_DIR_BINDINGS)/usr
	$(TOUCH) $@

$(RRDTOOL_INSTALL): $(RRDTOOL_INSTALL_BINDINGS) $(RRDTOOL_INSTALL_LIBRARY)

$(RRDTOOL_INSTALL_LIBRARY): $(RRDTOOL_CACHE_PKG_PROCESS_LIBRARY)
	$(RSYNC) $(RRDTOOL_INSTALL_DIR_LIBRARY)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@

$(RRDTOOL_INSTALL_BINDINGS): $(RRDTOOL_CACHE_PKG_PROCESS_BINDINGS)
	$(RSYNC) $(RRDTOOL_INSTALL_DIR_BINDINGS)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
