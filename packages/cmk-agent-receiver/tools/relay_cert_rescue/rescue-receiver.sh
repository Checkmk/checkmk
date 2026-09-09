#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Unlock relays whose client certificate has expired: stop the official agent receiver,
# run the same receiver with the certificate validity check relaxed, report every relay
# that renews, and put the official receiver back when the operator presses Ctrl-C.
# The gunicorn call below mirrors etc/init.d/agent-receiver.
#
# This is the whole tool: the gunicorn worker that does the relaxing is embedded below and
# written out at run time, so an affected customer receives a single file.
set -euo pipefail

{ [ -n "${OMD_ROOT:-}" ] && [ -n "${OMD_SITE:-}" ]; } ||
    {
        echo "Run this as the site user: omd su <site> (OMD_ROOT/OMD_SITE are unset)." >&2
        exit 1
    }

[ -t 0 ] ||
    {
        echo "Run this from a terminal: it asks for confirmation and waits for Ctrl-C." >&2
        exit 1
    }

# The renewal this script unblocks needs the p13 fix in the site itself: on 2.5.0p9 to
# p12 the relays do reconnect here and are reported, and still fail to renew -- which
# looks exactly like the script working. Only the 2.5.0 branch was ever affected, so
# any version that is not in that window passes through unchecked.
SITE_VERSION=$(omd version -b)
case "$SITE_VERSION" in
    2.5.0p9 | 2.5.0p9.* | 2.5.0p1[0-2] | 2.5.0p1[0-2].*)
        echo "This site is on $SITE_VERSION, where the relays cannot renew at all." >&2
        echo "They would reconnect to this script and still fail. Update the site to" >&2
        echo "2.5.0p13 or newer first -- see the Updates chapter of the manual." >&2
        exit 1
        ;;
esac

# shellcheck disable=SC1090,SC1091
. "$OMD_ROOT/etc/omd/site.conf"
[ "${CONFIG_AGENT_RECEIVER:-}" = on ] ||
    {
        echo "The agent receiver is disabled in this site." >&2
        exit 1
    }

# The trust store is the one file the official start deletes and rebuilds, so a start
# that failed halfway can leave it missing or empty. Without this check gunicorn would
# respawn workers forever printing a bare "[Errno 2] No such file or directory", with
# the real traceback going to var/log/agent-receiver/error.log rather than this terminal.
CERT_STORE="$OMD_ROOT/etc/ssl/agent_cert_store.pem"
[ -s "$CERT_STORE" ] ||
    {
        echo "Trust store $CERT_STORE is missing or empty." >&2
        echo "It is rebuilt when the agent receiver starts. Run:" >&2
        echo "    omd start agent-receiver && omd stop agent-receiver" >&2
        echo "and then start this script again." >&2
        exit 1
    }

ACCESS_LOG="$OMD_ROOT/var/log/agent-receiver/access.log"
RELAY_CONF="$OMD_ROOT/etc/check_mk/conf.d/wato/relay.mk"
# gunicorn writes its pid here and removes the file when it shuts down, and the restore
# below removes it too. So a file still lying here means this script died without
# restoring anything and the relaxed receiver may still be up, still accepting expired
# certificates: kill that pid, remove this file and run "omd start agent-receiver". The
# name is deliberately not agent-receiver.pid: that one is what omd start/status read.
RESCUE_PIDFILE="$OMD_ROOT/tmp/run/agent-receiver-rescue.pid"

cat <<EOF
This script is intended to be used to unlock relays whose certificates have expired.

Warning: during the healing process the agent receiver will NOT verify the expiration
date of any client certificate presented to it -- the registered agents' as well as
the relays'.

EOF

read -r -p "Do you want to continue (Y/N)? " ANSWER
case "$ANSWER" in
    [Yy] | [Yy][Ee][Ss]) ;;
    *)
        echo "Nothing was changed."
        exit 1
        ;;
esac

GUNICORN_PID=""
WORK_DIR=""

