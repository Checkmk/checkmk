include ../../Makefile.omd

NAME     = Python
VERSION  = 2.7.16
DIR      = $(NAME)-$(VERSION)

.PHONY: build install skel clean

build: bin/gcc bin/g++
	tar xzf $(DIR).tgz

	set -e ; for p in patches/*.dif ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(DIR) < $$p ; \
	done

# Things are a bit tricky here: For PGO/LTO we need a rather recent compiler,
# but we don't want to bake paths to our build system into _sysconfigdata and
# friends. Workaround: Find a recent compiler to be used for building and make a
# symlink for it under a generic name. :-P Furthermore, the build with PGO/LTO
# enables is mainly sequential, so a high build parallelism doesn't really
# help. Therefore we use just -j2.
	@PATH="$(abspath bin):$$PATH" ; \
	if  gcc -Xlinker --help | grep -q -e "-plugin" ; then \
	    OPTI="--enable-optimizations" ; \
	else \
	    OPTI="" ; \
	fi ; \
	cd $(DIR) ; \
	test "$(DISTRO_NAME)" = "SLES" && sed -i 's,#include <panel.h>,#include <ncurses/panel.h>,' Modules/_curses_panel.c ; \
	./configure \
	    --prefix="" \
	    --enable-shared \
	    --enable-unicode=ucs4 \
	    $$OPTI \
	    LDFLAGS="-Wl,--rpath,$(OMD_ROOT)/lib" ; \
	$(MAKE) -j2

# Install python files (needed by dependent packages like mod_python,
# python-modules, ...) during compilation and install targets.
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	PATH="$(abspath bin):$$PATH" ; $(MAKE) -j1 -C $(DIR) DESTDIR=$(PACKAGE_PYTHON_DESTDIR) install
	$(MAKE) sitecustomize.pyc

sitecustomize.pyc: sitecustomize.py
	export PYTHONPATH="$$PYTHONPATH:$(PACKAGE_PYTHON_PYTHONPATH)" ; \
	export LDFLAGS="$(PACKAGE_PYTHON_LDFLAGS)" ; \
	export LD_LIBRARY_PATH="$(PACKAGE_PYTHON_LD_LIBRARY_PATH)" ; \
	$(PACKAGE_PYTHON_EXECUTABLE) -m py_compile sitecustomize.py

# The compiler detection code below is basically what part of AC_PROC_CXX does.
bin/gcc:
	@CC="" ; \
	for PROG in gcc-9 clang-8 gcc-8 clang-7 gcc-7 clang-6.0 clang-5.0 gcc-6 clang-4.0 gcc-5 clang-3.9 clang-3.8 clang-3.7 clang-3.6 clang-3.5 gcc-4.9 gcc clang; do \
	    echo -n "checking for $$PROG... "; SAVED_IFS=$$IFS; IFS=: ; \
	    for DIR in $$PATH; do \
	        IFS=$$SAVED_IFS ; \
	        test -z "$$DIR" && DIR=. ; \
	        ABS_PROG="$$DIR/$$PROG" ; \
	        test -x "$$ABS_PROG" && { CC="$$ABS_PROG"; echo "$$CC"; break 2; } ; \
	    done ; \
	    echo "no"; IFS=$$SAVED_IFS ; \
	done ; \
	test -z "$$CC" && { echo "error: no C compiler found" >&2 ; exit 1; } ; \
	mkdir -p bin ; \
	rm -f bin/gcc ; \
	ln -s "$$CC" bin/gcc

bin/g++:
	@CXX="" ; \
	for PROG in g++-9 clang++-8 g++-8 clang++-7 g++-7 clang++-6.0 clang++-5.0 g++ clang++; do \
	    echo -n "checking for $$PROG... "; SAVED_IFS=$$IFS; IFS=: ; \
	    for DIR in $$PATH; do \
	        IFS=$$SAVED_IFS ; \
	        test -z "$$DIR" && DIR=. ; \
	        ABS_PROG="$$DIR/$$PROG" ; \
	        test -x "$$ABS_PROG" && { CXX="$$ABS_PROG"; echo "$$CXX"; break 2; } ; \
	    done ; \
	    echo "no"; IFS=$$SAVED_IFS ; \
	done ; \
	test -z "$$CXX" && { echo "error: no C++ compiler found" >&2 ; exit 1; } ; \
	mkdir -p bin ; \
	rm -f bin/g++ ; \
	ln -s "$$CXX" bin/g++

install: bin/gcc bin/g++
# NOTE: -j1 seems to be necessary when --enable-optimizations is used
	PATH="$(abspath bin):$$PATH" ; $(MAKE) -j1 -C $(DIR) DESTDIR=$(DESTDIR)$(OMD_ROOT) install
# Cleanup some unused stuff
	rm $(DESTDIR)$(OMD_ROOT)/bin/idle
	rm $(DESTDIR)$(OMD_ROOT)/bin/smtpd.py
# Fix python interpreter for kept scripts
	sed -i "1s|^#!.*python|#!$(OMD_ROOT)/bin/python|" \
	    $(DESTDIR)$(OMD_ROOT)/bin/pydoc \
	    $(DESTDIR)$(OMD_ROOT)/bin/python2.7-config \
	    $(DESTDIR)$(OMD_ROOT)/bin/2to3
	install -m 644 sitecustomize.py sitecustomize.pyc $(DESTDIR)$(OMD_ROOT)/lib/python2.7/

skel:

clean:
	rm -rf $(DIR) bin build $(PACKAGE_PYTHON_DESTDIR) sitecutomize.pyc

upstream:
	git rm Python-*.tgz
	wget https://www.python.org/ftp/python/$(VERSION)/Python-$(VERSION).tgz
	git add Python-$(VERSION).tgz
