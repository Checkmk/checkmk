include ../../Makefile.omd

SHELL = /bin/bash
NAME = check_mk
DISTNAME = $(NAME)-$(CMK_VERSION)

.PHONY: skel

build: clean
	if [ ! -f ../../../$(DISTNAME).tar.gz ]; then
	    $(MAKE) -C ../../.. $(DISTNAME).tar.gz
	fi
	tar xzf $(REPO_PATH)/$(DISTNAME).tar.gz
	cd $(DISTNAME) ; \
	  mkdir bin ; \
	  cd bin ; \
	  tar xzf ../bin.tar.gz ; \
	  make
	cd $(DISTNAME) ; \
	  mkdir active_checks ; \
	  cd active_checks ; \
	  tar xzf ../active_checks.tar.gz ; \
	  make

install:
	export bindir='$(OMD_ROOT)/bin' ; \
	export sharedir='$(OMD_ROOT)/share/check_mk' ; \
	export checksdir='$(OMD_ROOT)/share/check_mk/checks' ; \
	export modulesdir='$(OMD_ROOT)/share/check_mk/modules' ; \
	export web_dir='$(OMD_ROOT)/share/check_mk/web' ; \
	export mibsdir='$(OMD_ROOT)/share/snmp/mibs' ; \
	export docdir='$(OMD_ROOT)/share/doc/check_mk' ; \
	export checkmandir='$(OMD_ROOT)/share/check_mk/checkman' ; \
	export agentsdir='$(OMD_ROOT)/share/check_mk/agents' ; \
	export agentslibdir='/usr/lib/check_mk_agent' ; \
	export nagios_binary='$(OMD_ROOT)/bin/nagios' ; \
	export check_icmp_path='$(OMD_ROOT)/lib/nagios/plugins/check_icmp' ; \
	export pnptemplates='$(OMD_ROOT)/share/check_mk/pnp-templates' ; \
	export livebackendsdir='$(OMD_ROOT)/share/check_mk/livestatus' ; \
	export libdir='$(OMD_ROOT)/lib/check_mk' ; \
	export python_lib_dir='$(OMD_ROOT)/lib/python' ; \
	export confdir='$(OMD_ROOT)/skel/etc/check_mk' ; \
	export pnpconfdir='$(OMD_ROOT)/skel/etc/pnp4nagios' ; \
	export pnprraconf='$(OMD_ROOT)/share/check_mk/pnp-rraconf' ; \
	export apache_config_dir='/REMOVE/skel/etc/apache' ; \
	export agentsconfdir='/etc/check_mk' ; \
	export vardir='/REMOVE/var/lib/check_mk' ; \
	export nagios_config_file='/REMOVE/etc/nagios/nagios.cfg' ; \
	export nagconfdir='/REMOVE/etc/nagios/conf.d' ; \
	export htpasswd_file='/REMOVE/etc/nagios/htpasswd' ; \
	export nagios_startscript='/REMOVE/etc/init.d/nagios' ; \
	export nagpipe='/REMOVE/var/run/nagios/rw/nagios.cmd' ; \
	export rrddir='/REMOVE/var/lib/nagios/rrd' ; \
	export nagios_status_file='/REMOVE/var/spool/nagios/status.dat' ; \
	export livesock='/REMOVE/var/run/nagios/rw/live' ; \
	export checkmk_web_uri='/nag01/check_mk' ; \
	export nagiosurl='/nag01/nagios' ; \
	export cgiurl='/nag01/nagios/cgi-bin' ; \
	export pnp_url='/nag01/pnp4nagios/' ; \
	export enable_livestatus='no' ; \
	export nagios_auth_name='Nagios Access' ; \
	export nagiosuser='nagios' ; \
	export wwwgroup='nagios' ; \
	cd $(DISTNAME) ; DESTDIR=$(DESTDIR) ./setup.sh --yes

	# Delete files we do not want to package
	rm -rf $(DESTDIR)/REMOVE
	rm -f $(DESTDIR)$(OMD_ROOT)/skel/etc/check_mk/*-*.mk

	# Binaries
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(DISTNAME)/bin/* $(DESTDIR)$(OMD_ROOT)/bin
	rm -f $(DESTDIR)$(OMD_ROOT)/bin/Makefile $(DESTDIR)$(OMD_ROOT)/bin/*.cc

	# Install the diskspace cleanup plugin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/diskspace
	install -m 644 diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/check_mk

	# Install active checks
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	install -m 755 $(DISTNAME)/active_checks/* \
	    $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	rm $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/Makefile
	rm $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/*.cc
	chmod 755 $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins/*

	# GUI-Test (in doc/helpers)
	#mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	#tar xzf $(DISTNAME)/doc.tar.gz -C $(DESTDIR)$(OMD_ROOT)/bin \
	#    --strip-components 1 helpers/guitest
	#chmod +x $(DESTDIR)$(OMD_ROOT)/bin/*

skel:
	rm -f $(SKEL)/etc/check_mk/main.mk-*
	rm -f $(SKEL)/etc/check_mk/multisite.mk-*

clean:
	rm -rf check_mk-*.*.*[0-9] werks ChangeLog
