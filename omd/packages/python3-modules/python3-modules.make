PYTHON3_MODULES := python3-modules
# Use some pseudo version here. Don't use OMD_VERSION (would break the package cache)
PYTHON3_MODULES_VERS := 1.0
PYTHON3_MODULES_DIR := $(PYTHON3_MODULES)-$(PYTHON3_MODULES_VERS)
# Increase this to enforce a recreation of the build cache
# Note: Because the versions of the individual modules is not reflected in PYTHON3_MODULES_VERS,
#       like it is done in other OMD packages, we'll have to increase the BUILD_ID on every package
#       change.
PYTHON3_MODULES_BUILD_ID := 5

PYTHON3_MODULES_UNPACK:= $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-unpack
PYTHON3_MODULES_PATCHING := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-patching
PYTHON3_MODULES_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-build
PYTHON3_MODULES_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-install-intermediate
PYTHON3_MODULES_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-cache-pkg-process
PYTHON3_MODULES_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-install

PYTHON3_MODULES_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON3_MODULES_DIR)
PYTHON3_MODULES_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON3_MODULES_DIR)
PYTHON3_MODULES_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON3_MODULES_DIR)

# Used by other OMD packages
PACKAGE_PYTHON3_MODULES_DESTDIR    := $(PYTHON3_MODULES_INSTALL_DIR)
PACKAGE_PYTHON3_MODULES_PYTHONPATH := $(PACKAGE_PYTHON3_MODULES_DESTDIR)/lib/python3

PYTHON3_MODULES_LIST :=

PYTHON3_MODULES_LIST += setuptools_scm-4.1.2.tar.gz # needed by various setup.py
PYTHON3_MODULES_LIST += setuptools-git-1.2.tar.gz # needed by various setup.py
PYTHON3_MODULES_LIST += six-1.15.0.tar.gz # direct dependency + needed by bcrypt, cryptography, PyNaCl, python-dateutil, vcrpy, pyOpenSSL, python-active-directory
PYTHON3_MODULES_LIST += python-dateutil-2.8.2.tar.gz # direct dependency

PYTHON3_MODULES_LIST += PyYAML-5.4.1.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += wrapt-1.12.1.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += yarl-1.6.0.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += multidict-4.7.6.tar.gz # needed by yarl
PYTHON3_MODULES_LIST += idna-2.8.tar.gz # needed by yarl, requests
PYTHON3_MODULES_LIST += vcrpy-4.1.0.tar.gz # used by various unit tests to mock HTTP transactions

PYTHON3_MODULES_LIST += pycparser-2.20.tar.gz # needed by cffi
PYTHON3_MODULES_LIST += cffi-1.14.3.tar.gz # needed by PyNaCl, cryptography, bcrypt
PYTHON3_MODULES_LIST += PyNaCl-1.3.0.tar.gz # needed by paramiko
PYTHON3_MODULES_LIST += cryptography-3.3.2.tar.gz # needed by paramiko, pyOpenSSL
PYTHON3_MODULES_LIST += bcrypt-3.1.7.tar.gz # needed by paramiko
PYTHON3_MODULES_LIST += paramiko-2.6.0.tar.gz # direct dependency, used for SFTP transactions in check_sftp

PYTHON3_MODULES_LIST += pyasn1-0.4.8.tar.gz # needed by pysnmp
PYTHON3_MODULES_LIST += pyasn1-modules-0.2.8.tar.gz # needed by kubernetes
PYTHON3_MODULES_LIST += pycryptodomex-3.9.3.tar.gz # needed by pysnmp
PYTHON3_MODULES_LIST += ply-3.11.tar.gz # needed by pysmi, python-active-directory
PYTHON3_MODULES_LIST += pysmi-0.3.4.tar.gz # needed by pysnmp
PYTHON3_MODULES_LIST += pysnmp-4.4.12.tar.gz # needed by Event Console
PYTHON3_MODULES_LIST += snmpsim-0.4.7.tar.gz # needed by SNMP integration tests

