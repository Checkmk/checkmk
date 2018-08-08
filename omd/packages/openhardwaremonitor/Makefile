include ../../Makefile.omd

NAME         = openhardwaremonitor
VERSION      = 0.8.0
DIR          = openhardwaremonitor-$(VERSION)

.PHONY: setup clean-ohm dist build install skel clean

# This package can not, because it's a Mono project, and should not be built, because we compile
# a linux distro independent windows binary, during packaging procedure in the context of the
# single linux distributions. Instead we build the exe file during src/ packaging phase on our
# development server. This is equal to the precompiled windows agent and the agent updater.

build:

setup:
	sudo apt-get install \
	    mono-complete \
	    mono-xbuild

OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll: $(DIR)/Bin/Release/OpenHardwareMonitorCLI.exe $(DIR)/Bin/Release/OpenHardwareMonitorLib.dll
	cp -p $(DIR)/Bin/Release/OpenHardwareMonitorCLI.exe $(DIR)/Bin/Release/OpenHardwareMonitorLib.dll .

$(DIR)/Bin/Release/OpenHardwareMonitorCLI.exe $(DIR)/Bin/Release/OpenHardwareMonitorLib.dll: $(DIR) $(DIR)/OpenHardwareMonitorCLI $(DIR)/OpenHardwareMonitor.sln
	xbuild /p:Configuration=Release /p:TargetFrameworkVersion="v4.5" $(DIR)/OpenHardwareMonitor.sln /target:OpenHardwareMonitorCLI

$(DIR): $(DIR).zip
	unzip -o $<
	touch -c $@

$(DIR)/OpenHardwareMonitorCLI: OpenHardwareMonitorCLI
	cp -r OpenHardwareMonitorCLI $(DIR)/

$(DIR)/OpenHardwareMonitor.sln: OpenHardwareMonitor.sln
	cp OpenHardwareMonitor.sln $(DIR)/

dist: OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll clean

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm
	install -m 755 OpenHardwareMonitorCLI.exe $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm
	install -m 755 OpenHardwareMonitorLib.dll $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/ohm

skel:

clean-ohm: clean
	rm -f OpenHardwareMonitorCLI.exe OpenHardwareMonitorLib.dll

clean:
	rm -rf $(DIR)
