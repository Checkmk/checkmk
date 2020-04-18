PYTHON2_NET_SNMP := python2-net-snmp
PYTHON2_NET_SNMP_VERS := 0b32548
PYTHON2_NET_SNMP_DIR := $(PYTHON2_NET_SNMP)-$(PYTHON2_NET_SNMP_VERS)

PYTHON2_NET_SNMP_UNPACK := $(BUILD_HELPER_DIR)/$(PYTHON2_NET_SNMP_DIR)-unpack
PYTHON2_NET_SNMP_PATCHING := $(BUILD_HELPER_DIR)/$(PYTHON2_NET_SNMP_DIR)-patching
PYTHON2_NET_SNMP_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON2_NET_SNMP_DIR)-build
PYTHON2_NET_SNMP_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON2_NET_SNMP_DIR)-install
PYTHON2_NET_SNMP_INSTALL_BASE := $(BUILD_HELPER_DIR)/$(PYTHON2_NET_SNMP_DIR)-install-base
PYTHON2_NET_SNMP_INSTALL_PYTHON := $(BUILD_HELPER_DIR)/$(PYTHON2_NET_SNMP_DIR)-install-python

#PYTHON2_NET_SNMP_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON2_NET_SNMP_DIR)
PYTHON2_NET_SNMP_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON2_NET_SNMP_DIR)
#PYTHON2_NET_SNMP_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON2_NET_SNMP_DIR)

$(PYTHON2_NET_SNMP_UNPACK): $(PACKAGE_DIR)/$(PYTHON2_NET_SNMP)/net-snmp-$(PYTHON2_NET_SNMP_VERS).tar.gz
	$(RM) -r $(PACKAGE_BUILD_DIR)/$(PYTHON2_NET_SNMP_DIR)
	$(MKDIR) -p $(PACKAGE_BUILD_DIR)/$(PYTHON2_NET_SNMP_DIR)
	$(TAR_GZ) $< -C $(PACKAGE_BUILD_DIR)/$(PYTHON2_NET_SNMP_DIR) --strip-components=1

	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(PYTHON2_NET_SNMP_BUILD): $(PYTHON2_NET_SNMP_PATCHING) $(PYTHON_CACHE_PKG_PROCESS) $(PERL_MODULES_BUILD)
# Skip Perl-Modules because of build errors when MIB loading is disabled.
# Skip Python binding because we need to use our own python, see install target.
	cd $(PYTHON2_NET_SNMP_BUILD_DIR) \
        && if [ "$(DISTRO_CODE)" == "el8" ]; then export CFLAGS='-Wformat -I../../include -D_REENTRANT -D_GNU_SOURCE -O2 -g -pipe -Wp,-D_FORTIFY_SOURCE=2 -Wp,-D_GLIBCXX_ASSERTIONS -fexceptions -fstack-protector-strong -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -specs=/usr/lib/rpm/redhat/redhat-annobin-cc1 -m64 -mtune=generic -fasynchronous-unwind-tables -fstack-clash-protection -fcf-protection -fwrapv -fno-strict-aliasing -I/usr/local/include -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64'; fi \
        && ./configure \
	    --enable-ipv6 \
	    --disable-agent \
	    --disable-snmptrapd-subagent \
	    --with-mibdirs="\$$HOME/local/share/snmp/mibs:$(OMD_ROOT)/share/snmp/mibs:/usr/share/snmp/mibs" \
	    --with-defaults \
	    --disable-scripts \
	    --prefix=$(OMD_ROOT) && $(MAKE)
	$(TOUCH) $@

$(PYTHON2_NET_SNMP_INSTALL): $(PYTHON2_NET_SNMP_INSTALL_PYTHON)
	$(TOUCH) $@

$(PYTHON2_NET_SNMP_INSTALL_PYTHON): $(PYTHON2_NET_SNMP_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/python
	cd $(PYTHON2_NET_SNMP_BUILD_DIR)/python && \
		export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH):$(DESTDIR)$(OMD_ROOT)/lib/python" ; \
	    export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	    $(PACKAGE_PYTHON_EXECUTABLE) setup.py install --basedir=.. --home=$(DESTDIR)$(OMD_ROOT) \
		--prefix='' \
		--install-platlib=$(DESTDIR)$(OMD_ROOT)/lib/python \
		--install-purelib=$(DESTDIR)$(OMD_ROOT)/lib/python \
		--root=/ \
		--single-version-externally-managed
	$(TOUCH) $@
# For some obscure reason beyond the mental capacities of mere humans, the
# easy_install mechanism triggered by the setup call above results in the
# creation of a lib/python/site.py, a copy of site-patch.py from setuptools.
# Having this in the PYTHONPATH makes it impossible to run python3-based SW as a
# site user, including gdb! So let's simply nuke it here...
# TODO(sp): Disabled for now, otherwise the netsnmp module is not found. Figure
# out what's really going on here!
#	$(RM) $(DESTDIR)$(OMD_ROOT)/lib/python/site.py*
