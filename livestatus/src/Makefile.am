# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include $(abs_top_srcdir)/defines.make

DOXYGEN ?= doxygen
PLANTUTML_VERSION ?= 1.2022.12
IWYU_TOOL ?= python3 $(shell command -v iwyu_tool.py)
RUN_CLANG_TIDY ?= python3 $(shell command -v run-clang-tidy-$(CLANG_VERSION).py)
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
    -I.. \
    -I$(LIBLIVESTATUS_INCLUDE) \
    -isystem $(ASIO_INCLUDE) \
    -DASIO_DISABLE_CONCEPTS \
    -DHAVE_RE2

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
    test/test_Table.cc \
    test/test_utilities.cc
$(test_neb_SOURCES): $(ASIO_INCLUDE) $(GOOGLETEST_INCLUDE)
test_neb_CPPFLAGS = $(AM_CPPFLAGS) -I$(GOOGLETEST_INCLUDE)
test_neb_LDFLAGS = $(AM_LDFLAGS)
test_neb_LDADD = \
    liblivestatusneb.a \
    -lstdc++fs \
    $(LIBLIVESTATUS_SO) \
    $(LIBS_DIR)/libgtest.a \
    $(LIBS_DIR)/libgtest_main.a \
    -lrrd \
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
        MacroExpander.cc \
        NagiosCore.cc \
        NebHost.cc \
        NebService.cc \
        Store.cc \
        TableEventConsoleEvents.cc \
        TableEventConsoleHistory.cc \
        TableLog.cc \
        TableServicesByGroup.cc \
        TableServicesByHostGroup.cc \
        TableStateHistory.cc \
        TimeperiodsCache.cc \
        module.cc \
        pnp4nagios.cc
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
	$(CXXLINK) -shared $^ -lstdc++fs -lpthread $(AM_LDFLAGS) $(LIBLIVESTATUS_SO)
# To make sure we can dlopen() our NEB later
	$(CXX) $(liblivestatusneb_a_CXXFLAGS) $(CXXFLAGS) -I. -I../.. -I.. -c NagiosMockup.cc -o NagiosMockup.o
	$(CXX) $(liblivestatusneb_a_CXXFLAGS) $(CXXFLAGS) NagiosMockup.o $@ -o NagiosMockup $(liblivestatusneb_a_LD_FLAGS) $(LIBLIVESTATUS_SO)
	$(RM) NagiosMockup

# NOTE: Using make's -B flag destroys all dependencies via the am--depfiles
# target, so we use a cruel sed hack below. :-P
compile_commands.json: Makefile $(unixcat_SOURCES) $(test_neb_SOURCES) $(liblivestatusneb_a_SOURCES)
	@$(MAKE) -nwk $$(echo " $^" | sed 's/ / -W /g') | $(top_srcdir)/scripts/run-pipenv run compiledb

tidy: compile_commands.json
	@echo clang-tidy-$(CLANG_VERSION) information start ===========================================
	@which clang-tidy-$(CLANG_VERSION)
	@clang-tidy-$(CLANG_VERSION) $(CLANG_TIDY_EXTRA_ARGS) --version
	@clang-tidy-$(CLANG_VERSION) $(CLANG_TIDY_EXTRA_ARGS) --extra-arg=-v dummy.cc 1> /dev/null || true
	@echo clang-tidy-$(CLANG_VERSION) information end =============================================
	$(RUN_CLANG_TIDY) $(CLANG_TIDY_EXTRA_ARGS) -quiet -j6 $(FILES_TO_CHECK)

iwyu: compile_commands.json
	@echo include-what-you-use information start ====================================
	@which include-what-you-use
	@include-what-you-use $(IWYU_EXTRA_ARGS) --version
	@include-what-you-use $(IWYU_EXTRA_ARGS) -v 2>&1 | grep -v "error: unable to handle compilation" || true
	@echo include-what-you-use information end ======================================
	$(IWYU_TOOL) -j4 --output-format=clang -p . $(FILES_TO_CHECK) -- $(IWYU_EXTRA_ARGS) -Xiwyu --error -Xiwyu --mapping_file=$(abs_top_srcdir)/livestatus/iwyu-mappings/check_mk.imp


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
