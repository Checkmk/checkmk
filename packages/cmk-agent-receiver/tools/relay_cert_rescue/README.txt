Rescue a relay whose certificate has expired
============================================

A relay renews its own client certificate. On sites 2.5.0p9 to p12 that renewal was
rejected, so the certificate eventually expired -- and an expired certificate cannot
even complete the TLS handshake, which locks the relay out of the endpoint that would
renew it and out of the version check that would let it update itself. This procedure
opens a temporary window in which the site accepts the expired certificate, just long
enough for the relay to update itself and renew. The relay keeps its ID, its hosts and
their history.

The procedure is one file, rescue-receiver.sh, which is what an affected customer is
handed. This document is not: it stays here, and it is the original of what support
walks the customer through -- published as a knowledge base article at
https://checkmk.atlassian.net/wiki/spaces/KB/pages/1420427266/How-to+renew+an+expired+Checkmk+Relay+certificate.
Change it here first, and copy it over.


Before you start
----------------

The site must be on 2.5.0p13 or newer. Check it as the site user:

    omd version -b

On p9 to p12 the relay would reconnect and still fail to renew, so update the site
first -- see the Updates chapter of the manual. On the Cloud edition you are always on
the newest version and this cannot be the problem.

Everything runs on the Checkmk server as the site user. Become it with "omd su <site>",
which gives you the site's own environment -- the script reads its configuration from
there and refuses to run without it. Nothing is installed and the site's configuration is
not touched. The script writes the receiver it runs into a temporary directory under the
site and deletes it again on exit. Running this when no relay is affected is harmless:
every relay that connects is reported with an expiry date still in the future, and
nothing changes.


Open the window
---------------

In a terminal you can leave open:

    chmod +x rescue-receiver.sh
    ./rescue-receiver.sh

Answer Y to the confirmation, and follow what the script prints:

    This script is intended to be used to unlock relays whose certificates have expired.

    Warning: during the healing process the agent receiver will NOT verify the expiration
    date of any client certificate presented to it -- the registered agents' as well as
    the relays'.

    Do you want to continue (Y/N)? Y

    Stopping agent-receiver:
    Stopping agent-receiver...killing 3069082...OK

    Starting agent-receiver in "relaxed" mode:
    OK, listening on [::]:8000

You never stop or start the receiver yourself: the script does both, and it puts the
official one back when you press Ctrl-C. Other relays, agent registrations and agent
push traffic keep working while the window is open.


Wait for the relays
-------------------

The script reports each relay once as it connects, and again when it has renewed:

    - Relay <alias> (<relay-id>): its certificate expires Sep  5 11:08:57 2026 GMT.
    - Relay <alias> (<relay-id>): certificates renewed!

The first line is a relay that has just been let in, with the expiry date of the
certificate it presented. A date in the past is an affected relay: it just completed a
handshake the official receiver refuses, so its repair can start. It then learns the
site's version, its host pulls the matching image and restarts the container, and the
new engine renews the certificate. This usually takes a few minutes, depending on how
fast the image downloads. A date in the future is a healthy relay that happened to
connect while the window was open -- nothing to do about it. A relay your site no longer
has configured appears with its ID alone, and agent traffic is not reported at all.

The second line is the one to wait for. Do not close the window before every affected
relay has reported it: a relay that reconnects but never renews is exactly as locked out
as before once the window closes, with the difference that you will believe it is
fixed.

If you want to watch the update from the relay's own host:

    sudo journalctl -f -u checkmk_relay-update-manager.path \
                       -u checkmk_relay-update-manager.service \
                       -u podman-auto-update.service \
                       -u checkmk_relay.service


Close the window
----------------

Press Ctrl-C. The script restores the official receiver:

    ^C
    Stopping agent-receiver in "relaxed" mode:
    OK

    Re-starting agent-receiver in regular mode:
    Starting agent-receiver...OK

Then confirm the site is back to its official state:

    omd status agent-receiver

Expected: "agent-receiver: running". That is the check that matters -- the relaxed
receiver binds the same port, so the official one could not have started if it were
still up. If the status says stopped, give it a few seconds and look again.

You can press Ctrl-C at any point, including in the middle. The official receiver comes
back either way; the relay simply goes back to being locked out, and you can start over.

Finally, delete the script:

    rm -f rescue-receiver.sh


If the official receiver does not come back
-------------------------------------------

The script restores the official receiver on every normal way out, including Ctrl-C in
the middle. It cannot do so if it is killed outright ("kill -9"), or if the machine it
runs on goes down. The relaxed receiver then stays up and keeps the port, so
"omd start agent-receiver" fails and "omd status agent-receiver" keeps saying stopped --
the status only ever looks at the official receiver, never at the relaxed one.

Two things are left behind in that case, and both are safe to check any time:

    ls ~/tmp/run/agent-receiver-rescue.pid ~/tmp/rescue-receiver.*

The pid file is written by the relaxed receiver and removed again when it stops, so if
it is there, the relaxed receiver probably still is too. Note that this is the state the
site is left in: it still accepts expired certificates. Clean it up as the site user:

    kill "$(cat ~/tmp/run/agent-receiver-rescue.pid)"
    rm -f ~/tmp/run/agent-receiver-rescue.pid
    rm -rf ~/tmp/rescue-receiver.*
    omd start agent-receiver

If the pid file is gone but the port is still taken, look for the process itself -- the
relaxed receiver is the only one that names itself "rescue-receiver":

    pgrep -a -f rescue-receiver

Then confirm the site is back to its official state:

    omd status agent-receiver


What the window relaxes, and what it does not
---------------------------------------------

While the window is open, the site accepts a client certificate whose validity dates
have passed. This cannot be narrowed to relays: the receiver serves the registered
agents over the same port, from a single SSL context, so an agent whose certificate has
expired is let in as well.

Everything else is unchanged: the certificate must still be issued by one of the CAs
your site trusts -- its relay CA or its agent CA -- the caller must still hold the
matching private key, and the receiver still requires the certificate's common name to
match the relay or agent ID in the URL, issued by the CA that endpoint expects. An
expired certificate can therefore act as the relay or agent it was issued for, and
nothing else.

Certificates of relays and agents you have decommissioned are accepted too, if their key
still exists somewhere and your site still knows them. That is why the window is meant to
be closed as soon as the affected relays have renewed, and why the script reports every
relay that comes in while it is open.
