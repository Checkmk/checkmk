#ifndef LogEntry_h
#define LogEntry_h

#define LOGCLASS_INFO              0 // all messages not in any other class
#define LOGCLASS_ALERT             1 // alerts: the change service/host state
#define LOGCLASS_PROGRAM           2 // important programm events (restart, ...)
#define LOGCLASS_NOTIFICATION      3 // host/service notifications
#define LOGCLASS_PASSIVECHECK      4 // passive checks
#define LOGCLASS_COMMAND           5 // external commands
#define LOGCLASS_STATE             6 // initial or current states
#define LOGCLASS_INVALID          -1 // never stored
#define LOGCLASS_ALL          0xffff

#include "nagios.h"

struct LogEntry
{
    unsigned   _lineno;      // line number in file
    time_t     _time;
    unsigned   _logclass;
    char      *_complete;  // copy of complete unsplit message
    char      *_options;   // points into _complete after ':'
    char      *_msg;       // split up with binary zeroes
    unsigned   _msglen;    // size of _msg
    char      *_text;      // points into msg
    char      *_host_name; // points into msg or is 0
    char      *_svc_desc;  // points into msg or is 0
    char      *_command_name;
    char      *_contact_name;
    int       _state;
    char      *_state_type;
    int       _attempt;
    char      *_check_output;
    char      *_comment;
    
    host      *_host;
    service   *_service;
    contact   *_contact;
    command   *_command;

    LogEntry(unsigned lineno, char *line);
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
};

#endif // LogEntry_h

