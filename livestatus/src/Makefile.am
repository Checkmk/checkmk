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

bin_PROGRAMS = unixcat

unixcat_SOURCES = unixcat.cc
unixcat_LDADD = -lpthread
unixcat_LDFLAGS = -static-libstdc++

pkglib_LIBRARIES = livestatus.so

livestatus_so_SOURCES = \
        AndingFilter.cc \
        AttributeListAsIntColumn.cc \
        AttributeListColumn.cc \
        BlobColumn.cc \
        ClientQueue.cc \
        Column.cc \
        ColumnsColumn.cc \
        CommandsHolderNagios.cc \
        ContactGroupsColumn.cc \
        ContactGroupsMemberColumn.cc \
        ContactsColumn.cc \
        CountAggregator.cc \
        CustomTimeperiodColumn.cc \
        CustomVarsColumn.cc \
        CustomVarsDictColumn.cc \
        CustomVarsDictFilter.cc \
        CustomVarsExplicitColumn.cc \
        CustomVarsListFilter.cc \
        CustomVarsNamesColumn.cc \
        CustomVarsValuesColumn.cc \
        DoubleAggregator.cc \
        DoubleColumn.cc \
        DoubleFilter.cc \
        DownCommColumn.cc \
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
        HostListFilter.cc \
        HostListStateColumn.cc \
        HostServiceState.cc \
        HostSpecialDoubleColumn.cc \
        HostSpecialIntColumn.cc \
        InputBuffer.cc \
        IntAggregator.cc \
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
        NegatingFilter.cc \
        NullColumn.cc \
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
        Renderer.cc \
        RendererBrokenCSV.cc \
        RendererCSV.cc \
        RendererJSON.cc \
        RendererPython.cc \
        RendererPython3.cc \
        ServiceContactsColumn.cc \
        ServiceGroupsColumn.cc \
        ServiceListColumn.cc \
        ServiceListFilter.cc \
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
        VariadicFilter.cc \
        WorldNagios.cc \
        auth.cc \
        global_counters.cc \
        mk_inventory.cc \
        mk_logwatch.cc \
        module.cc \
        opids.cc \
        pnp4nagios.cc \
        strutil.cc \
        waittriggers.cc

livestatus_so_CXXFLAGS = -fPIC
livestatus_so_CFLAGS   = -fPIC

livestatus.o: $(livestatus_so_OBJECTS) $(livestatus_so_DEPENDENCIES)
	-rm -f plugin.so
	$(CXX) $(LDFLAGS) -s -fPIC -shared $(livestatus_so_OBJECTS) -o $@ -lpthread -static-libstdc++

all-local: livestatus.o

install-data-local:
	$(mkinstalldirs) $(DESTDIR)$(pkglibdir)
	$(INSTALL_PROGRAM) livestatus.o $(DESTDIR)$(pkglibdir)
	rm -f $(DESTDIR)$(pkglibdir)/livestatus.so

clean-local:
	rm -f *~
