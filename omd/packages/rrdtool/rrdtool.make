RRDTOOL := rrdtool
# Note: We actually use the snapshot f1edd121a from 2017-06-11
RRDTOOL_VERS := 1.7.0
RRDTOOL_DIR := $(RRDTOOL)-$(RRDTOOL_VERS)

RRDTOOL_BUILD := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-build
RRDTOOL_INSTALL := $(BUILD_HELPER_DIR)/$(RRDTOOL_DIR)-install
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

.PHONY: $(RRDTOOL) $(RRDTOOL)-install $(RRDTOOL)-skel

$(RRDTOOL): $(RRDTOOL_BUILD)

$(RRDTOOL)-install: $(RRDTOOL_INSTALL)

$(RRDTOOL_BUILD): $(RRDTOOL_PATCHING) $(PYTHON_BUILD) $(PYTHON_MODULES_BUILD) 
# set perl environment to match the other perl modules
	$(ECHO) "install  --install_base  $(DESTDIR)$(OMD_ROOT)/lib/perl5" > .modulebuildrc
# The MS_ASYNC/mtime check is broken and often leads to non-killable sync syscalls.
# Furthermore, the check doesn't make sense at all in a chroot environment.
	case "$$(lsb_release -i | cut -f2) $$(lsb_release -r | cut -f2)" in \
	  CentOS\ 5.*) MS_ASYNC=broken ;; \
	  *) MS_ASYNC=ok ;; \
	esac ; \
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
	export rd_cv_ms_async="$$MS_ASYNC" ; \
	cd $(RRDTOOL_DIR) && \
        ./configure $(RRDTOOL_CONFIGUREOPTS) && \
        $(MAKE) all
	$(TOUCH) $@

$(RRDTOOL_INSTALL): $(RRDTOOL_BUILD)
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	export PYTHONPATH=$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH) ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH=$(PACKAGE_PYTHON_LD_LIBRARY_PATH) ; \
	export PATH="$(PACKAGE_PYTHON_BIN):$$PATH" ; \
	export PERL5LIB=$(PACKAGE_PERL_MODULES_PERL5LIB); \
	$(MAKE) DESTDIR=$(DESTDIR) -C $(RRDTOOL_DIR) install
# clean up perl man pages which end up in wrong location
# clean up systemd init files. Note that on RPM based distros this
# seem to be located in /usr/lib and on debian /lib.
	if [ -n "$(DESTDIR)" ]; then \
	    $(RM) -r $(DESTDIR)/usr/local ; \
	    $(RM) -r $(DESTDIR)/usr/share ; \
	    $(RM) -r $(DESTDIR)/lib ; \
	fi
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool
	install -m 644 $(RRDTOOL_DIR)/COPYRIGHT $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool
	install -m 644 $(RRDTOOL_DIR)/CONTRIBUTORS $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool
	$(TOUCH) $@

$(RRDTOOL)-skel:

$(RRDTOOL)-clean:
	$(RM) -r $(RRDTOOL_DIR) $(BUILD_HELPER_DIR)/$(RRDTOOL)*
	$(RM) -r .modulebuildrc
