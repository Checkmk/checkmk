APACHE_OMD := apache-omd
APACHE_OMD_VERS := 1.0
APACHE_OMD_DIR := $(APACHE_OMD)-$(APACHE_OMD_VERS)

APACHE_OMD_BUILD := $(BUILD_HELPER_DIR)/$(APACHE_OMD_DIR)-build
APACHE_OMD_INSTALL := $(BUILD_HELPER_DIR)/$(APACHE_OMD_DIR)-install

APACHE_OMD_MODULE_DIR=$(APACHE_MODULE_DIR)
ifeq ($(shell uname -m),x86_64)
  APACHE_OMD_MODULE_DIR=$(APACHE_MODULE_DIR_64)
endif

APACHE_MODULES := \
    mod_access_compat.so \
    mod_alias.so \
    mod_auth_basic.so \
    mod_authn_core.so \
    mod_authn_file.so \
    mod_authz_core.so \
    mod_authz_host.so \
    mod_authz_user.so \
    mod_autoindex.so \
    mod_cgi.so \
    mod_deflate.so \
    mod_dir.so \
    mod_env.so \
    mod_expires.so \
    mod_filter.so \
    mod_headers.so \
    mod_log_config.so \
    mod_mime.so \
    mod_mime_magic.so \
    mod_mpm_prefork.so \
    mod_negotiation.so \
    mod_proxy.so \
    mod_proxy_http.so \
    mod_rewrite.so \
    mod_setenvif.so \
    mod_status.so \
    mod_ssl.so \
    mod_unixd.so \
    mod_version.so

CENTOS_WORKAROUND := 0

VERSIONLT7 := $(shell expr $(DISTRO_VERSION) \<= 7)
ifeq ($(DISTRO_NAME),CENTOS)
  ifeq ($(VERSIONLT7), 1)
    CENTOS_WORKAROUND := 1
  endif
endif
ifeq ($(DISTRO_NAME),REDHAT)
  ifeq ($(VERSIONLT7), 1)
    CENTOS_WORKAROUND := 1
  endif
endif

$(APACHE_OMD_BUILD):
	$(TOUCH) $@

$(APACHE_OMD_INSTALL):
	# Install software below $(DESTDIR)$(OMD_ROOT)/{bin,lib,share}
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/omd
	install -m 644 $(PACKAGE_DIR)/$(APACHE_OMD)/apache.conf $(DESTDIR)$(OMD_ROOT)/share/omd/apache.conf
	# Create distribution independent alias for htpasswd command
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	$(LN) -sf $(HTPASSWD_BIN) $(DESTDIR)$(OMD_ROOT)/bin/htpasswd
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	install -m 775 $(PACKAGE_DIR)/$(APACHE_OMD)/APACHE_TCP_ADDR $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 775 $(PACKAGE_DIR)/$(APACHE_OMD)/APACHE_TCP_PORT $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/

	# This file is loaded by php-wrapper on RedHat/CentOS < 7
	if [ $(CENTOS_WORKAROUND) -eq 1 ]; then \
		$(MKDIR) $(SKEL)/etc/apache/; \
		cp /etc/php.ini $(SKEL)/etc/apache/php.ini; \
		echo -e "\n\n; OMD OMD OMD OMD OMD OMD\n\nmemory_limit=64M\n\n[Session]\nsession.save_path=###ROOT###/tmp/php/session\nupload_tmp_dir=###ROOT###/tmp/php/upload\nsoap.wsdl_cache_dir=###ROOT###/tmp/php/wsdl-cache\n" >> $(SKEL)/etc/apache/php.ini; \
	fi

	# Create working directories
	$(MKDIR) $(SKEL)/var/log/apache
	$(MKDIR) $(SKEL)/var/www
	$(MKDIR) $(SKEL)/tmp/apache/run
	$(MKDIR) $(SKEL)/tmp/php/session
	$(MKDIR) $(SKEL)/tmp/php/upload
	$(MKDIR) $(SKEL)/tmp/php/wsdl-cache

	# Install symlinks to apache modules for this platform
	# Some of the modules are optional on some platforms. Link only
	# the available ones.
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	for MODULE_FILE in $(APACHE_MODULES); do \
	    if [ -e $(APACHE_OMD_MODULE_DIR)/$$MODULE_FILE ]; then \
		$(LN) -sf $(APACHE_OMD_MODULE_DIR)/$$MODULE_FILE \
		    $(DESTDIR)$(OMD_ROOT)/lib/apache/modules/$$MODULE_FILE ; \
	    fi ; \
	done
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
