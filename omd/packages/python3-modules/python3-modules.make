PYTHON3_MODULES := python3-modules
PYTHON3_MODULES_VERS := $(OMD_VERSION)
PYTHON3_MODULES_DIR := $(PYTHON3_MODULES)-$(PYTHON3_MODULES_VERS)

PYTHON3_MODULES_UNPACK:= $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-unpack
PYTHON3_MODULES_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-build
PYTHON3_MODULES_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-install-intermediate
PYTHON3_MODULES_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES_DIR)-install

PYTHON3_MODULES_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(PYTHON3_MODULES_DIR)
PYTHON3_MODULES_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(PYTHON3_MODULES_DIR)
PYTHON3_MODULES_WORK_DIR := $(PACKAGE_WORK_DIR)/$(PYTHON3_MODULES_DIR)

# Used by other OMD packages
PACKAGE_PYTHON3_MODULES_DESTDIR    := $(PYTHON3_MODULES_INSTALL_DIR)
PACKAGE_PYTHON3_MODULES_PYTHONPATH := $(PACKAGE_PYTHON3_MODULES_DESTDIR)/lib/python3

.PHONY: $(PYTHON3_MODULES) $(PYTHON3_MODULES)-install $(PYTHON3_MODULES)-clean

$(PYTHON3_MODULES): $(PYTHON3_MODULES_BUILD)

$(PYTHON3_MODULES)-install: $(PYTHON3_MODULES_INSTALL)

PYTHON3_MODULES_LIST :=

PYTHON3_MODULES_LIST += setuptools_scm-3.3.3.tar.gz # needed by various setup.py
PYTHON3_MODULES_LIST += setuptools-git-1.2.tar.gz # needed by various setup.py
PYTHON3_MODULES_LIST += six-1.13.0.tar.gz # direct dependency + needed by bcrypt, cryptography, PyNaCl, python-dateutil, vcrpy, pyOpenSSL
PYTHON3_MODULES_LIST += python-dateutil-2.8.0.tar.gz # direct dependency

PYTHON3_MODULES_LIST += PyYAML-5.1.2.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += wrapt-1.11.2.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += yarl-1.3.0.tar.gz # needed by vcrpy
PYTHON3_MODULES_LIST += multidict-4.5.2.tar.gz # needed by yarl
PYTHON3_MODULES_LIST += idna-2.8.tar.gz # needed by yarl, requests
PYTHON3_MODULES_LIST += vcrpy-2.1.0.tar.gz # used by various unit tests to mock HTTP transactions

PYTHON3_MODULES_LIST += pycparser-2.19.tar.gz # needed by cffi
PYTHON3_MODULES_LIST += cffi-1.13.1.tar.gz # needed by PyNaCl, cryptography, bcrypt
PYTHON3_MODULES_LIST += PyNaCl-1.3.0.tar.gz # needed by paramiko
PYTHON3_MODULES_LIST += cryptography-2.8.tar.gz # needed by paramiko, pyOpenSSL
PYTHON3_MODULES_LIST += bcrypt-3.1.7.tar.gz # needed by paramiko
PYTHON3_MODULES_LIST += paramiko-2.6.0.tar.gz # direct dependency, used for SFTP transactions in check_sftp

PYTHON3_MODULES_LIST += pyasn1-0.4.7.tar.gz # needed by pysnmp
PYTHON3_MODULES_LIST += pycryptodomex-3.9.3.tar.gz # needed by pysnmp
PYTHON3_MODULES_LIST += ply-3.11.tar.gz # needed by pysmi
PYTHON3_MODULES_LIST += pysmi-0.3.4.tar.gz # needed by pysnmp
PYTHON3_MODULES_LIST += pysnmp-4.4.12.tar.gz # needed by Event Console

PYTHON3_MODULES_LIST += certifi-2019.9.11.tar.gz # needed by requests
PYTHON3_MODULES_LIST += chardet-3.0.4.tar.gz # needed by requests
PYTHON3_MODULES_LIST += urllib3-1.25.7.tar.gz # needed by requests
PYTHON3_MODULES_LIST += pyOpenSSL-19.1.0.tar.gz # needed by requests with extras = ["security"]
PYTHON3_MODULES_LIST += requests-2.22.0.tar.gz # needed by DCD

# TODO: Can we clean this up and use the intermediate install step results? Would be possible
# in the moment we merge the build and intermediate install in a single target
$(PYTHON3_MODULES_BUILD): $(PYTHON3_CACHE_PKG_PROCESS) $(FREETDS_INTERMEDIATE_INSTALL) $(PYTHON3_MODULES_UNPACK)
	set -e ; cd $(PYTHON3_MODULES_BUILD_DIR) ; \
	    unset DESTDIR MAKEFLAGS ; \
	    $(MKDIR) $(PACKAGE_PYTHON3_MODULES_PYTHONPATH) ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_MODULES_PYTHONPATH)" ; \
	    export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON3_PYTHONPATH)" ; \
	    export CPATH="$(PACKAGE_FREETDS_DESTDIR)/include" ; \
	    export LDFLAGS="$(PACKAGE_PYTHON3_LDFLAGS) $(PACKAGE_FREETDS_LDFLAGS)" ; \
	    export LD_LIBRARY_PATH="$(PACKAGE_PYTHON3_LD_LIBRARY_PATH)" ; \
	    export PATH="$(PACKAGE_PYTHON3_BIN):$$PATH" ; \
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
	$(RSYNC) $(PYTHON3_MODULES_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@

$(PYTHON3_MODULES)-skel:

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
	@echo 'yapf = "*"  # used for editor integration and the format-python Makefile target'
	@echo 'polib = "*"  # used by locale/add-authors for working with .po files'
	@echo ''
	@echo '[packages]'
	@echo $(patsubst %.zip,%,$(patsubst %.tar.gz,%,$(PYTHON3_MODULES_LIST))) | tr ' ' '\n' | sed 's/-\([0-9.]*\)$$/ = "==\1"/'
	@echo ''
	@echo '[requires]'
	@echo 'python_version = "3.7"'

$(PYTHON3_MODULES)-clean:
	rm -rf $(PYTHON3_MODULES_BUILD_DIR) $(BUILD_HELPER_DIR)/$(PYTHON3_MODULES)*
