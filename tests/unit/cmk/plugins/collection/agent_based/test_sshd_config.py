#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.sshd_config import (
    check_sshd_config,
    discover_sshd_config,
    parse_sshd_config,
)

_STRING_TABLE_UP_TO_DATE = [
    ["port", "22"],
    ["port", "23"],
    ["addressfamily", "any"],
    ["listenaddress", "[::]:22"],
    ["listenaddress", "0.0.0.0:22"],
    ["listenaddress", "[::]:23"],
    ["listenaddress", "0.0.0.0:23"],
    ["usepam", "yes"],
    ["logingracetime", "120"],
    ["x11displayoffset", "10"],
    ["maxauthtries", "6"],
    ["maxsessions", "10"],
    ["clientaliveinterval", "0"],
    ["clientalivecountmax", "3"],
    ["streamlocalbindmask", "0177"],
    ["permitrootlogin", "without-password"],
    ["ignorerhosts", "yes"],
    ["ignoreuserknownhosts", "no"],
    ["hostbasedauthentication", "no"],
    ["hostbasedusesnamefrompacketonly", "no"],
    ["pubkeyauthentication", "yes"],
    ["kerberosauthentication", "no"],
    ["kerberosorlocalpasswd", "yes"],
    ["kerberosticketcleanup", "yes"],
    ["gssapiauthentication", "no"],
    ["gssapicleanupcredentials", "yes"],
    ["gssapikeyexchange", "no"],
    ["gssapistrictacceptorcheck", "yes"],
    ["gssapistorecredentialsonrekey", "no"],
    [
        "gssapikexalgorithms",
        "gss-group14-sha256-,gss-group16-sha512-,gss-nistp256-sha256-,gss-curve25519-sha256-,gss-group14-sha1-,gss-gex-sha1-",
    ],
    ["passwordauthentication", "yes"],
    ["kbdinteractiveauthentication", "no"],
    ["printmotd", "no"],
    ["printlastlog", "yes"],
    ["x11forwarding", "yes"],
    ["x11uselocalhost", "yes"],
    ["permittty", "yes"],
    ["permituserrc", "yes"],
    ["strictmodes", "yes"],
    ["tcpkeepalive", "yes"],
    ["permitemptypasswords", "no"],
    ["compression", "yes"],
    ["gatewayports", "no"],
    ["usedns", "no"],
    ["allowtcpforwarding", "yes"],
    ["allowagentforwarding", "yes"],
    ["disableforwarding", "no"],
    ["allowstreamlocalforwarding", "yes"],
    ["streamlocalbindunlink", "no"],
    ["fingerprinthash", "SHA256"],
    ["exposeauthinfo", "no"],
    ["pidfile", "/run/sshd.pid"],
    ["modulifile", "/etc/ssh/moduli"],
    ["xauthlocation", "/usr/bin/xauth"],
    [
        "ciphers",
        "chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com",
    ],
    [
        "macs",
        "umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1",
    ],
    ["banner", "none"],
    ["forcecommand", "none"],
    ["chrootdirectory", "none"],
    ["trustedusercakeys", "none"],
    ["revokedkeys", "none"],
    ["securitykeyprovider", "internal"],
    ["authorizedprincipalsfile", "none"],
    ["versionaddendum", "none"],
    ["authorizedkeyscommand", "none"],
    ["authorizedkeyscommanduser", "none"],
    ["authorizedprincipalscommand", "none"],
    ["authorizedprincipalscommanduser", "none"],
    ["hostkeyagent", "none"],
    [
        "kexalgorithms",
        "curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,sntrup761x25519-sha512@openssh.com,diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256",
    ],
    [
        "casignaturealgorithms",
        "ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256",
    ],
    [
        "hostbasedacceptedalgorithms",
        "ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256",
    ],
    [
        "hostkeyalgorithms",
        "ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256",
    ],
    [
        "pubkeyacceptedalgorithms",
        "ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256",
    ],
    ["loglevel", "INFO"],
    ["syslogfacility", "AUTH"],
    ["authorizedkeysfile", ".ssh/authorized_keys", ".ssh/authorized_keys2"],
    ["hostkey", "/etc/ssh/ssh_host_rsa_key"],
    ["hostkey", "/etc/ssh/ssh_host_ecdsa_key"],
    ["hostkey", "/etc/ssh/ssh_host_ed25519_key"],
    ["acceptenv", "LANG"],
    ["acceptenv", "LC_*"],
    ["authenticationmethods", "any"],
    ["subsystem", "sftp", "/usr/lib/openssh/sftp-server"],
    ["maxstartups", "10:30:100"],
    ["persourcemaxstartups", "none"],
    ["persourcenetblocksize", "32:128"],
    ["permittunnel", "no"],
    ["ipqos", "lowdelay", "throughput"],
    ["rekeylimit", "0", "0"],
    ["permitopen", "any"],
    ["permitlisten", "any"],
    ["permituserenvironment", "no"],
    ["pubkeyauthoptions", "none"],
]

