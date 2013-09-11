// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef LogEntry_h
#define LogEntry_h

#define LOGCLASS_INFO              0 // all messages not in any other class
#define LOGCLASS_ALERT             1 // alerts: the change service/host state
#define LOGCLASS_PROGRAM           2 // important programm events (restart, ...)
#define LOGCLASS_NOTIFICATION      3 // host/service notifications
#define LOGCLASS_PASSIVECHECK      4 // passive checks
#define LOGCLASS_COMMAND           5 // external commands
#define LOGCLASS_STATE             6 // initial or current states
#define LOGCLASS_TEXT              7 // specific text passages. e.g "logging initial states"
#define LOGCLASS_INVALID          -1 // never stored
#define LOGCLASS_ALL          0xffff

#include "nagios.h"

enum LogEntryType {
    NONE,
    ALERT_HOST,
    ALERT_SERVICE,
    DOWNTIME_ALERT_HOST,
    DOWNTIME_ALERT_SERVICE,
    STATE_HOST,
    STATE_HOST_INITIAL,
    STATE_SERVICE,
    STATE_SERVICE_INITIAL,
    FLAPPING_HOST,
    FLAPPING_SERVICE,
    TIMEPERIOD_TRANSITION,
    NAGIOS_STARTING,
    LOG_VERSION,
    LOG_INITIAL_STATES,
};

struct LogEntry
{
    unsigned     _lineno;      // line number in file
    time_t       _time;
    unsigned     _logclass;
    LogEntryType _type;
    char        *_complete;  // copy of complete unsplit message
    char        *_options;   // points into _complete after ':'
    char        *_msg;       // split up with binary zeroes
    unsigned     _msglen;    // size of _msg
    char        *_text;      // points into msg
    char        *_host_name; // points into msg or is 0
    char        *_svc_desc;  // points into msg or is 0
    char        *_command_name;
    char        *_contact_name;
    int         _state;
    char        *_state_type;
    int         _attempt;
    char        *_check_output;
    char        *_comment;

    host        *_host;
    service     *_service;
    contact     *_contact;
    command     *_command;

    LogEntry(unsigned lineno, char *line, unsigned logclasses);
    ~LogEntry();

private:
    bool handleStatusEntry();
    bool handleStatusEntryBetter();
    bool handleNotificationEntry();
    bool handlePassiveCheckEntry();
    bool handleExternalCommandEntry();
    bool handleProgrammEntry();
    bool handleLogversionEntry();
    bool handleInfoEntry();
    bool handleTextEntry();
    int serviceStateToInt(char *s);
    int hostStateToInt(char *s);
};

#endif // LogEntry_h

