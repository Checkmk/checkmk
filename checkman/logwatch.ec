title: Forward Logwatch Messages to the Event Console
agents: linux, windows, aix, solaris
catalog: os/files
license: GPL
distribution: check_mk
description:
 This check processes the output of agents with the logwatch plugin. The windows agent has built
 in this extension. The check does not interpret or rate the incoming messages, it only reads
 and forwards them to the configured Check_MK Event Console.

inventory:
 One service "Log Forwarding" is created on each host when the option {logwatch_forward_to_ec} is
 set to {True}.

[parameters]
parameters (dict): This check works with the following keys:

 {"method"}: This value can have the following format: {None} (Default value): Tries to detect
 the path to the local mkeventd event pipe. {"/path/to/pipe"}: The path to a local mkeventd
 event pipe. {("udp", "127.0.0.1", 514)}: The udp host and port to forward the messages to.
 {("tcp", "127.0.0.1", 514)}: The tcp host and port to forward the messages to. It can also
 be configured to use the spooling mechanism of the event console. To configure this, either
 configure {"socket:"} to detect the spooling directory of the local event console or
 {"socket:/path/to/spool/directory"} to configure the path explicit to the local spool directory.
