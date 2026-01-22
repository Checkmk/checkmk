============
Relay Engine
============

Introduction and goals
======================

The relay is a separate installable component to collect monitoring data in segregated networks, i.e. the relay can talk to the site but not vice versa.
For simplicity the relay acts like a very lite remote site, it will collect monitoring data for hosts and forwards them to a site. However, it only runs the fetchers and not the checkers.
Once installed the relay is very hands off for the user, Checkmk will take care to sync configuration and version updates to it.

* Monitor hosts in a segregated network.
* Regularly push monitoring data to a site.
* Fetch monitoring data on demand (e.g. for service discovery in UI).
* Report about it's own health

Architecture
============

White-box overall system
------------------------

The relay component consists of multiple packages in Checkmk

**Relay Engine**:
The relay engine is installed on a remote host, together with the fetchers.
The engine is responsible to check for tasks from the site and schedule the fetchers for each host.
To ask for tasks or send monitoring data it contacts the agent receiver.

**Agent Receiver**:
The agent receiver is responsible for the communication with relay engines.
The communication is strictly one way, so the relay-engine can contact the agent-receiver but not the other way around.

**Fetcher**
Fetchers are involved on two places with the relay.
The first is the relay-engine runs the fetchers itself.
The second is that fetchers can send a fetch task to the relay (via agent receiver) for irregular tasks like a service discovery.

Relay Engine
------------
The relay-engine consists of a single main loop that reads from a queue and distributes the message on the queue to a bunch of processors.
In addition there are scheduler objects that can schedule recurring tasks.
Processors are simple classes that run asynchronously and act on tasks from the main loop.
Processors do not directly communicate back to the main loop, instead they submit to a main queue.
The main loop wakes up periodically and empties the main queue.
Here is an abstract picture of the architecture.

.. uml:: arch-comp-relay-abstract.puml


Examples for a Processor is the FetcherPool.
It can fetch data from a host and provides the result back to the main loop via the Main Queue.
Another example is the Site which is responsible for sending monitoring data from a fetcher to the site.
Here is a more concrete example with the fetcher pool and site as processors.

.. uml:: arch-comp-relay-example.puml

*Important* The FetcherPool and SiteProxy never directly share data.
Instead they let the main loop decide that to do and who acts next some data.

With this architecture we want to achieve some key benefits:

- Processors are simple objects with an input and output (no state)
- Processors are maximally decoupled, they know nothing of each other
- Each Processor class has one task
- The MainQueue is an event log of what the system did 

With this we can easily test each processor, and the main loop and queue act more as a router to which processors a task needs to be send.

Interfaces
^^^^^^^^^^
The relay engine does not expose any interfaces.
It only talks to the REST API of the agent receiver
