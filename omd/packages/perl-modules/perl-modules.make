PERL_MODULES := perl-modules
# Use some pseudo version here. Don't use OMD_VERSION (would break the package cache)
PERL_MODULES_VERS := 1.0
PERL_MODULES_DIR := $(PERL_MODULES)-$(PERL_MODULES_VERS)
# Increase this to enforce a recreation of the build cache
# Note: Because the versions of the individual modules is not reflected in PERL_MODULES_VERS,
#       like it is done in other OMD packages, we'll have to increase the BUILD_ID on every package
#       change.
PERL_MODULES_BUILD_ID := 2

PERL_MODULES_BUILD := $(BUILD_HELPER_DIR)/$(PERL_MODULES_DIR)-build
PERL_MODULES_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PERL_MODULES_DIR)-install-intermediate
PERL_MODULES_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PERL_MODULES_DIR)-cache-pkg-process
PERL_MODULES_INSTALL := $(BUILD_HELPER_DIR)/$(PERL_MODULES_DIR)-install

PERL_MODULES_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PERL_MODULES_DIR)
PERL_MODULES_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PERL_MODULES_DIR)
PERL_MODULES_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PERL_MODULES_DIR)

PERL_MODULES_BUILD_SRCDIR := $(PERL_MODULES_BUILD_DIR)/src
PERL_MODULES_BUILD_DESTDIR := $(PERL_MODULES_BUILD_DIR)/dest
PERL_MODULES_BUILD_PERL5LIB := $(PERL_MODULES_BUILD_DESTDIR)/lib/perl5

# Used by other packages
PACKAGE_PERL_MODULES_PERL5LIB := $(PERL_MODULES_INSTALL_DIR)/lib/perl5

PERL_MODULES_LIST1 := \
                   ExtUtils-MakeMaker-7.04.tar.gz \
                   parent-0.232.tar.gz \
                   version-0.9924.tar.gz \
                   Module-CoreList-5.20150420.tar.gz \
                   common-sense-3.73.tar.gz \
                   Types-Serialiser-1.0.tar.gz \
                   JSON-2.90.tar.gz \
                   JSON-PP-2.27300.tar.gz \
                   JSON-XS-3.01.tar.gz

