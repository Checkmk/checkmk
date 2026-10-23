==========================
Relay Engine Architecture
==========================

Introduction
============

The relay engine is the core component that runs on hosts in segregated networks to collect monitoring data.
It implements an event-driven, queue-based architecture that coordinates multiple asynchronous processors and schedulers to execute monitoring tasks and communicate with the central Checkmk site.

This document provides detailed information about the relay engine's internal architecture, component responsibilities, and processing flows.


Architecture Overview
=====================

Event-driven design
-------------------

The relay engine uses a central event queue (Main Queue) to coordinate all activities.
This design provides several benefits:

- All components communicate through the queue, creating a complete audit trail
- Processors are decoupled and can be tested independently
- The system is naturally asynchronous and non-blocking
- Task routing logic is centralized in the main loop

Core components
---------------

The relay engine consists of three types of components:

**Main Loop**: The event dispatcher that routes tasks from the queue to appropriate processors.

**Processors**: Asynchronous workers that handle specific task types and submit results back to the queue.

**Schedulers**: Components that generate tasks at appropriate times and place them on the queue.

.. uml:: arch-comp-relay-engine-components.puml


Main Loop
=========

The main loop is the heart of the relay engine.
It continuously reads tasks from the Main Queue and routes them to the appropriate processors.

Responsibilities
----------------

- Read tasks from the Main Queue in batches for efficiency
- Route each task to the appropriate processor(s) based on task type
- Handle special cases like configuration application
- Manage graceful shutdown
- Log all task routing for debugging

Task routing
------------

The main loop uses pattern matching to route tasks:

.. code-block:: python

   match task:
       case FetchTask():
           # Route to fetcher pool for execution
           await fetcher_pool.dispatch(task)

       case FetchResult():
           # Route to both scheduler and site
           service_scheduler.dispatch(task)
           await site.dispatch(task)

       case AdHocFetchTask():
           # Route to ad-hoc fetcher pool
           await adhoc_pool.dispatch(task)

       case ConfigUpdateTask():
           # Route to configuration processor
           await config_processor.dispatch(task)

       case ApplyConfigTask():
           # Special handling: apply configuration atomically
           await apply_configuration(task)

Batch processing
----------------

The main loop processes tasks in batches rather than one at a time.
This improves throughput by reducing queue access overhead:

.. code-block:: python

   async def read_batch(queue):
       """Read all available items from queue."""
       batch = [await queue.get()]  # Wait for at least one
       while not queue.empty():
           batch.append(queue.get_nowait())
       return batch

Configuration application
--------------------------

Configuration updates receive special handling in the main loop.
When an ``ApplyConfigTask`` arrives:

1. Stop all fetcher pools
2. Update the Service Scheduler with new host/service definitions
3. Restart fetcher pools with new configuration paths
4. Update logging configuration
5. Clear cached site clients (they may have new credentials)

This ensures atomic configuration updates with no partial state.


Processors
==========

Processors are async components that handle specific task types.
The main loop routes tasks to the appropriate processor based on task type.

.. note::
   The processor list below is a snapshot from the current implementation.
   Processors may be added, removed, or refactored over time.
   For the current set of processors, see ``non-free/packages/cmk-relay-engine/cmk/relay/processors/`` in the codebase.

**Fetcher Pool**:
Manages fetcher subprocesses that execute monitoring checks.
Distributes tasks to available fetchers, handles timeouts and errors, and returns results to the main queue.

**Ad-hoc Fetcher Pool**:
Similar to regular pool but handles on-demand requests from the site (e.g., service discovery).
Uses ``fetch-ad-hoc`` binary with task-specific configurations.

**Site Processor**:
Handles all HTTP communication with the Agent Receiver.
Sends monitoring data, task results, and errors via REST API with mTLS authentication.

**Configuration Processor**:
Extracts and validates configuration archives from the site.
Manages versioned configurations and generates apply tasks for the main loop.

**Certificate Rotation Processor**:
Generates new CSRs and requests certificate renewal from the Agent Receiver before expiration.

**Site Version Update Processor**:
Tracks the Checkmk site version and triggers container updates when mismatches are detected.


Schedulers
==========

Schedulers generate tasks at appropriate times and place them on the Main Queue.

.. note::
   The scheduler list below is a snapshot from the current implementation.
   For the current set of schedulers, see ``non-free/packages/cmk-relay-engine/cmk/relay/schedulers/`` in the codebase.

**Service Scheduler**:
Tracks next check time for each configured service.
Generates ``FetchTask`` objects when checks are due, handles retry logic for failures, and respects check time periods.

**Poll Scheduler**:
Polls the Agent Receiver for pending tasks (ad-hoc requests, configuration updates.
Maintains history to prevent duplicate processing and prioritizes configuration tasks.

**Certificate Rotation Scheduler**:
Checks certificate expiration daily and triggers renewal 7 days before expiry.


Task Flows
==========

This section illustrates how different task types flow through the relay engine components.

Scheduled monitoring
--------------------

1. Service Scheduler generates ``FetchTask`` for due check
2. Main Loop routes to Fetcher Pool
3. Fetcher subprocess executes check (SNMP/Agent/Program)
4. Fetcher returns CMC protocol output as ``FetchResult``
5. Main Loop routes to both Service Scheduler (updates next check time) and Site Processor
6. Site Processor sends data to Agent Receiver
7. Agent Receiver forwards to CMC

Service discovery (ad-hoc)
---------------------------

1. User triggers discovery in UI → Check Engine creates ``RelayFetcherTrigger``
2. Trigger serializes config and POSTs ``FetchAdHocTask`` to Agent Receiver
3. Poll Scheduler retrieves task on next poll (~2-5 seconds latency)
4. Main Loop routes to Ad-hoc Fetcher Pool
5. Ad-hoc fetcher executes discovery
6. Result flows back: Fetcher → Main Loop → Site Processor → Agent Receiver
7. Original trigger polls and retrieves result

Configuration update
--------------------

1. User activates changes → Site generates config archive (tar.gz) with new serial
2. Site POSTs to Agent Receiver ``/activate-config`` endpoint
3. Poll Scheduler retrieves ``ConfigUpdateTask`` on next poll
4. Configuration Processor validates and extracts archive to versioned directory
5. If serial is newer, generates ``ApplyConfigTask`` for Main Loop
6. Main Loop applies atomically: stops fetchers → updates config → restarts fetchers
7. Site Processor confirms success to Agent Receiver

The relay continues running checks during update until the atomic apply step, ensuring zero downtime.


See Also
========

- :doc:`arch-comp-relay`: Relay system overview
- :doc:`arch-comp-relay-engine-concurrency`: Event loop, background loops, subprocess pools and threads
- :doc:`arch-comp-agent-receiver`: Agent receiver (includes relay endpoints)
