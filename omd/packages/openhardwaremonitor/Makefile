include ../../Makefile.omd

NAME         = openhardwaremonitor
VERSION      = 0.8.0
DIR          = openhardwaremonitor-$(VERSION)

.PHONY: setup build-ohm clean-ohm dist build install skel clean

# This package can not, because it's a Mono project, and should not be built, because we compile
# a linux distro independent windows binary, during packaging procedure in the context of the
# single linux distributions. Instead we build the exe file during src/ packaging phase on our
# development server. This is equal to the precompiled windows agent and the agent updater.

setup:
	sudo apt-get install \
	    mono-complete \
	    mono-xbuild

OpenHardwareMonitorCLI.exe: build-ohm
	cp -p $(DIR)/Bin/Release/OpenHardwareMonitorCLI.exe .

OpenHardwareMonitorLib.dll: build-ohm
	cp -p $(DIR)/Bin/Release/OpenHardwareMonitorLib.dll .

build-ohm: clean-ohm
	unzip -d . $(DIR).zip
	cp -R OpenHardwareMonitorCLI OpenHardwareMonitor.sln $(DIR)
	xbuild /p:Configuration=Release /p:TargetFrameworkVersion="v4.5" $(DIR)/OpenHardwareMonitor.sln /target:OpenHardwareMonitorCLI

dist: OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll

build:

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm
	install -m 755 $(DIR)/OpenHardwareMonitorCLI.exe $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm
	install -m 755 $(DIR)/OpenHardwareMonitorLib.dll $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm

skel:

clean-ohm: clean
	rm -f OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll

clean:
	rm -rf $(DIR)
