PYTHON3_MODULES := python3-modules
PYTHON3_MODULES_VERS := $(OMD_VERSION)
PYTHON3_MODULES_DIR := $(PYTHON3_MODULES)-$(PYTHON3_MODULES_VERS)

PYTHON3_MODULES_UNPACK:= $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-unpack
PYTHON3_MODULES_PATCHING := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-patching
PYTHON3_MODULES_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-build
PYTHON3_MODULES_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-install-intermediate
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
PYTHON3_MODULES_LIST += python-dateutil-2.8.1.tar.gz # direct dependency

PYTHON3_MODULES_LIST += PyYAML-5.3.1.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += wrapt-1.12.1.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += yarl-1.6.0.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += multidict-4.7.6.tar.gz # needed by yarl
PYTHON3_MODULES_LIST += idna-2.8.tar.gz # needed by yarl, requests
PYTHON3_MODULES_LIST += vcrpy-4.1.0.tar.gz # used by various unit tests to mock HTTP transactions

PYTHON3_MODULES_LIST += pycparser-2.20.tar.gz # needed by cffi
PYTHON3_MODULES_LIST += cffi-1.14.3.tar.gz # needed by PyNaCl, cryptography, bcrypt
PYTHON3_MODULES_LIST += PyNaCl-1.3.0.tar.gz # needed by paramiko
PYTHON3_MODULES_LIST += cryptography-2.8.tar.gz # needed by paramiko, pyOpenSSL
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
PYTHON3_MODULES_LIST += urllib3-1.25.10.tar.gz # needed by requests
PYTHON3_MODULES_LIST += pyOpenSSL-19.1.0.tar.gz # needed by requests with extras = ["security"]
PYTHON3_MODULES_LIST += pyghmi-1.5.13.tar.gz # needed by base for IPMI
PYTHON3_MODULES_LIST += requests-2.22.0.tar.gz # needed by DCD, connexion
PYTHON3_MODULES_LIST += pykerberos-1.2.1.tar.gz # needed by check_bi_aggr
PYTHON3_MODULES_LIST += requests-kerberos-0.12.0.tar.gz # needed by check_bi_aggr
PYTHON3_MODULES_LIST += MarkupSafe-1.1.1.tar.gz # needed by Jinja2
PYTHON3_MODULES_LIST += itsdangerous-1.1.0.tar.gz # needed by Flask
PYTHON3_MODULES_LIST += Jinja2-2.10.3.tar.gz # needed by Flask
PYTHON3_MODULES_LIST += more-itertools-8.0.2.tar.gz # needed by zipp
PYTHON3_MODULES_LIST += zipp-0.6.0.tar.gz # needed by importlib_metadata
PYTHON3_MODULES_LIST += attrs-20.2.0.tar.gz # needed by jsonschema
PYTHON3_MODULES_LIST += importlib_metadata-1.2.0.tar.gz # needed by jsonschema
PYTHON3_MODULES_LIST += pyrsistent-0.15.6.tar.gz # needed by jsonschema
PYTHON3_MODULES_LIST += Click-7.0.tar.gz # needed by clickclick
PYTHON3_MODULES_LIST += Werkzeug-0.16.0.tar.gz # Needed by Flask
PYTHON3_MODULES_LIST += jsonschema-3.2.0.tar.gz # needed by connexion, openapi-spec-validator
PYTHON3_MODULES_LIST += clickclick-1.2.2.tar.gz # needed by connexion
PYTHON3_MODULES_LIST += Flask-1.1.1.tar.gz # needed by connexion
PYTHON3_MODULES_LIST += pytz-2020.1.tar.gz # needed by Flask-Babel
PYTHON3_MODULES_LIST += Babel-2.8.0.tar.gz # needed by Flask-Babel
PYTHON3_MODULES_LIST += Flask-Babel-1.0.0.tar.gz # needed by GUI for i18n support (lazy gettext)
PYTHON3_MODULES_LIST += inflection-0.3.1.tar.gz # needed by connexion
PYTHON3_MODULES_LIST += openapi-spec-validator-0.2.8.tar.gz # needed by connexion
PYTHON3_MODULES_LIST += swagger_ui_bundle-0.0.6.tar.gz # direct dependency
PYTHON3_MODULES_LIST += connexion-2.4.0.tar.gz # direct dependency

