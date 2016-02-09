// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

#include "LogEntry.h"
#include <stdlib.h>
#include <string.h>
#include "strutil.h"

LogEntry::LogEntry(unsigned lineno, char *line) {
    // zero all elements as fast as possible -> default values
    bzero(this, sizeof(LogEntry));
    _lineno = lineno;

    // make a copy of the message and strip trailing newline
    _msg = strdup(line);
    _msglen = strlen(line);
    while (_msglen > 0 && _msg[_msglen - 1] == '\n') {
        _msg[--_msglen] = '\0';

        // keep unsplitted copy of the message (needs lots of memory,
        // maybe we could optimize that one day...)
    }
    _complete = strdup(_msg);

    // pointer to options (everything after ':')
    _options = _complete;
    while ((*_options != 0) && *_options != ':') {
        _options++;
    }
    if (*_options != 0)  // line contains colon
    {
        _options++;  // skip ':'
        while (*_options == ' ') {
            _options++;  // skip space after ':'
        }
    }

    // [1260722267] xxx - extract timestamp, validate message
    if (_msglen < 13 || _msg[0] != '[' || _msg[11] != ']') {
        _logclass = LOGCLASS_INVALID;
        return;  // ignore invalid lines silently
    }
    _msg[11] = 0;  // zero-terminate time stamp
    _time = atoi(_msg + 1);
    _text = _msg + 13;  // also skip space after timestamp

    // now classify the log message. Some messages
    // refer to other table, some do not.
    if (handleStatusEntry() || handleNotificationEntry() ||
        handlePassiveCheckEntry() || handleExternalCommandEntry()) {
        updateReferences();
    } else {
        handleTextEntry() || handleProgrammEntry();  // Performance killer
                                                     // strstr in
                                                     // handleProgrammEntry!
    }
    // rest is LOGCLASS_INFO
}

LogEntry::~LogEntry() {
    free(_msg);
    free(_complete);
}

bool LogEntry::handleStatusEntry() {
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
    if ((strncmp(_text, "INITIAL HOST STATE: ", 20) == 0) ||
        (strncmp(_text, "CURRENT HOST STATE: ", 20) == 0) ||
        (strncmp(_text, "HOST ALERT: ", 12) == 0)) {
        if (_text[0] == 'H') {
            _logclass = LOGCLASS_ALERT;
            _type = ALERT_HOST;
        } else if (_text[0] == 'I') {
            _logclass = LOGCLASS_STATE;
            _type = STATE_HOST_INITIAL;
        } else {
            _logclass = LOGCLASS_STATE;
            _type = STATE_HOST;
        }

        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        _state = hostStateToInt(safe_next_token(&scan, ';'));
        _state_type = next_token(&scan, ';');
        _attempt = atoi(safe_next_token(&scan, ';'));
        _check_output = next_token(&scan, ';');
        return true;
    }
    if (strncmp(_text, "HOST DOWNTIME ALERT: ", 21) == 0) {
        _logclass = LOGCLASS_ALERT;
        _type = DOWNTIME_ALERT_HOST;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        _state_type = next_token(&scan, ';');
        _comment = next_token(&scan, ';');
        return true;
    }
    if (strncmp(_text, "HOST ACKNOWLEDGE ALERT: ", 24) == 0) {
        _logclass = LOGCLASS_ALERT;
        _type = ACKNOWLEDGE_ALERT_HOST;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        _state_type = next_token(&scan, ';');
        _contact_name = next_token(&scan, ';');
        _comment = next_token(&scan, ';');
        return true;
    }
    if (strncmp(_text, "HOST FLAPPING ALERT: ", 21) == 0) {
        _logclass = LOGCLASS_ALERT;
        _type = FLAPPING_HOST;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        _state_type = next_token(&scan, ';');
        _comment = next_token(&scan, ';');
        return true;
    }

    // SERVICE states
    if ((strncmp(_text, "INITIAL SERVICE STATE: ", 23) == 0) ||
        (strncmp(_text, "CURRENT SERVICE STATE: ", 23) == 0) ||
        (strncmp(_text, "SERVICE ALERT: ", 15) == 0)) {
        if (_text[0] == 'S') {
            _logclass = LOGCLASS_ALERT;
            _type = ALERT_SERVICE;
        } else if (_text[0] == 'I') {
            _logclass = LOGCLASS_STATE;
            _type = STATE_SERVICE_INITIAL;
        } else {
            _logclass = LOGCLASS_STATE;
            _type = STATE_SERVICE;
        }
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        _svc_desc = next_token(&scan, ';');
        _state = serviceStateToInt(safe_next_token(&scan, ';'));
        _state_type = next_token(&scan, ';');
        _attempt = atoi(safe_next_token(&scan, ';'));
        _check_output = next_token(&scan, ';');
        return true;
    }

    if (strncmp(_text, "SERVICE DOWNTIME ALERT: ", 24) == 0) {
        _logclass = LOGCLASS_ALERT;
        _type = DOWNTIME_ALERT_SERVICE;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        _svc_desc = next_token(&scan, ';');
        _state_type = next_token(&scan, ';');
        _comment = next_token(&scan, ';');
        return true;
    }

    if (strncmp(_text, "SERVICE ACKNOWLEDGE ALERT: ", 27) == 0) {
        _logclass = LOGCLASS_ALERT;
        _type = ACKNOWLEDGE_ALERT_SERVICE;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        _svc_desc = next_token(&scan, ';');
        _state_type = next_token(&scan, ';');
        _contact_name = next_token(&scan, ';');
        _comment = next_token(&scan, ';');
        return true;
    }

    if (strncmp(_text, "SERVICE FLAPPING ALERT: ", 24) == 0) {
        _logclass = LOGCLASS_ALERT;
        _type = FLAPPING_SERVICE;
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        _svc_desc = next_token(&scan, ';');
        _state_type = next_token(&scan, ';');
        _comment = next_token(&scan, ';');
        return true;
    }

    if (strncmp(_text, "TIMEPERIOD TRANSITION: ", 23) == 0) {
        _logclass = LOGCLASS_STATE;
        _type = TIMEPERIOD_TRANSITION;
        return true;
    }

    return false;
}

