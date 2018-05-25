include ../../Makefile.omd

# This package contains the SNAP 7 library (http://snap7.sourceforge.net/)
# and also the related python bindings (https://pypi.python.org/pypi/python-snap7/).

NAME     = snap7
VERSION  = 1.3.0
DIR      = snap7-full-$(VERSION)

PY_DIR     = python-snap7-0.9

ARCH = $(shell uname -m)
ifeq ($(ARCH),i686)
    ARCH=i386
endif

.PHONY: build install skel clean

build: check-python
	tar xzf $(DIR).tar.gz
	cd $(DIR)/build/unix && $(MAKE) -f $(ARCH)_linux.mk

# Now handle the python module
	tar xvzf $(PY_DIR).tar.gz

	set -e ; for p in python-patches/*.dif ; do \
	echo "applying $$p..." ; \
	    patch -d $(PY_DIR) -p1 < $$p ; \
	done

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib
	install -m 644 $(DIR)/build/bin/$(ARCH)-linux/libsnap7.so $(DESTDIR)$(OMD_ROOT)/lib

	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/python && \
	export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	cd $(PY_DIR) && \
	$(PACKAGE_PYTHON_EXECUTABLE) setup.py install --home=$(DESTDIR)$(OMD_ROOT) \
	    --prefix='' \
	    --install-platlib=$(DESTDIR)$(OMD_ROOT)/lib/python \
	    --install-purelib=$(DESTDIR)$(OMD_ROOT)/lib/python

skel:

clean:
	rm -rf $(DIR) $(PY_DIR)
