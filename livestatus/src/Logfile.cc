#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include "Logfile.h"
#include "logger.h"
#include "LogEntry.h"
#include "Query.h"

extern int num_cached_log_messages;

Logfile::Logfile(const char *path, bool watch)
    : _path(strdup(path))
    , _since(0)
    , _is_loaded(false)
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
    logger(LG_INFO, "HIRN: Logfile %s beginnt bei %d", path, _since);
    close(fd);
}


Logfile::~Logfile()
{
    free(_path);
    for (_entries_t::iterator it = _entries.begin();
	    it != _entries.end();
	    ++it)
    {
	delete it->second;
    }
}


void Logfile::load(unsigned logclasses)
{
    // TODO: implement watch
    logger(LG_INFO, "HIRN: Klassen 0x%x sind da. Brauche 0x%x", _logclasses_read, logclasses);
    unsigned missing_types = logclasses & ~_logclasses_read;

    if (missing_types == 0)
	return;

    logger(LG_INFO, "HIRN: Datei %s: Muss Typen laden: 0x%x", _path, missing_types);

    FILE *file = fopen(_path, "r");
    if (!file) {
	logger(LG_INFO, "Cannot open logfile '%s'", _path);
	return;
    }
    
    // TODO: skip to _read_pos, if watch
    uint32_t lineno = 0;
    while (fgets(_linebuffer, MAX_LOGLINE, file))
    {
	lineno++;
	if (processLogLine(lineno, missing_types))
	    num_cached_log_messages ++;
    }	
    fgetpos(file, &_read_pos);
    _logclasses_read |= missing_types;
    fclose(file);
}


bool Logfile::processLogLine(uint32_t lineno, unsigned logclasses)
{
    LogEntry *entry = new LogEntry(_linebuffer);
    // ignored invalid lines
    if (entry->_logclass == LOGCLASS_INVALID) {
	delete entry;
	return false;
    }
    if ((1 << entry->_logclass) & logclasses) {
	uint64_t key = makeKey(entry->_time, lineno);
	_entries.insert(make_pair(key, entry));
	return true;
    }
    else {
	delete entry;
	return false;
    }
}


bool Logfile::answerQuery(Query *query, time_t since, time_t until, unsigned logclasses)
{
    load(logclasses); // make sure all messages are present
    uint64_t sincekey = makeKey(since, 0);
    _entries_t::iterator it = _entries.lower_bound(sincekey);
    while (it != _entries.end())
    {
	LogEntry *entry = it->second;
	if (entry->_time >= until)
	    return false; // end found
	query->processDataset(entry);
	++it;
    }
    return true;
}


uint64_t Logfile::makeKey(time_t t, unsigned lineno)
{
    return (uint64_t)((uint64_t)t << 32) | (uint64_t)lineno;
}

