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
rm -rf $R

# install agent
mkdir -p "${R}/var/lib/cmk-agent/scripts"
install -m 751 "scripts/cmk-agent-useradd.sh" "${R}/var/lib/cmk-agent/scripts/cmk-agent-useradd.sh"

# xinitd
mkdir -p $R/etc/xinetd.d
install -m 644 cfg_examples/xinetd.conf $R/etc/xinetd.d/check-mk-agent
# Systemd
mkdir -p $R/usr/lib/systemd/system
install -m 644 cfg_examples/systemd/check-mk-agent\@.service $R/usr/lib/systemd/system
install -m 644 cfg_examples/systemd/check-mk-agent.socket $R/usr/lib/systemd/system
install -m 644 cfg_examples/systemd/check-mk-agent-async.service $R/usr/lib/systemd/system
install -m 644 cfg_examples/systemd/cmk-agent-ctl-daemon.service $R/usr/lib/systemd/system
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
%config(noreplace) /etc/xinetd.d/check-mk-agent
/usr/bin/check_mk_agent
/usr/bin/check_mk_caching_agent
/usr/bin/cmk-agent-ctl
/usr/bin/mk-job
/usr/bin/waitmax
/usr/lib/check_mk_agent
/usr/lib/systemd/system/check-mk-agent-async.service
/usr/lib/systemd/system/check-mk-agent.socket
/usr/lib/systemd/system/check-mk-agent@.service
/usr/lib/systemd/system/cmk-agent-ctl-daemon.service
/var/lib/check_mk_agent
/var/lib/cmk-agent/scripts/cmk-agent-useradd.sh

%pre

# migrate old xinetd service (regardless of the current super server setting)
if [ ! -e "/etc/xinetd.d/check-mk-agent" ] && [ -e "/etc/xinetd.d/check_mk" ]; then
    printf "migrating old /etc/xinetd.d/check_mk ... "
    sed 's/service check_mk/service check-mk-agent/' "/etc/xinetd.d/check_mk" >"/etc/xinetd.d/check-mk-agent" && rm "/etc/xinetd.d/check_mk" && printf "OK\n"
fi

# determine a suitable super server
super_server='missing'
which xinetd >/dev/null 2>&1 && super_server="xinetd"
which systemctl >/dev/null 2>&1 && super_server="systemd"
if [ "${super_server}" = "missing" ]; then
    cat << EOF
---------------------------------------------
WARNING

This package comes with configuration files
for the following super server(s):
  systemd (preferred)
  xinetd (fallback)
None of these have been found.
Hint: It's also possible to call the
Checkmk agent via SSH without a running
agent service.
---------------------------------------------

EOF
fi

%post
[ -f /etc/xinetd.d/check-mk-agent.rpmnew ] && rm /etc/xinetd.d/check-mk-agent.rpmnew

# determine a suitable super server
super_server='missing'
which xinetd >/dev/null 2>&1 && super_server="xinetd"
which systemctl >/dev/null 2>&1 && super_server="systemd"

if [ "${super_server}" = "systemd" ]; then
    if [ "$1" = "upgrade" ] || [ "$1" -ge 2 ] 2>/dev/null; then
        /var/lib/cmk-agent/scripts/cmk-agent-useradd.sh upgrade
    else
        /var/lib/cmk-agent/scripts/cmk-agent-useradd.sh new
    fi
fi

if which systemctl >/dev/null 2>&1; then
    rm -rf /etc/xinetd.d/check-mk-agent >/dev/null 2>&1

    if which xinetd >/dev/null 2>&1 && pgrep -G 0 -x xinetd >/dev/null 2>&1 ; then
        echo "Reloading xinetd..."
        service xinetd reload
    fi
else

    if which xinetd >/dev/null 2>&1 && which chkconfig >/dev/null 2>&1 ; then
        echo "Activating startscript of xinetd"
        chkconfig xinetd on
    fi

    if which xinetd >/dev/null 2>&1 ; then
        if pgrep -G 0 -x xinetd >/dev/null 2>&1 ; then
            echo "Reloading xinetd..."
            service xinetd reload
        else
            echo "Starting xinetd..."
            service xinetd start
        fi
    fi
fi

if which systemctl >/dev/null 2>&1; then
    echo "Enable Checkmk agent in systemd..."
    systemctl daemon-reload
    systemctl enable check-mk-agent.socket check-mk-agent-async cmk-agent-ctl-daemon
    systemctl restart check-mk-agent.socket check-mk-agent-async cmk-agent-ctl-daemon
fi

%preun

if which systemctl >/dev/null 2>&1 ; then
    echo "Disable Checkmk agent in systemd (if active)..."
    systemctl stop check-mk-agent.socket check-mk-agent-async cmk-agent-ctl-daemon >/dev/null 2>&1
    systemctl disable check-mk-agent.socket check-mk-agent-async cmk-agent-ctl-daemon >/dev/null 2>&1
fi

%postun

if which xinetd >/dev/null 2>&1 && pgrep -G 0 -x xinetd >/dev/null 2>&1 ; then
    echo "Reloading xinetd..."
    service xinetd reload
fi


