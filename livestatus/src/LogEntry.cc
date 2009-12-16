#include <string.h>
#include "LogEntry.h"
#include "strutil.h"
#include "logger.h"

LogEntry::LogEntry(char *line)
{
    // zero all elements as fast as possible -> default values
    bzero(this, sizeof(LogEntry));

    // make a copy of the message
    _msg = strdup(line);
    _msglen = strlen(line);
    while (_msglen > 0 && _msg[_msglen-1] == '\n')
	_msg[--_msglen] = '\0';

    // [1260722267] xxx - extract timestamp, validate message
    if (_msglen < 13 || _msg[0] != '[' || _msg[11] != ']')
	return; // ignore invalid lines silently
    _msg[11] = 0; // zero-terminate time stamp
    _time = atoi(_msg+1);
    _text = _msg + 13; // also skip space after timestamp

    // now classify the log message
    if (handleStatusEntry() ||
	handleNotificationEntry() ||
	handlePassiveCheckEntry() ||
	handleExternalCommandEntry() ||
	handleProgrammEntry() ||
	handleMiscEntry())
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
}

int LogEntry::serviceStateToInt(char *s)
{
    // WARN, CRIT, OK, UNKNOWN
    switch (s[0]) {
	case 'O': return 0;
	case 'W': return 1;
	case 'C': return 2;
	case 'U': return 3;
	default: return 4;
    }
}


int LogEntry::hostStateToInt(char *s)
{
    // WARN, CRIT, OK, UNKNOWN
    switch (s[1]) {
	case 'P': return 0;
	case 'O': return 1;
	case 'N': return 2;
	default: return 3;
    }
}

int LogEntry::stateTypeToInt(char *s)
{
    return s[0] == 'H' ? 1 : 0;
}


int LogEntry::startedStoppedToInt(char *s)
{
    return !strcmp(s, "STARTED") ? 1 : 0;
}


bool LogEntry::handleStatusEntry()
{
    // HOST states
    if (!strncmp(_text, "INITIAL HOST STATE: ", 20)
       || !strncmp(_text, "CURRENT HOST STATE: ", 20)
       || !strncmp(_text, "HOST ALERT: ", 12))
    {
	_logtype = LOGTYPE_STATE;
	char *scan = _text;
	_text = next_token(&scan, ':');
	scan++;

	_host_name    = next_token(&scan);
	_state        = hostStateToInt(next_token(&scan));
	_state_type   = stateTypeToInt(next_token(&scan));
	_attempt      = atoi(next_token(&scan));
	_check_output = next_token(&scan);
	return true;
    }
    else if (!strncmp(_text, "HOST DOWNTIME ALERT: ", 21))
    {
	_logtype = LOGTYPE_STATE;
	char *scan = _text;
	_text = next_token(&scan, ':');
	scan++;
	
	_host_name    = next_token(&scan);
	_state_type   = startedStoppedToInt(next_token(&scan));
	_comment      = next_token(&scan) + 1;
	return true;
    }

    // SERVICE states
    else if (!strncmp(_text, "INITIAL SERVICE STATE: ", 23)
       || !strncmp(_text, "CURRENT SERVICE STATE: ", 23)
       || !strncmp(_text, "SERVICE ALERT: ", 15))
    {
	_logtype = LOGTYPE_STATE;
	char *scan = _text;
	_text = next_token(&scan, ':');
	scan++;

	_host_name    = next_token(&scan);
	_svc_desc     = next_token(&scan);
	_state        = serviceStateToInt(next_token(&scan));
	_state_type   = stateTypeToInt(next_token(&scan));
	_attempt      = atoi(next_token(&scan));
	_check_output = next_token(&scan);
	return true;
    }
    else if (!strncmp(_text, "SERVICE DOWNTIME ALERT: ", 24))
    {
	_logtype = LOGTYPE_STATE;
	char *scan = _text;
	_text = next_token(&scan, ':');
	scan++;
	
	_host_name    = next_token(&scan);
	_svc_desc     = next_token(&scan);
	_state_type   = startedStoppedToInt(next_token(&scan));
	_comment      = next_token(&scan) + 1;
	return true;
    }
    return false;

}

bool LogEntry::handleNotificationEntry()
{
    if (!strncmp(_text, "HOST NOTIFICATION: ", 19)
        || !strncmp(_text, "SERVICE NOTIFICATION: ", 22))
    {
	_logtype = LOGTYPE_NOTIFICATION;
	bool svc = _text[0] == 'S';
	char *scan = _text;
	_text = next_token(&scan, ':');
	scan++;
	
	_contact_name  = next_token(&scan);
	_host_name     = next_token(&scan);
	if (svc) _svc_desc = next_token(&scan);
	_state_type    = stateTypeToInt(next_token(&scan));
	_command_name  = next_token(&scan);
	_check_output  = next_token(&scan);
	return true;
    }
    return false;
}

bool LogEntry::handlePassiveCheckEntry()
{
    return false;
}

bool LogEntry::handleExternalCommandEntry()
{
    if (!strncmp(_text, "EXTERNAL COMMAND:", 17)) 
    {
	_logtype = LOGTYPE_COMMAND;
	_text = _text + 18;
	return true; // TODO: join with host/service information?
	/* Damit wir die restlichen Spalten ordentlich befuellen, braeuchten
	   wir eine komplette Liste von allen external commands und
	   deren Parameteraufbau. Oder gibt es hier auch eine bessere
	   Loesung? */
    }
}

bool LogEntry::handleProgrammEntry()
{
    return false;
}

bool LogEntry::handleMiscEntry()
{
    return false;
}




LogEntry::~LogEntry()
{
    free(_msg);
}