PYTHON3_MODULES_LIST += certifi-2019.11.28.tar.gz # needed by requests
PYTHON3_MODULES_LIST += chardet-3.0.4.tar.gz # needed by requests
PYTHON3_MODULES_LIST += urllib3-1.26.7.tar.gz # needed by requests
PYTHON3_MODULES_LIST += pyOpenSSL-19.1.0.tar.gz # needed by requests with extras = ["security"]
PYTHON3_MODULES_LIST += pbr-5.4.4.tar.gz # needed by jira, pyghmi
PYTHON3_MODULES_LIST += pyghmi-1.5.13.tar.gz # needed by base for IPMI
PYTHON3_MODULES_LIST += requests-2.26.0.tar.gz # needed by DCD
PYTHON3_MODULES_LIST += charset-normalizer-2.0.6.tar.gz # needed by requests
PYTHON3_MODULES_LIST += pykerberos-1.2.1.tar.gz # needed by check_bi_aggr
PYTHON3_MODULES_LIST += requests-kerberos-0.12.0.tar.gz # needed by check_bi_aggr
PYTHON3_MODULES_LIST += MarkupSafe-1.1.1.tar.gz # needed by Jinja2
PYTHON3_MODULES_LIST += itsdangerous-1.1.0.tar.gz # needed by Flask
PYTHON3_MODULES_LIST += Jinja2-2.11.3.tar.gz # needed by Flask
PYTHON3_MODULES_LIST += more-itertools-8.0.2.tar.gz # needed by zipp
PYTHON3_MODULES_LIST += zipp-0.6.0.tar.gz # needed by importlib_metadata
PYTHON3_MODULES_LIST += attrs-20.2.0.tar.gz # needed by jsonschema
PYTHON3_MODULES_LIST += importlib_metadata-1.2.0.tar.gz # needed by jsonschema
PYTHON3_MODULES_LIST += pyrsistent-0.15.6.tar.gz # needed by jsonschema
PYTHON3_MODULES_LIST += click-7.1.2.tar.gz # needed by Flask
PYTHON3_MODULES_LIST += Werkzeug-2.0.2.tar.gz # Needed by Flask
PYTHON3_MODULES_LIST += jsonschema-3.2.0.tar.gz # needed by openapi-spec-validator
PYTHON3_MODULES_LIST += Flask-1.1.1.tar.gz # direct dependency
PYTHON3_MODULES_LIST += pytz-2020.1.tar.gz # needed by Flask-Babel
PYTHON3_MODULES_LIST += Babel-2.8.0.tar.gz # needed by Flask-Babel
PYTHON3_MODULES_LIST += Flask-Babel-1.0.0.tar.gz # needed by GUI for i18n support (lazy gettext)
PYTHON3_MODULES_LIST += openapi-spec-validator-0.2.9.tar.gz # direct dependency

PYTHON3_MODULES_LIST += psutil-5.6.7.tar.gz # needed for omdlib
PYTHON3_MODULES_LIST += passlib-1.7.2.tar.gz # needed for omdlib

PYTHON3_MODULES_LIST += defusedxml-0.6.0.tar.gz # needed for jira
PYTHON3_MODULES_LIST += oauthlib-3.1.0.tar.gz # needed for requests-oauthlib and jira
PYTHON3_MODULES_LIST += requests-oauthlib-1.3.0.tar.gz # needed for jira
PYTHON3_MODULES_LIST += requests-toolbelt-0.9.1.tar.gz # needed for jira
PYTHON3_MODULES_LIST += PyJWT-1.7.1.tar.gz # needed for jira
PYTHON3_MODULES_LIST += docutils-0.15.2.tar.gz # needed by boto3, jira
PYTHON3_MODULES_LIST += jira-2.0.0.tar.gz # needed for jira

PYTHON3_MODULES_LIST += adal-1.2.0.tar.gz # needed for agent_azure

PYTHON3_MODULES_LIST += Pillow-8.3.2.tar.gz # needed by GUI, reportlab
PYTHON3_MODULES_LIST += python-ldap-3.3.1.tar.gz # needed by GUI (User sync), python-active-directory
PYTHON3_MODULES_LIST += dicttoxml-1.7.4.tar.gz # needed by GUI (API XML format)
PYTHON3_MODULES_LIST += Cython-0.29.19.tar.gz # needed by numpy
PYTHON3_MODULES_LIST += numpy-1.18.4.tar.gz # needed by GUI (forecast graphs)
PYTHON3_MODULES_LIST += reportlab-3.5.34.tar.gz # needed by GUI (reporting)
PYTHON3_MODULES_LIST += PyPDF2-1.26.0.tar.gz # needed by GUI (reporting)
PYTHON3_MODULES_LIST += roman-3.2.tar.gz # needed by reporting frontmatter

PYTHON3_MODULES_LIST += cachetools-4.1.1.tar.gz # needed by kubernetes
PYTHON3_MODULES_LIST += google-auth-1.21.3.tar.gz # needed by kubernetes
PYTHON3_MODULES_LIST += rsa-4.6.tar.gz # needed by kubernetes
PYTHON3_MODULES_LIST += websocket_client-0.57.0.tar.gz # needed by kubernetes
PYTHON3_MODULES_LIST += kubernetes-10.0.1.tar.gz # needed by kubernetes

