#ifndef Logfile_h
#define Logfile_h

#include <sys/types.h>
#include <stdio.h>
#include <stdint.h>
#include <map>

using namespace std;

#define MAX_LOGLINE 65536

class LogEntry;
class Query;
class TableLog;

class Logfile
{
    char      *_path;
    time_t     _since;
    bool       _is_loaded;
    bool       _watch;         // true only for current logfile
    ino_t      _inode;         // needed to detect switching
    fpos_t     _read_pos;      // read until this position
    unsigned   _logclasses_read; // only these types have been read
    typedef map<uint64_t, LogEntry *> _entries_t; // key is time_t . lineno
    _entries_t _entries;
    char       _linebuffer[MAX_LOGLINE];

public:
    Logfile(const char *path, bool watch);
    ~Logfile();

    char *path() { return _path; };
    void load(TableLog *tablelog, time_t since, time_t until, unsigned logclasses);
    bool isLoaded() { return _is_loaded; };
    time_t since() { return _since; };
    long numEntries() { return _entries.size(); };
    bool answerQuery(Query *query, TableLog *tl, time_t since, time_t until, unsigned);
    long freeMessages(unsigned logclasses);

private:
    void deleteLogentries();
    void load(FILE *file, unsigned missing_types, TableLog *, time_t since, time_t until, unsigned logclasses);
    bool processLogLine(uint32_t, unsigned);
    uint64_t makeKey(time_t, unsigned);
};


#endif // Logfile_h

