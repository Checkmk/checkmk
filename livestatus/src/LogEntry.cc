#include <string.h>
#include "LogEntry.h"


LogEntry::LogEntry(char *line)
{
    // zero all elements as fast as possible -> default values
    bzero(this, sizeof(LogEntry));

    // make a copy of the message
    _msg = strdup(line);
    _msglen = strlen(line) + 1;

    // [1260722267] xxx - extract timestamp, validate message
    if (_msglen < 13 || _msg[0] != '[' || _msg[11] != ']')
	return; // ignore invalid lines silently
    _msg[11] = 0; // zero-terminate time stamp
    _time = atoi(_msg+1);
    _text = _msg + 13; // also skip space after timestamp
}

LogEntry::~LogEntry()
{
    free(_msg);
}


