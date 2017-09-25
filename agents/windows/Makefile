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


SHELL         = /bin/bash
VERSION       = 1.4.0p14
VERSION_DUMMY = @@@@@CHECK_MK_VERSION@@@@@
WINDRES       = i686-w64-mingw32-windres
GIT_REV       = $(shell git rev-parse --verify --short HEAD)

DEPDIR = depend
DEPFLAGS = -MT $@ -MMD -MP -MF $(DEPDIR)/$*.Td

COMMON_OPTS   = -Wall -static -static-libgcc -static-libstdc++ -fno-rtti -std=c++14 -gdwarf-2 -DCHECK_MK_VERSION='"$(VERSION_DUMMY)"' -D__USE_MINGW_ANSI_STDIO -DVCS_REV=\"$(VERSION)-$(GIT_REV)\"
COPTIONS      = -O2 -Wformat=2 -Werror $(COMMON_OPTS) $(DEPFLAGS)
# for debug builds
#COPTIONS      = -O0 $(COMMON_OPTS) $(DEPFLAGS)
MKDIR         = mkdir -p

POSTCOMPILE = mv -f -u $(DEPDIR)/$*.Td $(DEPDIR)/$*.d

ifeq ($(shell uname),Linux)
  CXX        = i686-w64-mingw32-g++
  CXX_64     = x86_64-w64-mingw32-g++
  WINDRES_64 = x86_64-w64-mingw32-windres
else
  CXX = mingw32-g++
endif

all: directories fix_linebreaks check_mk_agent.exe check_mk_agent-64.exe install_agent.exe install_agent-64.exe msi_installer

.PHONY: directories inc_build_version fix_linebreaks

setversion:
	sed -i 's/!define CHECK_MK_VERSION .*/!define CHECK_MK_VERSION "'$(NEW_VERSION)'"/' installer*.nsi ; \
	sed -ri 's/^(VERSION[[:space:]]*:?= *).*/\1'"$(NEW_VERSION)/" Makefile ; \
	rm check_mk_agent.exe check_mk_agent-64.exe check_mk_agent.msi ; \
	make install_agent.exe install_agent-64.exe msi_installer

