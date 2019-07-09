# Package definition
PYTHON3 := Python
PYTHON3_VERS := 3.7.3
PYTHON3_DIR := $(PYTHON3)-$(PYTHON3_VERS)

PYTHON3_BUILD := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-build
PYTHON3_COMPILE := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-compile
PYTHON3_INSTALL := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-install
PYTHON3_UNPACK := $(BUILD_HELPER_DIR)/$(PYTHON3_DIR)-unpack

.PHONY: Python3 Python3-install Python3-skel Python3-clean upstream

Python3: $(PYTHON3_BUILD)

Python3-install: $(PYTHON3_INSTALL)

# Environment variables
ifeq (0,$(shell gcc -Xlinker --help | grep -q -e "-plugin"; echo $$?))
PYTHON_ENABLE_OPTIMIZATIONS := --enable-optimizations
else
PYTHON_ENABLE_OPTIMIZATIONS :=
endif

$(PYTHON3_BUILD): $(PYTHON3_UNPACK)
# The build with PGO/LTO
# enables is mainly sequential, so a high build parallelism doesn't really
# help. Therefore we use just -j2.
	cd $(PYTHON3_DIR) ; \
	$(TEST) "$(DISTRO_NAME)" = "SLES" && sed -i 's,#include <panel.h>,#include <ncurses/panel.h>,' Modules/_curses_panel.c ; \
	./configure \
	    --prefix="" \
	    --enable-shared \
	    --enable-unicode=ucs4 \
	    $(PYTHON_ENABLE_OPTIMIZATIONS) \
	    LDFLAGS="-Wl,--rpath,$(OMD_ROOT)/lib"
	cd $(PYTHON3_DIR) ; $(MAKE) -j2
# Install python files (needed by dependent packages like mod_python,
# python-modules, ...) during compilation and install targets.
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	$(MAKE) -j1 -C $(PYTHON3_DIR) DESTDIR=$(PACKAGE_PYTHON3_DESTDIR) install
	$(TOUCH) $(PYTHON3_COMPILE)

$(PYTHON3_INSTALL): $(PYTHON3_BUILD) 
# Install python files (needed by dependent packages like mod_python,
# python-modules, ...) during compilation and install targets.
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	$(MAKE) -j1 -C $(PYTHON3_DIR) DESTDIR=$(DESTDIR)$(OMD_ROOT) install
# Fix python interpreter
	$(SED) -i '1s|^#!.*/python3\.7$$|#!/usr/bin/env python3|' $(addprefix $(DESTDIR)$(OMD_ROOT)/bin/,2to3-3.7 easy_install-3.7 idle3.7 pip3 pip3.7 pydoc3.7 pyvenv-3.7)
	$(TOUCH) $(PYTHON3_INSTALL)

Python3-clean:
	$(RM) -r $(DIR) $(BUILD_HELPER_DIR)/$(PYTHON3)* $(PACKAGE_PYTHON3_DESTDIR)
