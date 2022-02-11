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

%prep
%setup -n check-mk-agent-%{_version}

%install

R=$RPM_BUILD_ROOT
H="${R}/var/lib/cmk-agent"
rm -rf "${R}"

# install agent
mkdir -p "${R}/etc/check_mk"
mkdir -p "${H}/scripts/super-server/0_systemd"
mkdir -p "${H}/scripts/super-server/1_xinetd"
echo "# first available super server (default)" > "${R}/etc/check_mk/super-server.cfg"
install -m 751 "scripts/cmk-agent-useradd.sh" "${H}/scripts/cmk-agent-useradd.sh"
install -m 751 "scripts/super-server/setup" "${H}/scripts/super-server/setup"

# xinitd
install -m 751 "scripts/super-server/1_xinetd/setup" "${H}/scripts/super-server/1_xinetd/"
install -m 644 "scripts/super-server/1_xinetd/check-mk-agent" "${R}/etc/check_mk/xinetd-service-template.cfg"

# Systemd
install -m 751 "scripts/super-server/0_systemd/setup" "${H}/scripts/super-server/0_systemd/"
install -m 666 "scripts/super-server/0_systemd/check-mk-agent@.service" "${H}/scripts/super-server/0_systemd/"
install -m 666 "scripts/super-server/0_systemd/check-mk-agent.socket" "${H}/scripts/super-server/0_systemd/"
install -m 666 "scripts/super-server/0_systemd/check-mk-agent-async.service" "${H}/scripts/super-server/0_systemd/"
install -m 666 "scripts/super-server/0_systemd/cmk-agent-ctl-daemon.service" "${H}/scripts/super-server/0_systemd/"

mkdir -p $R/etc/check_mk
mkdir -p $R/usr/bin
install -m 755 check_mk_agent.linux $R/usr/bin/check_mk_agent
install -m 755 check_mk_caching_agent.linux $R/usr/bin/check_mk_caching_agent
install -m 755 waitmax $R/usr/bin
install -m 755 mk-job $R/usr/bin
install -m 755 linux/cmk-agent-ctl $R/usr/bin
mkdir -p $R/usr/lib/check_mk_agent/plugins
mkdir -p $R/usr/lib/check_mk_agent/local
mkdir -p $R/var/lib/check_mk_agent
mkdir -p $R/var/lib/check_mk_agent/job
mkdir -p $R/var/lib/check_mk_agent/spool

%clean
rm -rf $RPM_BUILD_ROOT

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
/var/lib/cmk-agent/scripts/super-server/setup trigger

if [ "$(/var/lib/cmk-agent/scripts/super-server/setup getdeployed)" = "systemd" ]; then
    if [ "$1" = "upgrade" ] || [ "$1" -ge 2 ] 2>/dev/null; then
        /var/lib/cmk-agent/scripts/cmk-agent-useradd.sh upgrade
    else
        /var/lib/cmk-agent/scripts/cmk-agent-useradd.sh new
    fi
fi

%preun

case "$1" in
    0|remove|purge)
        /var/lib/cmk-agent/scripts/super-server/setup cleanup
        /var/lib/cmk-agent/scripts/super-server/setup trigger
    ;;
esac
