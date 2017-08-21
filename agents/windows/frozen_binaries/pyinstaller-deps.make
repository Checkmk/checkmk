.PHONY: new_packages

# Python 2.7.13 yields a bug concerning the LoadLibrary() function on windows,
# see http://bugs.python.org/issue29082 . Use 2.7.12 instead.
PYTHON_VERSION = 2.7.12
BUILD_DIR =  $(shell realpath ./../../winbuild)
PLUGINS_DIR = $(shell realpath ./../../plugins)
# This package list originates from resolving the dependencies of the packages
# pyinstaller, pyopenssl, requests. The required packages are explicitly listed
# in favor of providing a working setup for a pyinstaller build with python 2.7
PYTHON_PACKAGES = \
src/pip/asn1crypto-0.22.0-py2.py3-none-any.whl \
src/pip/certifi-2017.7.27.1-py2.py3-none-any.whl \
src/pip/cffi-1.10.0-cp27-cp27m-win32.whl \
src/pip/chardet-3.0.4-py2.py3-none-any.whl \
src/pip/cryptography-2.0.3-cp27-cp27m-win32.whl \
src/pip/enum34-1.1.6-py2-none-any.whl \
src/pip/future-0.16.0.tar.gz \
src/pip/idna-2.6-py2.py3-none-any.whl \
src/pip/ipaddress-1.0.18-py2-none-any.whl \
src/pip/pycparser-2.18.tar.gz \
src/pip/PyInstaller-3.2.1.tar.bz2 \
src/pip/pyOpenSSL-17.2.0-py2.py3-none-any.whl \
src/pip/pypiwin32-219-cp27-none-win32.whl \
src/pip/requests-2.18.4-py2.py3-none-any.whl \
src/pip/setuptools-36.2.7-py2.py3-none-any.whl \
src/pip/six-1.10.0-py2.py3-none-any.whl \
src/pip/urllib3-1.22-py2.py3-none-any.whl

src/python-$(PYTHON_VERSION).msi:
	cd src && wget https://www.python.org/ftp/python/$(PYTHON_VERSION)/python-$(PYTHON_VERSION).msi

$(PYTHON_PACKAGES): src/python-$(PYTHON_VERSION).msi
	# Download needed python packages including depencencies. This has to be done
	# from within wine to obtain the correct win32 packages.
	# Note: We built this list to make the agent compilation reproducable. From time
	# to time we should update the packages here, but we don't want to fetch new versions
	# automatically.
	mkdir $(BUILD_DIR) && \
	export WINEPREFIX=$(BUILD_DIR) && \
	cd $(BUILD_DIR) && \
	cp $(CURDIR)/src/python-$(PYTHON_VERSION).msi . && \
	wine msiexec /qn /i python-$(PYTHON_VERSION).msi && \
	mkdir pip && \
	cd pip && \
	wine c:\\Python27\\python.exe -m pip download --no-deps asn1crypto==0.22.0 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps certifi==2017.7.27.1 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps cffi==1.10.0 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps chardet==3.0.4 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps cryptography==2.0.3 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps enum34==1.1.6 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps future==0.16.0 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps idna==2.6 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps ipaddress==1.0.18 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps pycparser==2.18 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps PyInstaller==3.2.1 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps pyOpenSSL==17.2.0 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps pypiwin32==219 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps requests==2.18.4 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps setuptools==36.2.7 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps six==1.10.0 && \
	wine c:\\Python27\\python.exe -m pip download --no-deps urllib3==1.22 && \
	mkdir -p $(CURDIR)/src/pip && \
	cp -r * $(CURDIR)/src/pip
	rm -rf $(BUILD_DIR)

new_packages: src/python-$(PYTHON_VERSION).msi
	# Use this target to obtain the newest versions of the needed packages.
	# You should update the explicit dependencies afterwars because the automatic
	# download of the latests packages might lead to an incosistent state, e.g.
	# if a package gets downloaded multiple times with different versions.
	mkdir $(BUILD_DIR) && \
	export WINEPREFIX=$(BUILD_DIR) && \
	cd $(BUILD_DIR) && \
	cp $(CURDIR)/src/python-$(PYTHON_VERSION).msi . && \
	wine msiexec /qn /i python-$(PYTHON_VERSION).msi && \
	mkdir pip && \
	cd pip && \
	wine c:\\Python27\\python.exe -m pip download requests && \
	wine c:\\Python27\\python.exe -m pip download pyinstaller && \
	wine c:\\Python27\\python.exe -m pip download pyOpenSSL && \
	mkdir -p $(CURDIR)/src/pip && \
	cp -r * $(CURDIR)/src/pip
	rm -rf $(BUILD_DIR)

src/vcredist_x86.exe:
	cd src && \
		wget https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x86.exe

setup:
	sudo apt-get install scons upx-ucl wine
