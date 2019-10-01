# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

CLANG_VERSION ?= 8

CPPCHECK ?= cppcheck
DOXYGEN ?= doxygen
IWYU_TOOL ?= iwyu_tool
RUN_CLANG_TIDY ?= \
    $(abs_top_srcdir)/scripts/run-clang-tidy.py \
        -clang-tidy-binary=clang-tidy-$(CLANG_VERSION) \
        -clang-apply-replacements-binary=clang-apply-replacements-$(CLANG_VERSION)
PIPENV := LANG=C PIPENV_VENV_IN_PROJECT=true PIPENV_PIPFILE=$(abs_top_srcdir)/virtual-envs/2.7/Pipfile pipenv

bin_PROGRAMS = unixcat

unixcat_SOURCES = unixcat.cc
unixcat_LDADD = -lpthread
unixcat_LDFLAGS = -static-libstdc++

pkglib_LIBRARIES = liblivestatus.a

liblivestatus_a_SOURCES = \
        AndingFilter.cc \
        AttributeListAsIntColumn.cc \
        AttributeListColumn.cc \
        Average.cc \
        BlobColumn.cc \
        ClientQueue.cc \
        Column.cc \
        ColumnFilter.cc \
        ColumnsColumn.cc \
        CommentColumn.cc \
        ContactGroupsColumn.cc \
        ContactGroupsMemberColumn.cc \
        CountAggregator.cc \
        CustomTimeperiodColumn.cc \
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
        DynamicLogwatchFileColumn.cc \
        EventConsoleConnection.cc \
        Filter.cc \
        HostContactsColumn.cc \
        HostFileColumn.cc \
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
        Logfile.cc \
        Logger.cc \
        LogwatchListColumn.cc \
        MetricsColumn.cc \
        NagiosCore.cc \
        NullColumn.cc \
        OffsetBoolColumn.cc \
        OffsetDoubleColumn.cc \
        OffsetIntColumn.cc \
        OffsetPerfdataColumn.cc \
        OffsetSStringColumn.cc \
        OffsetStringColumn.cc \
        OffsetStringHostMacroColumn.cc \
        OffsetStringMacroColumn.cc \
        OffsetStringServiceMacroColumn.cc \
        OffsetTimeColumn.cc \
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
        ServiceContactsColumn.cc \
        ServiceGroupMembersColumn.cc \
        ServiceGroupsColumn.cc \
        ServiceListColumn.cc \
        ServiceListStateColumn.cc \
        ServiceSpecialDoubleColumn.cc \
        ServiceSpecialIntColumn.cc \
        StatsColumn.cc \
        StatusSpecialIntColumn.cc \
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
        TimeperiodColumn.cc \
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

.PHONY: tidy iwyu cppcheck cppcheck-xml documentation

liblivestatus_a_CPPFLAGS = -I.. @BOOST_CPPFLAGS@ @RE2_CPPFLAGS@
liblivestatus_a_CXXFLAGS = -fPIC

livestatus.o: $(liblivestatus_a_OBJECTS)
# Note: libstdc++fs is only available as a static library, so we are lucky. For
# RE2 we make sure that this is the case, too.
	$(CXXLINK) -shared $^ -lstdc++fs -lpthread -static-libstdc++ @BOOST_LDFLAGS@ @BOOST_ASIO_LIB@ @RE2_LDFLAGS@ @RE2_LIBS@
# To make sure we can dlopen() our NEB later
	$(CXX) $(liblivestatus_a_CXXFLAGS) $(CXXFLAGS) -c NagiosMockup.cc -o NagiosMockup.o
	$(CXX) $(liblivestatus_a_CXXFLAGS) $(CXXFLAGS) NagiosMockup.o $@ -o NagiosMockup
	$(RM) NagiosMockup

compile_commands.json: Makefile $(wildcard *.cc *.h)
	$(MAKE) -C $(top_srcdir) .venv
	$(PIPENV) --venv
	$(PIPENV) run compiledb --no-build make

tidy: compile_commands.json
	$(RUN_CLANG_TIDY) -quiet -j6 $(FILES_TO_CHECK)

iwyu: compile_commands.json
	$(IWYU_TOOL) --output-format=clang -p . $(FILES_TO_CHECK) -- --mapping_file=$(abs_top_srcdir)/livestatus/iwyu-mappings/check_mk.imp

# NOTE: cppcheck seems to ignore files on the command line when --project=... is given.  :-P
cppcheck: compile_commands.json
	$(CPPCHECK) -UCMC --enable=all --suppressions-list=$(abs_top_srcdir)/.cppcheck-suppressions --inline-suppr --project=compile_commands.json --quiet --template=gcc

# We need to mangle the result a bit to make Jenkins' Cppcheck plugin happy
cppcheck-xml: compile_commands.json
	$(CPPCHECK) -UCMC --enable=all --suppressions-list=$(abs_top_srcdir)/.cppcheck-suppressions --inline-suppr --project=compile_commands.json --quiet --template=gcc --xml --xml-version=2 2> cppcheck-result.xml
	sed -i "s%\\(<location.* file=\"\\)\\([^/]\\)%\\1$(subdir)/\\2%" cppcheck-result.xml

documentation:
	$(DOXYGEN) doc/Doxyfile

all-local: livestatus.o

install-data-local:
	$(mkinstalldirs) $(DESTDIR)$(pkglibdir)
	$(INSTALL_PROGRAM) livestatus.o $(DESTDIR)$(pkglibdir)
	rm -f $(DESTDIR)$(pkglibdir)/liblivestatus.a

clean-local:
	rm -rf *~ compile_commands.json cppcheck-result.xml html
