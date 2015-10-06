// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.


#ifndef types_h
#define types_h


#include <windows.h>
#include <string>
// umm, this is a C header, not actually part of C++ until C++11. This may be a problem in older
// MSVCs
#include <stdint.h>


static const unsigned int SECTION_CHECK_MK     = 0x00000001;
static const unsigned int SECTION_UPTIME       = 0x00000002;
static const unsigned int SECTION_DF           = 0x00000004;
static const unsigned int SECTION_PS           = 0x00000008;
static const unsigned int SECTION_MEM          = 0x00000010;
static const unsigned int SECTION_SERVICES     = 0x00000020;
static const unsigned int SECTION_WINPERF      = 0x00000040;
static const unsigned int SECTION_LOGWATCH     = 0x00000080;
static const unsigned int SECTION_SYSTEMTIME   = 0x00000100;
static const unsigned int SECTION_PLUGINS      = 0x00000200;
static const unsigned int SECTION_LOCAL        = 0x00000400;
static const unsigned int SECTION_SPOOL        = 0x00000800;
static const unsigned int SECTION_MRPE         = 0x00001000;
static const unsigned int SECTION_FILEINFO     = 0x00002000;
static const unsigned int SECTION_LOGFILES     = 0x00004000;


// Needed for only_from
struct ipspec {
    uint32_t address;
    uint32_t netmask;
    int      bits;
};

// Configuration for section [winperf]
struct winperf_counter {
    int   id;
    char *name;
};

// Configuration entries from [logwatch] for individual logfiles
struct eventlog_config_entry {
    eventlog_config_entry(int level, int hide_context, const char *name)
        : name(name)
        , level(level)
        , hide_context(hide_context)
    {}

    std::string name;
    int level;
    int hide_context;
};

// How single scripts are executed
enum script_execution_mode {
    SYNC, // inline
    ASYNC // delayed
};

// How delayed scripts are executed
enum script_async_execution {
    PARALLEL,
    SEQUENTIAL
};


// States for plugin and local scripts
enum script_status {
    SCRIPT_IDLE,
    SCRIPT_FINISHED,
    SCRIPT_COLLECT,
    SCRIPT_ERROR,
    SCRIPT_TIMEOUT,
    SCRIPT_NONE,
};

enum script_type {
    PLUGIN,
    LOCAL,
    MRPE
};

// Used by mrpe and local/plugins scripts
struct runas_include{
    char        path[256];
    char        user[256];
    script_type type;
};

struct script_container {
    char                  *path;        // full path with interpreter, cscript, etc.
    char                  *script_path; // path of script
    int                    max_age;
    int                    timeout;
    int                    max_retries;
    int                    retry_count;
    time_t                 buffer_time;
    char                  *buffer;
    char                  *buffer_work;
    char                  *run_as_user;
    script_type            type;
    script_execution_mode  execution_mode;
    script_status          status;
    script_status          last_problem;
    volatile bool          should_terminate;
    HANDLE                 worker_thread;
    HANDLE                 job_object;
};

struct retry_config{
    char         *pattern;
    int           retries;
};


enum file_encoding {
    UNDEF,
    DEFAULT,
    UNICODE,
};


// Stores the condition pattern together with its state
// Pattern definition within the config file:
//      C = *critpatternglobdescription*
struct condition_pattern {
    char  state;
    char *glob_pattern;
};
typedef std::vector<condition_pattern*> condition_patterns_t;


// A textfile instance containing information about various file
// parameters and the pointer to the matching pattern_container
struct logwatch_textfile {
    char                 *path;
    unsigned long long    file_id;   // used to detect if a file has been replaced
    unsigned long long    file_size; // size of the file
    unsigned long long    offset;    // current fseek offset in the file
    bool                  missing;   // file no longer exists
    bool                  nocontext; // do not report ignored lines
    file_encoding         encoding;
    condition_patterns_t *patterns;  // glob patterns applying for this file
};


// Single element of a globline:
// C:/tmp/Testfile*.log
struct glob_token {
    char *pattern;
    bool  nocontext;
    bool  found_match;
};
typedef std::vector<glob_token*> glob_tokens_t;

// Container for all globlines read from the config
// The following is considered a globline
// textfile = C:\Logfile1.txt C:\tmp\Logfile*.txt
struct globline_container {
    glob_tokens_t        tokens;
    condition_patterns_t patterns;
};


// Command definitions for MRPE
struct mrpe_entry {
    char run_as_user[256];
    char command_line[256];
    char plugin_name[64];
    char service_description[256];
};


// Our memory of what event logs we know and up to
// which record entry we have seen its messages so
// far.
struct eventlog_file_state {
    eventlog_file_state(char *name)
        : name(name)
        , num_known_records(0)
        , newly_discovered(true)
    {}
    std::string name;
    DWORD num_known_records;
    bool newly_discovered;
};


struct eventlog_hint_t {
    char  *name;
    DWORD record_no;
};


struct timeout_config {
    char *pattern;
    int  timeout;
};


struct cache_config {
    char *pattern;
    int  max_age;
};


struct execution_mode_config {
    char                  *pattern;
    script_execution_mode  mode;
};


typedef std::vector<winperf_counter*>       winperf_counters_t;
typedef std::vector<ipspec*>                only_from_t;
typedef std::vector<std::string>            execute_suffixes_t;
typedef std::vector<logwatch_textfile*>     logwatch_textfiles_t;
typedef std::vector<globline_container*>    logwatch_globlines_t;
typedef std::vector<eventlog_config_entry>  eventlog_config_t;
typedef std::vector<mrpe_entry*>            mrpe_entries_t;
typedef std::vector<runas_include*>         mrpe_include_t;
typedef std::vector<eventlog_file_state>    eventlog_state_t;
typedef std::vector<eventlog_hint_t*>       eventlog_hints_t;
typedef std::vector<char*>                  fileinfo_paths_t;
typedef std::vector<retry_config*>          retry_count_configs_t;
typedef std::vector<timeout_config*>        timeout_configs_t;
typedef std::vector<cache_config*>          cache_configs_t;
typedef std::vector<execution_mode_config*> execution_mode_configs_t;
typedef std::vector<runas_include*>         script_include_t;



// poor mans binder for a member function. Unnecessary if we ever use a C++11 compiler
template <typename ObjectT, typename ReturnT>
class KVBind {
public:
    typedef ReturnT (ObjectT::*Function)(char*, char*);

    KVBind(ObjectT *obj = NULL)
        : _obj(obj)
        , _func(NULL)
    { }

    void setFunc(Function func)
    {
        this->_func = func;
    }

    bool isUnset() const { return (_obj == NULL) || (_func == NULL); }

    ReturnT operator()(char *key, char *value) {
        return (_obj->*_func)(key, value);
    }

private:

    ObjectT *_obj;
    Function _func;

};


#endif // types_h
