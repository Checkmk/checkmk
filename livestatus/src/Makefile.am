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

unixcat_SOURCES = unixcat.c
unixcat_LDADD = -lpthread

pkglib_LIBRARIES = livestatus.so

livestatus_so_SOURCES = \
        AndingFilter.cc \
        AttributelistColumn.cc \
        AttributelistFilter.cc \
        BlobColumn.cc \
        ClientQueue.cc \
        Column.cc \
        ColumnsColumn.cc \
        CommandsHolderNagios.cc \
        ContactgroupsColumn.cc \
        ContactgroupsMemberColumn.cc \
        ContactsColumn.cc \
        CountAggregator.cc \
        CustomTimeperiodColumn.cc \
        CustomVarsColumn.cc \
        CustomVarsExplicitColumn.cc \
        CustomVarsFilter.cc \
        DoubleAggregator.cc \
        DoubleColumn.cc \
        DoubleColumnFilter.cc \
        DownCommColumn.cc \
        DowntimeOrComment.cc \
        DowntimesOrComments.cc \
        DynamicColumn.cc \
        EmptyColumn.cc \
        Filter.cc \
        GlobalCountersColumn.cc \
        HostContactsColumn.cc \
        HostFileColumn.cc \
        HostServiceState.cc \
        HostSpecialDoubleColumn.cc \
        HostSpecialIntColumn.cc \
        HostgroupsColumn.cc \
        HostlistColumn.cc \
        HostlistColumnFilter.cc \
        HostlistStateColumn.cc \
        InputBuffer.cc \
        IntAggregator.cc \
        IntColumn.cc \
        IntColumnFilter.cc \
        ListColumn.cc \
        ListColumnFilter.cc \
        LogCache.cc \
        LogEntry.cc \
        Logfile.cc \
        LogwatchListColumn.cc \
        DynamicLogwatchFileColumn.cc \
        MetricsColumn.cc \
        NullColumn.cc \
        OffsetDoubleColumn.cc \
        OffsetIntColumn.cc \
        OffsetSStringColumn.cc \
        OffsetStringColumn.cc \
        OffsetStringHostMacroColumn.cc \
        OffsetStringMacroColumn.cc \
        OffsetStringServiceMacroColumn.cc \
        OffsetTimeColumn.cc \
        OffsetTimeperiodColumn.cc \
        OringFilter.cc \
        OutputBuffer.cc \
        PerfdataAggregator.cc \
        Query.cc \
        ServiceContactsColumn.cc \
        ServiceSpecialDoubleColumn.cc \
        ServiceSpecialIntColumn.cc \
        ServicegroupsColumn.cc \
        ServicelistColumn.cc \
        ServicelistColumnFilter.cc \
        ServicelistStateColumn.cc \
        StatsColumn.cc \
        StatusSpecialIntColumn.cc \
        Store.cc \
        StringColumn.cc \
        StringColumnFilter.cc \
        Table.cc \
        TableColumns.cc \
        TableCommands.cc \
        TableContactgroups.cc \
        TableContacts.cc \
        TableDownComm.cc \
        TableEventConsole.cc \
        TableEventConsoleEvents.cc \
        TableEventConsoleHistory.cc \
        TableEventConsoleStatus.cc \
        TableHostgroups.cc \
        TableHosts.cc \
        TableHostsByGroup.cc \
        TableLog.cc \
        TableServicegroups.cc \
        TableServices.cc \
        TableServicesByGroup.cc \
        TableServicesByHostGroup.cc \
        TableStateHistory.cc \
        TableStatus.cc \
        TableTimeperiods.cc \
        TimeColumnFilter.cc \
        TimePointerColumn.cc \
        TimeperiodsCache.cc \
        WorldNagios.cc \
        auth.cc \
        global_counters.c \
        logger.c \
        mk_inventory.cc \
        mk_logwatch.cc \
        module.c \
        opids.cc \
        pnp4nagios.cc \
        store_c.cc \
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
