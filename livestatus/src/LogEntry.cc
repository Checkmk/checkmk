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

#include <string.h>
#include <time.h>
#include <stdlib.h>

#include "LogEntry.h"
#include "strutil.h"
#include "logger.h"

LogEntry::LogEntry(unsigned lineno, char *line, unsigned logclasses = LOGCLASS_ALL)
{
    // zero all elements as fast as possible -> default values
    bzero(this, sizeof(LogEntry));
    _lineno = lineno;

    // make a copy of the message and strip trailing newline
    _msg = strdup(line);
    _msglen = strlen(line);
    while (_msglen > 0 && _msg[_msglen-1] == '\n')
        _msg[--_msglen] = '\0';


    // keep unsplitted copy of the message (needs lots of memory,
    // maybe we could optimize that one day...)
    _complete = strdup(_msg);

    // pointer to options (everything after ':')
    _options = _complete;
    while (*_options && *_options != ':')
        _options ++;
    if (*_options) // line contains colon
    {
        _options ++; // skip ':'
        while (*_options == ' ')
            _options ++; // skip space after ':'
    }

    // [1260722267] xxx - extract timestamp, validate message
    if (_msglen < 13 || _msg[0] != '[' || _msg[11] != ']') {
        _logclass = LOGCLASS_INVALID;
        return; // ignore invalid lines silently
    }
    _msg[11] = 0; // zero-terminate time stamp
    _time = atoi(_msg+1);
    _text = _msg + 13; // also skip space after timestamp

    // If LOGCLASS_INFO is in logclasses we can't thin out the function calls
    logclasses = 1 << LOGCLASS_INFO & logclasses ? LOGCLASS_ALL : logclasses;

    // now classify the log message. Some messages
    // refer to other table, some do not.
    if (((1 << LOGCLASS_ALERT & logclasses) && handleStatusEntry()) ||
        ((1 << LOGCLASS_NOTIFICATION & logclasses) && handleNotificationEntry()) ||
        ((1 << LOGCLASS_PASSIVECHECK & logclasses) && handlePassiveCheckEntry()) ||
        ((1 << LOGCLASS_COMMAND & logclasses) && handleExternalCommandEntry())
        )
    {
        if (_host_name)
            _host = find_host(_host_name);
        if (_svc_desc)
            _service = find_service(_host_name, _svc_desc);
        if (_contact_name)
            _contact = find_contact(_contact_name);
        if (_command_name)
            _command = find_command(_command_name);
    }
    else {
        (1 << LOGCLASS_PROGRAM & logclasses) && handleProgrammEntry(); // Performance killer strstr!
        (1 << LOGCLASS_TEXT    & logclasses) && handleTextEntry();
    }


    // rest is LOGCLASS_INFO
}

LogEntry::~LogEntry()
{
    free(_msg);
    free(_complete);
}