// Examples of host notifications. Beware CUSTOM and DOWNTIME notifications
// have a different column order. This can be considered as a bug. But we
// need to parse that anyway.
// HOST NOTIFICATION: omdadmin;localhost;check-mk-notify;DOWNTIMESTOPPED (UP);mk
// HOST NOTIFICATION: omdadmin;localhost;CUSTOM (UP);check-mk-notify;OK -
// 127.0.0.1: rta 0.055ms, lost 0%;omdadmin;TEST
// HOST NOTIFICATION: omdadmin;localhost;DOWN;check-mk-notify;Manually set to
// Down by omdadmin
bool LogEntry::handleNotificationEntry() {
    if ((strncmp(_text, "HOST NOTIFICATION: ", 19) == 0) ||
        (strncmp(_text, "SERVICE NOTIFICATION: ", 22) == 0)) {
        _logclass = LOGCLASS_NOTIFICATION;
        bool svc = _text[0] == 'S';
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _contact_name = next_token(&scan, ';');
        _host_name = next_token(&scan, ';');
        if (svc) {
            _svc_desc = next_token(&scan, ';');
        }

        _state_type = safe_next_token(&scan, ';');
        _command_name = next_token(&scan, ';');

        if (svc) {
            _state = serviceStateToInt(_state_type);
        } else {
            _state = hostStateToInt(_state_type);
        }

        // If that state is not parsable then we assume that the order
        // is swapped
        if ((svc && _state == 4) || (!svc && _state == 3)) {
            const char *swap = _state_type;
            _state_type = _command_name;
            _command_name = swap;
            if (svc) {
                _state = serviceStateToInt(_state_type);
            } else {
                _state = hostStateToInt(_state_type);
            }
        }

        _check_output = next_token(&scan, ';');
        return true;
    }

    return false;
}

