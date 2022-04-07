# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include $(abs_top_srcdir)/defines.make

DOXYGEN ?= doxygen
PLANTUTML_VERSION ?= 1.2020.16
IWYU_TOOL ?= python3 $(abs_top_srcdir)/scripts/iwyu_tool.py
RUN_CLANG_TIDY ?= \
    python3 $(abs_top_srcdir)/scripts/run-clang-tidy.py \
        -clang-tidy-binary=clang-tidy-$(CLANG_VERSION) \
        -clang-apply-replacements-binary=clang-apply-replacements-$(CLANG_VERSION)
VALGRIND ?= $(shell valgrind --version > /dev/null 2>&1 && echo "valgrind --quiet --num-callers=30 --error-exitcode=42")
INCLUDES_DIR := includes
LIBS_DIR := libs

PACKAGE_ASIO := $(abs_top_srcdir)/omd/packages/asio
ASIO_VERSION := asio-asio-1-18-2
ASIO_INCLUDE := $(INCLUDES_DIR)/asio

RRDTOOL_VERSION := rrdtool-1.7.2
RRDTOOL_PATH := $(abs_top_srcdir)/omd/build/intermediate_install/$(RRDTOOL_VERSION)
RRDTOOL_BUILD_LOG := $(RRDTOOL_PATH)/build.log
RRDTOOL_LD_FLAGS := -lrrd -L$(RRDTOOL_PATH)/lib
RRDTOOL_CPPFLAGS := -I$(RRDTOOL_PATH)/include

PACKAGE_GOOGLETEST := $(abs_top_srcdir)/omd/packages/googletest
GOOGLETEST_VERSION := googletest-f3ef7e173f
GOOGLETEST_INCLUDE := $(INCLUDES_DIR)/googletest

.PHONY: unit-test tidy iwyu documentation documentation-quick

AM_CPPFLAGS = \
    -I.. \
    -isystem $(ASIO_INCLUDE) \
    -DASIO_DISABLE_CONCEPTS \
    @RE2_CPPFLAGS@

AM_LDFLAGS = \
    -static-libstdc++ \
    @RE2_LDFLAGS@

bin_PROGRAMS = unixcat
noinst_PROGRAMS = test_neb

unixcat_SOURCES = unixcat.cc
$(unixcat_SOURCES): $(ASIO_INCLUDE)
unixcat_LDADD = -lpthread

test_neb_SOURCES = \
    test/DummyNagios.cc \
    test/TableQueryHelper.cc \
    test/test_AttributeListColumn.cc \
    test/test_BlobColumn.cc \
    test/test_BoolColumn.cc \
    test/test_CrashReport.cc \
    test/test_DictFilter.cc \
    test/test_DoubleColumn.cc \
    test/test_FileSystemHelper.cc \
    test/test_IntColumn.cc \
    test/test_ListColumn.cc \
    test/test_LogEntry.cc \
    test/test_MacroExpander.cc \
    test/test_Metric.cc \
    test/test_Queue.cc \
    test/test_RegExp.cc \
    test/test_StringColumn.cc \
    test/test_StringUtil.cc \
    test/test_Table.cc \
    test/test_TimeColumn.cc \
    test/test_utilities.cc
$(test_neb_SOURCES): $(ASIO_INCLUDE) $(GOOGLETEST_INCLUDE) $(RRDTOOL_VERSION)
test_neb_CPPFLAGS = \
    $(AM_CPPFLAGS) \
    -I$(GOOGLETEST_INCLUDE) \
    $(RRDTOOL_CPPFLAGS)
test_neb_LDFLAGS = \
    $(AM_LDFLAGS) \
    $(RRDTOOL_LD_FLAGS)
test_neb_LDADD = \
    liblivestatus.a \
    -lstdc++fs \
    @RE2_LIBS@ \
    $(LIBS_DIR)/libgtest.a \
    $(LIBS_DIR)/libgtest_main.a \
    -lrrd \
    -lpthread