inline bool LogEntry::handleStatusEntry()
{
//// TODO: check if its worth of implementing
//// Most lines are status entries anyway... 
//    int len_text = strlen(_text);
//    if (len_text < 12)
//        return false;
//
//    // Quick basic check
//    // We can skip all other strcmp() calls
//    // if the first letter does not match
//    switch (_text[0]) {
//        case 'I':
//        case 'C':
//        case 'S':
//        case 'T':
//        case 'H':
//            break;
//        default:
//            return false;
//    }

    // HOST states
    if (!strncmp(_text, "INITIAL HOST STATE: ", 20)
     || !strncmp(_text, "CURRENT HOST STATE: ", 20)
     || !strncmp(_text, "HOST ALERT: ", 12))
    {
        if (_text[0] == 'H'){
            _logclass = LOGCLASS_ALERT;
            _type     = ALERT_HOST;
        }
        else if(_text[0] == 'I') {
            _logclass = LOGCLASS_STATE;
            _type     = STATE_HOST_INITIAL;
        }
        else {
            _logclass = LOGCLASS_STATE;
            _type     = STATE_HOST;
        }

        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name    = next_token(&scan, ';');
        _state        = hostStateToInt(save_next_token(&scan, ';'));
        _state_type   = next_token(&scan, ';');
        _attempt      = atoi(save_next_token(&scan, ';'));
        _check_output = next_token(&scan, ';');
        return true;
    }
    else if (!strncmp(_text, "HOST DOWNTIME ALERT: ", 21))
    {
        _logclass = LOGCLASS_ALERT;
        _type     = DOWNTIME_ALERT_HOST;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name    = next_token(&scan, ';');
        _state_type   = next_token(&scan, ';');
        _comment      = next_token(&scan, ';') + 1;
        return true;
    }
    else if (!strncmp(_text, "HOST FLAPPING ALERT: ", 21))
    {
        _logclass = LOGCLASS_ALERT;
        _type     = FLAPPING_HOST;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name    = next_token(&scan, ';');
        _state_type   = next_token(&scan, ';');
        _comment      = next_token(&scan, ';') + 1;
        return true;
    }

    // SERVICE states
    else if (!strncmp(_text, "INITIAL SERVICE STATE: ", 23)
          || !strncmp(_text, "CURRENT SERVICE STATE: ", 23)
          || !strncmp(_text, "SERVICE ALERT: ", 15))
    {
        if (_text[0] == 'S'){
            _logclass = LOGCLASS_ALERT;
            _type     = ALERT_SERVICE;
        }
        else if(_text[0] == 'I') {
            _logclass = LOGCLASS_STATE;
            _type     = STATE_SERVICE_INITIAL;
        }
        else{
            _logclass = LOGCLASS_STATE;
            _type     = STATE_SERVICE;
        }
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name    = next_token(&scan, ';');
        _svc_desc     = next_token(&scan, ';');
        _state        = serviceStateToInt(save_next_token(&scan, ';'));
        _state_type   = next_token(&scan, ';');
        _attempt      = atoi(save_next_token(&scan, ';'));
        _check_output = next_token(&scan, ';');
        return true;
    }
    else if (!strncmp(_text, "SERVICE DOWNTIME ALERT: ", 24))
    {
        _logclass = LOGCLASS_ALERT;
        _type     = DOWNTIME_ALERT_SERVICE;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name    = next_token(&scan, ';');
        _svc_desc     = next_token(&scan, ';');
        _state_type   = next_token(&scan, ';');
        _comment      = next_token(&scan, ';') + 1;
        return true;
    }
    else if (!strncmp(_text, "SERVICE FLAPPING ALERT: ", 24))
    {
        _logclass = LOGCLASS_ALERT;
        _type     = FLAPPING_SERVICE;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name    = next_token(&scan, ';');
        _svc_desc     = next_token(&scan, ';');
        _state_type   = next_token(&scan, ';');
        _comment      = next_token(&scan, ';') + 1;
        return true;
    }


    else if (!strncmp(_text, "TIMEPERIOD TRANSITION: ", 23))
    {
        _logclass = LOGCLASS_STATE;
        _type     = TIMEPERIOD_TRANSITION;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _command_name  = next_token(&scan, ';');
        _check_output  = next_token(&scan, ';');
        _state_type    = next_token(&scan, ';');
        return true;
    }

    return false;
}

