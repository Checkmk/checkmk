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


#include "Configuration.h"
#include "stringutil.h"
#include <cstdio>



extern void verbose(const char *format, ...);


static const int CHECK_MK_AGENT_PORT = 6556;


Configuration::Configuration(const Environment &env)
    : _enabled_sections(0xffffffff)
    , _port(CHECK_MK_AGENT_PORT)
    , _default_script_execution_mode(SYNC)
    , _default_script_async_execution(SEQUENTIAL)
    , _crash_debug(false)
    , _logwatch_send_initial_entries(false)
    , _environment(env)
    , _ps_use_wmi(false)
    , _ps_full_path(false)
{
    _logwatch_globlines.setGroupFunction(&Configuration::addConditionPattern);

    CollectorRegistry::instance().startFile();
    readConfigFile(configFileName(false));

    CollectorRegistry::instance().startFile();
    readConfigFile(configFileName(true));
}


bool Configuration::sectionEnabled(unsigned int section)
{
    return _enabled_sections & section;
}


std::string Configuration::configFileName(bool local) const
{
    return std::string(_environment.agentDirectory()) + "\\"
        + "check_mk"
        + (local ? "_local" : "")
        +".ini";
}


bool Configuration::parseCrashDebug(char *value)
{
    int s = parse_boolean(value);
    if (s == -1)
        return false;
    _crash_debug = s;
    return true;
}


bool Configuration::handleGlobalConfigVariable(char *var, char *value)
{
    if (!strcmp(var, "only_from")) {
        std::vector<const char*> only_from = split_line(value, isspace);
        for (std::vector<const char*>::const_iterator iter = only_from.begin();
                iter != only_from.end(); ++iter) {
            addOnlyFrom(*iter);
        }
        return true;
    }
    else if (!strcmp(var, "port")) {
        _port = atoi(value);
        return true;
    }
    else if (!strcmp(var, "execute")) {
        parseExecute(value);
        return true;
    }
    else if (!strcmp(var, "async_script_execution")) {
        if (!strcmp(value, "parallel"))
            _default_script_async_execution = PARALLEL;
        else if (!strcmp(value, "sequential"))
            _default_script_async_execution = SEQUENTIAL;
        return true;
    }
    // Do not longer use this!
    else if (!strcmp(var, "caching_method")) {
        if (!strcmp(value, "async")) {
            _default_script_async_execution = PARALLEL;
            _default_script_execution_mode  = ASYNC;
        }
        else if (!strcmp(value, "sync")) {
            _default_script_async_execution = SEQUENTIAL;
            _default_script_execution_mode  = ASYNC;
        }
        else if (!strcmp(value, "off")) {
            _default_script_async_execution = SEQUENTIAL;
            _default_script_execution_mode  = SYNC;
        }
        return true;
    }
    else if (!strcmp(var, "crash_debug")) {
        return parseCrashDebug(value);
    }
    else if (!strcmp(var, "sections")) {
        _enabled_sections = 0;
        char *word;
        while ((word = next_word(&value))) {
            if (!strcmp(word, "check_mk"))
                _enabled_sections |= SECTION_CHECK_MK;
            else if (!strcmp(word, "uptime"))
                _enabled_sections |= SECTION_UPTIME;
            else if (!strcmp(word, "df"))
                _enabled_sections |= SECTION_DF;
            else if (!strcmp(word, "ps"))
                _enabled_sections |= SECTION_PS;
            else if (!strcmp(word, "mem"))
                _enabled_sections |= SECTION_MEM;
            else if (!strcmp(word, "services"))
                _enabled_sections |= SECTION_SERVICES;
            else if (!strcmp(word, "winperf"))
                _enabled_sections |= SECTION_WINPERF;
            else if (!strcmp(word, "logwatch"))
                _enabled_sections |= SECTION_LOGWATCH;
            else if (!strcmp(word, "logfiles"))
                _enabled_sections |= SECTION_LOGFILES;
            else if (!strcmp(word, "systemtime"))
                _enabled_sections |= SECTION_SYSTEMTIME;
            else if (!strcmp(word, "plugins"))
                _enabled_sections |= SECTION_PLUGINS;
            else if (!strcmp(word, "local"))
                _enabled_sections |= SECTION_LOCAL;
            else if (!strcmp(word, "spool"))
                _enabled_sections |= SECTION_SPOOL;
            else if (!strcmp(word, "mrpe"))
                _enabled_sections |= SECTION_MRPE;
            else if (!strcmp(word, "fileinfo"))
                _enabled_sections |= SECTION_FILEINFO;
            else {
                fprintf(stderr, "Invalid section '%s'.\r\n", word);
                return false;
            }
        }
        return true;
    }

    return false;
}


