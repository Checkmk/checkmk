# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

Summary:   Checkmk Agent for Linux
Name:      check-mk-agent
Version:   %{_rpm_version}
Release:   1
License:   GPL
Group:     System/Monitoring
URL:       https://checkmk.com/
Vendor:    tribe29 GmbH
Source:    check-mk-agent-%{_version}.tar.gz
BuildRoot: %{_topdir}/buildroot
AutoReq:   off
AutoProv:  off
BuildArch: noarch
Obsoletes: check_mk-agent check_mk_agent check_mk-agent-logwatch
Provides:  check_mk-agent check_mk_agent

%description
 The Checkmk Agent for Linux provides information about the system.
 This can be used to monitor the host via Checkmk.


%global _python_bytecompile_errors_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build 0

# Override CentOS 6+ specific behaviour that the build root is erased before
# building. This does not work very well with our way of preparing the files
define __spec_install_pre %{___build_pre} &&\
    mkdir -p `dirname "$RPM_BUILD_ROOT"` &&\
    mkdir -p "$RPM_BUILD_ROOT"

%files
%defattr(-,root,root)
/etc/check_mk
%config(noreplace) /etc/check_mk/super-server.cfg
%config(noreplace) /etc/check_mk/xinetd-service-template.cfg
/usr/bin/check_mk_agent
/usr/bin/check_mk_caching_agent
/usr/bin/cmk-agent-ctl
/usr/bin/mk-job
/usr/bin/waitmax
/usr/lib/check_mk_agent
/var/lib/check_mk_agent
/var/lib/cmk-agent/scripts/cmk-agent-useradd.sh
/var/lib/cmk-agent/scripts/super-server/0_systemd/check-mk-agent-async.service
/var/lib/cmk-agent/scripts/super-server/0_systemd/check-mk-agent.socket
/var/lib/cmk-agent/scripts/super-server/0_systemd/check-mk-agent@.service
/var/lib/cmk-agent/scripts/super-server/0_systemd/cmk-agent-ctl-daemon.service
/var/lib/cmk-agent/scripts/super-server/0_systemd/setup
/var/lib/cmk-agent/scripts/super-server/1_xinetd/setup
/var/lib/cmk-agent/scripts/super-server/setup

%post

/var/lib/cmk-agent/scripts/super-server/setup cleanup
/var/lib/cmk-agent/scripts/super-server/setup deploy

if [ "$(/var/lib/cmk-agent/scripts/super-server/setup getdeployed)" = "systemd" ]; then
    if [ "$1" = "upgrade" ] || [ "$1" -ge 2 ] 2>/dev/null; then
        /var/lib/cmk-agent/scripts/cmk-agent-useradd.sh upgrade
    else
        /var/lib/cmk-agent/scripts/cmk-agent-useradd.sh new
    fi
fi

/var/lib/cmk-agent/scripts/super-server/setup trigger

%preun

/var/lib/cmk-agent/scripts/super-server/setup cleanup
case "$1" in
    0|remove|purge)
        /var/lib/cmk-agent/scripts/super-server/setup trigger
    ;;
esac