bool LogEntry::handlePassiveCheckEntry() {
    if ((strncmp(_text, "PASSIVE SERVICE CHECK: ", 23) == 0) ||
        (strncmp(_text, "PASSIVE HOST CHECK: ", 20) == 0)) {
        _logclass = LOGCLASS_PASSIVECHECK;
        bool svc = _text[8] == 'S';
        char *scan = _text;
        _text = next_token(&scan, ':');
        scan++;

        _host_name = next_token(&scan, ';');
        if (svc) {
            _svc_desc = next_token(&scan, ';');
        }
        _state = atoi(safe_next_token(&scan, ';'));
        _check_output = next_token(&scan, ';');
        return true;
    }

    return false;
}

bool LogEntry::handleExternalCommandEntry() {
    if (strncmp(_text, "EXTERNAL COMMAND:", 17) == 0) {
        _logclass = LOGCLASS_COMMAND;
        char *scan = _text;
        _text = next_token(&scan, ':');
        return true;  // TODO(mk): join with host/service information?
        /* Damit wir die restlichen Spalten ordentlich befuellen, braeuchten
           wir eine komplette Liste von allen external commands und
           deren Parameteraufbau. Oder gibt es hier auch eine bessere
           Loesung? */
    }
    return false;
}

bool LogEntry::handleTextEntry() {
    if (strncmp(_text, "LOG VERSION: 2.0", 16) == 0) {
        _logclass = LOGCLASS_PROGRAM;
        _type = LOG_VERSION;
        return true;
    }
    if ((strncmp(_text, "logging initial states", 22) == 0) ||
        (strncmp(_text, "logging intitial states", 23) == 0)) {
        _logclass = LOGCLASS_PROGRAM;
        _type = LOG_INITIAL_STATES;
        return true;
    }
    return false;
}

bool LogEntry::handleProgrammEntry() {
    if ((strstr(_text, "starting...") != nullptr) ||
        (strstr(_text, "active mode...") != nullptr)) {
        _logclass = LOGCLASS_PROGRAM;
        _type = CORE_STARTING;
        return true;
    }
    if ((strstr(_text, "shutting down...") != nullptr) ||
        (strstr(_text, "Bailing out") != nullptr) ||
        (strstr(_text, "standby mode...") != nullptr)) {
        _logclass = LOGCLASS_PROGRAM;
        _type = CORE_STOPPING;
        return true;
    }
    if (strstr(_text, "restarting...") != nullptr) {
        _logclass = LOGCLASS_PROGRAM;
        return true;
    }
    return false;
}

int LogEntry::serviceStateToInt(const char *s) {
    if (s == nullptr) {
        return 3;  // can happen at garbled log line
    }

    const char *last = s + strlen(s) - 1;
    if (*last == ')') {
        last--;
    }

    // WARN, CRITICAL, OK, UNKNOWN, RECOVERY
    switch (*last) {
        case 'K':
            return 0;
        case 'Y':
            return 0;
        case 'G':
            return 1;
        case 'L':
            return 2;
        case 'N':
            return 3;
        default:
            return 4;
    }
}

int LogEntry::hostStateToInt(const char *s) {
    if (s == nullptr) {
        return 2;  // can happen at garbled log line
    }

    const char *last = s + strlen(s) - 1;
    if (*last == ')') {  // handle CUSTOM (UP) and DOWNTIMESTOPPED (DOWN)
        last--;
    }

    // UP, DOWN, UNREACHABLE, RECOVERY
    switch (*last) {
        case 'P':
            return 0;
        case 'Y':
            return 0;
        case 'N':
            return 1;
        case 'E':
            return 2;
        default:
            return 3;
    }
}

unsigned LogEntry::updateReferences() {
    unsigned updated = 0;
    if (_host_name != nullptr) {
        _host = find_host(_host_name);
        updated++;
    }
    if (_svc_desc != nullptr) {
        _service = find_service(_host_name, _svc_desc);
        updated++;
    }
    if (_contact_name != nullptr) {
        _contact = find_contact(_contact_name);
        updated++;
    }
    if (_command_name != nullptr) {
        // Older Nagios headers are not const-correct... :-P
        _command = find_command(const_cast<char *>(_command_name));
        updated++;
    }
    return updated;
}
