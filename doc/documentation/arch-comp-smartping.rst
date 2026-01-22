==========
Smart Ping
==========

Introduction and goals
======================

Smart Ping is a high-performance host monitoring mechanism exclusive to the Checkmk Microcore (CMC).
It provides efficient reachability checks for monitored hosts, designed to overcome the performance
limitations of traditional active check mechanisms like ``check_icmp``.

Traditional active checks require the core to spawn a subprocess (``check_icmp``) for each host check,
wait for the response, and process the result. This approach creates significant overhead: process
creation, context switching, and individual timeouts for each host. In large-scale environments with
thousands of hosts, this becomes a major performance bottleneck.

Smart Ping solves this through a hybrid approach:

1. **Continuous ICMP probing**: A single ``icmpsender`` helper process continuously sends ICMP echo
   requests to all monitored hosts
2. **Passive traffic monitoring**: A single ``icmpreceiver`` helper process captures *any* network
   traffic (ICMP echo replies, TCP SYN/RST packets) from monitored hosts
3. **Instant detection**: When traffic from a host is detected, it is immediately marked as UP
   without subprocess overhead

Key benefits:

* **Performance**: Eliminates per-host subprocess creation overhead
* **Scalability**: Single sender/receiver pair handles thousands of hosts
* **Efficiency**: Detects reachability from any network traffic, not just ping responses
* **Speed**: Sub-second detection of host availability


Requirements overview
---------------------

**Functional requirements:**

* Monitor host reachability without per-host subprocess overhead
* Detect host UP state from any incoming network traffic (ICMP, TCP)
* Handle both IPv4 and IPv6 traffic
* Mark hosts as DOWN when no traffic is received within configured timeout

**Quality goals:**

* Minimal CPU and memory footprint regardless of host count
* Sub-second detection of host availability
* Scalable to tens of thousands of hosts
* Reliable timeout handling for unreachable hosts


Architecture
============

White-box overall system
-------------------------

Smart Ping consists of three main components:

.. uml::

   package "Checkmk Microcore (CMC)" {
      component "Core" as core
      component "ICMPSender" as sender
      component "ICMPReceiver" as receiver
   }
   
   package "Helper Processes" {
      component "icmpsender\n(CAP_NET_RAW)" as icmpsender_proc
      component "icmpreceiver\n(CAP_NET_RAW)" as icmpreceiver_proc
   }
   
   cloud "Network" as network
   
   core --> sender : queue IP addresses
   sender --> icmpsender_proc : stdin: IP addresses
   icmpsender_proc --> sender : stderr: error messages
   icmpsender_proc --> network : ICMP echo requests
   
   network --> icmpreceiver_proc : captured packets\n(ICMP, TCP SYN/RST)
   icmpreceiver_proc --> receiver : stdout: source IP addresses
   icmpreceiver_proc --> receiver : stderr: error messages
   receiver --> core : process results


**Core Components:**

1. **Core**: Manages Smart Ping scheduling and timeout detection
2. **ICMPSender**: Manages communication with the icmpsender helper process
3. **ICMPReceiver**: Manages communication with the icmpreceiver helper process
4. **icmpsender**: Helper process that continuously sends ICMP echo requests using raw sockets
5. **icmpreceiver**: Helper process that captures network packets using libpcap


Component interactions
~~~~~~~~~~~~~~~~~~~~~~

The **Core** manages a schedule of hosts configured with Smart Ping. It periodically extracts
hosts from the schedule and queues their IP addresses to **ICMPSender**.

**ICMPSender** buffers IP addresses and writes them to the stdin of the ``icmpsender`` helper
process. The helper continuously sends ICMP echo requests using raw sockets to probe host
reachability.

**ICMPReceiver** reads IP addresses from the stdout of the ``icmpreceiver`` helper process,
which uses libpcap to capture packets from all network interfaces. When a packet from a
monitored host is captured (ICMP echo reply, TCP SYN, or TCP RST), the helper writes the
source IP address to stdout.

The **Core** processes results from **ICMPReceiver** and marks hosts as UP. If no traffic
is received within the configured timeout, the Core marks the host as DOWN.


Interfaces
----------

Configuration
~~~~~~~~~~~~~

Smart Ping is configured globally via ``cmk/base/default_config/cmc.py`` and per-host via
rulesets. Configuration includes check intervals, timeout thresholds, and tuning parameters
for the sender and receiver processes.

Configuration is serialized to Protocol Buffers and passed to the helper processes at
startup and on configuration changes.


Host check command
~~~~~~~~~~~~~~~~~~

Hosts use Smart Ping when their check command is ``@smartping``. This special marker is
recognized by the CMC and triggers Smart Ping scheduling instead of subprocess-based active checks.

The command is automatically set when the host check command is configured as "Smart" and
the host is not a cluster host (cluster hosts use parent-based reachability instead).


Data flow
~~~~~~~~~

**IP address queueing** (Core → icmpsender):

