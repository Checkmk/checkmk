#ifndef LogEntry_h
#define LogEntry_h

#define LOGCLASS_INFO              0
#define LOGCLASS_STATE             1
#define LOGCLASS_PROGRAM           2
#define LOGCLASS_NOTIFICATION      3
#define LOGCLASS_PASSIVECHECK      4
#define LOGCLASS_COMMAND           5
#define LOGCLASS_INVALID          -1 // never stored
#define LOGCLASS_ALL          0xffff

#include "nagios.h"

struct LogEntry
{
    time_t     _time;
    unsigned   _logclass;
    char      *_msg;       // split up with binary zeroes
    unsigned   _msglen;    // size of _msg
    char      *_text;      // points into msg
    char      *_host_name; // points into msg or is 0
    char      *_svc_desc;  // points into msg or is 0
    char      *_command_name;
    char      *_contact_name;
    int       _state;
    int       _state_type;
    int       _attempt;
    char      *_check_output;
    char      *_comment;
    
    host      *_host;
    service   *_service;
    contact   *_contact;
    command   *_command;

    LogEntry(char *line);
    ~LogEntry();

private:
    bool handleStatusEntry();
    bool handleNotificationEntry();
    bool handlePassiveCheckEntry();
    bool handleExternalCommandEntry();
    bool handleProgrammEntry();
    bool handleInfoEntry();
    int serviceStateToInt(char *s);
    int hostStateToInt(char *s);
    int stateTypeToInt(char *s);
    int startedStoppedToInt(char *s);
};

#endif // LogEntry_h

