include ../../Makefile.omd

NAME     = python-modules
SHELL    = /bin/bash
VERSION  = $(OMD_VERSION)

PATCHES  := $(wildcard patches/*.dif)

MODULES =

# Modules needed because of own packed python (would be available in OS)
MODULES += setuptools-40.6.2.zip  # needed by rrdtool bindings

# Modules really needed on all platforms
MODULES += pysphere-0.1.7.zip
MODULES += pyasn1-0.4.2.tar.gz
MODULES += pyasn1-modules-0.2.2.tar.gz
MODULES += pycryptodomex-3.4.7.tar.gz
MODULES += ordereddict-1.1.tar.gz # needed by pysmi
MODULES += ply-3.11.tar.gz # needed by pysmi
MODULES += pysmi-0.3.0.tar.gz # needed by EC (for trap translation)
MODULES += pysnmp-4.4.4.tar.gz # needed by EC (for trap translation)

MODULES += setuptools-git-1.2.tar.gz # needed for pymssql
MODULES += pymssql-2.1.3.tar.gz # needed for check_sql (together with freetds)

LEGACY_LDAP=0
ifeq ($(DISTRO_CODE),el5)
    LEGACY_LDAP=1
    PATCHES += patches/0019-PyNaCl-fortify-source.patch
endif

ifeq ($(LEGACY_LDAP), 1)
    MODULES += python-ldap-2.3.13.tar.gz
else
    MODULES += python-ldap-2.4.32.tar.gz
    PATCHES += patches/0001-python-ldap-2.4.32-disable-sasl.patch
endif

# Check_MK Edition specific
MODULES += simplejson-3.15.0.tar.gz

ifneq ($(filter $(DISTRO_CODE),sles15 buster),)
    # Partial backport of 716eebb7de600a32300cc391ac9ecb67dd1aabf6 (specific for sles15)
    # Since 1.6 all distros use mysqlclient. Better keep the old module for the other
    # distros to reduce risk of breaking things
    MODULES += mysqlclient-1.3.13.tar.gz # needed by check_sql
else
    MODULES += MySQL-python-1.2.5.zip # needed by check_sql
    PATCHES += patches/0002_MySQL-python-use-distutils.patch
endif
MODULES += psycopg2-2.6.2.tar.gz # needed by check_sql
MODULES += dicttoxml-1.7.4.tar.gz # needed by inventory XML export
MODULES += pycparser-2.18.tar.gz # needed for cffi
MODULES += enum34-1.1.6.tar.gz # needed for cffi
MODULES += cffi-1.11.5.tar.gz # needed by e.g. Pillow
MODULES += Pillow-5.0.0.tar.gz # needed by reportlab (pillow>=2.4.0)
MODULES += pip-10.0.1.tar.gz # needed by reportlab (pip>=1.4.1)
MODULES += reportlab-3.4.0.tar.gz # needed by reporting
MODULES += PyPDF2-1.26.0.tar.gz # needed by reporting

MODULES += npyscreen-4.10.5.tar.gz # needed for mkbench
MODULES += psutil-5.4.3.tar.gz # needed for mkbench

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

MODULES += six-1.11.0.tar.gz
MODULES += ipaddress-1.0.22.tar.gz

MODULES += netifaces-0.10.7.tar.gz # needed for LDAP (nearest DC detection)
MODULES += dnspython-1.15.0.zip # needed for LDAP (nearest DC detection)
MODULES += python-ad-0.9.tar.gz # needed for LDAP (nearest DC detection)

MODULES += idna-2.5.tar.gz
ifneq ($(filter $(DISTRO_CODE),el5 lucid sles11sp1 sles11sp2 sles11sp3 sles11sp4 squeeze),)
    MODULES += cryptography-1.4.tar.gz
    PATCHES += patches/0005-NID_ecdsa_with_SHA-fix.patch
    PATCHES += patches/0009-cryptography-1.4-disable-version-warning.patch
else ifneq ($(filter $(DISTRO_CODE),el6),)
# Cryptography dropped support for OpenSSL 1.0.0 with release 1.7
# (https://github.com/pyca/cryptography/blob/master/CHANGELOG.rst),
# so we stick with 1.5.3.
    MODULES += cryptography-1.5.3.tar.gz
    PATCHES += patches/0004-CMS_DEBUG_DECRYPT-fix.patch
    PATCHES += patches/0009-cryptography-1.5.3-disable-version-warning.patch
else
    MODULES += asn1crypto-0.24.0.tar.gz
    MODULES += cryptography-2.3.1.tar.gz
endif

MODULES += certifi-2018.10.15.tar.gz
MODULES += chardet-3.0.4.tar.gz
MODULES += urllib3-1.21.1.tar.gz
# Added for NetApp special agent, but may be used in other components too in future
MODULES += requests-2.16.0.tar.gz
# Has requests as dependency -> must be built after
MODULES += pyOpenSSL-16.2.0.tar.gz
# Added for check_bi_aggr with kerberos support
MODULES += pykerberos-1.2.1.tar.gz
MODULES += requests-kerberos-0.11.0.tar.gz
# Added for tinkerforge special agent
MODULES += tinkerforge-2.1.15.tar.gz
# Added for check_sftp
MODULES += bcrypt-3.1.4.tar.gz
MODULES += PyNaCl-1.3.0.tar.gz
MODULES += paramiko-2.1.2.tar.gz
# Added for IPMI monitoring of management interface
MODULES += pbr-4.0.0.tar.gz
MODULES += pyghmi-1.2.14.tar.gz

MODULES += typing-3.6.4.tar.gz
MODULES += scandir-1.7.tar.gz
MODULES += pathlib2-2.3.2.tar.gz
# Added for scheduling (cmk/schedule.py)
MODULES += python-dateutil-2.6.1.tar.gz

# Added with 1.5.0p12 for supporting the new special agents
# Added for azure special agent
MODULES += PyJWT-1.6.4.tar.gz
MODULES += SecretStorage-2.3.1.tar.gz
MODULES += adal-1.2.0.tar.gz
MODULES += azure-nspkg-3.0.2.zip
MODULES += azure-common-1.1.16.zip
MODULES += azure-mgmt-nspkg-3.0.2.zip
MODULES += isodate-0.6.0.tar.gz
MODULES += oauthlib-2.1.0.tar.gz
MODULES += requests-oauthlib-1.0.0.tar.gz
MODULES += msrest-0.6.1.tar.gz
# use azure-mgmt-monitor 0.4.0 and its dependency
# msrestazure 0.4.34 since the monitor version 0.5.0
# will not deliver all metrics.
MODULES += msrestazure-0.4.34.tar.gz
MODULES += azure-mgmt-monitor-0.4.0.zip
MODULES += azure-mgmt-resource-2.0.0.zip
MODULES += azure-mgmt-compute-4.3.1.zip
MODULES += configparser-3.5.0.tar.gz
MODULES += entrypoints-0.2.3.tar.gz
# setuptools_scm>=1.15.0 is required by keyring but not declared correctly
MODULES += setuptools_scm-3.2.0.tar.gz
MODULES += keyring-15.1.0.tar.gz
# Added for AWS special agent
MODULES += docutils-0.14.tar.gz
MODULES += futures-3.2.0.tar.gz
MODULES += jmespath-0.9.3.tar.gz
MODULES += botocore-1.12.43.tar.gz
MODULES += s3transfer-0.1.13.tar.gz
MODULES += boto3-1.9.42.tar.gz
# Added for kubernetes monitoring
MODULES += cachetools-3.0.0.tar.gz
MODULES += rsa-4.0.tar.gz
MODULES += google-auth-1.6.1.tar.gz
MODULES += PyYAML-3.13.tar.gz
MODULES += websocket_client-0.54.0.tar.gz
MODULES += kubernetes-8.0.0.tar.gz


.PHONY: build check-freetds install skel clean dump-Pipfile

build: check-python check-freetds unpack
	set -e ; cd dest && \
	    mkdir -p $(PACKAGE_PYTHON_MODULES_PYTHONPATH) || true; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_MODULES_PYTHONPATH)" ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	    export CPATH="$(PACKAGE_FREETDS_DESTDIR)/include" ; \
	    export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS) $(PACKAGE_FREETDS_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	    for M in $(MODULES); do \
		echo "Building $$M..." ; \
		PKG=$${M//.tar.gz/} ; \
		PKG=$${PKG//.zip/} ; \
		if [ $$PKG = pysnmp-git ]; then \
		    PKG=pysnmp-master ; \
		fi ; \
		cd $$PKG ; \
	        $(PACKAGE_PYTHON_EXECUTABLE) setup.py build ; \
	        $(PACKAGE_PYTHON_EXECUTABLE) setup.py install \
		    --root=$(PACKAGE_PYTHON_MODULES_DESTDIR) \
	            --prefix='' \
	            --install-platlib=/lib \
	            --install-purelib=/lib ; \
	        cd .. ; \
	    done

unpack:
	mkdir -p dest
	cd dest && \
	    for M in $(MODULES); do \
		echo "Unpacking $$M..." ; \
		if echo $$M | grep .tar.gz; then \
		    tar xvzf ../src/$$M ; \
		else \
		    unzip -o ../src/$$M ; \
		fi \
	    done
	set -e ; for p in $$(echo $(PATCHES) | tr " " "\n" | sort); do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d dest < $$p ; \
	done

# NOTE: Setting SODIUM_INSTALL variable below is an extremely cruel hack to
# avoid installing libsodium headers and libraries. The need for this hack
# arises because of our "interesting" flag use for "setup.py install" and our
# double installation. We should really switch to e.g. pipenv here.
install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/python
	set -e ; cd dest && \
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

skel:

clean:
	rm -rf dest $(PACKAGE_PYTHON_MODULES_DESTDIR)

dump-Pipfile:
	@echo '# ATTENTION: Most of this file is generated by omd/packages/python-modules/Makefile'
	@echo '[[source]]'
	@echo 'url = "https://pypi.python.org/simple"'
	@echo 'verify_ssl = true'
	@echo 'name = "pypi"'
	@echo ''
	@echo '[dev-packages]'
	@echo 'pytest = "*"'
	@echo 'pytest-cov = "*"'
	@echo 'pytest-mock = "*"'
	@echo '"beautifulsoup4" = "*"'
	@echo 'pytest-stepwise = "*"'
	@echo 'dill = "*"'
	@echo '"html5lib" = "*"'
	@echo 'bandit = "*"'
	@echo 'lockfile = "*"'
	@echo 'lxml = "*"'
	@echo 'pylint = "*"'
	@echo 'pyenchant = "*"'
	@echo 'yapf = "*"'
	@echo 'docker = "*"'
	@echo ''
	@echo '[packages]'
	@echo $(patsubst %.zip,%,$(patsubst %.tar.gz,%,$(MODULES))) | tr ' ' '\n' | sed 's/-\([0-9.]*\)$$/ = "==\1"/'
	@echo 'python-snap7 = "==0.5"  # actually some unknown version between 0.4 and 0.5... >:-('
	@echo ''
	@echo '[requires]'
	@echo 'python_version = "2.7"'
