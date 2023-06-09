# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include $(abs_top_srcdir)/defines.make

BUILD_CXX ="$(shell $(CXX) --version | head --lines=1)"
BUILD_DATE = "$(shell date -R)"
BUILD_HOSTNAME = "$(shell uname -n)"

JOBS ?= 6
DOXYGEN ?= doxygen
VALGRIND ?= $(shell valgrind --version > /dev/null 2>&1 && echo "valgrind --quiet --num-callers=30 --error-exitcode=42")
INCLUDES_DIR := includes
LIBS_DIR := libs

PACKAGE_ASIO := $(abs_top_srcdir)/third_party/asio
ASIO_VERSION := asio-1.24.0-patched
ASIO_INCLUDE := $(INCLUDES_DIR)/asio

LIBLIVESTATUS_PATH := $(abs_top_srcdir)/packages/livestatus
LIBLIVESTATUS_RUN := $(LIBLIVESTATUS_PATH)/run
LIBLIVESTATUS_INCLUDE := $(LIBLIVESTATUS_PATH)/include
LIBLIVESTATUS_SO := $(LIBLIVESTATUS_PATH)/build/src/liblivestatus.so
RE2_INCLUDE := $(LIBLIVESTATUS_PATH)/build/_deps/re2-src

PACKAGE_GOOGLETEST := $(abs_top_srcdir)/third_party/googletest
GOOGLETEST_VERSION := googletest-71140c3ca7-patched
GOOGLETEST_INCLUDE := $(INCLUDES_DIR)/googletest

.PHONY: unit-test tidy iwyu documentation documentation-quick

AM_CPPFLAGS = \
    -Iinclude \
    -I.. \
    -I$(LIBLIVESTATUS_INCLUDE) \
    -isystem $(ASIO_INCLUDE) \
    -DASIO_DISABLE_CONCEPTS \
    -DHAVE_RE2 \
    -DVERSION=\"$(VERSION)\" \
    -DBUILD_CXX=\"$(BUILD_CXX)\" \
    -DBUILD_DATE=\"$(BUILD_DATE)\" \
    -DBUILD_HOSTNAME=\"$(BUILD_HOSTNAME)\"

AM_LDFLAGS = \
    -static-libstdc++

bin_PROGRAMS = unixcat
noinst_PROGRAMS = test_neb

unixcat_SOURCES = unixcat.cc
$(unixcat_SOURCES): $(ASIO_INCLUDE)
unixcat_LDADD = -lpthread

test_neb_SOURCES = \
    test/DummyNagios.cc \
    test/TableQueryHelper.cc \
    test/test_CrashReport.cc \
    test/test_DictFilter.cc \
    test/test_MacroExpander.cc \
    test/test_utilities.cc
$(test_neb_SOURCES): $(ASIO_INCLUDE) $(GOOGLETEST_INCLUDE)
test_neb_CPPFLAGS = $(AM_CPPFLAGS) -I$(GOOGLETEST_INCLUDE)
test_neb_LDFLAGS = $(AM_LDFLAGS)
test_neb_LDADD = \
    liblivestatusneb.a \
    $(LIBLIVESTATUS_SO) \
    $(LIBS_DIR)/libgtest.a \
    $(LIBS_DIR)/libgtest_main.a \
    -lpthread

.PHONY: always-rebuild-livestatus-lib
$(LIBLIVESTATUS_SO): always-rebuild-livestatus-lib
	@echo Building lib livestatus...
	$(LIBLIVESTATUS_RUN) --build

unit-test: test_neb$(EXEEXT) $(LIBLIVESTATUS_SO)
	LD_LIBRARY_PATH=$(dir $(LIBLIVESTATUS_SO)) \
		GTEST_OUTPUT=xml:test_detail_livestatus.xml \
		$(VALGRIND) \
		./test_neb$(EXEEXT)

pkglib_LIBRARIES = liblivestatusneb.a

liblivestatusneb_a_CXXFLAGS = -fPIC
liblivestatusneb_a_CPPFLAGS = $(AM_CPPFLAGS)
liblivestatusneb_a_LD_FLAGS = $(AM_LDFLAGS)
liblivestatusneb_a_SOURCES = \
        src/MacroExpander.cc \
        src/NebCore.cc \
        src/NebHost.cc \
        src/NebService.cc \
        src/TimeperiodsCache.cc \
        src/module.cc
$(liblivestatusneb_a_SOURCES): $(ASIO_INCLUDE)

# Called during packaging. Copied from Makefile.am "all-am" to exclude noinst* targets
all-packaging-local: Makefile $(bin_PROGRAMS) $(pkglib_LIBRARIES) all-local

$(ASIO_INCLUDE): $(ASIO_VERSION)
	mkdir -p $@
	rsync -a --delete --exclude="Makefile.*" --exclude=.gitignore $</include/ $@
	touch $@