// retrieve the next line from a multi-sz registry key
const TCHAR *get_next_multi_sz(const std::vector<TCHAR> &data, size_t &offset)
{
    const TCHAR *next = &data[offset];
    size_t len = strlen(next);
    if ((len == 0) || (offset + len > data.size())) {
        // the second condition would only happen with an invalid registry value but that's not
        // unheard of
        return NULL;
    } else {
        offset += len + 1;
        return next;
    }
}


int Configuration::getCounterIdFromLang(const char *language, const char *counter_name)
{
    char regkey[512];
    snprintf(regkey, sizeof(regkey), "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Perflib\\%s", language);
    HKEY hKey;
    LONG result = RegOpenKeyEx(HKEY_LOCAL_MACHINE, regkey, REG_MULTI_SZ, KEY_READ, &hKey);

    // preflight
    std::vector<TCHAR> szValueName;
    DWORD dwcbData = 0;
    RegQueryValueEx(hKey, "Counter", NULL, NULL, (LPBYTE)&szValueName[0], &dwcbData);
    szValueName.resize(dwcbData);
    // actual read op
    RegQueryValueEx(hKey, "Counter", NULL, NULL, (LPBYTE) &szValueName[0], &dwcbData);
    RegCloseKey (hKey);

    if (result != ERROR_SUCCESS) {
        return -1;
    }

    size_t offset = 0;
    for(;;) {
        const TCHAR *id = get_next_multi_sz(szValueName, offset);
        const TCHAR *name = get_next_multi_sz(szValueName, offset);
        if ((id == NULL) || (name == NULL)) {
            break;
        }
        if (strcmp(name, counter_name) == 0) {
            return strtol(id, NULL, 10);
        }
    }

    return -1;
}

int Configuration::getPerfCounterId(const char *counter_name)
{
    int counter_id;
    // Try to find it in current language
    if ((counter_id = getCounterIdFromLang("CurrentLanguage", counter_name)) != -1)
        return counter_id;

    // Try to find it in english
    if ((counter_id = getCounterIdFromLang("009", counter_name)) != -1)
        return counter_id;

    return -1;
}

bool Configuration::handleWinperfConfigVariable(char *var, char *value)
{
    if (!strcmp(var, "counters")) {
        _winperf_counters.startBlock();
        char *colon = strrchr(value, ':');
        if (!colon) {
            fprintf(stderr, "Invalid counter '%s' in section [winperf]: need number(or text) and colon, e.g. 238:processor.\n", value);
            exit(1);
        }
        *colon = 0;
        winperf_counter *tmp_counter = new winperf_counter();
        tmp_counter->name = strdup(colon + 1);

        bool is_digit = true;
        for (unsigned int i = 0; i < strlen(value); i++)
            if (!isdigit(value[i])) {
                is_digit = false;
                int id = getPerfCounterId(value);
                if (id == -1) {
                    fprintf(stderr, "No matching performance counter id found for %s.\n", value);
                    return false;
                }
                tmp_counter->id = id;
                break;
            }

        if(is_digit)
            tmp_counter->id = atoi(value);
        _winperf_counters.add(tmp_counter);
        return true;
    }
    return false;
}


// Add a new state pattern to the current pattern container
void Configuration::addConditionPattern(globline_container *&globline, const char *state, const char *value)
{
    condition_pattern *new_pattern = new condition_pattern();
    new_pattern->state = state[0];
    new_pattern->glob_pattern = strdup(value);
    globline->patterns.push_back(new_pattern);
}