unit-test: test_neb$(EXEEXT)
	GTEST_OUTPUT=xml $(VALGRIND) ./test_neb$(EXEEXT)

pkglib_LIBRARIES = liblivestatus.a

liblivestatus_a_CXXFLAGS = -fPIC
liblivestatus_a_CPPFLAGS = \
    $(AM_CPPFLAGS) \
    $(RRDTOOL_CPPFLAGS)
liblivestatus_a_LD_FLAGS = \
    $(AM_LDFLAGS) \
    $(RRDTOOL_LD_FLAGS)
liblivestatus_a_SOURCES = \
        AndingFilter.cc \
        AttributeListColumn.cc \
        Average.cc \
        Column.cc \
        ColumnFilter.cc \
        CommentRenderer.cc \
        CountAggregator.cc \
        CrashReport.cc \
        DictFilter.cc \
        DoubleFilter.cc \
        DowntimeRenderer.cc \
        DynamicEventConsoleReplicationColumn.cc \
        DynamicFileColumn-impl.cc \
        EventConsoleConnection.cc \
        FileSystemHelper.cc \
        Filter.cc \
        HostListRenderer.cc \
        HostListState.cc \
        HostServiceState.cc \
        InputBuffer.cc \
        IntFilter.cc \
        ListFilter.cc \
        LogCache.cc \
        LogEntry.cc \
        Logfile.cc \
        Logger.cc \
        LogwatchList.cc \
        MacroExpander.cc \
        Metric.cc \
        NagiosCore.cc \
        NullColumn.cc \
        OringFilter.cc \
        OutputBuffer.cc \
        PerfdataAggregator.cc \
        POSIXUtils.cc \
        Query.cc \
        RegExp.cc \
        Renderer.cc \
        RendererBrokenCSV.cc \
        RendererCSV.cc \
        RendererJSON.cc \
        RendererPython.cc \
        RendererPython3.cc \
        RRDColumn.cc \
        ServiceGroupMembersColumn.cc \
        ServiceListRenderer.cc \
        ServiceListState.cc \
        StatsColumn.cc \
        Store.cc \
        StringFilter.cc \
        StringUtils.cc \
        Table.cc \
        TableColumns.cc \
        TableCommands.cc \
        TableComments.cc \
        TableContactGroups.cc \
        TableContacts.cc \
        TableCrashReports.cc \
        TableDowntimes.cc \
        TableEventConsole.cc \
        TableEventConsoleEvents.cc \
        TableEventConsoleHistory.cc \
        TableEventConsoleReplication.cc \
        TableEventConsoleRules.cc \
        TableEventConsoleStatus.cc \
        TableHostGroups.cc \
        TableHosts.cc \
        TableHostsByGroup.cc \
        TableLog.cc \
        TableServiceGroups.cc \
        TableServices.cc \
        TableServicesByGroup.cc \
        TableServicesByHostGroup.cc \
        TableStateHistory.cc \
        TableStatus.cc \
        TableTimeperiods.cc \
        TimeFilter.cc \
        TimeperiodsCache.cc \
        Triggers.cc \
        User.cc \
        global_counters.cc \
        mk_inventory.cc \
        mk_logwatch.cc \
        module.cc \
        opids.cc \
        pnp4nagios.cc \
        strutil.cc
$(liblivestatus_a_SOURCES): $(ASIO_INCLUDE) $(RRDTOOL_VERSION)

# Called during packaging. Copied from Makefile.am "all-am" to exclude noinst* targets
all-packaging-local: Makefile $(bin_PROGRAMS) $(pkglib_LIBRARIES) all-local

$(ASIO_INCLUDE): $(ASIO_VERSION)
	mkdir -p $@
	rsync -a --delete --exclude=Makefile.am --exclude=.gitignore $</asio/include/ $@
	touch $@

