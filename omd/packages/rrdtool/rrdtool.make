RRDTOOL := rrdtool
# Note: We actually use the snapshot f1edd121a from 2017-06-11
RRDTOOL_VERS := 1.7.1
RRDTOOL_DIR := $(RRDTOOL)-$(RRDTOOL_VERS)

RRDTOOL_CONFIGURE := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-configure
RRDTOOL_BUILD := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-build
RRDTOOL_BUILD_LIBRARY := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-build-library
RRDTOOL_BUILD_BINDINGS := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-build-bindings
RRDTOOL_INSTALL := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install
RRDTOOL_INSTALL_LIBRARY := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install-library
RRDTOOL_INSTALL_BINDINGS := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install-bindings
RRDTOOL_PATCHING := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-patching

RRDTOOL_CONFIGUREOPTS  := \
	--prefix=$(OMD_ROOT) \
	--disable-ruby \
	--disable-libwrap \
	--enable-perl-site-install \
	--disable-tcl \
	--disable-lua \
	--disable-rrdcgi \
	--with-perl-options="LIB=$(DESTDIR)$(OMD_ROOT)/lib/perl5/lib/perl5"

.PHONY: $(RRDTOOL) $(RRDTOOL)-install $(RRDTOOL)-skel $(RRDTOOL)-build $(RRDTOOL)-build-bindings $(RRDTOOL)-build-library \
	$(RRDTOOL)-install-bindings $(RRDTOOL)-install-library

$(RRDTOOL): $(RRDTOOL_BUILD)

$(RRDTOOL)-install: $(RRDTOOL_INSTALL)
$(RRDTOOL)-install-bindings: $(RRDTOOL_INSTALL_BINDINGS)
$(RRDTOOL)-install-library: $(RRDTOOL_INSTALL_LIBRARY)
$(RRDTOOL)-build: $(RRDTOOL_BUILD)
$(RRDTOOL)-build-bindings: $(RRDTOOL_BUILD_BINDINGS)
$(RRDTOOL)-build-library: $(RRDTOOL_BUILD_LIBRARY)

$(RRDTOOL_CONFIGURE): $(RRDTOOL_PATCHING)
# TODO: We need to find out which variables here are needed for the configure and which for the make calls
	$(ECHO) "install  --install_base  $(DESTDIR)$(OMD_ROOT)/lib/perl5" > .modulebuildrc
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export PERL5LIB=$(PACKAGE_PERL_MODULES_PERL5LIB); \
	export PERL_MM_OPT=INSTALL_BASE=$(DESTDIR)$(OMD_ROOT)/lib/perl5; \
	export MODULEBUILDRC=$$(pwd)/.modulebuildrc; \
	export PKG_CONFIG_PATH="../../glib/glib-2.13.7:../../pango/pango-1.17.5:../../cairo/cairo-1.4.6/src"; \
	export top_builddir="."; \
	export LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 -L$$(pwd)/../../cairo/cairo-1.4.6/src/.libs -L$$(pwd)/../../glib/glib-2.13.7/glib/.libs -L$$(pwd)/../../pango/pango-1.17.5/pango/.libs -L$$(pwd)/../../pango/pango-1.17.5/pango $(PACKAGE_PYTHON_LDFLAGS)" ; \
	export CPPFLAGS="$(shell pkg-config --cflags gthread-2.0) -I$$(pwd)/../../glib/glib-2.13.7 -I$$(pwd)/../../glib/glib-2.13.7/glib -I$$(pwd)/../../pango/pango-1.17.5 -I$$(pwd)/../../pango/pango-1.17.5/pango -I$$(pwd)/../../cairo/cairo-1.4.6/src" ; \
	cd $(RRDTOOL_DIR) && \
        ./configure $(RRDTOOL_CONFIGUREOPTS)
	$(TOUCH) $@

$(RRDTOOL_BUILD): $(RRDTOOL_BUILD_LIBRARY) $(RRDTOOL_BUILD_BINDINGS)

