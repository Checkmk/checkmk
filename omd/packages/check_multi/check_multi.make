CHECK_MULTI := check_multi
CHECK_MULTI_VERS := 83346b6
CHECK_MULTI_DIR := $(CHECK_MULTI)-$(CHECK_MULTI_VERS)
CHECK_MULTI_ARCH := $(CHECK_MULTI)-latest-$(CHECK_MULTI_VERS)
ROOTDIR := \\\$$ENV{OMD_ROOT}
SITE := \\\$$ENV{OMD_SITE}
TESTDIR := ../t/packages/check_multi/t

CHECK_MULTI_BUILD := $(BUILD_HELPER_DIR)/$(CHECK_MULTI_ARCH)-build
CHECK_MULTI_INSTALL := $(BUILD_HELPER_DIR)/$(CHECK_MULTI_ARCH)-install
CHECK_MULTI_UNPACK := $(BUILD_HELPER_DIR)/$(CHECK_MULTI_ARCH)-unpack

.PHONY: $(CHECK_MULTI) $(CHECK_MULTI)-install $(CHECK_MULTI)-skel $(CHECK_MULTI)-clean

$(CHECK_MULTI): $(CHECK_MULTI_BUILD)

$(CHECK_MULTI)-install: $(CHECK_MULTI_INSTALL)

$(CHECK_MULTI)-skel:

# TODO
#--with-nagios-name=<nagios>       set nagios name (there might be some clones ;)) (default:nagios)
#--with-action_url="$(OMD_SITE)/pnp4nagios/index.php/graph?host=\\\$$HOSTNAME\\\$$&srv=\\\$$SERVICEDESC\\\$$"
CHECK_MULTI_CONFIGUREOPTS := \
	--libexecdir="$(ROOTDIR)/lib/nagios/plugins" \
	--prefix="$(ROOTDIR)" \
	--with-action_mouseover=1 \
	--with-add_tag_to_list_entries=0 \
	--with-cancel_before_global_timeout=0 \
	--with-checkresults_dir="$(ROOTDIR)/tmp/nagios/checkresults" \
	--with-child_interval=0.0 \
	--with-child_timeout=11 \
	--with-client_perl="/usr/bin/perl" \
	--with-cmdfile_update_interval=86400 \
	--with-collapse=1 \
	--with-complain_unknown_macros=1 \
	--with-config_dir="$(ROOTDIR)/etc/$(CHECK_MULTI)" \
	--with-cumulate_ignore_zero=1 \
	--with-cumulate_max_rows=5 \
	--with-empty_output_is_unknown=1 \
	--with-ethtool="/sbin/ethtool" \
	--with-exec_open3=0 \
	--with-extended_perfdata=1 \
	--with-extinfo_in_status=0 \
	--with-feed_passive_autocreate=0 \
	--with-feed_passive_dir="$(ROOTDIR)/etc/$(CHECK_MULTI)/feed_passive" \
	--with-feed_passive_dir_permissions=0750 \
	--with-findbin=1 \
	--with-file_extension="cmd" \
	--with-html_ascii_notification=0 \
	--with-ignore_missing_cmd_file=0 \
	--with-illegal_chars="\r" \
	--with-image_path="/$(SITE)/nagios/images" \
	--with-indent=" " \
	--with-indent_label=1 \
	--with-livestatus="$(ROOTDIR)/tmp/run/live" \
	--with-loose_perfdata=1 \
	--with-name="" \
	--with-nagios-user=$(SITE) \
	--with-nagios-group=$(SITE) \
	--with-no_checks_rc=3 \
	--with-notes_url="/${SITE}/wiki/doku.php?id=start&idx=none" \
	--with-objects_cache="$(ROOTDIR)/var/nagios/objects.cache" \
	--with-objects_cache_delimiter="," \
	--with-omd_environment=1 \
	--with-parent_timeout=60 \
	--with-perfdata_pass_through=0 \
	--with-persistent=0 \
	--with-plugin_path="$(ROOTDIR)/lib/nagios/plugins" \
	--with-pnp_add2url="" \
	--with-pnp_url="/$(SITE)/pnp4nagios" \
	--with-pnp_version=0.6 \
	--with-report=13 \
	--with-report_inherit_mask=-1 \
	--with-signal_rc=3 \
	--with-snmp_community="public" \
	--with-snmp_port=161 \
	--with-status_dat="$(ROOTDIR)/tmp/nagios/status.dat" \
	--with-style_plus_minus="" \
	--with-tag_notes_link="" \
	--with-target="_self" \
	--with-tmp_dir="$(ROOTDIR)/tmp/check_multi" \
	--with-tmp_dir_permissions=01777 \
	--with-tmp_etc="$(ROOTDIR)/tmp/check_multi/etc" \

$(CHECK_MULTI_BUILD): $(CHECK_MULTI_UNPACK)
	cd $(CHECK_MULTI_DIR) ; ./configure $(CHECK_MULTI_CONFIGUREOPTS)
	$(MAKE) -C $(CHECK_MULTI_DIR) all
	$(TOUCH) $@

$(CHECK_MULTI_INSTALL): $(CHECK_MULTI_BUILD)
	#--- plugin
	install -m 755 $(CHECK_MULTI_DIR)/plugins/check_multi $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins

	#--- readme
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/check_multi
	install -m 644 $(CHECK_MULTI_DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/check_multi

	#--- allow to find testdir in plugin directory
	test -L check_multi || ln -s $(CHECK_MULTI_DIR) check_multi
	$(TOUCH) $@

$(CHECK_MULTI)-clean:
	rm -rf $(CHECK_MULTI_DIR) check_multi $(BUILD_HELPER_DIR)/$(CHECK_MULTI)*

$(CHECK_MULTI)-get:
	#wget --no-clobber my-plugin.de/check_multi/check_multi-stable-$(CHECK_MULTI_VERS).tar.gz
	wget --no-clobber my-plugin.de/check_multi/check_multi-latest.tar.gz

$(CHECK_MULTI)-get-force:
	#rm check_multi-stable-$(CHECK_MULTI_VERS).tar.gz
	#wget --no-clobber my-plugin.de/check_multi/check_multi-stable-$(CHECK_MULTI_VERS).tar.gz
	rm check_multi-latest-$(CHECK_MULTI_VERS).tar.gz
	wget --no-clobber my-plugin.de/check_multi/check_multi-latest.tar.gz
