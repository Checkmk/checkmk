PYTHON_VERSION = 2.7.16
BUILD_DIR := $(shell realpath ./../../winbuild)
PLUGINS_DIR := $(shell realpath ./../../plugins)

ifndef SRC_DIR # Don't overwrite SRC_DIR if specified by calling Makefile
	SRC_DIR := $(shell realpath src)
endif

# This package list originates from resolving the dependencies of the packages
# pyinstaller, pyopenssl, requests. The required packages are explicitly listed
# in favor of providing a working setup for a pyinstaller build with python 2.7

# Match package names with their filenames in order to reference them
altgraph = $(SRC_DIR)/pip/altgraph-0.15-py2.py3-none-any.whl
asn1crypto = $(SRC_DIR)/pip/asn1crypto-0.24.0-py2.py3-none-any.whl
certifi = $(SRC_DIR)/pip/certifi-2018.4.16-py2.py3-none-any.whl
cffi = $(SRC_DIR)/pip/cffi-1.11.5-cp27-cp27m-win32.whl
dis3 = $(SRC_DIR)/pip/dis3-0.1.2.tar.gz
chardet = $(SRC_DIR)/pip/chardet-3.0.4-py2.py3-none-any.whl
crytography = $(SRC_DIR)/pip/cryptography-2.2.2-cp27-cp27m-win32.whl
enum34 = $(SRC_DIR)/pip/enum34-1.1.6-py2-none-any.whl
future = $(SRC_DIR)/pip/future-0.16.0.tar.gz
idna = $(SRC_DIR)/pip/idna-2.6-py2.py3-none-any.whl
ipaddress = $(SRC_DIR)/pip/ipaddress-1.0.22-py2.py3-none-any.whl
macholib = $(SRC_DIR)/pip/macholib-1.9-py2.py3-none-any.whl
pefile = $(SRC_DIR)/pip/pefile-2017.11.5.tar.gz
pycparser = $(SRC_DIR)/pip/pycparser-2.18.tar.gz
PyInstaller = $(SRC_DIR)/pip/PyInstaller-3.3.1.tar.gz
PySocks = $(SRC_DIR)/pip/PySocks-1.6.8.tar.gz
pyOpenSSL = $(SRC_DIR)/pip/pyOpenSSL-17.5.0-py2.py3-none-any.whl
pypiwin32 = $(SRC_DIR)/pip/pywin32-223-cp27-cp27m-win32.whl
requests = $(SRC_DIR)/pip/requests-2.21.0-py2.py3-none-any.whl
setuptools = $(SRC_DIR)/pip/setuptools-39.1.0-py2.py3-none-any.whl
six = $(SRC_DIR)/pip/six-1.11.0-py2.py3-none-any.whl
urllib3 = $(SRC_DIR)/pip/urllib3-1.24.1-py2.py3-none-any.whl
wheel = $(SRC_DIR)/pip/wheel-0.33.1-py2.py3-none-any.whl
win_inet_pton = $(SRC_DIR)/pip/win_inet_pton-1.0.1.tar.gz

# This list expands to filenames and is meant to be used
# as depencencie(s). There must not be matching targets in order
# to prevent automatic download
PYTHON_PACKAGE_FILES = \
	$(altgraph) \
	$(asn1crypto) \
	$(certifi) \
	$(cffi) \
	$(dis3) \
	$(chardet) \
	$(crytography) \
	$(enum34) \
	$(future) \
	$(idna) \
	$(ipaddress) \
	$(macholib) \
	$(pefile) \
	$(pycparser) \
	$(PyInstaller) \
	$(PySocks) \
	$(pyOpenSSL) \
	$(pypiwin32) \
	$(requests) \
	$(setuptools) \
	$(six) \
	$(urllib3) \
	$(wheel) \
	$(win_inet_pton)

# This list is meant to be used as target(s) for manual download
PYTHON_PACKAGES = \
	altgraph \
	asn1crypto \
	certifi \
	cffi \
	dis3 \
	chardet \
	crytography \
	enum34 \
	future \
	idna \
	ipaddress \
	macholib \
	pefile \
	pycparser \
	PyInstaller \
	PySocks \
	pyOpenSSL \
	pypiwin32 \
	requests \
	setuptools \
	six \
	urllib3 \
	wheel \
	win_inet_pton

# Matching from filename to download-string.
# When used as target, the target variable
# must be extended two times in order to obtain the desired download-string.
# E.g. make PyInstaller -> pip download $($($@))
$(altgraph) := altgraph==0.15
$(asn1crypto) := asn1crypto==0.24.0
$(certifi) := certifi==2018.4.16
$(cffi) := cffi==1.11.5
$(dis3) := dis3==0.1.2
$(chardet) := chardet==3.0.4
$(crytography) := cryptography==2.2.2
$(enum34) := enum34==1.1.6
$(future) := future==0.16.0
$(idna) := idna==2.6
$(ipaddress) := ipaddress==1.0.22
$(macholib) := macholib==1.9
$(pefile) := pefile==2017.11.5
$(pycparser) := pycparser==2.18
$(PyInstaller) := PyInstaller==3.3.1
$(PySocks) := PySocks==1.6.8
$(pyOpenSSL) := pyOpenSSL==17.5.0
$(pypiwin32) := pypiwin32==223
$(requests) := requests==2.21.0
$(setuptools) := setuptools==39.1.0
$(six) := six==1.11.0
$(urllib3) := urllib3==1.24.1
$(wheel) := wheel==0.33.1
$(win_inet_pton) := win_inet_pton==1.0.1


$(BUILD_DIR)/drive_c/Python27/python.exe: $(SRC_DIR)/python-$(PYTHON_VERSION).msi
	mkdir -p $(BUILD_DIR) && \
	export WINEPREFIX=$(BUILD_DIR) && \
	cd $(BUILD_DIR) && \
	cp $(SRC_DIR)/python-$(PYTHON_VERSION).msi . && \
	wine msiexec /qn /i python-$(PYTHON_VERSION).msi && \
	touch $(BUILD_DIR)/drive_c/Python27/python.exe

.PHONY: setup new_packages download_packages \
download_vcredist download_python $(PYTHON_PACKAGES)

download_packages: $(PYTHON_PACKAGES)

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
	wine c:\\Python27\\python.exe -m pip download --no-deps $($($@)) && \
	mkdir -p $(SRC_DIR)/pip && \
	cp --no-clobber -r * $(SRC_DIR)/pip

download_python:
	mkdir -p $(SRC_DIR) && \
	cd $(SRC_DIR) && \
	curl -O https://www.python.org/ftp/python/$(PYTHON_VERSION)/python-$(PYTHON_VERSION).msi

download_vcredist:
	mkdir -p $(SRC_DIR) && \
	cd $(SRC_DIR) && \
		curl -O https://download.microsoft.com/download/1/1/1/1116b75a-9ec3-481a-a3c8-1777b5381140/vcredist_x86.exe

download_sources: download_python download_packages download_vcredist

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
	wine c:\\Python27\\python.exe -m pip download pypiwin32 && \
	wine c:\\Python27\\python.exe -m pip download requests && \
	wine c:\\Python27\\python.exe -m pip download requests[socks] && \
	wine c:\\Python27\\python.exe -m pip download pyinstaller && \
	wine c:\\Python27\\python.exe -m pip download pyOpenSSL && \
	mkdir -p $(SRC_DIR)/pip && \
	cp -r * $(SRC_DIR)/pip

setup:
	sudo apt-get install scons upx-ucl wine