// Function is UNUSED and under DEVELOPMENT
// Might replace the handleStatusEntry function one day
// Its purpose is to reduce the amount of strcmp to speedup
// the read process. Risk: LOGCLASS Classification accuracy might suffer
inline bool LogEntry::handleStatusEntryBetter()
{
    int len_text = strlen(_text);
    if (len_text < 12)
        return false;

    // Patterns
//  "INITIAL SERVICE STATE: "
//  "CURRENT SERVICE STATE: "
//  "SERVICE ALERT: "
//  "SERVICE DOWNTIME ALERT: "
//  "SERVICE FLAPPING ALERT: "
//  "TIMEPERIOD TRANSITION: "
//  "INITIAL HOST STATE: "
//  "CURRENT HOST STATE: "
//  "HOST ALERT: "
//  "HOST DOWNTIME ALERT: "
//  "HOST FLAPPING ALERT: "

    // SERVICES
    if (!strncmp(_text, "SERVICE", 7) || !strncmp(_text + 8, "SERVICE", 7)) {
        bool is_state = false;
        if (!strncmp(_text, "INITIAL", 7)) {
            _logclass = LOGCLASS_STATE;
            _type     = STATE_SERVICE_INITIAL;
            is_state = true;
        } else if (!strncmp(_text + 8, "ALERT", 5)) {
            _logclass = LOGCLASS_ALERT;
            _type     = ALERT_SERVICE;
            is_state = true;
        } else if (!strncmp(_text, "CURRENT", 7)) {
            _logclass = LOGCLASS_STATE;
            _type     = STATE_SERVICE;
            is_state = true;
        }
        if (is_state) {
            char *scan = _text;
            _text = next_token(&scan, ':');
            scan++;

            _host_name    = next_token(&scan, ';');
            _svc_desc     = next_token(&scan, ';');
            _state        = serviceStateToInt(save_next_token(&scan, ';'));
            _state_type   = next_token(&scan, ';');
            _attempt      = atoi(save_next_token(&scan, ';'));
            _check_output = next_token(&scan, ';');
            return true;
        }

        if (!strncmp(_text + 8, "DOWNTIME", 8)){
            _logclass = LOGCLASS_ALERT;
            _type     = DOWNTIME_ALERT_SERVICE;
            char *scan = _text;
            _text = next_token(&scan, ':');
            scan++;

            _host_name    = next_token(&scan, ';');
            _svc_desc     = next_token(&scan, ';');
            _state_type   = next_token(&scan, ';');
            _comment      = next_token(&scan, ';') + 1;
            return true;
        } else if (!strncmp(_text + 8, "FLAPPING", 8)) {
            _logclass = LOGCLASS_ALERT;
            _type     = FLAPPING_SERVICE;
            char *scan = _text;
            _text = next_token(&scan, ':');
            scan++;

            _host_name    = next_token(&scan, ';');
            _svc_desc     = next_token(&scan, ';');
            _state_type   = next_token(&scan, ';');
            _comment      = next_token(&scan, ';') + 1;
            return true;
        }
    } else if (!strncmp(_text, "HOST", 5) || !strncmp(_text + 8, "HOST", 5)) {
        bool is_state = false;
        if (!strncmp(_text, "INITIAL", 7)) {
            _logclass = LOGCLASS_STATE;
            _type     = STATE_HOST_INITIAL;
            is_state = true;
        } else if (!strncmp(_text + 6, "ALERT", 5)) {
            _logclass = LOGCLASS_ALERT;
            _type     = ALERT_HOST;
            is_state = true;
        } else if (!strncmp(_text, "CURRENT", 7)) {
            _logclass = LOGCLASS_STATE;
            _type     = STATE_HOST;
            is_state = true;
        }
        if (is_state) {
            char *scan = _text;
            _text = next_token(&scan, ':');
            scan++;

            _host_name    = next_token(&scan, ';');
            _svc_desc     = next_token(&scan, ';');
            _state        = serviceStateToInt(save_next_token(&scan, ';'));
            _state_type   = next_token(&scan, ';');
            _attempt      = atoi(save_next_token(&scan, ';'));
            _check_output = next_token(&scan, ';');
            return true;
        }
        else if (!strncmp(_text + 6, "DOWNTIME", 8))
        {
            _logclass = LOGCLASS_ALERT;
            _type     = DOWNTIME_ALERT_HOST;
            char *scan = _text;
            _text = next_token(&scan, ':');
            scan++;

            _host_name    = next_token(&scan, ';');
            _state_type   = next_token(&scan, ';');
            _comment      = next_token(&scan, ';') + 1;
            return true;
        }
        else if (!strncmp(_text + 6, "HOST FLAPPING ALERT: ", 8))
        {
            _logclass = LOGCLASS_ALERT;
            _type     = FLAPPING_HOST;
            char *scan = _text;
            _text = next_token(&scan, ':');
            scan++;

            _host_name    = next_token(&scan, ';');
            _state_type   = next_token(&scan, ';');
            _comment      = next_token(&scan, ';') + 1;
            return true;
        }

    }
    else if (!strncmp(_text, "TIMEPERIOD TRANSITION: ", 23))
    {
        _logclass = LOGCLASS_STATE;
        _type     = TIMEPERIOD_TRANSITION;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _command_name  = next_token(&scan, ';');
        _check_output  = next_token(&scan, ';');
        _state_type    = next_token(&scan, ';');
        return true;
    }
    return false;
}


