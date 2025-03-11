PNP4NAGIOS := pnp4nagios

PNP4NAGIOS_BUILD := $(BUILD_HELPER_DIR)/$(PNP4NAGIOS)-build
PNP4NAGIOS_INSTALL := $(BUILD_HELPER_DIR)/$(PNP4NAGIOS)-install

# Unset CONFIG_SITE
CONFIG_SITE = ''

.PHONY: $(PNP4NAGIOS_BUILD)
$(PNP4NAGIOS_BUILD):
	bazel build @$(PNP4NAGIOS)//:$(PNP4NAGIOS)
	bazel build @$(PNP4NAGIOS)//:skel

.PHONY: $(PNP4NAGIOS_INSTALL)
$(PNP4NAGIOS_INSTALL): $(PNP4NAGIOS_BUILD)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(PNP4NAGIOS)/$(PNP4NAGIOS)/ $(DESTDIR)$(OMD_ROOT)/
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/doc/pnp4nagios/*
	$(RSYNC) --chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fg=r,Fo=r $(BAZEL_BIN_EXT)/$(PNP4NAGIOS)/skel/ $(DESTDIR)$(OMD_ROOT)/skel
	install -m 644 $(BAZEL_BIN_EXT)/$(PNP4NAGIOS)/share/diskspace/pnp4nagios $(DESTDIR)$(OMD_ROOT)/share/diskspace/pnp4nagios
	install -m 755 $(BAZEL_BIN_EXT)/$(PNP4NAGIOS)/lib/omd/hooks/PNP4NAGIOS $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	# remove .gitignores that are added because genrules don't support directories
	find $(DESTDIR)$(OMD_ROOT)/ -name ".gitignore" -delete
	# Add symlinks, as bazel is dereferencing them
	cd $(DESTDIR)$(OMD_ROOT)/skel/etc/rc.d/ ; \
	ln -sf ../init.d/npcd 50-npcd ; \
	ln -sf ../init.d/pnp_gearman_worker 52-pnp_gearman_worker
	sed -i 's|PLACEHOLDER|$(OMD_ROOT)|' $(DESTDIR)$(OMD_ROOT)/lib/pnp4nagios/process_perfdata.pl
