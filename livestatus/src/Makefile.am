# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

CLANG_VERSION ?= 10

CPPCHECK ?= cppcheck
CPPCHECK_NEB_RESULT ?= cppcheck-result.xml
DOXYGEN ?= doxygen
PLANTUTML_VERSION ?= 1.2020.16
IWYU_TOOL ?= $(abs_top_srcdir)/scripts/iwyu_tool
RUN_CLANG_TIDY ?= \
    $(abs_top_srcdir)/scripts/run-clang-tidy.py \
        -clang-tidy-binary=clang-tidy-$(CLANG_VERSION) \
        -clang-apply-replacements-binary=clang-apply-replacements-$(CLANG_VERSION)
VALGRIND ?= $(shell valgrind --version > /dev/null 2>&1 && echo "valgrind --quiet")
INCLUDES_DIR := includes
LIBS_DIR := libs

PACKAGE_ASIO := $(abs_top_srcdir)/omd/packages/asio
ASIO_VERSION := asio-asio-1-18-0
ASIO_INCLUDE := $(INCLUDES_DIR)/asio

RRDTOOL_VERSION := rrdtool-1.7.1
RRDTOOL_SRC_DIR := $(abs_top_srcdir)/omd/build/package_build/$(RRDTOOL_VERSION)/src
RRDTOOL_BUILD_LOG := $(RRDTOOL_SRC_DIR)/build.log
RRDTOOL_LD_FLAGS := -lrrd -L$(RRDTOOL_SRC_DIR)/.libs
RRDTOOL_CPPFLAGS := -I$(RRDTOOL_SRC_DIR)

PACKAGE_GOOGLETEST := $(abs_top_srcdir)/omd/packages/googletest
GOOGLETEST_VERSION := googletest-07d4a6e93d
GOOGLETEST_INCLUDE := $(INCLUDES_DIR)/googletest

.PHONY: unit-test tidy iwyu cppcheck cppcheck-xml documentation

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
    test/test_CrashReport.cc \
    test/test_CustomVarsDictFilter.cc \
    test/test_FileSystemHelper.cc \
    test/test_LogEntry.cc \
    test/test_MacroExpander.cc \
    test/test_Metric.cc \
    test/test_Queue.cc \
    test/test_RegExp.cc \
    test/test_StringUtil.cc \
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
        AttributeListAsIntColumn.cc \
        AttributeListColumn.cc \
        Average.cc \
        BlobColumn.cc \
        Column.cc \
        ColumnFilter.cc \
        CommentColumn.cc \
        ContactGroupsColumn.cc \
        CountAggregator.cc \
        CrashReport.cc \
        CustomVarsDictColumn.cc \
        CustomVarsDictFilter.cc \
        CustomVarsExplicitColumn.cc \
        CustomVarsNamesColumn.cc \
        CustomVarsValuesColumn.cc \
        DoubleColumn.cc \
        DoubleFilter.cc \
        DowntimeColumn.cc \
        DowntimeOrComment.cc \
        DowntimesOrComments.cc \
        DynamicColumn.cc \
        DynamicEventConsoleReplicationColumn.cc \
        DynamicFileColumn-impl.cc \
        DynamicRRDColumn.cc \
        EventConsoleConnection.cc \
        FileColumn-impl.cc \
        FileSystemHelper.cc \
        Filter.cc \
        HostContactsColumn.cc \
        HostGroupsColumn.cc \
        HostListColumn.cc \
        HostListStateColumn.cc \
        HostServiceState.cc \
        HostSpecialDoubleColumn.cc \
        HostSpecialIntColumn.cc \
        InputBuffer.cc \
        IntColumn.cc \
        IntFilter.cc \
        ListColumn.cc \
        ListFilter.cc \
        LogCache.cc \
        LogEntry.cc \
        LogEntryStringColumn.cc \
        Logfile.cc \
        Logger.cc \
        LogwatchListColumn.cc \
        MacroExpander.cc \
        Metric.cc \
        NagiosCore.cc \
        NullColumn.cc \
        OringFilter.cc \
        OutputBuffer.cc \
        PerfdataAggregator.cc \
        Query.cc \
        RegExp.cc \
        Renderer.cc \
        RendererBrokenCSV.cc \
        RendererCSV.cc \
        RendererJSON.cc \
        RendererPython.cc \
        RendererPython3.cc \
        RRDColumn.cc \
        ServiceContactsColumn.cc \
        ServiceGroupMembersColumn.cc \
        ServiceGroupsColumn.cc \
        ServiceListColumn.cc \
        ServiceListStateColumn.cc \
        ServiceSpecialDoubleColumn.cc \
        ServiceSpecialIntColumn.cc \
        StatsColumn.cc \
        Store.cc \
        StringColumn.cc \
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
        TimeColumn.cc \
        TimeFilter.cc \
        TimeperiodsCache.cc \
        Triggers.cc \
        auth.cc \
        global_counters.cc \
        mk_inventory.cc \
        mk_logwatch.cc \
        module.cc \
        opids.cc \
        pnp4nagios.cc \
        strutil.cc
$(liblivestatus_a_SOURCES): $(ASIO_INCLUDE) $(RRDTOOL_VERSION)

