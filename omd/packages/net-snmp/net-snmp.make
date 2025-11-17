NET_SNMP := net-snmp
NET_SNMP_DIR := $(NET_SNMP)

NET_SNMP_BUILD := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-build
NET_SNMP_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-install-intermediate
NET_SNMP_INSTALL := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-install

NET_SNMP_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(NET_SNMP_DIR)
NET_SNMP_PYTHONPATH := $(NET_SNMP_INSTALL_DIR)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/site-packages

.PHONY: $(NET_SNMP_BUILD)
$(NET_SNMP_BUILD):
# Skip Perl-Modules because of build errors when MIB loading is disabled.
# Skip Python binding because we need to use our own python, see install target.
	$(BAZEL_BUILD) @$(NET_SNMP)//:$(NET_SNMP)

.PHONY: $(NET_SNMP_INTERMEDIATE_INSTALL)
$(NET_SNMP_INTERMEDIATE_INSTALL): $(NET_SNMP_BUILD)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(NET_SNMP)/$(NET_SNMP)/ $(NET_SNMP_INSTALL_DIR)
	chmod 644 $(NET_SNMP_INSTALL_DIR)/share/snmp/mibs/*

.PHONY: $(NET_SNMP_INSTALL)
$(NET_SNMP_INSTALL): $(NET_SNMP_INTERMEDIATE_INSTALL)
	$(PACKAGE_PYTHON_EXECUTABLE) -m compileall \
	    -f \
	    --invalidation-mode=checked-hash \
	    -s "$(NET_SNMP_PYTHONPATH)/" \
	    -o 0 -o 1 -o 2 -j0 \
	    "$(NET_SNMP_PYTHONPATH)/netsnmp/"
	PYTHONPATH=$(DESTDIR)$(OMD_ROOT)/lib/python$(PYTHON_MAJOR_DOT_MINOR)/site-packages \
		PYTHONDONTWRITEBYTECODE=1 \
		$(PACKAGE_PYTHON_EXECUTABLE) -c "from pysmi.scripts.mibdump import start; start()" \
		--mib-searcher=$(NET_SNMP_INSTALL_DIR)/share/snmp/mibs \
		--destination-directory=$(NET_SNMP_INSTALL_DIR)/share/snmp/compiled_mibs \
		--no-python-compile \
		--rebuild \
		"$(shell pwd)/RFC-1212.txt" $(wildcard $(NET_SNMP_INSTALL_DIR)/share/snmp/mibs/*.txt)
	$(RSYNC) $(NET_SNMP_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