PYTHON3_MODULES_LIST += psutil-5.6.7.tar.gz # needed for omdlib
PYTHON3_MODULES_LIST += passlib-1.7.2.tar.gz # needed for omdlib

PYTHON3_MODULES_LIST += defusedxml-0.6.0.tar.gz # needed for jira
PYTHON3_MODULES_LIST += oauthlib-3.1.0.tar.gz # needed for requests-oauthlib and jira
PYTHON3_MODULES_LIST += pbr-5.4.4.tar.gz # needed for jira
PYTHON3_MODULES_LIST += requests-oauthlib-1.3.0.tar.gz # needed for jira
PYTHON3_MODULES_LIST += requests-toolbelt-0.9.1.tar.gz # needed for jira
PYTHON3_MODULES_LIST += PyJWT-1.7.1.tar.gz # needed for jira
PYTHON3_MODULES_LIST += jira-2.0.0.tar.gz # needed for jira

PYTHON3_MODULES_LIST += adal-1.2.0.tar.gz # needed for agent_azure

PYTHON3_MODULES_LIST += Pillow-7.2.0.tar.gz # needed by GUI, reportlab
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

PYTHON3_MODULES_LIST += docutils-0.15.2.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += jmespath-0.9.4.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += botocore-1.14.11.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += s3transfer-0.3.2.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += boto3-1.11.11.tar.gz # needed by boto3 (aws)
PYTHON3_MODULES_LIST += python-snap7-0.10.tar.gz # needed by Siemens PLC special agent

PYTHON3_MODULES_LIST += PyMySQL-0.9.3.tar.gz # needed by check_sql active check
PYTHON3_MODULES_LIST += psycopg2-binary-2.8.4.tar.gz # needed by check_sql active check

# To automatically generate checkmk.yaml OpenAPI spec file
PYTHON3_MODULES_LIST += apispec-2.0.2.tar.gz
PYTHON3_MODULES_LIST += marshmallow-2.20.5.tar.gz
PYTHON3_MODULES_LIST += marshmallow-oneofschema-1.0.6.tar.gz
PYTHON3_MODULES_LIST += apispec-oneofschema-2.1.1.tar.gz

PYTHON3_MODULES_LIST += mypy_extensions-0.4.3.tar.gz  # direct dependency
PYTHON3_MODULES_LIST += typing_extensions-3.7.4.1.tar.gz  # direct dependency

PYTHON3_MODULES_LIST += dnspython-1.16.0.zip  # needed by python-active-directory
PYTHON3_MODULES_LIST += python-active-directory-1.0.5.tar.gz  # direct dependency
PYTHON3_MODULES_LIST += docstring_parser-0.7.2.tar.gz  # direct dependency
PYTHON3_MODULES_LIST += yapf-0.30.0.tar.gz  # formatter for REST-API documentation code examples
PYTHON3_MODULES_LIST += pyprof2calltree-1.4.5.tar.gz  # converts cProfile info into cachegrind files
PYTHON3_MODULES_LIST += repoze.profile-2.3.tar.gz  # very minimal wsgi profiling middleware