restore_official_receiver() {
    # An impatient second Ctrl-C must not interrupt the restore half-way and leave the
    # site with no receiver at all. HUP for the same reason: this is typically run over
    # ssh, and the default action for a hangup is to kill the shell.
    trap '' INT TERM HUP
    echo
    echo 'Stopping agent-receiver in "relaxed" mode:'
    if [ -n "$GUNICORN_PID" ] && kill -0 "$GUNICORN_PID" 2>/dev/null; then
        kill "$GUNICORN_PID" 2>/dev/null || true
        for _ in $(seq 1 20); do
            kill -0 "$GUNICORN_PID" 2>/dev/null || break
            sleep 1
        done
        kill -9 "$GUNICORN_PID" 2>/dev/null || true
        wait "$GUNICORN_PID" 2>/dev/null || true
    fi
    # gunicorn removes this itself when it stops in time; after the kill -9 above it does
    # not, and a stale one would be read as a failed run and could block the next start.
    rm -f "$RESCUE_PIDFILE"
    if [ -n "$WORK_DIR" ]; then
        rm -rf "$WORK_DIR"
    fi
    echo "OK"
    echo
    echo "Re-starting agent-receiver in regular mode:"
    if ! omd start agent-receiver; then
        echo >&2
        echo "ERROR: the official agent receiver did NOT come back up." >&2
        echo "The site is currently running without an agent receiver." >&2
        echo "Check 'omd status agent-receiver' and var/log/agent-receiver/error.log." >&2
    fi
}
trap restore_official_receiver EXIT
# Without these the EXIT trap would not run and the site would be left with no receiver
# at all. Ctrl-C is the normal way out; TERM covers being killed from elsewhere.
trap 'exit 130' INT
trap 'exit 143' TERM

echo
echo "Stopping agent-receiver:"
omd stop agent-receiver

# The worker below has to be a module gunicorn can import, so it is written out here and
# removed again by the EXIT trap. It lives under the site's own tmp directory, which the
# worker processes can read and which nothing outside the site can write.
WORK_DIR=$(mktemp -d "$OMD_ROOT/tmp/rescue-receiver.XXXXXX")
# The receiver reports the relays it lets in on its own stdout, which is a different
# process writing to the same terminal: a relay connecting while this script is still
# printing would cut into the text. Collect it in a file instead and let the loop at the
# end of this script read it, so all output is in the order the operator reads it.
RECEIVER_OUTPUT="$WORK_DIR/receiver.out"

# Quoted delimiter: the worker is Python and must reach the file exactly as written here.
cat <<'RESCUE_RECEIVER_PY' >"$WORK_DIR/rescue_receiver.py"
"""Temporarily let a relay with an expired certificate reach its site again.

A relay authenticates to its site with a client certificate it renews itself. On sites
2.5.0p9 to p12 that renewal was rejected, so certificates eventually expired -- and an
expired certificate cannot even complete the TLS handshake, which locks the relay out of
the very endpoint that would fix it, and out of the version check that would let it
update itself.

This worker is the official one with a single change: the client certificate's validity
*period* is not checked. Chain, CA and common name are still verified, so a caller still
needs a certificate genuinely issued by one of the CAs this site trusts -- its relay CA
or its agent CA -- and the matching private key. The receiver builds a single SSL context
for everything that connects to it, so this cannot be narrowed to relays: expired agent
certificates are accepted too while this worker runs. Once the relay can talk to the site
again it repairs itself: it learns the site's version, its host pulls the matching image,
and the new engine renews the certificate correctly.

It also reports every relay it lets in, with the expiry date of the certificate that
relay presented, so the operator can tell which relays were actually affected. That
date exists nowhere else: the site keeps the relay CA, not the certificates it signed.

This module is not shipped: rescue-receiver.sh writes it out, runs it and deletes it
again.
"""

from __future__ import annotations

import asyncio
import os
import ssl
from ssl import SSLObject
from typing import Final, override

import uvicorn.config

from cmk.agent_receiver.worker import (
    _ClientCertProtocol,
    _extract_client_cert_names,
    ClientCertWorker,
)

# OpenSSL's X509_V_FLAG_NO_CHECK_TIME. Python's ssl module does not export the constant,
# but SSLContext.verify_flags passes the bits straight to X509_VERIFY_PARAM_set_flags.
# It disables the validity-period check only: a certificate from any other CA is still
# rejected with "unable to get local issuer certificate".
NO_CHECK_TIME: Final = 0x200000