$(ASIO_VERSION): $(PACKAGE_ASIO)/$(ASIO_VERSION).tar.gz $(PACKAGE_ASIO)/asio.diff
	$(RM) -r $@
	tar xzf $<
	patch -p0 < $(PACKAGE_ASIO)/asio.diff
	touch $@

$(RRDTOOL_VERSION):
# TODO: This is specialized for OMD environments. We need make this automatically detect the
# OMD scenario and perform specific things for OMD and other things for rrdtool standalone.
	@echo Building rrdtool library...
# Building rrdtool with modern compilers results in *tons* of warnings, which
# would totally hide any output of our own stuff, so we write it to a log file
# in case something goes seriously wrong.
	mkdir -p $$(dirname $(RRDTOOL_BUILD_LOG))
	LANG=C make -j4 -C $$(dirname $$(dirname $$(dirname $(RRDTOOL_PATH)))) rrdtool-build-library >$(RRDTOOL_BUILD_LOG) 2>&1
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

$(GOOGLETEST_VERSION)/CMakeLists.txt: $(PACKAGE_GOOGLETEST)/$(GOOGLETEST_VERSION).tar.gz $(PACKAGE_GOOGLETEST)/googletest.diff
	$(RM) -r $(GOOGLETEST_VERSION)
	tar xzf $<
	patch -p0 < $(PACKAGE_GOOGLETEST)/googletest.diff
	touch $@

livestatus.o: $(liblivestatus_a_OBJECTS)
# Note: libstdc++fs is only available as a static library, so we are lucky. For
# RE2 we make sure that this is the case, too.
	$(CXXLINK) -shared $^ -lstdc++fs -lpthread $(AM_LDFLAGS) @RE2_LIBS@ $(RRDTOOL_LD_FLAGS)
# To make sure we can dlopen() our NEB later
	$(CXX) $(liblivestatus_a_CXXFLAGS) $(CXXFLAGS) -I. -I../.. -I.. -c NagiosMockup.cc -o NagiosMockup.o
	$(CXX) $(liblivestatus_a_CXXFLAGS) $(CXXFLAGS) NagiosMockup.o $@ -o NagiosMockup $(liblivestatus_a_LD_FLAGS)
	$(RM) NagiosMockup

# NOTE: Using make's -B flag destroys all dependencies via the am--depfiles
# target, so we use a cruel sed hack below. :-P
compile_commands.json: $(unixcat_SOURCES) $(test_neb_SOURCES) $(liblivestatus_a_SOURCES)
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
	$(IWYU_TOOL) -j4 --output-format=clang -p . $(FILES_TO_CHECK) -- $(IWYU_EXTRA_ARGS) -Xiwyu --mapping_file=$(abs_top_srcdir)/livestatus/iwyu-mappings/check_mk.imp

documentation: compile_commands.json doc/plantuml.jar
	$(DOXYGEN) doc/Doxyfile
	$(RM) '$$depbase.Tpo'

documentation-quick: compile_commands.json doc/plantuml.jar
	( cat doc/Doxyfile; echo "CLANG_ASSISTED_PARSING=NO") | $(DOXYGEN) -

doc/plantuml.jar:
	wget https://master.dl.sourceforge.net/project/plantuml/$(PLANTUTML_VERSION)/plantuml.$(PLANTUTML_VERSION).jar --quiet --output-document=$@ || { $(RM) $@; exit 1; }

all-local: livestatus.o

install-data-local:
	$(mkinstalldirs) $(DESTDIR)$(pkglibdir)
	$(INSTALL_PROGRAM) livestatus.o $(DESTDIR)$(pkglibdir)
	rm -f $(DESTDIR)$(pkglibdir)/liblivestatus.a

clean-local:
	rm -rf *~ compile_commands.json test_detail.xml html $(INCLUDES_DIR) $(LIBS_DIR) $(ASIO_VERSION) $(GOOGLETEST_VERSION)