PERL_MODULES_LIST2 := \
                  Capture-Tiny-0.27.tar.gz \
                  Carp-Clan-6.04.tar.gz \
                  Class-Accessor-0.34.tar.gz \
                  Class-Singleton-1.5.tar.gz \
                  Config-General-2.56.tar.gz \
                  Crypt-Blowfish_PP-1.12.tar.gz \
                  Data-Dumper-2.154.tar.gz \
                  Digest-MD5-2.54.tar.gz \
                  Digest-SHA1-2.13.tar.gz \
                  ExtUtils-Constant-0.23.tar.gz \
                  Getopt-Long-2.43.tar.gz \
                  HTTP-Date-6.02.tar.gz \
                  Locale-Maketext-Simple-0.21.tar.gz \
                  Math-Calc-Units-1.07.tar.gz \
                  Module-Find-0.12.tar.gz \
                  Module-Load-0.32.tar.gz \
                  Params-Check-0.38.tar.gz \
                  PathTools-3.47.tar.gz \
                  Scalar-List-Utils-1.42.tar.gz \
                  Sub-Exporter-Progressive-0.001011.tar.gz \
                  Sub-Install-0.928.tar.gz \
                  Sys-SigAction-0.21.tar.gz \
                  Term-ReadLine-Gnu-1.25.tar.gz \
                  Term-ShellUI-0.92.tar.gz \
                  Term-Size-0.207.tar.gz \
                  TermReadKey-2.37.tar.gz \
                  Text-ParseWords-3.29.tar.gz \
                  Time-HiRes-1.9726.tar.gz \
                  Try-Tiny-0.22.tar.gz \
                  Perl-OSType-1.008.tar.gz \
                  base-2.18.tar.gz \
                  Archive-Zip-1.68.tar.gz \
                  HTML-Parser-3.71.tar.gz \
                  Term-Clui-1.70.tar.gz \
                  URI-1.67.tar.gz \
                  Class-MethodMaker-2.22.tar.gz \
                  HTTP-Message-6.06.tar.gz \
                  Module-Load-Conditional-0.64.tar.gz \
                  Net-HTTP-6.07.tar.gz \
                  Term-ProgressBar-2.17.tar.gz \
                  Test-Cmd-1.08.tar.gz \
                  Test-Simple-1.001014.tar.gz \
                  XML-LibXML-2.0134.tar.gz \
                  HTTP-Cookies-6.01.tar.gz \
                  IPC-Cmd-0.92.tar.gz \
                  ExtUtils-CBuilder-0.280220.tar.gz \
                  ExtUtils-ParseXS-3.24.tar.gz \
                  Module-Metadata-1.000027.tar.gz \
                  IO-1.25.tar.gz \
                  LWP-Protocol-https-6.10.tar.gz \
                  List-AllUtils-0.09.tar.gz \
                  libwww-perl-6.13.tar.gz \
                  Module-Build-0.4007.tar.gz \
                  Module-Runtime-0.014.tar.gz \
                  YAML-Tiny-1.67.tar.gz \
                  Module-Install-1.16.tar.gz \
                  XML-NamespaceSupport-1.11.tar.gz \
                  XML-SAX-Base-1.08.tar.gz \
                  XML-SAX-0.99.tar.gz \
                  XML-Simple-2.20.tar.gz \
                  Monitoring-Livestatus-0.74.tar.gz \
                  Params-Util-1.07.tar.gz \
                  Path-Class-0.35.tar.gz \
                  Socket-2.019.tar.gz \
                  XML-Parser-2.44.tar.gz \
                  XML-Twig-3.52.tar.gz \
                  Config-Tiny-2.20.tgz \
                  Crypt-SSLeay-0.72.tar.gz \
                  File-SearchPath-0.06.tar.gz \
                  Module-Implementation-0.09.tar.gz \
                  Params-Validate-1.18.tar.gz \
                  DateTime-Locale-0.45.tar.gz \
                  DateTime-TimeZone-1.88.tar.gz \
                  Monitoring-Plugin-0.38.tar.gz \
                  Nagios-Plugin-0.36.tar.gz \
                  DateTime-1.18.tar.gz

# TODO: Use PERL_MODULES_WORK_DIR for $(PACKAGE_DIR)/$(PERL_MODULES)/src/%-patched.tar.gz
$(PACKAGE_DIR)/$(PERL_MODULES)/src/%-patched.tar.gz: $(PACKAGE_DIR)/$(PERL_MODULES)/src/%.tar.gz
	$(MKDIR) $(PERL_MODULES_WORK_DIR)
	tar xf $< -C $(PERL_MODULES_WORK_DIR)
	set -e ; for P in $$($(LS) $(PACKAGE_DIR)/$(PERL_MODULES)/patches/$**.dif); do \
	    $(ECHO) "applying $$P..." ; \
	    $(PATCH) -p1 -b -d $(PERL_MODULES_WORK_DIR)/$* < $$P ; \
	done
	tar -cz -C $(PERL_MODULES_WORK_DIR) -f $@ $*


PERL_MODULES_CACHE_PKG_PATH := $(call cache_pkg_path,$(PERL_MODULES_DIR),$(PERL_MODULES_BUILD_ID))

$(PERL_MODULES_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PERL_MODULES_DIR),$(PERL_MODULES_BUILD_ID),$(PERL_MODULES_INTERMEDIATE_INSTALL))

$(PERL_MODULES_CACHE_PKG_PROCESS): $(PERL_MODULES_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PERL_MODULES_CACHE_PKG_PATH),$(PERL_MODULES_DIR))
	$(call upload_pkg_archive,$(PERL_MODULES_CACHE_PKG_PATH),$(PERL_MODULES_DIR),$(PERL_MODULES_BUILD_ID))
	$(TOUCH) $@

