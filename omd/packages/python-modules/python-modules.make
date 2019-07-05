PYTHON_MODULES := python-modules
PYTHON_MODULES_VERS := $(OMD_VERSION)
PYTHON_MODULES_DIR := $(PYTHON_MODULES)-$(PYTHON_MODULES_VERS)

PYTHON_MODULES_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON_MODULES_DIR)-build
PYTHON_MODULES_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON_MODULES_DIR)-install
PYTHON_MODULES_UNPACK:= $(BUILD_HELPER_DIR)/$(PYTHON_MODULES_DIR)-unpack
# The custom patching rule for python-modules needs to be called
PYTHON_MODULES_PATCHING := $(BUILD_HELPER_DIR)/$(PYTHON_MODULES_DIR)-patching-c

.PHONY: $(PYTHON_MODULES) $(PYTHON_MODULES)-install $(PYTHON_MODULES)-clean

$(PYTHON_MODULES): $(PYTHON_MODULES_BUILD)

$(PYTHON_MODULES)-install: $(PYTHON_MODULES_INSTALL)

$(PYTHON_MODULES)-patching: $(PYTHON_MODULES_PATCHING)

PYTHON_MODULES_PATCHES  := $(wildcard $(PACKAGE_DIR)/$(PYTHON_MODULES)/patches/*.dif)

PYTHON_MODULES_LIST :=

# Modules needed because of own packed python (would be available in OS)
PYTHON_MODULES_LIST += setuptools-40.6.2.zip  # needed by rrdtool bindings
PYTHON_MODULES_LIST += setuptools_scm-3.1.0.tar.gz

# Modules really needed on all platforms
PYTHON_MODULES_LIST += pysphere-0.1.7.zip
PYTHON_MODULES_LIST += pyasn1-0.4.4.tar.gz
PYTHON_MODULES_LIST += pyasn1-modules-0.2.2.tar.gz
PYTHON_MODULES_LIST += pycryptodomex-3.6.6.tar.gz
PYTHON_MODULES_LIST += ordereddict-1.1.tar.gz # needed by pysmi
PYTHON_MODULES_LIST += ply-3.11.tar.gz # needed by pysmi
PYTHON_MODULES_LIST += pysmi-0.3.2.tar.gz # needed by EC (for trap translation)
PYTHON_MODULES_LIST += pysnmp-4.4.4.tar.gz # needed by EC (for trap translation)
PYTHON_MODULES_LIST += snmpsim-0.4.6.tar.gz # needed by SNMP integration tests
PYTHON_MODULES_LIST += setuptools-git-1.2.tar.gz # needed for pymssql on some older platforms
PYTHON_MODULES_LIST += pymssql-2.1.3.tar.gz # needed for check_sql (together with freetds)

LEGACY_LDAP=0
ifeq ($(DISTRO_CODE),el5)
    LEGACY_LDAP=1
    PYTHON_MODULES_PATCHES += $(PACKAGE_DIR)/$(PYTHON_MODULES)/patches/0018-mysqlclient-fortify-source.patch
    PYTHON_MODULES_PATCHES += $(PACKAGE_DIR)/$(PYTHON_MODULES)/patches/0019-PyNaCl-fortify-source.patch
endif

ifeq ($(LEGACY_LDAP), 1)
    PYTHON_MODULES_LIST += python-ldap-2.3.13.tar.gz
else
    PYTHON_MODULES_LIST += python-ldap-3.1.0.tar.gz
    PYTHON_MODULES_PATCHES += $(PACKAGE_DIR)/$(PYTHON_MODULES)/patches/0001-python-ldap-3.1.0-disable-sasl.patch
endif

# Check_MK Edition specific
PYTHON_MODULES_LIST += simplejson-3.16.0.tar.gz
PYTHON_MODULES_LIST += mysqlclient-1.3.13.tar.gz  # needed by check_sql
PYTHON_MODULES_LIST += psycopg2-2.6.2.tar.gz # needed by check_sql
PYTHON_MODULES_LIST += dicttoxml-1.7.4.tar.gz # needed by inventory XML export
PYTHON_MODULES_LIST += pycparser-2.19.tar.gz # needed for cffi and azure
PYTHON_MODULES_LIST += enum34-1.1.6.tar.gz # needed for cffi
PYTHON_MODULES_LIST += cffi-1.11.5.tar.gz # needed by e.g. Pillow
PYTHON_MODULES_LIST += Pillow-5.3.0.tar.gz # needed by reportlab (pillow>=2.4.0)
PYTHON_MODULES_LIST += pip-18.1.tar.gz # needed by reportlab (pip>=1.4.1)
PYTHON_MODULES_LIST += reportlab-3.5.9.tar.gz # needed by reporting
PYTHON_MODULES_LIST += PyPDF2-1.26.0.tar.gz # needed by reporting

PYTHON_MODULES_LIST += npyscreen-4.10.5.tar.gz # needed for mkbench
PYTHON_MODULES_LIST += psutil-5.4.7.tar.gz # needed for mkbench

# OpenSSL versions shipped:
#    0x0090802f (OpenSSL 0.9.8e-rhel5 01 Jul 2008): centos55
#    0x0090808f (OpenSSL 0.9.8h 28 May 2008): sles11sp1
#    0x009080af (OpenSSL 0.9.8j 07 Jan 2009): sles11sp2 sles11sp3 sles11sp4
#    0x009080bf (OpenSSL 0.9.8k 25 Mar 2009): lucid
#    0x009080ff (OpenSSL 0.9.8o 01 Jun 2010): squeeze
#    0x10000003 (OpenSSL 1.0.0 29 Mar 2010): el6
#    0x1000100f (OpenSSL 1.0.1 14 Mar 2012): precise
#    0x1000105f (OpenSSL 1.0.1e 11 Feb 2013): el7 cma wheezy
#    0x1000106f (OpenSSL 1.0.1f 6 Jan 2014): trusty utopic vivid
#    0x1000109f (OpenSSL 1.0.1i 6 Aug 2014): sles12 sles12sp1
#    0x1000114f (OpenSSL 1.0.1t  3 May 2016): jessie
#    0x1000204f (OpenSSL 1.0.2d 9 Jul 2015): wily
#    0x1000207f (OpenSSL 1.0.2g  1 Mar 2016): artful xenial yakkety zesty
#    0x100020af (OpenSSL 1.0.2j-fips  26 Sep 2016): sles12sp2-64
#    0x100020af (OpenSSL 1.0.2j-fips  26 Sep 2016): sles12sp3-64
#    0x100020cf (OpenSSL 1.0.2l  25 May 2017): cma-stretch-64
#    0x100020cf (OpenSSL 1.0.2l  25 May 2017): stretch-64
#    0x1010007f (OpenSSL 1.1.0g  2 Nov 2017): bionic-64
#    0x1010008f (OpenSSL 1.1.0h-fips  27 Mar 2018): sles15-64
#    0x1010100f (OpenSSL 1.1.1  11 Sep 2018): cosmic-64
#
# Starting with version 1.5, cryptography has dropped support for OpenSSL 0.9.8,
# see https://cryptography.io/en/latest/faq/#installing-cryptography-with-openssl-0-9-8-fails.
#
# More fun facts about the mad OpenSSL versionitis: Contrary to the release
# strategy on https://www.openssl.org/policies/releasestrat.html, letter
# releases *do* contain new features, which is totally confusing and leads the
# version numbering scheme ad absurdum. In our case, the problematic thing is
# CMS_DEBUG_DECRYPT. The 0.9.8 series has it starting with 0.9.8u, the 1.0.0
# series has it starting with 1.0.0h, and both the 1.0.1 and 1.0.2 series always
# have it. Alas, the cryptography Python module is unaware of the fact that not
# all 1.0.0 versions have it, so we have to use a patch. A similar madness
# happens with NID_ecdsa_with_SHA{224,256,384,512}, which magically appear in
# 0.9.8i. Again, cryptography has a bug here and assumes it from 0.9.8g onwards,
# so we need to patch one more time.

PYTHON_MODULES_LIST += six-1.11.0.tar.gz
PYTHON_MODULES_LIST += ipaddress-1.0.22.tar.gz

PYTHON_MODULES_LIST += netifaces-0.10.7.tar.gz # needed for LDAP (nearest DC detection)
PYTHON_MODULES_LIST += dnspython-1.15.0.zip # needed for LDAP (nearest DC detection)
PYTHON_MODULES_LIST += python-ad-0.9.tar.gz # needed for LDAP (nearest DC detection)

PYTHON_MODULES_LIST += idna-2.7.tar.gz
# Added for NetApp special agent, but may be used in other components too in future
PYTHON_MODULES_LIST += requests-2.20.1.tar.gz
# Added for IPMI monitoring of management interface
PYTHON_MODULES_LIST += pbr-5.1.0.tar.gz

ifneq ($(filter $(DISTRO_CODE),el5 lucid sles11sp1 sles11sp2 sles11sp3 sles11sp4 squeeze),)
    PYTHON_MODULES_LIST += cryptography-1.4.tar.gz
    # Has requests as dependency -> must be built after
    PYTHON_MODULES_LIST += pyOpenSSL-16.2.0.tar.gz
    PYTHON_MODULES_LIST += paramiko-2.1.2.tar.gz
    PYTHON_MODULES_LIST += pyghmi-1.1.0.tar.gz
    PYTHON_MODULES_PATCHES += $(PACKAGE_DIR)/$(PYTHON_MODULES)/patches/0005-NID_ecdsa_with_SHA-fix.patch
    PYTHON_MODULES_PATCHES += $(PACKAGE_DIR)/$(PYTHON_MODULES)/patches/0009-cryptography-1.4-disable-version-warning.patch
else
    PYTHON_MODULES_LIST  += asn1crypto-0.24.0.tar.gz
    PYTHON_MODULES_LIST  += cryptography-2.4.1.tar.gz
    # Has requests as dependency -> must be built after
    PYTHON_MODULES_LIST += pyOpenSSL-18.0.0.tar.gz
    PYTHON_MODULES_LIST += paramiko-2.4.2.tar.gz
    PYTHON_MODULES_LIST += pyghmi-1.2.14.tar.gz
    PYTHON_MODULES_PATCHES += $(PACKAGE_DIR)/$(PYTHON_MODULES)/patches/0009-cryptography-2.4.1-disable-version-warning.patch
endif

PYTHON_MODULES_LIST += certifi-2018.10.15.tar.gz
PYTHON_MODULES_LIST += chardet-3.0.4.tar.gz
PYTHON_MODULES_LIST += urllib3-1.24.1.tar.gz
# Added for check_bi_aggr with kerberos support
PYTHON_MODULES_LIST += pykerberos-1.2.1.tar.gz
PYTHON_MODULES_LIST += requests-kerberos-0.12.0.tar.gz
# Added for tinkerforge special agent
PYTHON_MODULES_LIST += tinkerforge-2.1.19.tar.gz
# Added for check_sftp
PYTHON_MODULES_LIST += bcrypt-3.1.4.tar.gz
PYTHON_MODULES_LIST += PyNaCl-1.3.0.tar.gz

PYTHON_MODULES_LIST += typing-3.6.6.tar.gz
PYTHON_MODULES_LIST += scandir-1.9.0.tar.gz
PYTHON_MODULES_LIST += pathlib2-2.3.2.tar.gz
# Added for scheduling (cmk/schedule.py)
PYTHON_MODULES_LIST += python-dateutil-2.7.5.tar.gz
PYTHON_MODULES_LIST += python-snap7-0.10.tar.gz
# Added for azure special agent
PYTHON_MODULES_LIST += PyJWT-1.6.4.tar.gz
PYTHON_MODULES_LIST += adal-1.2.0.tar.gz
PYTHON_MODULES_LIST += oauthlib-2.1.0.tar.gz
PYTHON_MODULES_LIST += requests-oauthlib-1.0.0.tar.gz
PYTHON_MODULES_LIST += configparser-3.5.1.tar.gz
# Added for the GUI
PYTHON_MODULES_LIST += Werkzeug-0.14.1.tar.gz
PYTHON_MODULES_LIST += passlib-1.7.1.tar.gz
# Added for AWS special agent
PYTHON_MODULES_LIST += docutils-0.14.tar.gz
PYTHON_MODULES_LIST += futures-3.2.0.tar.gz
PYTHON_MODULES_LIST += jmespath-0.9.3.tar.gz
PYTHON_MODULES_LIST += botocore-1.12.43.tar.gz
PYTHON_MODULES_LIST += s3transfer-0.1.13.tar.gz
PYTHON_MODULES_LIST += boto3-1.9.42.tar.gz
# Added for kubernetes monitoring
PYTHON_MODULES_LIST += cachetools-3.0.0.tar.gz
PYTHON_MODULES_LIST += rsa-4.0.tar.gz
PYTHON_MODULES_LIST += google-auth-1.6.1.tar.gz
PYTHON_MODULES_LIST += PyYAML-5.1.tar.gz
PYTHON_MODULES_LIST += websocket_client-0.54.0.tar.gz
PYTHON_MODULES_LIST += kubernetes-8.0.0.tar.gz
# Added for jira notification script
PYTHON_MODULES_LIST += defusedxml-0.5.0.tar.gz
PYTHON_MODULES_LIST += requests-toolbelt-0.9.1.tar.gz
PYTHON_MODULES_LIST += jira-2.0.0.tar.gz
# Has been added for opsgenie notification plugin
PYTHON_MODULES_LIST += opsgenie-sdk-0.3.1.tar.gz
PYTHON_MODULES_LIST += pytz-2019.1.tar.gz
# Added for easier debugging of check plugins in OMD scope
PYTHON_MODULES_LIST += fancycompleter-0.8.tar.gz # needed for pdbpp
PYTHON_MODULES_LIST += wmctrl-0.3.tar.gz # needed for pdbpp
PYTHON_MODULES_LIST += pdbpp-0.10.0.tar.gz
PYTHON_MODULES_LIST += PySnooper-0.0.31.tar.gz
# Added to support Python 3 transition
PYTHON_MODULES_LIST += future-0.17.1.tar.gz


# NOTE: Cruel hack below! We need to have a recent GCC visible in the PATH
# because the SSSE3 detection in pycryptodomex is slightly broken. :-/
$(PYTHON_MODULES_BUILD): $(PYTHON_BUILD) $(FREETDS_BUILD) $(PYTHON_MODULES_PATCHING)
	set -e ; cd $(PYTHON_MODULES_DIR) ; \
	    $(MKDIR) $(PACKAGE_PYTHON_MODULES_PYTHONPATH) ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH)" ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	    export CPATH="$(PACKAGE_FREETDS_DESTDIR)/include" ; \
	    export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS) $(PACKAGE_FREETDS_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	    PATH="$(abspath ./bin):$$PATH" ; \
	    for M in $(PYTHON_MODULES_LIST); do \
		echo "Building $$M..." ; \
		PKG=$${M//.tar.gz/} ; \
		PKG=$${PKG//.zip/} ; \
		if [ $$PKG = pysnmp-git ]; then \
		    PKG=pysnmp-master ; \
		fi ; \
	    	echo $$PWD ;\
		cd $$PKG ; \
		$(PACKAGE_PYTHON_EXECUTABLE) setup.py build ; \
		$(PACKAGE_PYTHON_EXECUTABLE) setup.py install \
		    --root=$(PACKAGE_PYTHON_MODULES_DESTDIR) \
		    --prefix='' \
		    --install-data=/share \
		    --install-platlib=/lib \
		    --install-purelib=/lib ; \
		cd .. ; \
	    done
	$(TOUCH) $@

$(PYTHON_MODULES_PATCHING): $(PYTHON_MODULES_UNPACK)
	echo $(PYTHON_MODULES_PATCHES)
	set -e ; for p in $$(echo $(PYTHON_MODULES_PATCHES) | tr " " "\n" | sort); do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(PYTHON_MODULES_DIR) < $$p ; \
	done
	$(TOUCH) $@

$(PYTHON_MODULES_UNPACK): $(addprefix $(PACKAGE_DIR)/$(PYTHON_MODULES)/src/,$(PYTHON_MODULES_LIST)) $(PYTHON_MODULES_PATCHES) $(PACKAGE_DIR)/$(PYTHON_MODULES)/patches
	$(RM) -r $(PYTHON_MODULES_DIR)
	$(MKDIR) $(PYTHON_MODULES_DIR)
	cd $(PYTHON_MODULES_DIR) && \
	    for M in $(PYTHON_MODULES_LIST); do \
		echo "Unpacking $$M..." ; \
		if echo $$M | grep .tar.gz; then \
		    $(TAR_GZ) $(PACKAGE_DIR)/$(PYTHON_MODULES)/src/$$M ; \
		else \
		    $(UNZIP) $(PACKAGE_DIR)/$(PYTHON_MODULES)/src/$$M ; \
		fi \
	    done
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

# NOTE: Setting SODIUM_INSTALL variable below is an extremely cruel hack to
# avoid installing libsodium headers and libraries. The need for this hack
# arises because of our "interesting" flag use for "setup.py install" and our
# double installation. We should really switch to e.g. pipenv here.
$(PYTHON_MODULES_INSTALL): $(PYTHON_MODULES_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/python
	set -e ; cd $(PYTHON_MODULES_DIR) ; \
	    export SODIUM_INSTALL="system" ; \
	    export PYTHONPATH=$$PYTHONPATH:"$(PACKAGE_PYTHON_MODULES_PYTHONPATH)" ; \
	    export PYTHONPATH=$$PYTHONPATH:"$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	    export CPATH="$(PACKAGE_FREETDS_DESTDIR)/include" ; \
	    export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS) $(PACKAGE_FREETDS_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	    for M in $$(ls); do \
		echo "Installing $$M..." ; \
		cd $$M ; \
		$(PACKAGE_PYTHON_EXECUTABLE) setup.py install \
		    --root=$(DESTDIR)$(OMD_ROOT) \
		    --prefix='' \
		    --install-data=/share \
		    --install-platlib=/lib/python \
		    --install-purelib=/lib/python ; \
		cd .. ; \
	    done
# Cleanup some unwanted files (example scripts)
	rm -f $(DESTDIR)$(OMD_ROOT)/bin/*.py || true
# Fix python interpreter for kept scripts
	for F in $(DESTDIR)$(OMD_ROOT)/bin/easy_install \
		 $(DESTDIR)$(OMD_ROOT)/bin/easy_install-2.7 \
		 $(DESTDIR)$(OMD_ROOT)/bin/libsmi2pysnmp \
		 $(DESTDIR)$(OMD_ROOT)/bin/pip \
		; do \
	    if [ -f $$F ]; then \
		sed -i "1s|^#!.*python|#!/usr/bin/env python|" $$F; \
	    fi ; \
	done
	$(TOUCH) $@

$(PYTHON_MODULES)-skel:

python-modules-dump-Pipfile:
	@echo '# ATTENTION: Most of this file is generated by omd/packages/python-modules/Makefile'
	@echo '[[source]]'
	@echo 'url = "https://pypi.python.org/simple"'
	@echo 'verify_ssl = true'
	@echo 'name = "pypi"'
	@echo ''
	@echo '[dev-packages]'
	@echo 'astroid = "*"  # used by testlib.pylint_checker_localization'
	@echo 'bandit = "*"  # used by test/Makefile'"'"'s test-bandit target'
	@echo '"beautifulsoup4" = "*"  # used by the GUI crawler and various tests'
	@echo 'bson = "*"  # used by test_mk_mongodb unit test'
	@echo 'compiledb = "*"  # used by the Livestatus/CMC Makefiles for building compile_command.json'
	@echo 'docker = "*"  # used by test_docker test and mk_docker agent plugin'
	@echo 'freezegun = "*"  # used by various unit tests'
	@echo 'isort = "*"  # used as a plugin for editors'
	@echo 'lxml = "*"  # used via beautifulsoup4 as a parser and in the agent_netapp special agent'
	@echo 'mock = "*"  # used in checktestlib in unit tests'
	@echo 'mockldap = "*"  # used in test_userdb_ldap_connector unit test'
	@echo 'pylint = "*"  # used by test/Makefile'"'"'s test-pylint target'
	@echo 'pymongo = "*"  # used by mk_mongodb agent plugin'
	@echo 'pytest = "*"  # used by various test/Makefile targets'
	@echo 'pytest-cov = "*"'
	@echo 'pytest-mock = "*"'
	@echo 'yapf = "==0.26.0"  # used by test/Makefile'"'"'s test-bandit target. Keep 0.26.0 for the moment to avoid reformatting.'
	@echo ''
	@echo '[packages]'
	@echo $(patsubst %.zip,%,$(patsubst %.tar.gz,%,$(PYTHON_MODULES_LIST))) | tr ' ' '\n' | sed 's/-\([0-9.]*\)$$/ = "==\1"/'
	@echo ''
	@echo '[requires]'
	@echo 'python_version = "2.7"'

$(PYTHON_MODULES)-clean:
	rm -rf $(PYTHON_MODULES_DIR) $(BUILD_HELPER_DIR)/$(PYTHON_MODULES)*