inline bool LogEntry::handleNotificationEntry()
{
    if (!strncmp(_text, "HOST NOTIFICATION: ", 19)
        || !strncmp(_text, "SERVICE NOTIFICATION: ", 22))
    {
        _logclass = LOGCLASS_NOTIFICATION;
        bool svc = _text[0] == 'S';
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _contact_name  = next_token(&scan, ';');
        _host_name     = next_token(&scan, ';');
        if (svc) {
            _svc_desc = next_token(&scan, ';');
            _state_type = save_next_token(&scan, ';');
            _state = serviceStateToInt(_state_type);
        }
        else {
            _state_type = save_next_token(&scan, ';');
            _state = hostStateToInt(_state_type);
        }

        _command_name  = next_token(&scan, ';');
        _check_output  = next_token(&scan, ';');
        return true;
    }

    return false;
}

inline bool LogEntry::handlePassiveCheckEntry()
{
    if (!strncmp(_text, "PASSIVE SERVICE CHECK: ", 23)
        || !strncmp(_text, "PASSIVE HOST CHECK: ", 20))
    {
        _logclass = LOGCLASS_PASSIVECHECK;
        bool svc = _text[8] == 'S';
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name    = next_token(&scan, ';');
        if (svc)
            _svc_desc     = next_token(&scan, ';');
        _state        = atoi(save_next_token(&scan, ';'));
        _check_output = next_token(&scan, ';');
        return true;
    }

    return false;
}

inline bool LogEntry::handleExternalCommandEntry()
{
    if (!strncmp(_text, "EXTERNAL COMMAND:", 17))
    {
        _logclass = LOGCLASS_COMMAND;
        char *scan = _text;
        _text = next_token(&scan, ':');
        return true; // TODO: join with host/service information?
        /* Damit wir die restlichen Spalten ordentlich befuellen, braeuchten
           wir eine komplette Liste von allen external commands und
           deren Parameteraufbau. Oder gibt es hier auch eine bessere
           Loesung? */
    }
    return false;
}

inline bool LogEntry::handleTextEntry() {
    if (!strncmp(_text, "LOG VERSION: 2.0", 16)){
        _logclass = LOGCLASS_PROGRAM;
        _type     = LOG_VERSION;
        return true;
    }
    else if (!strncmp(_text, "logging initial states", 22)){
        _logclass = LOGCLASS_PROGRAM;
        _type     = LOG_INITIAL_STATES;
        return true;
    }
    return false;
}

inline bool LogEntry::handleProgrammEntry()
{
    if (strstr(_text, "starting... (PID=")){
        _logclass = LOGCLASS_PROGRAM;
        _type     = NAGIOS_STARTING;
        return true;
    }
    else if (strstr(_text, "restarting...") ||
            strstr(_text, "shutting down...") ||
            strstr(_text, "Bailing out") ||
            strstr(_text, "active mode...") ||
            strstr(_text, "standby mode..."))
    {
        _logclass = LOGCLASS_PROGRAM;
        return true;
    }
    return false;
}


inline int LogEntry::serviceStateToInt(char *s)
{
    char *last = s + strlen(s) - 1;
    if (*last == ')')
        last--;

    // WARN, CRITICAL, OK, UNKNOWN, RECOVERY
    switch (*last) {
        case 'K': return 0;
        case 'Y': return 0;
        case 'G': return 1;
        case 'L': return 2;
        case 'N': return 3;
        default:  return 4;
    }
}


inline int LogEntry::hostStateToInt(char *s)
{
    char *last = s + strlen(s) - 1;
    if (*last == ')')
        last--;

    // UP, DOWN, UNREACHABLE, RECOVERY
    switch (*last) {
        case 'P': return 0;
        case 'Y': return 0;
        case 'N': return 1;
        case 'E': return 2;
        default:  return 3;
    }
}

