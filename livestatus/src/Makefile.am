# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

bin_PROGRAMS = unixcat
unixcat_SOURCES = unixcat.c
unixcat_LDADD = -lpthread

pkglib_LIBRARIES = livestatus.so

livestatus_so_SOURCES = \
	AndingFilter.cc ClientQueue.cc Column.cc ColumnsColumn.cc CustomVarsExplicitColumn.cc \
	ContactsColumn.cc CustomVarsColumn.cc CustomVarsFilter.cc DoubleColumn.cc \
	DoubleColumnFilter.cc DowntimeOrComment.cc DownCommColumn.cc DynamicColumn.cc EmptyColumn.cc NullColumn.cc \
	Filter.cc GlobalCountersColumn.cc HostContactsColumn.cc HostgroupsColumn.cc \
	HostlistColumn.cc HostlistColumnFilter.cc HostlistStateColumn.cc MetricsColumn.cc \
	HostSpecialIntColumn.cc ServiceSpecialIntColumn.cc InputBuffer.cc IntColumn.cc IntColumnFilter.cc \
	ListColumn.cc ListColumnFilter.cc OffsetDoubleColumn.cc OffsetIntColumn.cc \
	OffsetStringColumn.cc OffsetTimeperiodColumn.cc OringFilter.cc OutputBuffer.cc \
	OffsetTimeColumn.cc TimePointerColumn.cc TimeColumnFilter.cc PerfdataAggregator.cc \
	Query.cc ServiceContactsColumn.cc ServicegroupsColumn.cc ServicelistColumn.cc \
	ServicelistColumnFilter.cc ServicelistStateColumn.cc store_c.cc Store.cc \
	StringColumn.cc StringColumnFilter.cc strutil.cc Table.cc TableColumns.cc StatusSpecialIntColumn.cc \
	HostSpecialDoubleColumn.cc TableCommands.cc TableContacts.cc TableDownComm.cc TableHostgroups.cc \
	ServiceSpecialDoubleColumn.cc TableHosts.cc TableServicegroups.cc TableServices.cc TableStatus.cc  \
	LogEntry.cc LogCache.cc Logfile.cc TableStateHistory.cc TableLog.cc TableTimeperiods.cc TableContactgroups.cc \
	ContactgroupsMemberColumn.cc OffsetStringMacroColumn.cc OffsetStringServiceMacroColumn.cc \
	OffsetStringHostMacroColumn.cc StatsColumn.cc IntAggregator.cc CountAggregator.cc \
	DoubleAggregator.cc AttributelistColumn.cc AttributelistFilter.cc BlobColumn.cc HostFileColumn.cc \
	global_counters.c  module.c  logger.c waittriggers.c TimeperiodsCache.cc pnp4nagios.cc mk_inventory.cc \
	ContactgroupsColumn.cc CustomTimeperiodColumn.cc HostServiceState.cc opids.cc auth.cc

livestatus_so_CXXFLAGS = -I$(top_srcdir)/$(nagios_headers) -fPIC
livestatus_so_CFLAGS   = $(livestatus_so_CXXFLAGS)

livestatus.o: $(livestatus_so_OBJECTS) $(livestatus_so_DEPENDENCIES)
	-rm -f plugin.so
	$(CXX) $(LDFLAGS) -s -fPIC -shared $(livestatus_so_OBJECTS) -o $@ -lpthread -lstdc++

all-local: livestatus.o

install-data-local:
	$(mkinstalldirs) $(DESTDIR)$(pkglibdir)
	$(INSTALL_PROGRAM) livestatus.o $(DESTDIR)$(pkglibdir)
	rm -f $(DESTDIR)$(pkglibdir)/livestatus.so

clean-local:
	rm -f *~
