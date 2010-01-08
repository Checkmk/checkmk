#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include "Logfile.h"
#include "logger.h"
#include "LogEntry.h"
#include "Query.h"
#include "TableLog.h"

extern int num_cached_log_messages;

Logfile::Logfile(const char *path, bool watch)
    : _path(strdup(path))
    , _since(0)
    , _watch(watch)
    , _inode(0)
      , _logclasses_read(0)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
	logger(LG_INFO, "Cannot open logfile '%s'", path);
	return;
    }

    char line[12];
    if (12 != read(fd, line, 12)) {
	close(fd);
	return; // ignoring. might be empty
    }

    if (line[0] != '[' || line[11] != ']') {
	logger(LG_INFO, "Ignoring logfile '%s':does not begin with '[123456789] '", path);
	close(fd);
	return;
    }

    line[11] = 0;
    _since = atoi(line+1);
    close(fd);
}


Logfile::~Logfile()
{
    free(_path);
    flush();
}


void Logfile::flush()
{
    for (_entries_t::iterator it = _entries.begin();
	    it != _entries.end();
	    ++it)
    {
	delete it->second;
    }
    _entries.clear();
    _logclasses_read = 0;
}


void Logfile::load(TableLog *tablelog, time_t since, time_t until, unsigned logclasses)
{
    unsigned missing_types = logclasses & ~_logclasses_read;

    FILE *file = 0;
    // The current logfile has the _watch flag set to true.
    // In that case, if the logfile has grown, we need to 
    // load the rest of the file, even if no logclasses
    // are missing.
    if (_watch) {
	file = fopen(_path, "r");
	if (!file) {
	    logger(LG_INFO, "Cannot open logfile '%s'", _path);
	    return;
	}

	// file might have grown. Read all classes that we already
	// have read to the end of the file
	if (_logclasses_read) {
	    fsetpos(file, &_read_pos); // continue at previous end
	    load(file, _logclasses_read, tablelog, since, until, logclasses);
	    fgetpos(file, &_read_pos);
	}
	if (missing_types) {
	    fseek(file, 0, SEEK_SET);
	    load(file, missing_types, tablelog, since, until, logclasses);
	    _logclasses_read |= missing_types;
	}
	fclose(file);
    }
    else 
    {
	if (missing_types == 0)
	    return;

	file = fopen(_path, "r");
	if (!file) {
	    logger(LG_INFO, "Cannot open logfile '%s'", _path);
	    return;
	}

	load(file, missing_types, tablelog, since, until, logclasses);
	fclose(file);
	_logclasses_read |= missing_types;
    }
}

void Logfile::load(FILE *file, unsigned missing_types, 
	TableLog *tablelog, time_t since, time_t until, unsigned logclasses)
{
    uint32_t lineno = 0;
    while (fgets(_linebuffer, MAX_LOGLINE, file))
    {
	lineno++;
	if (processLogLine(lineno, missing_types)) {
	    num_cached_log_messages ++;
	    tablelog->handleNewMessage(this, since, until, logclasses); // memory management
	}
    }	
}


long Logfile::freeMessages(unsigned logclasses)
{
    long freed = 0;
    for (_entries_t::iterator it = _entries.begin();
	    it != _entries.end();
	    ++it)
    {
	LogEntry *entry = it->second;
	if ((1 << entry->_logclass) & logclasses)
	{
	    delete it->second;
	    _entries.erase(it);
	    freed ++;
	}
    }
    _logclasses_read &= ~logclasses;
    return freed;
}


bool Logfile::processLogLine(uint32_t lineno, unsigned logclasses)
{
    LogEntry *entry = new LogEntry(lineno, _linebuffer);
    // ignored invalid lines
    if (entry->_logclass == LOGCLASS_INVALID) {
	delete entry;
	return false;
    }
    if ((1 << entry->_logclass) & logclasses) {
	uint64_t key = makeKey(entry->_time, lineno);
	if (_entries.find(key) == _entries.end())
	    _entries.insert(make_pair(key, entry));
	return true;
    }
    else {
	delete entry;
	return false;
    }
}


bool Logfile::answerQuery(Query *query, TableLog *tablelog, time_t since, time_t until, unsigned logclasses)
{
    load(tablelog, since, until, logclasses); // make sure all messages are present
    uint64_t sincekey = makeKey(since, 0);
    _entries_t::iterator it = _entries.lower_bound(sincekey);
    while (it != _entries.end())
    {
	LogEntry *entry = it->second;
	if (entry->_time >= until)
	    return false; // end found
	if (!query->processDataset(entry))
	    return false; // limit exceeded
	++it;
    }
    return true;
}


uint64_t Logfile::makeKey(time_t t, unsigned lineno)
{
    return (uint64_t)((uint64_t)t << 32) | (uint64_t)lineno;
}