bool Configuration::handleLogfilesConfigVariable(char *var, char *value)
{
    loadLogwatchOffsets();
    if (!strcmp(var, "textfile")) {
        if (value != 0)
            addGlobline(value);
        return true;
    }
    else if (!strcmp(var, "warn")) {
        if (value != 0)
            return _logwatch_globlines.addGroup("W", value);
        return true;
    }
    else if (!strcmp(var, "crit")) {
        if (value != 0)
            return _logwatch_globlines.addGroup("C", value);
        return true;
    }
    else if (!strcmp(var, "ignore")) {
        if (value != 0)
            return _logwatch_globlines.addGroup("I", value);
        return true;
    }
    else if (!strcmp(var, "ok")) {
        if (value != 0)
            return _logwatch_globlines.addGroup("O", value);
        return true;
    }
    return false;
}


void Configuration::parseLogwatchStateLine(char *line)
{
    /* Example: line = "M://log1.log|98374598374|0|16"; */
    rstrip(line);
    char *p = line;
    while (*p && *p != '|') p++;
    *p = 0;
    char *path = line;
    p++;

    char *token = strtok(p, "|");
    if (!token) return; // Ignore invalid lines
    unsigned long long file_id = string_to_llu(token);

    token = strtok(NULL, "|");
    if (!token) return;
    unsigned long long file_size = string_to_llu(token);

    token = strtok(NULL, "|");
    if (!token) return;
    unsigned long long offset = string_to_llu(token);

    logwatch_textfile *tf = new logwatch_textfile();
    tf->path = strdup(path);
    tf->file_id = file_id;
    tf->file_size = file_size;
    tf->offset = offset;
    tf->missing = false;
    tf->patterns = 0;
    _logwatch_hints.push_back(tf);
}


void Configuration::loadLogwatchOffsets()
{
    static bool offsets_loaded = false;
    if (!offsets_loaded) {
        FILE *file = fopen(_environment.logwatchStatefile().c_str(), "r");
        if (file) {
            char line[256];
            while (NULL != fgets(line, sizeof(line), file)) {
                parseLogwatchStateLine(line);
            }
            fclose(file);
        }
        offsets_loaded = true;
    }
}


// Add a new textfile and to the global textfile list
// and determine some initial values
bool Configuration::addNewLogwatchTextfile(const char *full_filename, glob_token* token, condition_patterns_t &patterns)
{
    logwatch_textfile *new_textfile = new logwatch_textfile();

    HANDLE hFile = CreateFile(full_filename,// file to open
            GENERIC_READ,          // open for reading
            FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
            NULL,                  // default security
            OPEN_EXISTING,         // existing file only
            FILE_ATTRIBUTE_NORMAL, // normal file
            NULL);                 // no attr. template

    BY_HANDLE_FILE_INFORMATION fileinfo;
    GetFileInformationByHandle(hFile, &fileinfo);
    CloseHandle(hFile);

    new_textfile->path      = strdup(full_filename);
    new_textfile->missing   = false;
    new_textfile->patterns  = &patterns;
    new_textfile->nocontext = token->nocontext;

    // Hier aus den gespeicherten Hints was holen....
    bool found_hint = false;
    for (logwatch_textfiles_t::const_iterator it_lh = _logwatch_hints.begin();
         it_lh != _logwatch_hints.end(); ++it_lh) {
        logwatch_textfile *hint = *it_lh;
        if (!strcmp(hint->path, full_filename)) {
            new_textfile->file_size = hint->file_size;
            new_textfile->file_id = hint->file_id;
            new_textfile->offset = hint->offset;
            found_hint = true;
            break;
        }
    }

    if (!found_hint) {
        new_textfile->file_size    = (unsigned long long)fileinfo.nFileSizeLow +
            (((unsigned long long)fileinfo.nFileSizeHigh) << 32);
        new_textfile->file_id      = (unsigned long long)fileinfo.nFileIndexLow +
            (((unsigned long long)fileinfo.nFileIndexHigh) << 32);
        new_textfile->offset       = new_textfile->file_size;
    }

    _logwatch_textfiles.add(new_textfile);
    return true;
}