# "Already patched" marker. The patch below wraps uvicorn's factory instead of editing
# it, so running twice would wrap our own wrapper -- and gunicorn calls it once per
# worker (re)start, all in the same master process, so it does run more than once.
_relaxed = False


def relax_certificate_validity() -> None:
    """Stop checking client certificate dates. Idempotent.

    The uvicorn worker ignores gunicorn's ssl_context hook and builds the context in
    uvicorn.config.create_ssl_context, so that is what we wrap.
    """
    global _relaxed
    if _relaxed:
        return
    original_create_ssl_context = uvicorn.config.create_ssl_context

    def create_relaxed_ssl_context(*args: object, **kwargs: object) -> ssl.SSLContext:
        context = original_create_ssl_context(*args, **kwargs)  # type: ignore[arg-type]
        context.verify_flags |= NO_CHECK_TIME
        # Proof that uvicorn really does build its context through the global we wrapped.
        # Assigning to it succeeds even if uvicorn stopped calling it, and the receiver
        # would then reject the expired certificates while looking perfectly healthy, so
        # the script waits for this line rather than for the port alone.
        # nosemgrep: disallow-print
        print("RESCUE: relaxed SSL context in use.", flush=True)
        return context

    uvicorn.config.create_ssl_context = create_relaxed_ssl_context
    _relaxed = True


# Relays already reported, so that a relay polling every second produces one line.
_reported: Final[set[str]] = set()


def report_client_certificate(ssl_object: SSLObject | None) -> None:
    """Print, once per relay, when the certificate it just presented expires.

    That date exists nowhere else: the site keeps the relay CA, not the certificates it
    signed. Agents use this receiver too and are told apart by their issuer -- a relay's
    is the relay CA, whose common name is the site ID (see cmk.utils.certs.RelaysCA).
    """
    if ssl_object is None:
        return
    relay_id, issuer_cn = _extract_client_cert_names(ssl_object)
    if relay_id is None or relay_id in _reported or issuer_cn != os.environ["OMD_SITE"]:
        return
    _reported.add(relay_id)
    not_after = (ssl_object.getpeercert() or {}).get("notAfter", "unknown")
    # nosemgrep: disallow-print
    print(f"- Relay {relay_id}: its certificate expires {not_after}.", flush=True)


class _ReportingProtocol(_ClientCertProtocol):
    """The official protocol, reporting each relay it accepts.

    connection_made runs once per connection, after the TLS handshake, which is where
    the peer certificate becomes available -- and before any request, so a relay is
    reported even if it only ever connects.
    """

    @override
    def connection_made(self, transport: asyncio.Transport) -> None:  # type: ignore[override]
        super().connection_made(transport)
        report_client_certificate(transport.get_extra_info("ssl_object"))


class RescueWorker(ClientCertWorker):
    """The official worker, minus the validity check, reporting the relays it lets in.

    Relaxing in __init__ rather than at import time keeps importing this module free of
    side effects. Gunicorn constructs the worker in the master, before forking, and
    uvicorn builds the SSL context later in the child, when the server runs -- so this
    is early enough, and it is why relax_certificate_validity has to be idempotent.
    """

    CONFIG_KWARGS = {
        **ClientCertWorker.CONFIG_KWARGS,
        "http": _ReportingProtocol,
    }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        relax_certificate_validity()
RESCUE_RECEIVER_PY

if ping -c1 ::1 &>/dev/null; then ANY_ADDRESS="[::]"; else ANY_ADDRESS="0.0.0.0"; fi

echo
echo 'Starting agent-receiver in "relaxed" mode:'
gunicorn \
    -c "$OMD_ROOT/etc/agent-receiver/gunicorn.conf.py" \
    --ciphers "ECDHE+AESGCM:CHACHA20:ECDHE+AES256:!aNULL:!eNULL:!MD5:!RC4:!3DES:!SHA1:!CBC" \
    --keyfile "$OMD_ROOT/etc/ssl/sites/$OMD_SITE.pem" \
    --certfile "$OMD_ROOT/etc/ssl/sites/$OMD_SITE.pem" \
    --ca-certs "$CERT_STORE" \
    --cert-reqs 1 \
    -b "${ANY_ADDRESS}:${CONFIG_AGENT_RECEIVER_PORT}" \
    -n rescue-receiver \
    -p "$RESCUE_PIDFILE" \
    --pythonpath "$WORK_DIR" \
    -k rescue_receiver.RescueWorker \
    'cmk.agent_receiver.main:main_app()' >"$RECEIVER_OUTPUT" 2>&1 &
