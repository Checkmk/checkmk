bin_PROGRAMS = unixcat
unixcat_SOURCES = unixcat.c
unixcat_CFLAGS = -lpthread

pkglib_LIBRARIES = livestatus.so
livestatus_so_SOURCES = \
	AndingFilter.cc ClientQueue.cc Column.cc ColumnsColumn.cc \
	ContactsColumn.cc CustomVarsColumn.cc CustomVarsFilter.cc DoubleColumn.cc \
	DoubleColumnFilter.cc Downtime.cc DowntimesColumn.cc EmptyColumn.cc \
	Filter.cc GlobalCountersColumn.cc HostContactsColumn.cc HostgroupsColumn.cc \
	HostlistColumn.cc HostlistColumnFilter.cc HostlistStateColumn.cc \
	HostSpecialIntColumn.cc InputBuffer.cc IntColumn.cc IntColumnFilter.cc \
	ListColumn.cc ListColumnFilter.cc OffsetDoubleColumn.cc OffsetIntColumn.cc \
	OffsetStringColumn.cc OffsetTimeperiodColumn.cc OringFilter.cc OutputBuffer.cc \
	Query.cc ServiceContactsColumn.cc ServicegroupsColumn.cc ServicelistColumn.cc \
	ServicelistColumnFilter.cc ServicelistStateColumn.cc store.cc Store.cc \
	StringColumn.cc StringColumnFilter.cc strutil.cc Table.cc TableColumns.cc \
	TableCommands.cc TableContacts.cc TableDowntimes.cc TableHostgroups.cc \
	TableHosts.cc TableServicegroups.cc TableServices.cc TableStatus.cc  \
	global_counters.c  module.c  logger.c 

livestatus_so_CXXFLAGS = -I$(top_srcdir)/nagios -fPIC
livestatus_so_CFLAGS   = $(livestatus_so_CXXFLAGS) 

livestatus.o: $(livestatus_so_OBJECTS) $(livestatus_so_DEPENDENCIES)
	-rm -f plugin.so
	$(CXX) -s -fPIC -shared $(livestatus_so_OBJECTS) -o $@ -lpthread -lstdc++

all-local: livestatus.o

clean-local:
	rm -f *~