logwatch_textfile *Configuration::getLogwatchTextfile(const char *filename)
{
    for (logwatch_textfiles_t::const_iterator it_tf = _logwatch_textfiles->begin();
         it_tf != _logwatch_textfiles->end(); ++it_tf) {
        if (strcmp(filename, (*it_tf)->path) == 0)
            return *it_tf;
    }
    return 0;
}


// Check if the given full_filename already exists. If so, do some basic file integrity checks
// Otherwise create a new textfile instance
void Configuration::updateOrCreateLogwatchTextfile(const char *full_filename, glob_token* token, condition_patterns_t &patterns)
{
    logwatch_textfile *textfile;
    if ((textfile = getLogwatchTextfile(full_filename)) != NULL)
    {
        HANDLE hFile = CreateFile(textfile->path,// file to open
                GENERIC_READ,          // open for reading
                FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
                NULL,                  // default security
                OPEN_EXISTING,         // existing file only
                FILE_ATTRIBUTE_NORMAL, // normal file
                NULL);                 // no attr. template

        BY_HANDLE_FILE_INFORMATION fileinfo;
        // Do some basic checks to ensure its still the same file
        // try to fill the structure with info regarding the file
        if (hFile != INVALID_HANDLE_VALUE)
        {
            if (GetFileInformationByHandle(hFile, &fileinfo))
            {
                unsigned long long file_id = (unsigned long long)fileinfo.nFileIndexLow +
                    (((unsigned long long)fileinfo.nFileIndexHigh) << 32);
                textfile->file_size        = (unsigned long long)fileinfo.nFileSizeLow +
                    (((unsigned long long)fileinfo.nFileSizeHigh) << 32);

                if (file_id != textfile->file_id) {                // file has been changed
                    verbose("File %s: id has changed from %s",
                            full_filename, llu_to_string(textfile->file_id));
                    verbose(" to %s\n", llu_to_string(file_id));
                    textfile->offset = 0;
                    textfile->file_id = file_id;
                }
                else if (textfile->file_size < textfile->offset) { // file has been truncated
                    verbose("File %s: file has been truncated\n", full_filename);
                    textfile->offset = 0;
                }

                textfile->missing = false;
            }
            CloseHandle(hFile);
        }
        else {
            verbose("Cant open file with CreateFile %s\n", full_filename);
        }
    }
    else
        addNewLogwatchTextfile(full_filename, token, patterns); // Add new file
}

// Process a single expression (token) of a globline and try to find matching files
void Configuration::processGlobExpression(glob_token *glob_token, condition_patterns_t &patterns)
{
    WIN32_FIND_DATA data;
    char full_filename[512];
    glob_token->found_match = false;
    HANDLE h = FindFirstFileEx(glob_token->pattern, FindExInfoStandard, &data, FindExSearchNameMatch, NULL, 0);
    if (h != INVALID_HANDLE_VALUE) {
        glob_token->found_match = true;
        const char *basename = "";
        char *end = strrchr(glob_token->pattern, '\\');
        if (end) {
            *end = 0;
            basename = glob_token->pattern;
        }
        snprintf(full_filename,sizeof(full_filename), "%s\\%s", basename, data.cFileName);
        updateOrCreateLogwatchTextfile(full_filename, glob_token, patterns);

        while (FindNextFile(h, &data)){
            snprintf(full_filename,sizeof(full_filename), "%s\\%s", basename, data.cFileName);
            updateOrCreateLogwatchTextfile(full_filename, glob_token, patterns);
        }

        if (end)
            *end = '\\'; // repair string
        FindClose(h);
    }
}

// Add a new globline from the config file:
// C:/Testfile | D:/var/log/data.log D:/tmp/art*.log
// This globline is split into tokens which are processed by process_glob_expression
void Configuration::addGlobline(char *value)
{
    // Each globline receives its own pattern container
    // In case new files matching the glob pattern are we
    // we already have all state,regex patterns available
    globline_container *new_globline = new globline_container();

    _logwatch_globlines.add(new_globline);

    // Split globline into tokens
    if (value != 0) {
        char *copy = strdup(value);
        char *token = strtok(copy, "|");
        while (token) {
            token = lstrip(token);
            glob_token *new_token = new glob_token();

            if (!strncmp(token, "nocontext", 9))
            {
                new_token->nocontext = true;
                token += 9;
                token = lstrip(token);
            }
            else
                new_token->nocontext = false;

            new_token->pattern = strdup(token);
            new_globline->tokens.push_back(new_token);
            processGlobExpression(new_token, new_globline->patterns);
            token = strtok(NULL, "|");
        }
        free(copy);
    }
}


