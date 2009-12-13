#ifndef LogEntry_h
#define LogEntry_h

#define LOGTYPE_STATE             0
#define LOGTYPE_INFO              1
#define LOGTYPE_PROGRAM           2
#define LOGTYPE_NOTIFICATION      3
#define LOGTYPE_PASSIVECHECK      4
#define LOGTYPE_ALL          0xffff

#include "nagios.h"

struct LogEntry
{
    time_t     _time;
    unsigned   _logtype;
    char      *_msg;       // split up with binary zeroes
    unsigned   _msglen;    // size of _msg
    char      *_text;      // points into msg
    char      *_host_name; // points into msg or is 0
    char      *_svc_desc;  // points into msg or is 0
    char      *_contact_name;   // points into msg or is 0
    host      *_host;
    service   *_service;
    contact   *_contact;
    char      *_check_output;
    char      *_perfdata;
    int        _state;     // new host or service state
    int        _hard;      // 0: hard, 1: soft

    LogEntry(char *line);
    ~LogEntry();
};

#endif // LogEntry_h

