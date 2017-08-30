include ../../Makefile.omd

NAME     = python-modules
SHELL    = /bin/bash
VERSION  = $(OMD_VERSION)
DISTRO   = $(shell ../../distro)
TMP_INSTALL_PATH = $(shell pwd)/tmp.python

PATCHES  := $(wildcard patches/*.dif)

MODULES =
# Modules really needed on all platforms
MODULES += pysphere-0.1.7.zip
MODULES += pyasn1-0.2.3.tar.gz
MODULES += pycryptodome-3.4.5.tar.gz
MODULES += ordereddict-1.1.tar.gz # needed by pysmi
MODULES += ply-3.10.tar.gz # needed by pysmi
MODULES += pysmi-0.1.0.tar.gz # needed by EC (for trap translation)
MODULES += pysnmp-4.3.5.tar.gz # needed by EC (for trap translation)

MODULES += setuptools-git-1.1.tar.gz # needed for pymssql
MODULES += pymssql-2.1.3.tar.gz # needed for check_sql (together with freetds)

# Modules needed because of own packed python (would be available in OS)
MODULES += setuptools-28.8.0.tar.gz  # needed by rrdtool bindings

LEGACY_LDAP=0
ifeq ($(DISTRO_CODE),el5)
    LEGACY_LDAP=1
endif

ifeq ($(LEGACY_LDAP), 1)
    MODULES += python-ldap-2.3.13.tar.gz
else
    MODULES += python-ldap-2.4.32.tar.gz
    PATCHES += patches/0001-python-ldap-2.4.32-disable-sasl.patch
endif

# Check_MK Edition specific
MODULES += simplejson-3.10.0.tar.gz
MODULES += MySQL-python-1.2.5.zip # needed by check_sql
MODULES += psycopg2-2.6.2.tar.gz # needed by check_sql
MODULES += dicttoxml-1.7.4.tar.gz # needed by inventory XML export
MODULES += pycparser-2.17.tar.gz # needed for cffi
MODULES += enum34-1.1.6.tar.gz # needed for cffi
MODULES += cffi-1.10.0.tar.gz # needed by e.g. Pillow
MODULES += Pillow-3.4.2.tar.gz # needed by reportlab (pillow>=2.4.0)
MODULES += pip-9.0.1.tar.gz # needed by reportlab (pip>=1.4.1)
MODULES += reportlab-3.3.0.tar.gz # needed by reporting
MODULES += PyPDF2-1.26.0.tar.gz # needed by reporting

MODULES += npyscreen-4.10.5.tar.gz # needed for mkbench
MODULES += psutil-5.2.0.tar.gz # needed for mkbench

# OpenSSL versions shipped:
#    0x0090802f (OpenSSL 0.9.8e-rhel5 01 Jul 2008): centos55
#    0x0090808f (OpenSSL 0.9.8h 28 May 2008): sles11sp1
#    0x009080af (OpenSSL 0.9.8j 07 Jan 2009): sles11sp2 sles11sp3 sles11sp4
#    0x009080bf (OpenSSL 0.9.8k 25 Mar 2009): lucid
#    0x009080ff (OpenSSL 0.9.8o 01 Jun 2010): squeeze
#    0x10000003 (OpenSSL 1.0.0 29 Mar 2010): centos60
#    0x1000100f (OpenSSL 1.0.1 14 Mar 2012): precise
#    0x1000105f (OpenSSL 1.0.1e 11 Feb 2013): centos70 cma wheezy
#    0x1000106f (OpenSSL 1.0.1f 6 Jan 2014): trusty utopic vivid
#    0x1000109f (OpenSSL 1.0.1i 6 Aug 2014): sles12 sles12sp1
#    0x1000114f (OpenSSL 1.0.1t  3 May 2016): jessie
#    0x1000204f (OpenSSL 1.0.2d 9 Jul 2015): wily
#    0x1000207f (OpenSSL 1.0.2g  1 Mar 2016): xenial
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

MODULES += six-1.10.0.tar.gz
MODULES += ipaddress-1.0.18.tar.gz

MODULES += netifaces-0.10.6.tar.gz # needed for LDAP (nearest DC detection)
MODULES += dnspython-1.15.0.zip # needed for LDAP (nearest DC detection)
MODULES += python-ad-0.9.tar.gz # needed for LDAP (nearest DC detection)

MODULES += idna-2.5.tar.gz
ifneq ($(filter $(DISTRO_CODE),el5 lucid sles11sp1 sles11sp2 sles11sp3 sles11sp4 squeeze),)
    MODULES += cryptography-1.4.tar.gz
    PATCHES += patches/0005-NID_ecdsa_with_SHA-fix.patch
    PATCHES += patches/0009-cryptography-1.4-disable-version-warning.patch
else
    MODULES += cryptography-1.5.3.tar.gz
    PATCHES += patches/0004-CMS_DEBUG_DECRYPT-fix.patch
    PATCHES += patches/0009-cryptography-1.5.3-disable-version-warning.patch
endif

# Added for NetApp special agent, but may be used in other components too in future
MODULES+=requests-2.13.0.tar.gz
# Has requests as dependency -> must be built after
MODULES += pyOpenSSL-16.2.0.tar.gz
# Added for check_bi_aggr with kerberos support
MODULES+=pykerberos-1.1.14.tar.gz
MODULES+=requests-kerberos-0.11.0.tar.gz
# Added for tinkerforge special agent
MODULES+=tinkerforge-2.1.11.tar.gz
# Added for check_sftp
MODULES+=paramiko-2.1.2.tar.gz


.PHONY: build check-freetds install skel clean

build: check-python check-freetds unpack
	set -e ; cd dest && \
	    mkdir -p $(TMP_INSTALL_PATH)/lib || true; \
	    export PYTHONPATH=$$PYTHONPATH:$(TMP_INSTALL_PATH)/lib ; \
	    export PYTHONPATH=$$PYTHONPATH:$(DESTDIR)$(OMD_ROOT)/lib/python ; \
	    export PYTHONPATH=$$PYTHONPATH:$(PYTHON_LIB) ; \
	    export PYTHONPATH=$$PYTHONPATH:$(shell pwd)/dest/setuptools-28.8.0 ; \
	    export CPATH="$(shell pwd)/../freetds/freetds-0.95.95/include" ; \
	    export LDFLAGS="-L$(shell pwd)/../python/tmp.python27/lib -L$(PYTHON_LIB)/config -L$(shell pwd)/../freetds/freetds-0.95.95/src/dblib/.libs" ; \
	    for M in $(MODULES); do \
		echo "Building $$M..." ; \
		PKG=$${M//.tar.gz/} ; \
		PKG=$${PKG//.zip/} ; \
		if [ $$PKG = pysnmp-git ]; then \
		    PKG=pysnmp-master ; \
		fi ; \
		cd $$PKG ; \
	        $(PYTHON) setup.py build ; \
	        $(PYTHON) setup.py install \
		    --root=$(TMP_INSTALL_PATH) \
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
	set -e ; for p in $(PATCHES) ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d dest < $$p ; \
	done


check-freetds:
	@if [ ! -d ../freetds/freetds-0.95.95 ]; then \
	    echo "ERROR: You need to build the \"freetds\" package first" ; \
	    exit 1 ; \
	fi

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/python
	set -e ; cd dest && \
	    export PYTHONPATH=$$PYTHONPATH:$(TMP_INSTALL_PATH)/lib ; \
	    export PYTHONPATH=$$PYTHONPATH:$(DESTDIR)$(OMD_ROOT)/lib/python ; \
	    export PYTHONPATH=$$PYTHONPATH:$(PYTHON_LIB) ; \
	    for M in $$(ls); do \
		echo "Installing $$M..." ; \
		cd $$M ; \
	        $(PYTHON) setup.py install \
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
	rm -rf dest tmp.python