// Revalidate the existance of logfiles and check if the files attribute (id / size) indicate a change
void Configuration::revalidateLogwatchTextfiles()
{
    // First of all invalidate all textfiles
    for (logwatch_textfiles_t::const_iterator it_tf = _logwatch_textfiles->begin();
            it_tf != _logwatch_textfiles->end(); ++it_tf) {
        (*it_tf)->missing = true;
    }

    for (logwatch_globlines_t::iterator it_line = _logwatch_globlines->begin();
         it_line != _logwatch_globlines->end(); ++it_line) {
        for (glob_tokens_t::iterator it_token = (*it_line)->tokens.begin();
             it_token != (*it_line)->tokens.end(); it_token++) {
            processGlobExpression(*it_token, (*it_line)->patterns);
        }
    }
}


void Configuration::addOnlyFrom(const char *value)
{
    unsigned a, b, c, d;
    int bits = 32;

    if (strchr(value, '/')) {
        if (5 != sscanf(value, "%u.%u.%u.%u/%d", &a, &b, &c, &d, &bits)) {
            fprintf(stderr, "Invalid value %s for only_hosts\n", value);
            exit(1);
        }
    }
    else {
        if (4 != sscanf(value, "%u.%u.%u.%u", &a, &b, &c, &d)) {
            fprintf(stderr, "Invalid value %s for only_hosts\n", value);
            exit(1);
        }
    }

    uint32_t ip = a + b * 0x100 + c * 0x10000 + d * 0x1000000;
    uint32_t mask_swapped = 0;
    for (int bit = 0; bit < bits; bit ++)
        mask_swapped |= 0x80000000 >> bit;
    uint32_t mask;
    unsigned char *s = (unsigned char *)&mask_swapped;
    unsigned char *t = (unsigned char *)&mask;
    t[3] = s[0];
    t[2] = s[1];
    t[1] = s[2];
    t[0] = s[3];


    if ((ip & mask) != ip) {
        fprintf(stderr, "Invalid only_hosts entry: host part not 0: %s/%u",
                ipv4_to_text(ip), bits);
        exit(1);
    }

    ipspec *tmp_ipspec = new ipspec();
    tmp_ipspec->address = ip;
    tmp_ipspec->netmask = mask;
    tmp_ipspec->bits    = bits;
    _only_from.add(tmp_ipspec);
}


void Configuration::parseExecute(char *value)
{
    char *suffix;
    while (0 != (suffix = next_word(&value)))
        _execute_suffixes.add(suffix);
}


bool Configuration::handleLogwatchConfigVariable(char *var, char *value)
{
    if (!strncmp(var, "logfile ", 8)) {
        int level;
        char *logfilename = lstrip(var + 8);
        lowercase(logfilename);

        // value might have the option nocontext
        int hide_context = 0;
        char *s = value;
        while (*s && *s != ' ')
            s++;
        if (*s == ' ') {
            if (!strcmp(s+1, "nocontext"))
                hide_context = 1;
        }
        *s = 0;

        if (!strcmp(value, "off"))
            level = -1;
        else if (!strcmp(value, "all"))
            level = 0;
        else if (!strcmp(value, "warn"))
            level = 1;
        else if (!strcmp(value, "crit"))
            level = 2;
        else {
            fprintf(stderr, "Invalid log level '%s'.\r\n"
                    "Allowed are off, all, warn and crit.\r\n", value);
            return false;
        }

        _eventlog_config.add(eventlog_config_entry(level, hide_context, logfilename));

        return true;
    }
    else if (!strcmp(var, "sendall")) {
        int s = parse_boolean(value);
        if (s == -1)
            return false;
        _logwatch_send_initial_entries = s;
        return true;
    }
    return false;
}