GUNICORN_PID=$!

# gunicorn logs to var/log/agent-receiver/, so a failure to start is silent here: wait
# for the port to accept connections instead, and show both logs if it never does.
for _ in $(seq 1 30); do
    if ! kill -0 "$GUNICORN_PID" 2>/dev/null; then break; fi
    # uvicorn binds the port after building its SSL context, so by the time we get a
    # connection the patch must have reported itself. Both conditions, never just one.
    if timeout 1 bash -c ": >/dev/tcp/127.0.0.1/$CONFIG_AGENT_RECEIVER_PORT" 2>/dev/null &&
        grep -q "RESCUE: relaxed SSL context in use." "$RECEIVER_OUTPUT"; then
        STARTED=yes
        break
    fi
    sleep 1
done
if [ "${STARTED:-}" != yes ]; then
    if timeout 1 bash -c ": >/dev/tcp/127.0.0.1/$CONFIG_AGENT_RECEIVER_PORT" 2>/dev/null; then
        echo "The agent receiver is listening, but the certificate validity check was" >&2
        echo "NOT relaxed: this uvicorn no longer builds its SSL context through" >&2
        echo "uvicorn.config.create_ssl_context. Expired certificates would still be" >&2
        echo "rejected, so this script cannot help as it stands." >&2
    else
        echo "The relaxed agent receiver did not come up. Last errors:" >&2
        tail -n 20 "$RECEIVER_OUTPUT" "$OMD_ROOT/var/log/agent-receiver/error.log" >&2 || true
    fi
    exit 1
fi
echo "OK, listening on ${ANY_ADDRESS}:${CONFIG_AGENT_RECEIVER_PORT}"

cat <<EOF

Your relay(s) with expired certificates should start to update soon. When the healing
process of a relay is completed it will be shown below.

Alternatively you can follow the update on the relay host itself with:

sudo journalctl -f -u checkmk_relay-update-manager.path \\
                   -u checkmk_relay-update-manager.service \\
                   -u podman-auto-update.service \\
                   -u checkmk_relay.service

When you detect that all your affected relays are healthy, press Ctrl+C.

EOF

# A relay's certificate carries only its ID, so the name the operator knows it by comes
# from the site's own configuration. Resolved here, both lines below get it.
relay_name() {
    local relay_id=$1 alias=""
    [ -r "$RELAY_CONF" ] &&
        alias=$(sed -n "s/.*'$relay_id': {'alias': '\([^']*\)'.*/\1/p" "$RELAY_CONF" | tail -n1)
    [ -n "$alias" ] && echo "$alias ($relay_id)" || echo "$relay_id"
}

# Everything the operator sees from here on comes through this loop: the relays the
# receiver let in, and the relays that have renewed. A relay that renews successfully
# POSTs its CSR and gets a 200; the broken engine of 2.5.0p9 to p12 gets a 422 there, so
# a 200 proves two things at once: the relay is already running fixed code, and it has
# just been handed a fresh certificate.
# The receiver's output is read from the start, so a relay that connected while this
# script was still starting up is reported now rather than lost; the access log is read
# from its end, since it holds the whole history of the site.
{
    tail -n +1 -F "$RECEIVER_OUTPUT" &
    tail -n 0 -F "$ACCESS_LOG" &
    wait
} |
    while IFS= read -r line; do
        case "$line" in
            "- Relay "*)
                relay_id=${line#- Relay }
                relay_id=${relay_id%%:*}
                echo "- Relay $(relay_name "$relay_id"): ${line#*: }"
                continue
                ;;
            *'"POST /'"$OMD_SITE"'/relays/'*'/csr HTTP/'*'" 200'*) ;;
            *) continue ;;
        esac
        relay_id=${line#*"/relays/"}
        relay_id=${relay_id%%/*}
        case " ${RENEWED:-} " in *" $relay_id "*) continue ;; esac
        RENEWED="${RENEWED:-} $relay_id"
        echo "- Relay $(relay_name "$relay_id"): certificates renewed!"
    done
