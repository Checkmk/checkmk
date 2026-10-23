# IBM SVC / Spectrum Virtualize

Monitoring for **IBM SAN Volume Controller (SVC)** storage systems and the
compatible **IBM Spectrum Virtualize** family (e.g. IBM Storwize / FlashSystem).

Data is collected by the `agent_ibmsvc` special agent, which connects to the
system over SSH and runs `ls*` administration commands (system, enclosure,
mdisk, mdiskgrp, host, node, port and performance statistics). The check
plugins in this package parse that output to monitor capacity, hardware health,
port status, the event log and I/O performance.