$(PERL_MODULES_BUILD): $(PACKAGE_DIR)/$(PERL_MODULES)/src/Crypt-SSLeay-0.72-patched.tar.gz
	$(MKDIR) $(PERL_MODULES_BUILD_DESTDIR)
	$(MKDIR) $(PERL_MODULES_BUILD_SRCDIR)
	$(RSYNC) $(PACKAGE_DIR)/$(PERL_MODULES)/src/. $(PERL_MODULES_BUILD_SRCDIR)/.
	$(RSYNC) $(PACKAGE_DIR)/$(PERL_MODULES)/build_module.pl $(PACKAGE_DIR)/$(PERL_MODULES)/lib $(PERL_MODULES_BUILD_SRCDIR)/.
	set -e ; for F in $$(ls $(PERL_MODULES_BUILD_SRCDIR)/*-patched.tar.gz); do \
		echo $$F; \
		echo $${F/-patched/}; \
	    mv $$F $${F/-patched/}; \
	done
	echo "install --install_base $(PERL_MODULES_BUILD_DESTDIR)" > $(PERL_MODULES_BUILD_DESTDIR)/.modulebuildrc
	set -e; unset LANG; \
	    unset DESTDIR; \
	    unset MAKEFLAGS ; \
	    unset PERL5LIB; \
	    unset PERL_MB_OPT; \
	    unset PERL_LOCAL_LIB_ROOT; \
	    unset PERL_MM_OPT; \
	    export PATH=$(PERL_MODULES_BUILD_DESTDIR)/bin:$$PATH; \
	    export PERL_MM_OPT=INSTALL_BASE=$(PERL_MODULES_BUILD_DESTDIR); \
	    export PERL_MB_OPT=--install_base=$(PERL_MODULES_BUILD_DESTDIR); \
	    export MODULEBUILDRC=$(PERL_MODULES_BUILD_DESTDIR)/.modulebuildrc; \
	    export PERL5LIB=$(PERL_MODULES_BUILD_PERL5LIB):$(PERL_MODULES_BUILD_SRCDIR)/lib:$(PERL_MODULES_BUILD_SRCDIR)/Crypt-SSLeay-0.72; \
	    cd $(PERL_MODULES_BUILD_SRCDIR) ; \
		FORCE=1 ./build_module.pl -d "$(DISTRO_INFO)" -p $(PERL_MODULES_BUILD_DESTDIR) $(PERL_MODULES_LIST1); \
	    export PERL_JSON_BACKEND='JSON::XS'; \
	    cd $(PERL_MODULES_BUILD_SRCDIR) ; \
	    ./build_module.pl -d "$(DISTRO_INFO)" -p $(PERL_MODULES_BUILD_DESTDIR) $(PERL_MODULES_LIST2)
# Fixup some library permissions. They need to be owner writable to make
# dh_strip command of deb packaging procedure work
	find $(PERL_MODULES_BUILD_DESTDIR)/lib -type f -name \*.so -exec chmod u+w {} \;
	cd $(PERL_MODULES_BUILD_PERL5LIB)/ ; $(RM) utils.pm ; ln -s ../../../nagios/plugins/utils.pm .
	$(MKDIR) $(PERL_MODULES_BUILD_PERL5LIB)/CPAN
	cp $(PACKAGE_DIR)/$(PERL_MODULES)/MyConfig.pm $(PERL_MODULES_BUILD_PERL5LIB)/CPAN/MyConfig.skel
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(PERL_MODULES_INTERMEDIATE_INSTALL): $(PERL_MODULES_BUILD)
	$(MKDIR) $(PERL_MODULES_INSTALL_DIR)/lib/perl5 $(PERL_MODULES_INSTALL_DIR)/bin
	$(RSYNC) $(PERL_MODULES_BUILD_DESTDIR)/lib $(PERL_MODULES_INSTALL_DIR)/lib/perl5/
	$(RSYNC) $(PERL_MODULES_BUILD_DESTDIR)/bin $(PERL_MODULES_INSTALL_DIR)/lib/perl5/
	$(MKDIR) $(PERL_MODULES_INSTALL_DIR)/local/lib/perl5
	install -m 755 $(PACKAGE_DIR)/$(PERL_MODULES)/bin/cpan.wrapper $(PERL_MODULES_INSTALL_DIR)/bin/cpan.wrapper
	$(TOUCH) $@

$(PERL_MODULES_INSTALL): $(PERL_MODULES_CACHE_PKG_PROCESS)
	$(RSYNC) $(PERL_MODULES_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	echo "install  --install_base  ###ROOT###/local/lib/perl5" > $(SKEL)/.modulebuildrc
	$(TOUCH) $@