PYTHON3_MODULES_LIST += jmespath-0.10.0.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += botocore-1.21.49.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += s3transfer-0.5.0.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += boto3-1.18.49.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += python-snap7-0.10.tar.gz # needed by Siemens PLC special agent

PYTHON3_MODULES_LIST += pymssql-2.1.5.tar.gz # needed by check_sql active check
PYTHON3_MODULES_LIST += PyMySQL-0.9.3.tar.gz # needed by check_sql active check
PYTHON3_MODULES_LIST += psycopg2-binary-2.8.4.tar.gz # needed by check_sql active check

# To automatically generate checkmk.yaml OpenAPI spec file
PYTHON3_MODULES_LIST += apispec-3.3.1.tar.gz
PYTHON3_MODULES_LIST += marshmallow-3.11.1.tar.gz
PYTHON3_MODULES_LIST += marshmallow-oneofschema-2.1.0.tar.gz
PYTHON3_MODULES_LIST += apispec-oneofschema-3.0.0.tar.gz

PYTHON3_MODULES_LIST += mypy_extensions-0.4.3.tar.gz  # direct dependency
PYTHON3_MODULES_LIST += typing_extensions-3.7.4.1.tar.gz  # direct dependency

PYTHON3_MODULES_LIST += dnspython-1.16.0.zip  # needed by python-active-directory
PYTHON3_MODULES_LIST += python-active-directory-1.0.5.tar.gz  # direct dependency
PYTHON3_MODULES_LIST += docstring_parser-0.7.2.tar.gz  # direct dependency
PYTHON3_MODULES_LIST += yapf-0.30.0.tar.gz  # formatter for REST-API documentation code examples
PYTHON3_MODULES_LIST += pyprof2calltree-1.4.5.tar.gz  # converts cProfile info into cachegrind files
PYTHON3_MODULES_LIST += repoze.profile-2.3.tar.gz  # very minimal wsgi profiling middleware
PYTHON3_MODULES_LIST += pyparsing-2.4.7.tar.gz  # direct dependency
PYTHON3_MODULES_LIST += ordered-set-4.0.2.tar.gz # needed by deepdiff
PYTHON3_MODULES_LIST += deepdiff-5.0.2.tar.gz  # used for recording setup audit log
PYTHON3_MODULES_LIST += redis-3.5.3.tar.gz  # needed by GUI (caching)

PYTHON3_MODULES_LIST += tenacity-6.3.1.tar.gz # needed by opsgenie-sdk
PYTHON3_MODULES_LIST += opsgenie-sdk-2.0.3.tar.gz # needed by opsgenie_issues