$(ASIO_VERSION): $(PACKAGE_ASIO)/$(ASIO_VERSION).tar.gz
	$(RM) -r $@
	tar xzf $<
	touch $@

$(GOOGLETEST_INCLUDE): $(GOOGLETEST_VERSION)/Makefile
# NOTE: We don't want the googletest files in our compile_commands.json!
	$(MAKE) -C $(GOOGLETEST_VERSION) install > /dev/null
	touch $(GOOGLETEST_INCLUDE) $(LIBS_DIR)/libgmock.a $(LIBS_DIR)/libgmock_main.a $(LIBS_DIR)/libgtest.a $(LIBS_DIR)/libgtest_main.a
# See: https://www.gnu.org/software/automake/manual/html_node/Multiple-Outputs.html
$(LIBS_DIR)/libgmock.a: $(GOOGLETEST_INCLUDE)
$(LIBS_DIR)/libgmock_main.a: $(LIBS_DIR)/libgmock.a
$(LIBS_DIR)/libgtest.a: $(LIBS_DIR)/libgmock_main.a
$(LIBS_DIR)/libgtest_main.a: $(LIBS_DIR)/libgtest.a

$(GOOGLETEST_VERSION)/Makefile: $(GOOGLETEST_VERSION)/CMakeLists.txt
	@cd $(GOOGLETEST_VERSION) && \
	cmake -DCMAKE_CXX_COMPILER=$$(echo "$(CXX)" | sed 's/ -.*//') \
        -DCMAKE_INSTALL_PREFIX=.. \
        -DCMAKE_INSTALL_INCLUDEDIR=$(GOOGLETEST_INCLUDE) \
        -DCMAKE_INSTALL_LIBDIR=libs \
        .
	touch $@

$(GOOGLETEST_VERSION)/CMakeLists.txt: $(PACKAGE_GOOGLETEST)/$(GOOGLETEST_VERSION).tar.gz
	$(RM) -r $(GOOGLETEST_VERSION)
	tar xzf $<
	touch $@

livestatus.o: $(liblivestatusneb_a_OBJECTS) $(LIBLIVESTATUS_SO)
# Note: libstdc++fs is only available as a static library, so we are lucky.
	$(CXXLINK) -shared $^ -lpthread $(AM_LDFLAGS) $(LIBLIVESTATUS_SO)
# To make sure we can dlopen() our NEB later. TODO: This should be part of the tests.
	$(CXX) $(liblivestatusneb_a_CXXFLAGS) $(CXXFLAGS) -Iinclude -I. -I.. -c test/NagiosMockup.cc -o test/NagiosMockup.o
	$(CXX) $(liblivestatusneb_a_CXXFLAGS) $(CXXFLAGS) test/NagiosMockup.o $@ -o test/NagiosMockup $(liblivestatusneb_a_LD_FLAGS) $(LIBLIVESTATUS_SO)
	$(RM) test/NagiosMockup

# NOTE: Using make's -B flag destroys all dependencies via the am--depfiles
# target, so we use a cruel sed hack below. :-P
compile_commands.json: Makefile $(unixcat_SOURCES) $(test_neb_SOURCES) $(liblivestatusneb_a_SOURCES)
	@$(MAKE) -nwk $$(echo " $^" | sed 's/ / -W /g') | $(top_srcdir)/scripts/run-pipenv run compiledb

tidy: compile_commands.json
	@python3 "$(shell command -v run-clang-tidy-$(CLANG_VERSION).py)" \
            -j "$(JOBS)" \
            -p=. \
            -quiet \
            $(CLANG_TIDY_EXTRA_ARGS) \
            $(FILES_TO_CHECK)

iwyu: compile_commands.json
	@python3 "$(shell command -v iwyu_tool.py)" \
            --jobs="$(JOBS)" \
            -p=. \
            --output-format=clang \
            $(FILES_TO_CHECK) -- \
            -Xiwyu --error \
            -Xiwyu "--mapping_file=$(realpath .iwyu/check_mk.imp)" \
            $(IWYU_EXTRA_ARGS)

documentation: compile_commands.json
	PLANTUML_JAR_PATH=$(PLANTUML_JAR_PATH) $(DOXYGEN) doc/Doxyfile
	$(RM) '$$depbase.Tpo'

documentation-quick: compile_commands.json
	( cat doc/Doxyfile; echo "CLANG_ASSISTED_PARSING=NO") | PLANTUML_JAR_PATH=$(PLANTUML_JAR_PATH) $(DOXYGEN) -

all-local: livestatus.o

install-data-local:
	$(mkinstalldirs) $(DESTDIR)$(pkglibdir)
	$(INSTALL_PROGRAM) livestatus.o $(DESTDIR)$(pkglibdir)
	rm -f $(DESTDIR)$(pkglibdir)/liblivestatusneb.a

clean-local:
	rm -rf *~ compile_commands.json test_detail.xml html $(INCLUDES_DIR) $(LIBS_DIR) $(ASIO_VERSION) $(GOOGLETEST_VERSION)
