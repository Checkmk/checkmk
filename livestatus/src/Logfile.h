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

class Logfile
{
    char      *_path;
    time_t     _since;
    bool       _is_loaded;
    bool       _watch;         // true only for current logfile
    ino_t      _inode;         // needed to detect switching
    fpos_t     _read_pos;      // read until this position
    unsigned   _logtypes_read; // only these types have been read
    typedef map<uint64_t, LogEntry *> _entries_t; // key is time_t . lineno
    _entries_t _entries;
    char       _linebuffer[MAX_LOGLINE];

public:
    Logfile(const char *path, bool watch);
    ~Logfile();

    void load(unsigned logtypes);
    bool isLoaded() { return _is_loaded; };
    time_t since() { return _since; };
    bool answerQuery(Query *query, time_t since, time_t until, unsigned);

private:
    void processLogLine(uint32_t, unsigned);
    uint64_t makeKey(time_t, unsigned);
};


#endif // Logfile_h