# Converts all files which are targeted to a windows system to CRLF
fix_linebreaks:
	for F in mrpe/* plugins/* *.ini; do \
	    if [ -f "$$F" ]; then \
	        sed -i 's/\r//' "$$F" ; \
	        sed -i 's/$$/\r/' "$$F" ; \
	    fi ; \
	done

# -----------------------------------------------------------------------------
# 1. Create ressource files with version and product information. Note: That file
# contains a dummy version number, which is later being replaced with the
# actual version number, during 'make version'
# -----------------------------------------------------------------------------
inc_build_version:
	echo $$(( $$(cat build_version) + 1 )) > build_version.new && mv build_version.new build_version
	BUILD_VERSION=$$(cat build_version) ; \
	   sed -e "s/%VERSION%/$(VERSION_DUMMY)/g" \
	       -e "s/%YEAR%/$$(date +%Y)/g" \
	       -e "s/%BUILD_VERSION%/$$BUILD_VERSION/g" check_mk_agent.rc.in > check_mk_agent.rc

check_mk_agent.res: check_mk_agent.rc
	$(WINDRES) $< -O coff -o $@

check_mk_agent-64.res: check_mk_agent.rc
	$(WINDRES_64) $< -O coff -o $@

# -----------------------------------------------------------------------------
# 2. Create directories for the object files
# -----------------------------------------------------------------------------

directories:
	${MKDIR} obj
	${MKDIR} obj/sections
	${MKDIR} obj64
	${MKDIR} obj64/sections
	${MKDIR} $(DEPDIR)
	${MKDIR} $(DEPDIR)/sections


# -----------------------------------------------------------------------------
# 3. Compile the Windows agent from the sources, without a specific version
# number. Instead a placeholder is being used as version.a
# -----------------------------------------------------------------------------

SRCS = check_mk_agent.cc SettingsCollector.cc Configuration.cc Configurable.cc Environment.cc stringutil.cc\
       types.cc wmiHelper.cc ListenSocket.cc PerfCounter.cc PerfCounterCommon.cc Thread.cc OutputProxy.cc\
       logging.cc Crypto.cc OHMMonitor.cc EventLog.cc ExternalCmd.cc EventLogVista.cc IEventLog.cc\
       crashhandling.cc SectionManager.cc Section.cc sections/SectionPS.cc sections/SectionWMI.cc\
       sections/SectionUptime.cc sections/SectionCheckMK.cc sections/SectionSystemtime.cc\
       sections/SectionDF.cc sections/SectionServices.cc sections/SectionMem.cc sections/SectionFileinfo.cc\
       sections/SectionWinperf.cc sections/SectionLogwatch.cc sections/SectionGroup.cc\
       sections/SectionSkype.cc sections/SectionOHM.cc sections/SectionPerfcounter.cc\
       sections/SectionEventlog.cc sections/SectionPluginGroup.cc\
       sections/SectionCrashDebug.cc sections/SectionSpool.cc sections/SectionMRPE.cc

OBJS = $(addprefix obj/,$(SRCS:.cc=.o))
OBJS64 = $(addprefix obj64/,$(SRCS:.cc=.o))


obj/%.o: %.cc $(DEPDIR)/%.d
	$(CXX) -c $(COPTIONS) -o $@  $<
	$(POSTCOMPILE)

obj64/%.o: %.cc
	$(CXX_64) -c $(COPTIONS) -o $@  $<
	$(POSTCOMPILE)

check_mk_agent.unstripped.exe: $(OBJS)
	$(MAKE) inc_build_version
	$(MAKE) check_mk_agent.res
	$(CXX) $(COPTIONS) -o $@ $^ check_mk_agent.res -lwsock32 -lws2_32 -lole32 -loleaut32 -lwbemuuid -lpsapi -lshlwapi -limagehlp

check_mk_agent-64.unstripped.exe: $(OBJS64)
	$(MAKE) inc_build_version
	$(MAKE) check_mk_agent-64.res
	$(CXX_64) $(COPTIONS) -o $@ $^ check_mk_agent-64.res -lwsock32 -lws2_32 -lole32 -loleaut32 -lwbemuuid -lpsapi -lshlwapi -limagehlp


check_mk_agent.unversioned.exe: check_mk_agent.unstripped.exe
	strip -o $@ $^

check_mk_agent-64.unversioned.exe: check_mk_agent-64.unstripped.exe
	strip -o $@ $^

$(DEPDIR)/%.d: ;
.PRECIOUS: $(DEPDIR)/%.d

-include $(patsubst %,$(DEPDIR)/%.d,$(basename $(SRCS)))

# -----------------------------------------------------------------------------
# 4. Create final executable files by inserting actual version number. No
# recompilation is thus needed during 'make version'
# -----------------------------------------------------------------------------

check_mk_agent.exe.versioned:
	./bin_replace $(VERSION_DUMMY) "$(VERSION)" < check_mk_agent.unversioned.exe > check_mk_agent.exe
	chmod 755 check_mk_agent.exe

check_mk_agent-64.exe.versioned:
	./bin_replace $(VERSION_DUMMY) "$(VERSION)" < check_mk_agent-64.unversioned.exe > check_mk_agent-64.exe
	chmod 755 check_mk_agent-64.exe

# important: %.exe.versioned must not depend on %.exe.unversioned because on the
# automated build system, "make ...versioned" is called and that system doesn't
# provide the right compiler to build this agent
%.exe: %.unversioned.exe %.exe.versioned
	true

# -----------------------------------------------------------------------------
# NSIS installer will be removed and replaced by multiarch MSI installer
# -----------------------------------------------------------------------------
install_agent.exe: check_mk_agent.exe.versioned crash.exe nowin.exe
	if ! which makensis; then \
	    echo "ERROR: makensis missing. Please install the nsis package." ; \
	    exit 1 ; \
	fi
	makensis installer.nsi
	chmod +x install_agent.exe

install_agent-64.exe: check_mk_agent-64.exe.versioned crash.exe nowin.exe
	if ! which makensis; then \
	    echo "ERROR: makensis missing. Please install the nsis package." ; \
	    exit 1 ; \
	fi
	makensis installer-64.nsi
	chmod +x install_agent-64.exe

msi_installer:
	cd msibuild ; make BUILD_VERSION=$$(cat ../build_version) CHECK_MK_VERSION=$(VERSION)
	mv msibuild/check_mk_agent.msi .
	chmod +x check_mk_agent.msi

crash.exe: crash.cc
	$(CXX) -o $@ $<

nowin.exe: nowin.cc
	$(CXX) -o $@ $<

clean:
	rm -f *.o *.exe *~ svn-*.tmp *.rc *.res obj/*.o obj64/*.o obj/sections/*.o obj64/sections/*.o
	make -C msibuild clean

mrproper: clean
	rm -f *.exe

setup:
	sudo apt-get install nsis lcab binutils-mingw-w64-i686 binutils-mingw-w64-x86-64 g++-mingw-w64-i686 g++-mingw-w64-x86-64