# TODO: Can we clean this up and use the intermediate install step results? Would be possible
# in the moment we merge the build and intermediate install in a single target
$(PYTHON3_MODULES_BUILD): $(PYTHON3_CACHE_PKG_PROCESS) $(OPENSSL_INTERMEDIATE_INSTALL) $(FREETDS_INTERMEDIATE_INSTALL) $(POSTGRESQL_INTERMEDIATE_INSTALL) $(PYTHON3_MODULES_PATCHING)
# rpath: Create some dummy rpath which has enough space for later replacement
# by the final rpath
	set -e ; cd $(PYTHON3_MODULES_BUILD_DIR) ; \
	    unset DESTDIR MAKEFLAGS ; \
	    $(MKDIR) $(PACKAGE_PYTHON3_MODULES_PYTHONPATH) ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH)" ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_PYTHONPATH)" ; \
	    export CPATH="$(PACKAGE_FREETDS_DESTDIR)/include:$(PACKAGE_OPENSSL_INCLUDE_PATH):$(PACKAGE_POSTGRESQL_INCLUDE_PATH)" ; \
	    export LDFLAGS="-Wl,--rpath,/omd/versions/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxlib $(PACKAGE_PYTHON3_LDFLAGS) $(PACKAGE_FREETDS_LDFLAGS) $(PACKAGE_OPENSSL_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH):$(PACKAGE_OPENSSL_LD_LIBRARY_PATH):$(PACKAGE_POSTGRESQL_LD_LIBRARY_PATH)" ; \
	    export PATH="$(PACKAGE_PYTHON3_BIN):$(PACKAGE_POSTGRESQL_BIN):$$PATH" ; \
	    for M in $(PYTHON3_MODULES_LIST); do \
		echo "=== Building $$M..." ; \
		PKG=$${M//.tar.gz/} ; \
		PKG=$${PKG//.zip/} ; \
		cd $$PKG ; \
		$(PACKAGE_PYTHON3_EXECUTABLE) setup.py build ; \
		$(PACKAGE_PYTHON3_EXECUTABLE) setup.py install \
		    --root=$(PYTHON3_MODULES_INSTALL_DIR) \
		    --prefix='' \
		    --install-data=/share \
		    --install-platlib=/lib/python3 \
		    --install-purelib=/lib/python3 ; \
		cd .. ; \
	    done
# For some highly obscure unknown reason some files end up world-writable. Fix that!
	chmod -R o-w $(PYTHON3_MODULES_INSTALL_DIR)/lib/python3
	$(TOUCH) $@

$(PYTHON3_MODULES_UNPACK): $(addprefix $(PACKAGE_DIR)/$(PYTHON3_MODULES)/src/,$(PYTHON3_MODULES_LIST))
	$(RM) -r $(PYTHON3_MODULES_BUILD_DIR)
	$(MKDIR) $(PYTHON3_MODULES_BUILD_DIR)
	cd $(PYTHON3_MODULES_BUILD_DIR) && \
	    for M in $(PYTHON3_MODULES_LIST); do \
		echo "Unpacking $$M..." ; \
		if echo $$M | grep .tar.gz; then \
		    $(TAR_GZ) $(PACKAGE_DIR)/$(PYTHON3_MODULES)/src/$$M ; \
		else \
		    $(UNZIP) $(PACKAGE_DIR)/$(PYTHON3_MODULES)/src/$$M ; \
		fi \
	    done
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(PYTHON3_MODULES_INTERMEDIATE_INSTALL): $(PYTHON3_MODULES_BUILD)
# Cleanup some unwanted files (example scripts)
	find $(PYTHON3_MODULES_INSTALL_DIR)/bin -name \*.py ! -name snmpsimd.py -exec rm {} \;
# These files break the integration tests on the CI server. Don't know exactly
# why this happens only there, but should be a working fix.
	$(RM) -r $(PYTHON3_MODULES_INSTALL_DIR)/share/snmpsim/data
# AV false positive: A file in test/ is recognized as corrupt by AV proxies.
# solution: don't package test/
	$(RM) -r $(PYTHON3_MODULES_INSTALL_DIR)/test/
# Fix python interpreter for kept scripts
	$(SED) -i '1s|^#!.*/python3$$|#!/usr/bin/env python3|' $(addprefix $(PYTHON3_MODULES_INSTALL_DIR)/bin/,chardetect fakebmc jirashell pbr pyghmicons pyghmiutil pyjwt pyrsa-decrypt pyrsa-encrypt pyrsa-keygen pyrsa-priv2pub pyrsa-sign pyrsa-verify virshbmc snmpsimd.py)
	$(TOUCH) $@

PYTHON3_MODULES_CACHE_PKG_PATH := $(call cache_pkg_path,$(PYTHON3_MODULES_DIR),$(PYTHON3_MODULES_BUILD_ID))

$(PYTHON3_MODULES_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(PYTHON3_MODULES_DIR),$(PYTHON3_MODULES_BUILD_ID),$(PYTHON3_MODULES_INTERMEDIATE_INSTALL))

$(PYTHON3_MODULES_CACHE_PKG_PROCESS): $(PYTHON3_MODULES_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(PYTHON3_MODULES_CACHE_PKG_PATH),$(PYTHON3_MODULES_DIR))
	$(call upload_pkg_archive,$(PYTHON3_MODULES_CACHE_PKG_PATH),$(PYTHON3_MODULES_DIR),$(PYTHON3_MODULES_BUILD_ID))
# Ensure that the rpath of the python binary and dynamic libs always points to the current version path
	set -e ; for F in $$(find $(PYTHON3_MODULES_INSTALL_DIR) -name \*.so); do \
	    chrpath -r "$(OMD_ROOT)/lib" $$F; \
	    echo -n "Test rpath of $$F..." ; \
		if chrpath "$$F" | grep "=$(OMD_ROOT)/lib" >/dev/null 2>&1; then \
		    echo OK ; \
		else \
		    echo "ERROR ($$(chrpath $$F))"; \
		    exit 1 ; \
		fi \
	done
	$(TOUCH) $@

$(PYTHON3_MODULES_INSTALL): $(PYTHON3_MODULES_CACHE_PKG_PROCESS)
	$(RSYNC) -v $(PYTHON3_MODULES_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
