APACHE := apache-omd
APACHE_VERS := 1.0
APACHE_DIR := $(APACHE)-$(APACHE_VERS)

MODULE_DIR=$(APACHE_MODULE_DIR)
ifeq ($(shell uname -m),x86_64)
  MODULE_DIR=$(APACHE_MODULE_DIR_64)
endif

ifeq ($(APACHE_VERSION),)
APACHE_VERSION      = $(shell $(APACHE_BIN) -v | awk '/version/ {print $$3}' | awk -F/ '{print $$2}')
endif
APACHE_VERSION_MAIN = $(word 1, $(subst ., ,$(APACHE_VERSION)))
APACHE_VERSION_SUB  = $(word 2, $(subst ., ,$(APACHE_VERSION)))
APACHE_24_OR_NEWER  = $(shell [ $(APACHE_VERSION_MAIN) -ge 2 -a $(APACHE_VERSION_SUB) -ge 4 ] && echo 1 || echo 0)


ifeq ($(APACHE_24_OR_NEWER), 1)
    APACHE_MODULES := mod_mpm_prefork.so \
		     mod_access_compat.so \
		     mod_authn_core.so \
		     mod_authz_core.so \
		     mod_filter.so \
		     mod_unixd.so
else
    APACHE_MODULES := mod_authn_default.so \
		     mod_authz_default.so
endif

APACHE_MODULES += \
		     mod_log_config.so \
		     mod_auth_basic.so \
		     mod_authn_file.so \
		     mod_authz_host.so \
		     mod_authz_user.so \
		     mod_autoindex.so \
		     mod_env.so \
		     mod_expires.so \
		     mod_deflate.so \
		     mod_headers.so \
		     mod_setenvif.so \
		     mod_mime_magic.so \
		     mod_mime.so \
		     mod_negotiation.so \
		     mod_dir.so \
		     mod_alias.so \
		     mod_rewrite.so \
		     mod_cgi.so \
		     mod_status.so \
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

APACHE_OMD_INSTALL := $(BUILD_HELPER_DIR)/$(APACHE_DIR)-install
APACHE_OMD_SKEL := $(BUILD_HELPER_DIR)/$(APACHE_DIR)-skel


.PHONY: $(APACHE) $(APACHE)-install $(APACHE)-skel $(APACHE)-clean

$(APACHE):

$(APACHE)-install: $(APACHE_OMD_INSTALL)

$(APACHE)-skel: $(APACHE_OMD_SKEL)

$(APACHE_OMD_INSTALL):
	# Install software below $(DESTDIR)$(OMD_ROOT)/{bin,lib,share}
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/omd
	install -m 644 $(PACKAGE_DIR)/$(APACHE)/apache.conf $(DESTDIR)$(OMD_ROOT)/share/omd/apache.conf
	# Create distribution independent alias for htpasswd command
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	$(LN) -sf $(HTPASSWD_BIN) $(DESTDIR)$(OMD_ROOT)/bin/htpasswd
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	install -m 775 $(PACKAGE_DIR)/$(APACHE)/APACHE_TCP_ADDR $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 775 $(PACKAGE_DIR)/$(APACHE)/APACHE_TCP_PORT $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(TOUCH) $@

$(APACHE_OMD_SKEL): $(APACHE_OMD_INSTALL)
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
	    if [ -e $(MODULE_DIR)/$$MODULE_FILE ]; then \
		$(LN) -sf $(MODULE_DIR)/$$MODULE_FILE \
		    $(DESTDIR)$(OMD_ROOT)/lib/apache/modules/$$MODULE_FILE ; \
	    fi ; \
	done
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