bool Configuration::handleMrpeConfigVariable(char *var, char *value)
{
    if (!strcmp(var, "check")) {
        // First word: service description
        // Rest: command line
        char *service_description = next_word(&value);
        char *command_line = value;
        if (!command_line || !command_line[0]) {
            fprintf(stderr, "Invalid command specification for mrpe:\r\n"
                    "Format: SERVICEDESC COMMANDLINE\r\n");
            return false;
        }

        mrpe_entry* tmp_entry = new mrpe_entry();
        memset(tmp_entry, 0, sizeof(mrpe_entry));

        strncpy(tmp_entry->command_line, command_line,
                sizeof(tmp_entry->command_line));
        strncpy(tmp_entry->service_description, service_description,
                sizeof(tmp_entry->service_description));

        // compute plugin name, drop directory part
        char *plugin_name = next_word(&value);
        char *p = strrchr(plugin_name, '/');
        if (!p)
            p = strrchr(plugin_name, '\\');
        if (p)
            plugin_name = p + 1;
        strncpy(tmp_entry->plugin_name, plugin_name,
                sizeof(tmp_entry->plugin_name));
        _mrpe_entries.add(tmp_entry);
        return true;
    }
    else if (!strncmp(var, "include", 7)) {
        char *user = NULL;
        if (strlen(var) > 7)
            user = lstrip(var + 7);

        runas_include* tmp = new runas_include();
        memset(tmp, 0, sizeof(*tmp));

        if (user)
            snprintf(tmp->user, sizeof(tmp->user), user);
        snprintf(tmp->path, sizeof(tmp->path), value);
        _mrpe_includes.add(tmp);
        return true;
    }
    return false;
}


bool Configuration::handleFileinfoConfigVariable(char *var, char *value)
{
    if (!strcmp(var, "path")) {
        _fileinfo_paths.add(strdup(value));
        return true;
    }
    return false;
}


bool Configuration::handleScriptConfigVariable(char *var, char *value, script_type type)
{
    if (!strncmp(var, "timeout ", 8)) {
        char *script_pattern  = lstrip(var + 8);
        timeout_config *entry = new timeout_config();
        entry->pattern        = strdup(script_pattern);
        entry->timeout        = atoi(value);
        if (type == PLUGIN)
            _timeout_configs_plugin.add(entry);
        else
            _timeout_configs_local.add(entry);
    }
    else if (!strncmp(var, "cache_age ", 10)) {
        char *plugin_pattern = lstrip(var + 10);
        cache_config* entry  = new cache_config();
        entry->pattern       = strdup(plugin_pattern);
        entry->max_age       = atoi(value);
        if (type == PLUGIN)
            _cache_configs_plugin.add(entry);
        else
            _cache_configs_local.add(entry);
    }
    else if (!strncmp(var, "retry_count ", 12)) {
        char *plugin_pattern = lstrip(var + 12);
        retry_config *entry  = new retry_config();
        entry->pattern       = strdup(plugin_pattern);
        entry->retries       = atoi(value);
        if (type == PLUGIN)
            _retry_configs_plugin.add(entry);
        else
            _retry_configs_local.add(entry);
    }
    else if (!strncmp(var, "execution ", 10)) {
        char *plugin_pattern = lstrip(var + 10);
        execution_mode_config *entry  = new execution_mode_config();
        entry->pattern       = strdup(plugin_pattern);
        entry->mode          = !strncmp(value, "async", 5) ? ASYNC : SYNC;
        if (type == PLUGIN)
            _execution_mode_configs_plugin.add(entry);
        else
            _execution_mode_configs_local.add(entry);
    }
    else if (!strncmp(var, "include", 7)) {
        char *user = NULL;
        if (strlen(var) > 7)
            user = lstrip(var + 7);

        runas_include* tmp = new runas_include();
        memset(tmp, 0, sizeof(*tmp));

        if (user)
            snprintf(tmp->user, sizeof(tmp->user), user);

        tmp->type = type;
        snprintf(tmp->path, sizeof(tmp->path), value);
        _script_includes.add(tmp);
        return true;
    }
    return true;
}


bool Configuration::handlePluginConfigVariable(char *var, char *value)
{
    bool res = handleScriptConfigVariable(var, value, PLUGIN);
    return res;
}