* Binary protocol: ``<version_byte><address_bytes>``
* IPv4: 1 byte (value 4) + 4 address bytes
* IPv6: 1 byte (value 6) + 16 address bytes


**Result reporting** (icmpreceiver → Core):

* Same binary format as queueing
* Each captured packet from a monitored host triggers one result message


Runtime view
============

Normal operation
----------------

.. uml::

   participant "Core" as core
   participant "ICMPSender" as sender
   participant "icmpsender" as sender_proc
   participant "icmpreceiver" as receiver_proc
   participant "ICMPReceiver" as receiver
   participant "Network" as net
   
   == Initialization ==
   core -> sender : updateConfig()
   core -> receiver : updateConfig()
   sender -> sender_proc : spawn with config
   receiver -> receiver_proc : spawn with config
   receiver_proc -> net : start packet capture
   
   == Regular checking ==
   loop Every check_interval
      core -> core : extract hosts from schedule
      core -> sender : queuePing(ip_address)
      sender -> sender : buffer IP addresses
      sender -> sender_proc : write buffered IPs
      sender_proc -> net : send ICMP echo
   end
   
   == Packet detection ==
   net -> receiver_proc : any packet from host
   receiver_proc -> receiver : write source IP
   receiver -> core : processResult()
   core -> core : mark host UP


Timeout handling
----------------

If no traffic is detected from a host within its configured Smart Ping timeout,
the Core handles the timeout:

.. uml::

   participant "Core" as core
   participant "Host" as host
   
   loop Every check_interval
      core -> host : check last_check_time
      alt timeout exceeded
         core -> host : mark as DOWN
         core -> core : log timeout
      else within timeout
         core -> core : continue waiting
      end
   end


Helper process management
-------------------------

The ICMPSender and ICMPReceiver components manage the lifecycle of helper processes:

**Startup:**

1. Spawns helper processes with connected stdin/stdout/stderr pipes
2. Helper processes run with ``CAP_NET_RAW`` capability for raw socket and packet capture access

**Communication:**

1. Event loop polls file descriptors for I/O readiness
2. Reads/writes data in binary protocol format
3. Logs error messages from stderr

**Shutdown:**

1. Terminates helper processes
2. For icmpreceiver, forceful termination is required (blocked in libpcap loop)
3. Cleans up file descriptors and buffers


ICMP sender process
-------------------

The ``icmpsender`` helper continuously sends ICMP echo requests:

* Opens multiple raw sockets for parallelism
* Reads IP addresses from stdin
* Constructs and sends ICMP echo request packets
* Supports configurable throttling to control network load


ICMP receiver process
---------------------

The ``icmpreceiver`` helper passively captures network packets:

* Uses libpcap to capture from all network interfaces
* Applies BPF filter for ICMP and TCP SYN/RST packets
* Handles VLAN encapsulation
* Extracts source IP addresses
* Writes detected IPs to stdout


Deployment view
===============

Process hierarchy
-----------------

::

   cmc (Checkmk Microcore)
   ├── icmpsender (spawned by ICMPSender)
   │   ├── Capabilities: CAP_NET_RAW
   │   ├── Multiple raw sockets
   │   └── stdin/stdout/stderr pipes
   └── icmpreceiver (spawned by ICMPReceiver)
       ├── Capabilities: CAP_NET_RAW
       ├── libpcap on all interfaces
       └── stdin/stdout/stderr pipes


File system locations
---------------------

* **Executables**: ``lib/cmc/icmpsender``, ``lib/cmc/icmpreceiver``
* **Logs**: Integrated into CMC logs (``var/log/cmc.log``) with logger ``cmk.smartping``


Permissions
-----------

Both helper binaries require Linux capabilities:

* **icmpsender**: ``CAP_NET_RAW`` for creating raw sockets to send ICMP packets
* **icmpreceiver**: ``CAP_NET_RAW`` for using libpcap to capture packets

Capabilities are set during package installation. If the system doesn't support capabilities
(old kernel, unsupported filesystem), the installer falls back to setuid for compatibility.


Risks and technical debts
==========================

Risks
-----

**Privileged helper processes**
   Both icmpsender and icmpreceiver run with ``CAP_NET_RAW`` capability. While they have
   minimal attack surface and perform limited operations, any vulnerability could potentially
   be exploited for privilege escalation or network sniffing.

**Packet capture on all interfaces**
   The icmpreceiver captures packets from all network interfaces, which could be a privacy
   concern in some environments. Only source IP addresses are extracted and processed.

**False positives from spurious traffic**
   Any network traffic from a host's IP address will mark it as UP, including network scans
   or spoofed packets. This could mask actual host failures if spurious traffic is present.

Technical debts
---------------

**Hard-coded packet types**
   The BPF filter for packet capture is hard-coded. Supporting new protocols requires
   code changes to icmpreceiver.

**Limited observability**
   No metrics or detailed statistics about Smart Ping performance are exposed, making
   tuning and troubleshooting difficult.

**Global network capture scope**
   Smart Ping captures from all interfaces globally, which may not work correctly in
   containerized or network-isolated environments with namespaces.