# TODO: Can we clean this up and use the intermediate install step results? Would be possible
# in the moment we merge the build and intermediate install in a single target
$(PYTHON3_MODULES_BUILD): $(PYTHON3_CACHE_PKG_PROCESS) $(OPENSSL_INTERMEDIATE_INSTALL) $(FREETDS_INTERMEDIATE_INSTALL) $(POSTGRESQL_INTERMEDIATE_INSTALL) $(PYTHON3_MODULES_PATCHING)
	set -e ; cd $(PYTHON3_MODULES_BUILD_DIR) ; \
	    unset DESTDIR MAKEFLAGS ; \
	    $(MKDIR) $(PACKAGE_PYTHON3_MODULES_PYTHONPATH) ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH)" ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_PYTHONPATH)" ; \
	    export CPATH="$(PACKAGE_FREETDS_DESTDIR)/include:$(PACKAGE_OPENSSL_INCLUDE_PATH):$(PACKAGE_POSTGRESQL_INCLUDE_PATH)" ; \
	    export LDFLAGS="$(PACKAGE_PYTHON3_LDFLAGS) $(PACKAGE_FREETDS_LDFLAGS) $(PACKAGE_OPENSSL_LDFLAGS)" ; \
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
# Ensure all native modules have the correct rpath set
	set -e ; for F in $$(find $(PACKAGE_PYTHON3_MODULES_PYTHONPATH) -name \*.so); do \
	    echo -n "Test rpath of $$F..." ; \
		if chrpath "$$F" | grep "=$(OMD_ROOT)/lib" >/dev/null 2>&1; then \
		    echo OK ; \
		else \
		    echo "ERROR ($$(chrpath $$F))"; \
		    exit 1 ; \
		fi \
	done
	$(TOUCH) $@

$(PYTHON3_MODULES_INSTALL): $(PYTHON3_MODULES_INTERMEDIATE_INSTALL)
	$(RSYNC) -v $(PYTHON3_MODULES_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@

python3-modules-dump-Pipfile:
	@echo '# ATTENTION: Most of this file is generated by omd/packages/python3-modules/python3-modules.make'
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
	@echo 'dockerpty = "*"  # used by dockerized tests for opening debug shells'
	@echo 'freezegun = "*"  # used by various unit tests'
	@echo 'isort = "*"  # used as a plugin for editors'
	@echo 'lxml = "*"  # used via beautifulsoup4 as a parser and in the agent_netapp special agent'
	@echo 'mock = "*"  # used in checktestlib in unit tests'
	@echo 'mockldap = "*"  # used in test_userdb_ldap_connector unit test'
	@echo 'pylint = "*"  # used by test/Makefile'"'"'s test-pylint target'
	@echo 'mypy = "*"  # used by test/static/Makefile'"'"'s test-mypy target'
	@echo 'pymongo = "*"  # used by mk_mongodb agent plugin'
	@echo 'pytest = "*"  # used by various test/Makefile targets'
	@echo 'pytest-cov = "*"  # used (indirectly) by test/Makefile'"'"'s test-unit-coverage-html target, see comment there'
	@echo 'pytest-mock = "*"  # used by quite a few unit/integration tests via the mocker fixture'
	@echo 'pytest-testmon = "*"  # used for pre-commit checking via .pre-commit-config.yaml'
	@echo 'responses = "*" # used for unit tests'
	@echo 'polib = "*"  # used by locale/add-authors for working with .po files'
	@echo 'webtest = "*"  # used by WSGI based tests'
	@echo 'pre-commit = "*"  # used to fix / find issues before commiting changes'
	@echo 'pyfakefs = "*" # used for unit tests'
	@echo 'flake8 = "*"'
	@echo 'sphinx = "*" # used for the plugin API documentation'
	@echo 'sphinx-autodoc-typehints = "*" # used for the plugin API documentation'
	@echo 'sphinx-rtd-theme = "*" # used for the plugin API documentation'
	@echo '3to2 = "*" # used for converting agent plugins from py3 to 2'
	@echo ''
	@echo '[packages]'
	@echo $(patsubst %.zip,%,$(patsubst %.tar.gz,%,$(PYTHON3_MODULES_LIST))) | tr ' ' '\n' | sed 's/-\([0-9.]*\)$$/ = "==\1"/'
	@echo ''
	@echo '[requires]'
	@echo 'python_version = "3.8"'