$(ASIO_INCLUDE): $(ASIO_VERSION)
	mkdir -p $(ASIO_INCLUDE)
	rsync -a --delete --exclude=Makefile.am --exclude=.gitignore $(ASIO_VERSION)/asio/include/ $(ASIO_INCLUDE)
	patch -p0 < $(PACKAGE_ASIO)/asio.diff
	touch $@

$(ASIO_VERSION): $(PACKAGE_ASIO)/$(ASIO_VERSION).tar.gz
	$(RM) -r $@
	tar xzf $<
	touch $@

$(RRDTOOL_VERSION):
# TODO: This is specialized for OMD environments. We need make this automatically detect the
# OMD scenario and perform specific things for OMD and other things for rrdtool standalone.
	@echo Building rrdtool library...
# Building rrdtool with modern compilers results in *tons* of warnings, which
# would totally hide any output of our own stuff, so we write it to a log file
# in case something goes seriously wrong.
	mkdir -p $$(dirname $(RRDTOOL_BUILD_LOG))
	LANG=C make -j4 -C $$(dirname $$(dirname $$(dirname $$(dirname $(RRDTOOL_SRC_DIR))))) rrdtool-build-library >$(RRDTOOL_BUILD_LOG) 2>&1
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
	cmake -DCMAKE_CXX_COMPILER=$(CXX) \
        -DCMAKE_INSTALL_PREFIX=.. \
        -DCMAKE_INSTALL_INCLUDEDIR=$(GOOGLETEST_INCLUDE) \
        -DCMAKE_INSTALL_LIBDIR=libs \
        .
	touch $@

$(GOOGLETEST_VERSION)/CMakeLists.txt: $(PACKAGE_GOOGLETEST)/$(GOOGLETEST_VERSION).tar.gz
	$(RM) -r $(GOOGLETEST_VERSION)
	tar xzf $<
	touch $@

livestatus.o: $(liblivestatus_a_OBJECTS)
# Note: libstdc++fs is only available as a static library, so we are lucky. For
# RE2 we make sure that this is the case, too.
	$(CXXLINK) -shared $^ -lstdc++fs -lpthread $(AM_LDFLAGS) @RE2_LIBS@ $(RRDTOOL_LD_FLAGS)
# To make sure we can dlopen() our NEB later
	$(CXX) $(liblivestatus_a_CXXFLAGS) $(CXXFLAGS) -c NagiosMockup.cc -o NagiosMockup.o
	$(CXX) $(liblivestatus_a_CXXFLAGS) $(CXXFLAGS) NagiosMockup.o $@ -o NagiosMockup $(liblivestatus_a_LD_FLAGS)
	$(RM) NagiosMockup

# NOTE: Using make's -B flag destroys all dependencies via the am--depfiles
# target, so we use a cruel sed hack below. :-P
compile_commands.json: $(unixcat_SOURCES) $(test_neb_SOURCES) $(liblivestatus_a_SOURCES)
	@$(MAKE) -nwk $$(echo " $^" | sed 's/ / -W /g') | $(top_srcdir)/scripts/run-pipenv run compiledb

tidy: compile_commands.json
	$(RUN_CLANG_TIDY) -quiet -j6 $(FILES_TO_CHECK)

iwyu: compile_commands.json
	$(IWYU_TOOL) --output-format=clang -p . $(FILES_TO_CHECK) -- -Xiwyu --mapping_file=$(abs_top_srcdir)/livestatus/iwyu-mappings/check_mk.imp

# NOTE: cppcheck seems to ignore files on the command line when --project=... is given.  :-P
cppcheck: compile_commands.json
	$(CPPCHECK) -UCMC --enable=all --suppressions-list=$(abs_top_srcdir)/.cppcheck-suppressions --inline-suppr --project=compile_commands.json --quiet --template=gcc --error-exitcode=2

# We need to mangle the result a bit to make Jenkins' Cppcheck plugin happy
cppcheck-xml: compile_commands.json
	$(CPPCHECK) -UCMC --enable=all --suppressions-list=$(abs_top_srcdir)/.cppcheck-suppressions --inline-suppr --project=compile_commands.json --quiet --template=gcc --xml --xml-version=2 2> $(CPPCHECK_NEB_RESULT)
	sed -i "s%\\(<location.* file=\"\\)\\([^/]\\)%\\1$(subdir)/\\2%" $(CPPCHECK_NEB_RESULT)

documentation: doc/plantuml.jar
	$(DOXYGEN) doc/Doxyfile

doc/plantuml.jar:
	wget https://master.dl.sourceforge.net/project/plantuml/$(PLANTUTML_VERSION)/plantuml.$(PLANTUTML_VERSION).jar -O $@

all-local: livestatus.o

install-data-local:
	$(mkinstalldirs) $(DESTDIR)$(pkglibdir)
	$(INSTALL_PROGRAM) livestatus.o $(DESTDIR)$(pkglibdir)
	rm -f $(DESTDIR)$(pkglibdir)/liblivestatus.a

clean-local:
	rm -rf *~ compile_commands.json $(CPPCHECK_NEB_RESULT) test_detail.xml html $(INCLUDES_DIR) $(LIBS_DIR) $(ASIO_VERSION) $(GOOGLETEST_VERSION)
