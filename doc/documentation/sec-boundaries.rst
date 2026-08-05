===================
Security Boundaries
===================

Here we state the intended security boundaries and the resulting security
promise. Violations of these promises will be treated as vulnerabilities and
fixed. There are some exceptions and variations that might not be obvious,
these are mentioned here as well.

The promise
===========

**Authority flows outward from the central site; data flows inward.** A
compromised central site must be assumed to compromise every remote site,
relay and monitored host attached to it. A compromise of a relay, remote
site or monitored host must not extend inward or sideways.

- A GUI admin user is equivalent to the site itself (except in Checkmk Cloud).
  Other GUI users are bounded by their permissions, but permissions such as
  editing rules or installing MKPs amount to code execution and therefore carry
  full site authority - including over the remote sites and relays that
  configuration reaches.
- Agent output is data, not instructions: a monitored host may lie about
  itself, but must not gain authority over the relay or site fetching from it.
- Baked agents installed manually or via the agent bakery are installed as root
  and can therefore compromise monitored hosts.
- Multi-tenancy promises that customer data is not shared among other customers.
  (Relays are always global)

Known weakenings
================

- *Secrets are replicated to every peer*: The password store and explicit
  passwords are shared among all sites/relays. (Multi-tenancy filters by
  customer, but not for relays)
- *The user database is replicated to every remote site*: Automation user
  secrets - where cleartext storage is enabled - and password hashes of local
  users are replicated to all sites. (Multi-tenancy filters by customer)
- *Piggyback lets a host speak for other hosts*: The agent output of a host can
  contain piggyback data for other hosts.
- *Agents influence their own configuration*: Host labels discovered from agent
  output take part in rule matching, so a monitored host has some influence
  over which rules apply to it.
