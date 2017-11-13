.PHONY: new_packages

# Python 2.7.13 yields a bug concerning the LoadLibrary() function on windows,
# see http://bugs.python.org/issue29082 . Use 2.7.12 instead.
PYTHON_VERSION = 2.7.12
BUILD_DIR =  $(shell realpath ./../../winbuild)
PLUGINS_DIR = $(shell realpath ./../../plugins)
# This package list originates from resolving the dependencies of the packages
# pyinstaller, pyopenssl, requests. The required packages are explicitly listed
# in favor of providing a working setup for a pyinstaller build with python 2.7

asn1crypto = src/pip/asn1crypto-0.22.0-py2.py3-none-any.whl
certifi = src/pip/certifi-2017.7.27.1-py2.py3-none-any.whl
cffi = src/pip/cffi-1.10.0-cp27-cp27m-win32.whl
chardet = src/pip/chardet-3.0.4-py2.py3-none-any.whl
crytography = src/pip/cryptography-2.0.3-cp27-cp27m-win32.whl
enum34 = src/pip/enum34-1.1.6-py2-none-any.whl
future = src/pip/future-0.16.0.tar.gz
idna = src/pip/idna-2.6-py2.py3-none-any.whl
ipaddress = src/pip/ipaddress-1.0.18-py2-none-any.whl
pycparser = src/pip/pycparser-2.18.tar.gz
PyInstaller = src/pip/PyInstaller-3.2.1.tar.bz2
pyOpenSSL = src/pip/pyOpenSSL-17.2.0-py2.py3-none-any.whl
pypiwin32 = src/pip/pypiwin32-219-cp27-none-win32.whl
requests = src/pip/requests-2.18.4-py2.py3-none-any.whl
setuptools = src/pip/setuptools-36.2.7-py2.py3-none-any.whl
six = src/pip/six-1.10.0-py2.py3-none-any.whl
urllib3 = src/pip/urllib3-1.22-py2.py3-none-any.whl

PYTHON_PACKAGES = \
	$(asn1crypto) \
	$(certifi) \
	$(cffi) \
	$(chardet) \
	$(crytography) \
	$(enum34) \
	$(future) \
	$(idna) \
	$(ipaddress) \
	$(pycparser) \
	$(PyInstaller) \
	$(pyOpenSSL) \
	$(pypiwin32) \
	$(requests) \
	$(setuptools) \
	$(six) \
	$(urllib3)

$(asn1crypto) := asn1crypto==0.22.0
$(certifi) := certifi==2017.7.27.1
$(cffi) := cffi==1.10.0
$(chardet) := chardet==3.0.4
$(crytography) := cryptography==2.0.3
$(enum34) := enum34==1.1.6
$(future) := future==0.16.0
$(idna) := idna==2.6
$(ipaddress) := ipaddress==1.0.18
$(pycparser) := pycparser==2.18
$(PyInstaller) := PyInstaller==3.2.1
$(pyOpenSSL) := pyOpenSSL==17.2.0
$(pypiwin32) := pypiwin32==219
$(requests) := requests==2.18.4
$(setuptools) := setuptools==36.2.7
$(six) := six==1.10.0
$(urllib3) := urllib3==1.22

src/python-$(PYTHON_VERSION).msi:
	mkdir -p src && \
	cd src && \
	curl -O https://www.python.org/ftp/python/$(PYTHON_VERSION)/python-$(PYTHON_VERSION).msi

$(BUILD_DIR)/drive_c/Python27/python.exe: src/python-$(PYTHON_VERSION).msi
	mkdir -p $(BUILD_DIR) && \
	export WINEPREFIX=$(BUILD_DIR) && \
	cd $(BUILD_DIR) && \
	cp $(CURDIR)/src/python-$(PYTHON_VERSION).msi . && \
	wine msiexec /qn /i python-$(PYTHON_VERSION).msi && \
	touch $(BUILD_DIR)/drive_c/Python27/python.exe

$(PYTHON_PACKAGES): $(BUILD_DIR)/drive_c/Python27/python.exe
	# Download needed python packages including depencencies. This has to be done
	# from within wine to obtain the correct win32 packages.
	# Note: We built this list to make the agent compilation reproducable. From time
	# to time we should update the packages here, but we don't want to fetch new versions
	# automatically.
	mkdir -p $(BUILD_DIR) && \
	export WINEPREFIX=$(BUILD_DIR) && \
	cd $(BUILD_DIR) && \
	mkdir -p pip && \
	cd pip && \
	wine c:\\Python27\\python.exe -m pip download --no-deps $($@) && \
	mkdir -p $(CURDIR)/src/pip && \
	cp -r * $(CURDIR)/src/pip

new_packages: $(BUILD_DIR)/drive_c/Python27/python.exe
	# Use this target to obtain the newest versions of the needed packages.
	# You should update the explicit dependencies afterwars because the automatic
	# download of the latests packages might lead to an incosistent state, e.g.
	# if a package gets downloaded multiple times with different versions.
	mkdir -p $(BUILD_DIR) && \
	export WINEPREFIX=$(BUILD_DIR) && \
	cd $(BUILD_DIR) && \
	mkdir pip && \
	cd pip && \
	wine c:\\Python27\\python.exe -m pip download requests && \
	wine c:\\Python27\\python.exe -m pip download pyinstaller && \
	wine c:\\Python27\\python.exe -m pip download pyOpenSSL && \
	mkdir -p $(CURDIR)/src/pip && \
	cp -r * $(CURDIR)/src/pip

src/vcredist_x86.exe:
	mkdir -p src && \
	cd src && \
		curl -O https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x86.exe

setup:
	sudo apt-get install scons upx-ucl wine