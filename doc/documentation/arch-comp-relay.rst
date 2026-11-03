============
Relay System
============

Introduction and goals
======================

The relay system enables Checkmk to monitor hosts in segregated or isolated networks where bidirectional communication between the central site and monitored hosts is not possible.
The relay acts as a lightweight remote monitoring proxy that can reach both the isolated hosts and the central site, forwarding monitoring data in one direction only.

Key capabilities:

* Monitor hosts in segregated networks
* Regularly push monitoring data from isolated networks to the central site
* Support on-demand data fetching for service discovery and diagnostics
* Automatically sync configuration and version updates from the central site
* Support SNMP, agent-based, and program-based data sources
* Provide certificate-based authentication and encryption

The relay operates on a pull-from-site, push-to-site model.
The relay periodically polls the central site for tasks and configuration updates, executes data collection tasks locally in the isolated network, and pushes results back to the site.

Architecture
============

White-box overall system
------------------------

The relay system consists of four main components distributed across packages:

**Relay Engine** (``non-free/packages/cmk-relay-engine``):
The relay engine is a containerized service installed on a host in the segregated network.
It runs fetchers to collect monitoring data and manages all local task execution.
The engine polls the central site for work, executes tasks, and pushes results back.
It handles scheduled monitoring checks, ad-hoc fetch requests, configuration updates, and certificate rotation.

**Agent Receiver** (``packages/cmk-agent-receiver``):
The agent receiver provides REST API endpoints for relay communication as interface for the relay.
It receives monitoring data from relays, manages task queues for each relay, handles relay registration and certificate management, and forwards data to the Checkmk core.
Communication is strictly initiated by the relay.

**Relay Protocols** (``packages/cmk-relay-protocols``):
This package defines shared data structures and communication protocols used between the relay engine and agent receiver.
It includes task specifications, monitoring data formats, configuration structures, and API request/response models.
These protocols ensure type-safe communication between components.

**Fetcher Integration** (``non-free/packages/cmk-core-helpers``):
The site-side fetchers can trigger ad-hoc data collection on relays.
When a user initiates service discovery or diagnostics in the UI, the fetcher uses a ``RelayFetcherTrigger`` to create a task in the agent receiver, which the relay picks up, executes, and returns results for.

Component interaction
^^^^^^^^^^^^^^^^^^^^^

.. uml:: arch-comp-relay-system.puml

Implementation Constraints
^^^^^^^^^^^^^^^^^^^^^^^^^^

The relay system operates under four fundamental constraints.
First, the relay and CMC must maintain version synchronization, a fundamental limitation of the fetcher/checker split architecture.
The fetcher and checker components are not independently versioned and assume code consistency across the site, as they are usually updated together.
Second, the relay must initiate all communication with the central site, as the architecture cannot assume the site can directly reach the relay in segregated networks.
Third, all communication with the relay must be treated as asynchronous with no guarantee of relay availability.
Fourth, the relay can only be registered with a central site, not with remote sites in a distributed setup.
The agent receiver rejects relay registration on remote sites with HTTP 403.

Relay Engine architecture
--------------------------

The relay engine uses an event-driven architecture with a main loop, asynchronous processors, and schedulers.
Processors handle specific tasks (fetching, sending data, configuration updates) and communicate only through a central queue, ensuring decoupling and testability.

For detailed architecture information, see :doc:`arch-comp-relay-engine`.


Data flows
----------

The relay system implements three main data flows:

**Scheduled monitoring**:
The relay engine periodically executes monitoring checks for configured hosts/services.
This is a simplified re-implementation of the fetching logic in the monitoring core.
Results are sent to the Agent Receiver, which forwards them to CMC.

**Ad-hoc fetch** :
Any UI interaction that requires fetcher output triggers an Ad-hoc fetch on the relay.
I.e. when a user triggers service discovery in the UI, the site creates a task in the Agent Receiver.
The relay polls for tasks, executes the fetch, and returns results. Typical latency is 2-5 seconds.

**Configuration updates**:
When a user activates changes, the site pushes a configuration archive to the Agent Receiver.
The relay polls for the config, validates it, and applies it atomically with zero downtime.

For detailed flow diagrams and internal processing, see :doc:`arch-comp-relay-engine`.


Deployment
==========

Container package
-----------------

The relay engine is deployed as a container image built with Bazel (OCI format).
The container is identical for all editions that support the relay, there are no edition specific relay builds.
The container definition is in ``omd/non-free/relay/`` and includes:

- Relay engine application (``non-free/packages/cmk-relay-engine``)
- Communication protocols (``packages/cmk-relay-protocols``)
- Fetcher helpers (``non-free/packages/cmk-core-helpers``)
- Check engine and plugin APIs
- Required Python dependencies

The container can be loaded with Docker or Podman using the provided loader scripts.

Installation
------------

The relay is installed in segregated networks using the ``install_relay.sh`` script, which:

1. Loads the container image from a tar archive
2. Sets up the relay configuration directory
3. Registers the relay with the Checkmk site
4. Configures systemd units for automatic updates
5. Starts the relay engine container

For details, see ``omd/non-free/relay/README.md``.

Automatic updates
-----------------

The relay automatically updates itself when the site version changes:

1. When the relay polls the Agent Receiver, it receives the site version in the response header
2. If the version differs from the relay's current version, the relay writes the new version to ``site-version.txt``
3. A systemd path unit monitors this file and triggers the update manager when it changes
4. The update manager pulls the new container image from the registry and tags it locally
5. Podman auto-update restarts the container with the new image

This ensures relays stay in sync with the site version without manual intervention.
The entire update process typically completes within minutes.


Security
========

Authentication
--------------

The relay system uses mutual TLS (mTLS) for all communication:

1. During registration, the relay generates a CSR with a unique relay ID
2. The site's CA signs the certificate, binding it to the relay ID
3. The relay uses the certificate for all subsequent HTTPS requests
4. The agent receiver validates the certificate on each request
5. The relay ID in the certificate must match the URL path

Certificate rotation happens automatically before expiration (typically triggered 7 days before expiry).

Authorization
-------------

Each relay is identified by its certificate's Common Name (CN).
The agent receiver:

- Validates that the CN matches the ``relay_id`` in the URL path
- Ensures the relay can only access its own tasks and data
- Requires site authentication for privileged operations like configuration updates

Network security
----------------

- All communication uses HTTPS with TLS 1.2+
- The relay initiates all connections (outbound only from the segregated network)
- No inbound ports need to be opened in the segregated network's firewall
- The relay trusts only the site's CA certificate

Secrets handling
----------------

- Passwords and secrets in configuration are encrypted before transmission
- The relay stores a secrets key to decrypt configuration data
- Ad-hoc tasks include temporary CA certificates for HTTPS checks
- Secrets are provided to fetcher processes via environment variables, never written to disk


See Also
========

- :doc:`arch-comp-relay-engine`: Detailed relay engine internals
- :doc:`arch-comp-relay-monitoring`: How site and relay components interact, per use case
- :doc:`arch-comp-agent-receiver`: Agent receiver (includes relay support)
- :doc:`arch-comp-checkengine`: Check engine architecture