bool Configuration::handleLocalConfigVariable(char *var, char *value)
{
    return handleScriptConfigVariable(var, value, LOCAL);
}


bool Configuration::handlePSConfigVariable(char *var, char *value)
{
    if (strcmp(var, "use_wmi") == 0) {
        int s = parse_boolean(value);
        if (s != -1) {
            _ps_use_wmi = s;
            return true;
        }
    } else if (strcmp(var, "full_path") == 0) {
        int s = parse_boolean(value);
        if (s != -1) {
            _ps_full_path = s;
            return true;
        }
    }
    return false;
}


bool Configuration::checkHostRestriction(char *patterns)
{
    char *word;
    std::string hostname = _environment.hostname();
    while ((word = next_word(&patterns))) {
        if (globmatch(word, hostname.c_str())) {
            return true;
        }
    }
    return false;
}


void Configuration::readConfigFile(const std::string &filename)
{
    FILE *file = fopen(filename.c_str(), "r");
    if (!file) {
        return;
    }

    char line[512];
    int lineno = 0;
    // bool (*variable_handler)(char *var, char *value) = 0;

    KVBind<Configuration, bool> variable_handler(this);

    bool is_active = true; // false in sections with host restrictions

    while (!feof(file)) {
        if (!fgets(line, sizeof(line), file)){
            fclose(file);
            return;
        }
        lineno ++;
        char *l = strip(line);
        if (l[0] == 0 || l[0] == '#' || l[0] == ';')
            continue; // skip empty lines and comments
        int len = strlen(l);
        if (l[0] == '[' && l[len-1] == ']') {
            // found section header
            l[len-1] = 0;
            char *section = l + 1;
            if (!strcmp(section, "global"))
                variable_handler.setFunc(&Configuration::handleGlobalConfigVariable);
            else if (!strcmp(section, "winperf"))
                variable_handler.setFunc(&Configuration::handleWinperfConfigVariable);
            else if (!strcmp(section, "logwatch"))
                variable_handler.setFunc(&Configuration::handleLogwatchConfigVariable);
            else if (!strcmp(section, "logfiles"))
                variable_handler.setFunc(&Configuration::handleLogfilesConfigVariable);
            else if (!strcmp(section, "mrpe"))
                variable_handler.setFunc(&Configuration::handleMrpeConfigVariable);
            else if (!strcmp(section, "fileinfo"))
                variable_handler.setFunc(&Configuration::handleFileinfoConfigVariable);
            else if (!strcmp(section, "plugins"))
                variable_handler.setFunc(&Configuration::handlePluginConfigVariable);
            else if (!strcmp(section, "local"))
                variable_handler.setFunc(&Configuration::handleLocalConfigVariable);
            else if (!strcmp(section, "ps"))
                variable_handler.setFunc(&Configuration::handlePSConfigVariable);
            else {
                fprintf(stderr, "Invalid section [%s] in %s in line %d.\r\n",
                        section, filename.c_str(), lineno);
                exit(1);
            }
            // forget host-restrictions if new section begins
            is_active = true;
        }
        else if (variable_handler.isUnset()) {
            fprintf(stderr, "Line %d is outside of any section.\r\n", lineno);
            exit(1);
        }
        else {
            // split up line at = sign
            char *s = l;
            while (*s && *s != '=')
                s++;
            if (*s != '=') {
                fprintf(stderr, "Invalid line %d in %s.\r\n",
                        lineno, filename.c_str());
                exit(1);
            }
            *s = 0;
            char *value = s + 1;
            char *variable = l;
            rstrip(variable);
            lowercase(variable);
            value = strip(value);

            // handle host restriction
            if (!strcmp(variable, "host"))
                is_active = checkHostRestriction(value);

            // skip all other variables for non-relevant hosts
            else if (!is_active)
                continue;

            // Useful for debugging host restrictions
            else if (!strcmp(variable, "print"))
                fprintf(stderr, "%s\r\n", value);


            else if (!variable_handler(variable, value)) {
                fprintf(stderr, "Invalid entry in %s line %d.\r\n", filename.c_str(), lineno);
                exit(1);
            }
        }
    }

    fclose(file);
}

