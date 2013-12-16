// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                     |_____|                      |
// |          __  __ _                   ____                         |
// |         |  \/  (_) ___ _ __ ___    / ___|___  _ __ ___           |
// |         | |\/| | |/ __| '__/ _ \  | |   / _ \| '__/ _ \          |
// |         | |  | | | (__| | | (_) | | |__| (_) | | |  __/          |
// |         |_|  |_|_|\___|_|  \___/   \____\___/|_|  \___|          |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of the Check_MK Micro Core.  Copyright by Mathias
// Kettner,  Preysingstr. 74,  81667 München, Germany.  All rights are
// reserved. You may *not* redistribute or modify this software unless
// you have a  written  permission of the owner.  This file  is  *not*
// available under GNU GPL. If you do not like this then please use  a
// different monitoring core.
//
// Please note: This software is experimental. Use at your own risk.

#include <string.h>
#include <time.h>
#include <stdlib.h>

#include "LogEntry.h"
#include "strutil.h"
#include "logger.h"

LogEntry::LogEntry(unsigned lineno, char *line)
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

    // now classify the log message. Some messages
    // refer to other table, some do not.
    if (handleStatusEntry() ||
        handleNotificationEntry() ||
        handlePassiveCheckEntry() ||
        handleExternalCommandEntry()
        )
    {
        updateReferences();
    }
    else {
        handleTextEntry() || handleProgrammEntry(); // Performance killer strstr in handleProgrammEntry!
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
        return true;
    }

    return false;
}

// Examples of host notifications. Beware CUSTOM and DOWNTIME notifications
// have a different column order. This can be considered as a bug. But we
// need to parse that anyway.
// HOST NOTIFICATION: omdadmin;localhost;check-mk-notify;DOWNTIMESTOPPED (UP);mk
// HOST NOTIFICATION: omdadmin;localhost;CUSTOM (UP);check-mk-notify;OK - 127.0.0.1: rta 0.055ms, lost 0%;omdadmin;TEST
// HOST NOTIFICATION: omdadmin;localhost;DOWN;check-mk-notify;Manually set to Down by omdadmin
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
        if (svc)
            _svc_desc = next_token(&scan, ';');

        _state_type = save_next_token(&scan, ';');
        _command_name  = next_token(&scan, ';');

        if (svc)
            _state = serviceStateToInt(_state_type);
        else
            _state = hostStateToInt(_state_type);

        // If that state is not parsable then we assume that the order
        // is swapped
        if ((svc && _state == 4) ||
            (!svc && _state == 3))
        {
            char *swap = _state_type;
            _state_type = _command_name;
            _command_name = swap;
            if (svc)
                _state = serviceStateToInt(_state_type);
            else
                _state = hostStateToInt(_state_type);
        }

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

inline bool LogEntry::handleTextEntry()
{
    if (!strncmp(_text, "LOG VERSION: 2.0", 16))
    {
        _logclass = LOGCLASS_PROGRAM;
        _type     = LOG_VERSION;
        return true;
    }
    else if (!strncmp(_text, "logging initial states", 22)
           || !strncmp(_text, "logging intitial states", 23))
    {
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
    if (*last == ')') // handle CUSTOM (UP) and DOWNTIMESTOPPED (DOWN)
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


unsigned LogEntry::updateReferences()
{
    unsigned updated = 0;
    if (_host_name) {
        _host = find_host(_host_name);
        updated++;
    }
    if (_svc_desc) {
        _service = find_service(_host_name, _svc_desc);
        updated++;
    }
    if (_contact_name) {
        _contact = find_contact(_contact_name);
        updated++;
    }
    if (_command_name) {
        _command = find_command(_command_name);
        updated++;
    }
    return updated;
}