$(RRDTOOL_BUILD_LIBRARY): $(RRDTOOL_CONFIGURE)
# Build everything except the bindings (which have python and so on as
# dependency which would take a long time to build)
# TODO: We need to find out which variables here are needed for the configure and which for the make calls
	$(ECHO) "install  --install_base  $(DESTDIR)$(OMD_ROOT)/lib/perl5" > .modulebuildrc
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export PERL5LIB=$(PACKAGE_PERL_MODULES_PERL5LIB); \
	export PERL_MM_OPT=INSTALL_BASE=$(DESTDIR)$(OMD_ROOT)/lib/perl5; \
	export MODULEBUILDRC=$$(pwd)/.modulebuildrc; \
	export PKG_CONFIG_PATH="../../glib/glib-2.13.7:../../pango/pango-1.17.5:../../cairo/cairo-1.4.6/src"; \
	export top_builddir="."; \
	export LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 -L$$(pwd)/../../cairo/cairo-1.4.6/src/.libs -L$$(pwd)/../../glib/glib-2.13.7/glib/.libs -L$$(pwd)/../../pango/pango-1.17.5/pango/.libs -L$$(pwd)/../../pango/pango-1.17.5/pango $(PACKAGE_PYTHON_LDFLAGS)" ; \
	export CPPFLAGS="$(shell pkg-config --cflags gthread-2.0) -I$$(pwd)/../../glib/glib-2.13.7 -I$$(pwd)/../../glib/glib-2.13.7/glib -I$$(pwd)/../../pango/pango-1.17.5 -I$$(pwd)/../../pango/pango-1.17.5/pango -I$$(pwd)/../../cairo/cairo-1.4.6/src" ; \
	$(MAKE) -C $(RRDTOOL_DIR)/po all && \
	$(MAKE) -C $(RRDTOOL_DIR)/src all && \
	$(MAKE) -C $(RRDTOOL_DIR)/tests all && \
	$(MAKE) -C $(RRDTOOL_DIR)/etc all
	$(TOUCH) $@

$(RRDTOOL_BUILD_BINDINGS): $(RRDTOOL_CONFIGURE) $(RRDTOOL_BUILD_LIBRARY) $(PYTHON_BUILD) $(PYTHON_MODULES_BUILD)
# TODO: We need to find out which variables here are needed for the configure and which for the make calls
	$(ECHO) "install  --install_base  $(DESTDIR)$(OMD_ROOT)/lib/perl5" > .modulebuildrc
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export PERL5LIB=$(PACKAGE_PERL_MODULES_PERL5LIB); \
	export PERL_MM_OPT=INSTALL_BASE=$(DESTDIR)$(OMD_ROOT)/lib/perl5; \
	export MODULEBUILDRC=$$(pwd)/.modulebuildrc; \
	export PKG_CONFIG_PATH="../../glib/glib-2.13.7:../../pango/pango-1.17.5:../../cairo/cairo-1.4.6/src"; \
	export top_builddir="."; \
	export LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 -L$$(pwd)/../../cairo/cairo-1.4.6/src/.libs -L$$(pwd)/../../glib/glib-2.13.7/glib/.libs -L$$(pwd)/../../pango/pango-1.17.5/pango/.libs -L$$(pwd)/../../pango/pango-1.17.5/pango $(PACKAGE_PYTHON_LDFLAGS)" ; \
	export CPPFLAGS="$(shell pkg-config --cflags gthread-2.0) -I$$(pwd)/../../glib/glib-2.13.7 -I$$(pwd)/../../glib/glib-2.13.7/glib -I$$(pwd)/../../pango/pango-1.17.5 -I$$(pwd)/../../pango/pango-1.17.5/pango -I$$(pwd)/../../cairo/cairo-1.4.6/src" ; \
	$(MAKE) -C $(RRDTOOL_DIR)/bindings all
	$(TOUCH) $@

$(RRDTOOL_INSTALL): $(RRDTOOL_INSTALL_LIBRARY) $(RRDTOOL_INSTALL_BINDINGS)

# TODO: We need to find out which variables here are needed for the configure and which for the make calls
$(RRDTOOL_INSTALL_LIBRARY): $(RRDTOOL_BUILD_LIBRARY)
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	$(MAKE) DESTDIR=$(DESTDIR) -C $(RRDTOOL_DIR)/po install && \
	$(MAKE) DESTDIR=$(DESTDIR) -C $(RRDTOOL_DIR)/src install && \
	$(MAKE) DESTDIR=$(DESTDIR) -C $(RRDTOOL_DIR)/tests install && \
	$(MAKE) DESTDIR=$(DESTDIR) -C $(RRDTOOL_DIR)/etc install
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool
	install -m 644 $(RRDTOOL_DIR)/COPYRIGHT $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool
	install -m 644 $(RRDTOOL_DIR)/CONTRIBUTORS $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool
	$(TOUCH) $@

# TODO: We need to find out which variables here are needed for the configure and which for the make calls
$(RRDTOOL_INSTALL_BINDINGS): $(RRDTOOL_BUILD_BINDINGS)
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export PERL5LIB=$(PACKAGE_PERL_MODULES_PERL5LIB); \
	$(MAKE) DESTDIR=$(DESTDIR) -C $(RRDTOOL_DIR)/bindings install
# clean up perl man pages which end up in wrong location
# clean up systemd init files. Note that on RPM based distros this
# seem to be located in /usr/lib and on debian /lib.
	if [ -n "$(DESTDIR)" ]; then \
	    $(RM) -r $(DESTDIR)/usr/local ; \
	    $(RM) -r $(DESTDIR)/usr/share ; \
	    $(RM) -r $(DESTDIR)/lib ; \
	fi
	$(TOUCH) $@

$(RRDTOOL)-skel:

$(RRDTOOL)-clean:
	$(RM) -r $(RRDTOOL_DIR) $(BUILD_HELPER_DIR)/$(RRDTOOL)*
	$(RM) -r .modulebuildrc
