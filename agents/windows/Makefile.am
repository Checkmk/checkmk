bin_PROGRAMS = check_mk_agent wmitest

AUTOMAKE_OPTIONS = foreign
COMMON_OPTS = -O2 -Wformat=2 -Werror -Wall -fno-rtti -std=c++14 -gdwarf-2 \
              -DCHECK_MK_VERSION='"$(VERSION)"' -D__USE_MINGW_ANSI_STDIO
AM_CPPFLAGS = $(COMMON_OPTS)

AM_LDFLAGS = -static -static-libgcc -static-libstdc++
LD_COMMON = -lwsock32 -lws2_32 -lole32 -loleaut32 -lwbemuuid -lpsapi -lshlwapi -limagehlp -lntdll

check_mk_agent_LDADD = check_mk_agent.res $(LD_COMMON)

wmitest_LDADD = $(LD_COMMON)

# A left-over generated rc file in parent dir may disturb the build process.
clean_check_mk_agent_rc:
	rm -f ../check_mk_agent.rc

check_mk_agent.rc:
	BUILD_VERSION=$$(( $$(cat ../build_version) + 1 )) ; \
	echo $$BUILD_VERSION > ../build_version ; \
	ln -s ../check_mk_agent.ico check_mk_agent.ico ; \
	sed -e "s/%VERSION%/$(VERSION)/g" \
	    -e "s/%YEAR%/$$(date +%Y)/g" \
	    -e "s/%BUILD_VERSION%/$$BUILD_VERSION/g" \
	    ../check_mk_agent.rc.in > check_mk_agent.rc

check_mk_agent.res: check_mk_agent.rc | clean_check_mk_agent_rc
	$(WINDRES) $^ -O coff -o $@

check_mk_agent_SOURCES = \
        Configurable.cc \
        Configuration.cc \
        CrashHandler.cc \
        Crypto.cc \
        Environment.cc \
        EventLog.cc \
        EventLogVista.cc \
        ExternalCmd.cc \
        IEventLog.cc \
        ListenSocket.cc \
        Logger.cc \
        OHMMonitor.cc \
        OutputProxy.cc \
        PerfCounter.cc \
        PerfCounterCommon.cc \
        RotatingFileHandler.cc \
        Section.cc \
        SectionManager.cc \
        SettingsCollector.cc \
        Thread.cc \
        WinApi.cc \
        check_mk_agent.cc \
        check_mk_agent.rc \
        stringutil.cc \
        types.cc \
        win_error.cc \
        wmiHelper.cc \
        sections/SectionCheckMK.cc \
        sections/SectionDF.cc \
        sections/SectionEventlog.cc \
        sections/SectionFileinfo.cc \
        sections/SectionGroup.cc \
        sections/SectionLogwatch.cc \
        sections/SectionMRPE.cc \
        sections/SectionMem.cc \
        sections/SectionOHM.cc \
        sections/SectionPS.cc \
        sections/SectionPerfcounter.cc \
        sections/SectionPluginGroup.cc \
        sections/SectionServices.cc \
        sections/SectionSkype.cc \
        sections/SectionSpool.cc \
        sections/SectionSystemtime.cc \
        sections/SectionUptime.cc \
        sections/SectionWMI.cc \
        sections/SectionWinperf.cc

wmitest_SOURCES = wmitest.cc stringutil.cc WinApi.cc wmiHelper.cc

clean-local:
	-rm -f check_mk_agent.*
	-rm -f $(addprefix $(bindir)/,$(bin_PROGRAMS)) \
	$(patsubst %$(EXEEXT),%-64$(EXEEXT),$(addprefix $(bindir)/,$(bin_PROGRAMS))) \
	$(patsubst %$(EXEEXT),%.msi,$(addprefix $(bindir)/,$(bin_PROGRAMS)))

setversion:
	sed -i 's/^AC_INIT.*/AC_INIT([Check_MK Windows Agent], ['"$(NEW_VERSION)"'], [feedback@check-mk.org])/' ../configure.ac