_STRING_TABLE_DEPRECATED = [
    ["Protocol", "2"],
    ["Port", "22"],
    ["ListenAddress", "::"],
    ["AllowTcpForwarding", "no"],
    ["GatewayPorts", "no"],
    ["X11Forwarding", "yes"],
    ["X11DisplayOffset", "10"],
    ["X11UseLocalhost", "yes"],
    ["Banner", "/etc/issue"],
    ["PrintMotd", "no"],
    ["KeepAlive", "yes"],
    ["SyslogFacility", "auth"],
    ["LogLevel", "info"],
    ["HostKey", "/etc/ssh/ssh_host_rsa_key"],
    ["HostKey", "/etc/ssh/ssh_host_dsa_key"],
    ["ServerKeyBits", "768"],
    ["KeyRegenerationInterval", "3600"],
    ["StrictModes", "yes"],
    ["LoginGraceTime", "600"],
    ["MaxAuthTries", "6"],
    ["MaxAuthTriesLog", "3"],
    ["PermitEmptyPasswords", "no"],
    ["PasswordAuthentication", "yes"],
    ["ChallengeResponseAuthentication", "no"],
    ["PAMAuthenticationViaKBDInt", "yes"],
    ["PermitRootLogin", "without-password"],
    ["Subsystem", "sftp", "internal-sftp"],
    ["IgnoreRhosts", "yes"],
    ["RhostsAuthentication", "no"],
    ["RhostsRSAAuthentication", "no"],
    ["RSAAuthentication", "yes"],
    [
        "AllowUsers",
        "svc_device42",
        "svc_avs",
        "cmpstech",
        "ipp_read",
        "ipp_admin",
        "ryb3108",
        "sv_bmcdisco",
        "tym2108",
        "nyk2205",
        "izs2108",
        "kzd1112",
        "sxb1602",
        "prodread",
        "unixread",
    ],
    ["ClientAliveInterval", "30"],
    ["ClientAliveCountMax", "5"],
    ["GSSAPIAuthentication", "no"],
    ["PermitUserEnvironment", "yes"],
    ["Ciphers", "aes128-ctr,aes192-ctr,aes256-ctr"],
]


@pytest.mark.parametrize(
    ["string_table"],
    [
        pytest.param(_STRING_TABLE_UP_TO_DATE),
        pytest.param(_STRING_TABLE_DEPRECATED),
    ],
)
def test_discovery(string_table: StringTable) -> None:
    assert list(discover_sshd_config(parse_sshd_config(string_table))) == [Service()]


@pytest.mark.parametrize(
    ["string_table", "params", "expected_result"],
    [
        pytest.param(
            _STRING_TABLE_UP_TO_DATE,
            {},
            [
                Result(state=State.OK, summary="Ports: 22, 23"),
                Result(state=State.OK, summary="Use pluggable authentication module: yes"),
                Result(state=State.OK, summary="Permit root login: key-based"),
                Result(state=State.OK, summary="Allow password authentication: yes"),
                Result(state=State.OK, summary="Allow keyboard-interactive authentication: no"),
                Result(state=State.OK, summary="Permit X11 forwarding: yes"),
                Result(state=State.OK, summary="Permit empty passwords: no"),
                Result(
                    state=State.OK,
                    summary="Ciphers: aes128-ctr, aes128-gcm@openssh.com, aes192-ctr, aes256-ctr, aes256-gcm@openssh.com, chacha20-poly1305@openssh.com",
                ),
            ],
        ),
        pytest.param(
            _STRING_TABLE_UP_TO_DATE,
            {
                "port": [22],
                "passwordauthentication": "no",
                "kbdinteractiveauthentication": "yes",
            },
            [
                Result(state=State.CRIT, summary="Ports: 22, 23 (expected 22)"),
                Result(state=State.OK, summary="Use pluggable authentication module: yes"),
                Result(state=State.OK, summary="Permit root login: key-based"),
                Result(
                    state=State.CRIT, summary="Allow password authentication: yes (expected no)"
                ),
                Result(
                    state=State.CRIT,
                    summary="Allow keyboard-interactive authentication: no (expected yes)",
                ),
                Result(state=State.OK, summary="Permit X11 forwarding: yes"),
                Result(state=State.OK, summary="Permit empty passwords: no"),
                Result(
                    state=State.OK,
                    summary="Ciphers: aes128-ctr, aes128-gcm@openssh.com, aes192-ctr, aes256-ctr, aes256-gcm@openssh.com, chacha20-poly1305@openssh.com",
                ),
            ],
        ),
        pytest.param(
            _STRING_TABLE_DEPRECATED,
            {},
            [
                Result(state=State.OK, summary="Ports: 22"),
                Result(state=State.OK, summary="Protocols: 2"),
                Result(state=State.OK, summary="Permit X11 forwarding: yes"),
                Result(state=State.OK, summary="Permit empty passwords: no"),
                Result(state=State.OK, summary="Allow password authentication: yes"),
                Result(state=State.OK, summary="Allow challenge-response authentication: no"),
                Result(state=State.OK, summary="Permit root login: key-based"),
                Result(state=State.OK, summary="Ciphers: aes128-ctr, aes192-ctr, aes256-ctr"),
            ],
        ),
        pytest.param(
            _STRING_TABLE_DEPRECATED,
            {
                "kbdinteractiveauthentication": "no",
                "usepam": "yes",
            },
            [
                Result(state=State.OK, summary="Ports: 22"),
                Result(state=State.OK, summary="Protocols: 2"),
                Result(state=State.OK, summary="Permit X11 forwarding: yes"),
                Result(state=State.OK, summary="Permit empty passwords: no"),
                Result(state=State.OK, summary="Allow password authentication: yes"),
                Result(state=State.OK, summary="Allow challenge-response authentication: no"),
                Result(state=State.OK, summary="Permit root login: key-based"),
                Result(state=State.OK, summary="Ciphers: aes128-ctr, aes192-ctr, aes256-ctr"),
                Result(
                    state=State.CRIT,
                    summary="Use pluggable authentication module: not present in SSH daemon configuration",
                ),
            ],
        ),
        pytest.param(
            [],
            {"kbdinteractiveauthentication": "no"},
            [
                Result(
                    state=State.CRIT,
                    summary="Allow keyboard-interactive/challenge-response authentication: not present in SSH daemon configuration",
                )
            ],
        ),
    ],
)
def test_check(
    string_table: StringTable,
    params: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_sshd_config(
                params=params,
                section=parse_sshd_config(string_table),
            )
        )
        == expected_result
    )
