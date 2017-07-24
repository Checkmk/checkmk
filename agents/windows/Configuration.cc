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
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <shlwapi.h>
#include "PerfCounter.h"
#include "logging.h"
#include "stringutil.h"
#define __STDC_FORMAT_MACROS
#include <inttypes.h>

static const int CHECK_MK_AGENT_PORT = 6556;
static const int REALTIME_DEFAULT_PORT = 6559;

Configuration::Configuration(const Environment &env)
    : _enabled_sections(0xffffffff)
    , _realtime_sections(0x0)
    , _port(CHECK_MK_AGENT_PORT)
    , _realtime_port(REALTIME_DEFAULT_PORT)
    , _default_script_execution_mode(SYNC)
    , _default_script_async_execution(SEQUENTIAL)
    , _passphrase()
    , _realtime_timeout(90)
    , _crash_debug(false)
    , _section_flush(true)
    , _logwatch_send_initial_entries(false)
    , _support_ipv6(true)
    , _environment(env)
    , _ps_use_wmi(false)
    , _ps_full_path(false) {
    _logwatch_globlines.setGroupFunction(&Configuration::addConditionPattern);

    CollectorRegistry::instance().startFile();
    readConfigFile(configFileName(false));

    CollectorRegistry::instance().startFile();
    readConfigFile(configFileName(true));

    // ensure only supported sections are enabled for realtime updates
    _realtime_sections &= VALID_REALTIME_SECTIONS;

    if ((_realtime_sections == 0) != (_passphrase.empty())) {
        fprintf(
            stderr,
            "for realtime monitoring, both realtime sections and passphrase "
            "have to be set and valid.");
    }

    postProcessOnlyFrom();
}

unsigned long Configuration::enabledSections() const {
    return _enabled_sections;
}

unsigned long Configuration::realtimeSections() const {
    return _realtime_sections;
}

void Configuration::disableSection(unsigned long section) {
    _enabled_sections &= ~section;
    _realtime_sections &= ~section;
}

std::string Configuration::configFileName(bool local) const {
    return std::string(_environment.agentDirectory()) + "\\" + "check_mk" +
           (local ? "_local" : "") + ".ini";
}

bool Configuration::parseBoolean(char *value, bool &parameter) {
    int s = parse_boolean(value);
    if (s == -1) return false;
    parameter = s != 0;
    return true;
}

bool Configuration::handleGlobalConfigVariable(char *var, char *value) {
    if (!strcmp(var, "only_from")) {
        std::vector<const char *> only_from = split_line(value, isspace);
        for (std::vector<const char *>::const_iterator iter = only_from.begin();
             iter != only_from.end(); ++iter) {
            addOnlyFrom(*iter);
        }
        return true;
    } else if (!strcmp(var, "port")) {
        _port = atoi(value);
        return true;
    } else if (!strcmp(var, "realtime_port")) {
        _realtime_port = atoi(value);
        return true;
    } else if (!strcmp(var, "ipv6")) {
        return parseBoolean(value, _support_ipv6);
    } else if (!strcmp(var, "execute")) {
        parseExecute(value);
        return true;
    } else if (!strcmp(var, "async_script_execution")) {
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
            _default_script_execution_mode = ASYNC;
        } else if (!strcmp(value, "sync")) {
            _default_script_async_execution = SEQUENTIAL;
            _default_script_execution_mode = ASYNC;
        } else if (!strcmp(value, "off")) {
            _default_script_async_execution = SEQUENTIAL;
            _default_script_execution_mode = SYNC;
        }
        return true;
    } else if (!strcmp(var, "crash_debug")) {
        return parseBoolean(value, _crash_debug);
    } else if (!strcmp(var, "section_flush")) {
        return parseBoolean(value, _section_flush);
    } else if (!strcmp(var, "sections") || !strcmp(var, "realtime_sections")) {
        bool read_rt_sections = strcmp(var, "realtime_sections") == 0;
        unsigned long &mask =
            read_rt_sections ? _realtime_sections : _enabled_sections;
        // crashlog output always enabled for regular output, never for live
        // output
        mask = read_rt_sections ? 0 : SECTION_CRASHLOG;
        char *word;
        while ((word = next_word(&value))) {
            if (!strcmp(word, "check_mk"))
                mask |= SECTION_CHECK_MK;
            else if (!strcmp(word, "uptime"))
                mask |= SECTION_UPTIME;
            else if (!strcmp(word, "df"))
                mask |= SECTION_DF;
            else if (!strcmp(word, "ps"))
                mask |= SECTION_PS;
            else if (!strcmp(word, "mem"))
                mask |= SECTION_MEM;
            else if (!strcmp(word, "services"))
                mask |= SECTION_SERVICES;
            else if (!strcmp(word, "winperf"))
                mask |= SECTION_WINPERF;
            else if (!strcmp(word, "winperf_processor"))
                mask |= SECTION_WINPERF_CPU;
            else if (!strcmp(word, "winperf_if"))
                mask |= SECTION_WINPERF_IF;
            else if (!strcmp(word, "winperf_phydisk"))
                mask |= SECTION_WINPERF_PHYDISK;
            else if (!strcmp(word, "perfcounter"))
                mask |= SECTION_WINPERF_CONFIG;
            else if (!strcmp(word, "logwatch"))
                mask |= SECTION_LOGWATCH;
            else if (!strcmp(word, "logfiles"))
                mask |= SECTION_LOGFILES;
            else if (!strcmp(word, "systemtime"))
                mask |= SECTION_SYSTEMTIME;
            else if (!strcmp(word, "plugins")) {
                if (read_rt_sections) {
                    verbose("ignored plugin section for realtime checks");
                    // ... because of performance and because that code
                    // is almost certainly not thread-safe currently
                } else {
                    mask |= SECTION_PLUGINS;
                }
            } else if (!strcmp(word, "local")) {
                if (read_rt_sections) {
                    verbose("ignored local section for realtime checks");
                    // ... because of performance and because that code
                    // is almost certainly not thread-safe currently
                } else {
                    mask |= SECTION_LOCAL;
                }
            } else if (!strcmp(word, "spool"))
                mask |= SECTION_SPOOL;
            else if (!strcmp(word, "mrpe"))
                mask |= SECTION_MRPE;
            else if (!strcmp(word, "fileinfo"))
                mask |= SECTION_FILEINFO;
            else if (!strcmp(word, "wmi_cpuload"))
                mask |= SECTION_CPU;
            else if (!strcmp(word, "msexch"))
                mask |= SECTION_EXCHANGE;
            else if (!strcmp(word, "dotnet_clrmemory"))
                mask |= SECTION_DOTNET;
            else if (!strcmp(word, "webservices"))
                mask |= SECTION_WEBSERVICES;
            else if (!strcmp(word, "ohm"))
                mask |= SECTION_OHM;
            else {
                fprintf(stderr, "Invalid section '%s'.\r\n", word);
                return false;
            }
        }
        return true;
    } else if (strcmp(var, "realtime_timeout") == 0) {
        _realtime_timeout = strtol(value, 0, 10);
        return true;
    } else if (strcmp(var, "passphrase") == 0) {
        _passphrase = value;
        return true;
    }

    return false;
}

bool Configuration::handleWinperfConfigVariable(char *var, char *value) {
    if (!strcmp(var, "counters")) {
        _winperf_counters.startBlock();
        char *colon = strrchr(value, ':');
        if (!colon) {
            fprintf(stderr,
                    "Invalid counter '%s' in section [winperf]: need number(or "
                    "text) and colon, e.g. 238:processor.\n",
                    value);
            exit(1);
        }
        *colon = 0;
        winperf_counter *tmp_counter = new winperf_counter();
        tmp_counter->name = strdup(colon + 1);

        bool is_digit = true;
        for (unsigned int i = 0; i < strlen(value); i++)
            if (!isdigit(value[i])) {
                is_digit = false;
                int id = PerfCounterObject::resolve_counter_name(value);
                if (id == -1) {
                    fprintf(
                        stderr,
                        "No matching performance counter id found for %s.\n",
                        value);
                    return false;
                }
                tmp_counter->id = id;
                break;
            }

        if (is_digit) tmp_counter->id = atoi(value);
        _winperf_counters.add(tmp_counter);
        return true;
    }
    return false;
}

// Add a new state pattern to the current pattern container
void Configuration::addConditionPattern(globline_container *&globline,
                                        const char *state, const char *value) {
    condition_pattern *new_pattern = new condition_pattern();
    new_pattern->state = state[0];
    new_pattern->glob_pattern = strdup(value);
    globline->patterns.push_back(new_pattern);
}

bool Configuration::handleLogfilesConfigVariable(char *var, char *value) {
    loadLogwatchOffsets();
    if (!strcmp(var, "textfile")) {
        if (value != 0) addGlobline(value);
        return true;
    } else if (!strcmp(var, "warn")) {
        if (value != 0) return _logwatch_globlines.addGroup("W", value);
        return true;
    } else if (!strcmp(var, "crit")) {
        if (value != 0) return _logwatch_globlines.addGroup("C", value);
        return true;
    } else if (!strcmp(var, "ignore")) {
        if (value != 0) return _logwatch_globlines.addGroup("I", value);
        return true;
    } else if (!strcmp(var, "ok")) {
        if (value != 0) return _logwatch_globlines.addGroup("O", value);
        return true;
    }
    return false;
}

void Configuration::parseLogwatchStateLine(char *line) {
    /* Example: line = "M://log1.log|98374598374|0|16"; */
    rstrip(line);
    char *p = line;
    while (*p && *p != '|') p++;
    *p = 0;
    char *path = line;
    p++;

    char *token = strtok(p, "|");
    if (!token) return;  // Ignore invalid lines
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

void Configuration::loadLogwatchOffsets() {
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
bool Configuration::addNewLogwatchTextfile(const char *full_filename,
                                           glob_token *token,
                                           condition_patterns_t &patterns) {
    logwatch_textfile *new_textfile = new logwatch_textfile();

    HANDLE hFile =
        CreateFile(full_filename,  // file to open
                   GENERIC_READ,   // open for reading
                   FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                   NULL,                   // default security
                   OPEN_EXISTING,          // existing file only
                   FILE_ATTRIBUTE_NORMAL,  // normal file
                   NULL);                  // no attr. template

    BY_HANDLE_FILE_INFORMATION fileinfo;
    GetFileInformationByHandle(hFile, &fileinfo);
    CloseHandle(hFile);

    new_textfile->path = strdup(full_filename);
    new_textfile->missing = false;
    new_textfile->patterns = &patterns;
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
        new_textfile->file_size =
            (unsigned long long)fileinfo.nFileSizeLow +
            (((unsigned long long)fileinfo.nFileSizeHigh) << 32);
        new_textfile->file_id =
            (unsigned long long)fileinfo.nFileIndexLow +
            (((unsigned long long)fileinfo.nFileIndexHigh) << 32);
        new_textfile->offset = new_textfile->file_size;
    }

    _logwatch_textfiles.add(new_textfile);
    return true;
}

logwatch_textfile *Configuration::getLogwatchTextfile(const char *filename) {
    for (logwatch_textfiles_t::const_iterator it_tf =
             _logwatch_textfiles->begin();
         it_tf != _logwatch_textfiles->end(); ++it_tf) {
        if (strcmp(filename, (*it_tf)->path) == 0) return *it_tf;
    }
    return 0;
}

// Check if the given full_filename already exists. If so, do some basic file
// integrity checks
// Otherwise create a new textfile instance
void Configuration::updateOrCreateLogwatchTextfile(
    const char *full_filename, glob_token *token,
    condition_patterns_t &patterns) {
    logwatch_textfile *textfile;
    if ((textfile = getLogwatchTextfile(full_filename)) != NULL) {
        HANDLE hFile =
            CreateFile(textfile->path,  // file to open
                       GENERIC_READ,    // open for reading
                       FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                       NULL,                   // default security
                       OPEN_EXISTING,          // existing file only
                       FILE_ATTRIBUTE_NORMAL,  // normal file
                       NULL);                  // no attr. template

        BY_HANDLE_FILE_INFORMATION fileinfo;
        // Do some basic checks to ensure its still the same file
        // try to fill the structure with info regarding the file
        if (hFile != INVALID_HANDLE_VALUE) {
            if (GetFileInformationByHandle(hFile, &fileinfo)) {
                unsigned long long file_id =
                    (unsigned long long)fileinfo.nFileIndexLow +
                    (((unsigned long long)fileinfo.nFileIndexHigh) << 32);
                textfile->file_size =
                    (unsigned long long)fileinfo.nFileSizeLow +
                    (((unsigned long long)fileinfo.nFileSizeHigh) << 32);

                if (file_id != textfile->file_id) {  // file has been changed
                    verbose("File %s: id has changed from %" PRIu64,
                            full_filename, textfile->file_id);
                    verbose(" to %" PRIu64 "\n", file_id);
                    textfile->offset = 0;
                    textfile->file_id = file_id;
                } else if (textfile->file_size <
                           textfile->offset) {  // file has been truncated
                    verbose("File %s: file has been truncated\n",
                            full_filename);
                    textfile->offset = 0;
                }

                textfile->missing = false;
            }
            CloseHandle(hFile);
        } else {
            verbose("Cant open file with CreateFile %s\n", full_filename);
        }
    } else
        addNewLogwatchTextfile(full_filename, token, patterns);  // Add new file
}

// Process a single expression (token) of a globline and try to find matching
// files
void Configuration::processGlobExpression(glob_token *glob_token,
                                          condition_patterns_t &patterns) {
    WIN32_FIND_DATA data;
    char full_filename[512];
    glob_token->found_match = false;
    HANDLE h = FindFirstFileEx(glob_token->pattern, FindExInfoStandard, &data,
                               FindExSearchNameMatch, NULL, 0);
    if (h != INVALID_HANDLE_VALUE) {
        glob_token->found_match = true;
        const char *basename = "";
        char *end = strrchr(glob_token->pattern, '\\');
        if (end) {
            *end = 0;
            basename = glob_token->pattern;
        }
        if (!(data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) { // Skip directories

            snprintf(full_filename, sizeof(full_filename), "%s\\%s", basename,
                     data.cFileName);
            updateOrCreateLogwatchTextfile(full_filename, glob_token, patterns);
        }
        while (FindNextFile(h, &data)) {
            if (!(data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) { // Skip directories
                snprintf(full_filename, sizeof(full_filename), "%s\\%s", basename,
                         data.cFileName);
                updateOrCreateLogwatchTextfile(full_filename, glob_token, patterns);
            }
        }

        if (end) *end = '\\';  // repair string
        FindClose(h);
    }
}

// Add a new globline from the config file:
// C:/Testfile | D:/var/log/data.log D:/tmp/art*.log
// This globline is split into tokens which are processed by
// process_glob_expression
void Configuration::addGlobline(char *value) {
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

            if (!strncmp(token, "nocontext", 9)) {
                new_token->nocontext = true;
                token += 9;
                token = lstrip(token);
            } else
                new_token->nocontext = false;

            new_token->pattern = strdup(token);
            new_globline->tokens.push_back(new_token);
            processGlobExpression(new_token, new_globline->patterns);
            token = strtok(NULL, "|");
        }
        free(copy);
    }
}

// Revalidate the existance of logfiles and check if the files attribute (id /
// size) indicate a change
void Configuration::revalidateLogwatchTextfiles() {
    // First of all invalidate all textfiles
    for (logwatch_textfiles_t::const_iterator it_tf =
             _logwatch_textfiles->begin();
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

void Configuration::stringToIPv6(const char *value, uint16_t *address) {
    const char *pos = value;
    std::vector<uint16_t> segments;
    int skip_offset = -1;
    segments.reserve(8);

    while (pos != NULL) {
        char *endpos = NULL;
        unsigned long segment = strtoul(pos, &endpos, 16);
        if (segment > 0xFFFFu) {
            fprintf(stderr, "Invalid ipv6 address %s\n", value);
            exit(1);
        } else if (endpos == pos) {
            skip_offset = segments.size();
        } else {
            segments.push_back((unsigned short)segment);
        }
        if (*endpos != ':') {
            break;
        }
        pos = endpos + 1;
        ++segment;
    }

    int idx = 0;
    for (std::vector<uint16_t>::const_iterator iter = segments.begin();
         iter != segments.end(); ++iter) {
        if (idx == skip_offset) {
            // example with ::42: segments.size() = 1
            //   this will fill the first 7 fields with 0 and increment idx by 7
            for (size_t i = 0; i < 8 - segments.size(); ++i) {
                address[idx + i] = 0;
            }
            idx += 8 - segments.size();
        }

        address[idx++] = htons(*iter);
        assert(idx <= 8);
    }
}

void Configuration::stringToIPv4(const char *value, uint32_t &address) {
    unsigned a, b, c, d;
    if (4 != sscanf(value, "%u.%u.%u.%u", &a, &b, &c, &d)) {
        fprintf(stderr, "Invalid value %s for only_hosts\n", value);
        exit(1);
    }

    address = a + b * 0x100 + c * 0x10000 + d * 0x1000000;
}

void Configuration::netmaskFromPrefixIPv6(int bits, uint16_t *netmask) {
    memset(netmask, 0, sizeof(uint16_t) * 8);
    for (int i = 0; i < 8; ++i) {
        if (bits > 0) {
            int consume_bits = std::min(16, bits);
            netmask[i] = htons(0xFFFF << (16 - consume_bits));
            bits -= consume_bits;
        }
    }
}

void Configuration::netmaskFromPrefixIPv4(int bits, uint32_t &netmask) {
    uint32_t mask_swapped = 0;
    for (int bit = 0; bit < bits; bit++) mask_swapped |= 0x80000000 >> bit;
    unsigned char *s = (unsigned char *)&mask_swapped;
    unsigned char *t = (unsigned char *)&netmask;
    t[3] = s[0];
    t[2] = s[1];
    t[1] = s[2];
    t[0] = s[3];
}

void Configuration::addOnlyFrom(const char *value) {
    ipspec *result = new ipspec();

    char *slash_pos = strchr(value, '/');
    if (slash_pos != NULL) {
        // ipv4/ipv6 agnostic
        result->bits = strtol(slash_pos + 1, NULL, 10);
    } else {
        result->bits = 0;
    }

    result->ipv6 = strchr(value, ':') != NULL;

    if (result->ipv6) {
        if (result->bits == 0) {
            result->bits = 128;
        }
        stringToIPv6(value, result->ip.v6.address);
        netmaskFromPrefixIPv6(result->bits, result->ip.v6.netmask);

        // TODO verify that host part is 0
    } else {
        if (result->bits == 0) {
            result->bits = 32;
        }

        stringToIPv4(value, result->ip.v4.address);
        netmaskFromPrefixIPv4(result->bits, result->ip.v4.netmask);

        if ((result->ip.v4.address & result->ip.v4.netmask) !=
            result->ip.v4.address) {
            fprintf(stderr, "Invalid only_hosts entry: host part not 0: %s",
                    value);
            exit(1);
        }
    }
    _only_from.add(result);
}

void Configuration::postProcessOnlyFrom() {
    if (_support_ipv6) {
        // find all ipv4 specs, later insert a the same spec as a v6 adress.
        std::vector<ipspec *> v4specs;
        for (only_from_t::iterator iter = _only_from->begin();
             iter != _only_from->end(); ++iter) {
            if (!(*iter)->ipv6) {
                v4specs.push_back(*iter);
            }
        }

        for (std::vector<ipspec *>::const_iterator iter = v4specs.begin();
             iter != v4specs.end(); ++iter) {
            // also add a v4->v6 coverted filter
            ipspec *spec = *iter;

            ipspec *result = new ipspec();
            // first 96 bits are fixed: 0:0:0:0:0:ffff
            result->bits = 96 + spec->bits;
            result->ipv6 = true;
            memset(result->ip.v6.address, 0, sizeof(uint16_t) * 5);
            result->ip.v6.address[5] = 0xFFFFu;
            result->ip.v6.address[6] =
                static_cast<uint16_t>(spec->ip.v4.address & 0xFFFFu);
            result->ip.v6.address[7] =
                static_cast<uint16_t>(spec->ip.v4.address >> 16);
            netmaskFromPrefixIPv6(result->bits, result->ip.v6.netmask);
            _only_from.add(result);
        }
    }
}

void Configuration::parseExecute(char *value) {
    char *suffix;
    while (0 != (suffix = next_word(&value))) _execute_suffixes.add(suffix);
}

bool Configuration::handleLogwatchConfigVariable(char *var, char *value) {
    if (!strncmp(var, "logfile ", 8)) {
        int level;
        char *logfilename = lstrip(var + 8);
        lowercase(logfilename);

        // value might have the option nocontext
        int hide_context = 0;
        char *s = value;
        while (*s && *s != ' ') s++;
        if (*s == ' ') {
            if (!strcmp(s + 1, "nocontext")) hide_context = 1;
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
            fprintf(stderr,
                    "Invalid log level '%s'.\r\n"
                    "Allowed are off, all, warn and crit.\r\n",
                    value);
            return false;
        }

        _eventlog_config.add(
            eventlog_config_entry(level, hide_context, logfilename));

        return true;
    } else if (!strcmp(var, "sendall")) {
        int s = parse_boolean(value);
        if (s == -1) return false;
        _logwatch_send_initial_entries = s;
        return true;
    }
    return false;
}

bool Configuration::handleMrpeConfigVariable(char *var, char *value) {
    if (!strcmp(var, "check")) {
        // First word: service description
        // Rest: command line
        char *service_description = next_word(&value);
        char *command_line = value;
        if (!command_line || !command_line[0]) {
            fprintf(stderr,
                    "Invalid command specification for mrpe:\r\n"
                    "Format: SERVICEDESC COMMANDLINE\r\n");
            return false;
        }

        mrpe_entry *tmp_entry = new mrpe_entry();
        memset(tmp_entry, 0, sizeof(mrpe_entry));

        if (PathIsRelative(command_line)) {
            snprintf(tmp_entry->command_line, sizeof(tmp_entry->command_line),
                     "%s\\%s", _environment.agentDirectory().c_str(),
                     command_line);
        } else {
            strncpy(tmp_entry->command_line, command_line,
                    sizeof(tmp_entry->command_line));
        }

        strncpy(tmp_entry->service_description, service_description,
                sizeof(tmp_entry->service_description));

        // compute plugin name, drop directory part
        char *plugin_name = next_word(&value);
        char *p = strrchr(plugin_name, '/');
        if (!p) p = strrchr(plugin_name, '\\');
        if (p) plugin_name = p + 1;
        strncpy(tmp_entry->plugin_name, plugin_name,
                sizeof(tmp_entry->plugin_name));
        _mrpe_entries.add(tmp_entry);
        return true;
    } else if (!strncmp(var, "include", 7)) {
        char *user = NULL;
        if (strlen(var) > 7) user = lstrip(var + 7);

        runas_include *tmp = new runas_include();
        memset(tmp, 0, sizeof(*tmp));

        if (user) snprintf(tmp->user, sizeof(tmp->user), "%s", user);
        snprintf(tmp->path, sizeof(tmp->path), "%s", value);
        _mrpe_includes.add(tmp);
        return true;
    }
    return false;
}

bool Configuration::handleFileinfoConfigVariable(char *var, char *value) {
    if (!strcmp(var, "path")) {
        _fileinfo_paths.add(strdup(value));
        return true;
    }
    return false;
}

bool Configuration::handleScriptConfigVariable(char *var, char *value,
                                               script_type type) {
    if (!strncmp(var, "timeout ", 8)) {
        char *script_pattern = lstrip(var + 8);
        timeout_config *entry = new timeout_config();
        entry->pattern = strdup(script_pattern);
        entry->timeout = atoi(value);
        if (type == PLUGIN)
            _timeout_configs_plugin.add(entry);
        else
            _timeout_configs_local.add(entry);
    } else if (!strncmp(var, "cache_age ", 10)) {
        char *plugin_pattern = lstrip(var + 10);
        cache_config *entry = new cache_config();
        entry->pattern = strdup(plugin_pattern);
        entry->max_age = atoi(value);
        if (type == PLUGIN)
            _cache_configs_plugin.add(entry);
        else
            _cache_configs_local.add(entry);
    } else if (!strncmp(var, "retry_count ", 12)) {
        char *plugin_pattern = lstrip(var + 12);
        retry_config *entry = new retry_config();
        entry->pattern = strdup(plugin_pattern);
        entry->retries = atoi(value);
        if (type == PLUGIN)
            _retry_configs_plugin.add(entry);
        else
            _retry_configs_local.add(entry);
    } else if (!strncmp(var, "execution ", 10)) {
        char *plugin_pattern = lstrip(var + 10);
        execution_mode_config *entry = new execution_mode_config();
        entry->pattern = strdup(plugin_pattern);
        entry->mode = !strncmp(value, "async", 5) ? ASYNC : SYNC;
        if (type == PLUGIN)
            _execution_mode_configs_plugin.add(entry);
        else
            _execution_mode_configs_local.add(entry);
    } else if (!strncmp(var, "include", 7)) {
        char *user = NULL;
        if (strlen(var) > 7) user = lstrip(var + 7);

        runas_include *tmp = new runas_include();
        memset(tmp, 0, sizeof(*tmp));

        if (user) snprintf(tmp->user, sizeof(tmp->user), "%s", user);

        tmp->type = type;
        snprintf(tmp->path, sizeof(tmp->path), "%s", value);
        _script_includes.add(tmp);
        return true;
    }
    return true;
}

bool Configuration::handlePluginConfigVariable(char *var, char *value) {
    bool res = handleScriptConfigVariable(var, value, PLUGIN);
    return res;
}

bool Configuration::handleLocalConfigVariable(char *var, char *value) {
    return handleScriptConfigVariable(var, value, LOCAL);
}

bool Configuration::handlePSConfigVariable(char *var, char *value) {
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

bool Configuration::checkHostRestriction(char *patterns) {
    char *word;
    std::string hostname = _environment.hostname();
    while ((word = next_word(&patterns))) {
        if (globmatch(word, hostname.c_str())) {
            return true;
        }
    }
    return false;
}

void Configuration::readConfigFile(const std::string &filename) {
    FILE *file = fopen(filename.c_str(), "r");
    if (!file) {
        return;
    }

    char line[512];
    int lineno = 0;
    // bool (*variable_handler)(char *var, char *value) = 0;

    KVBind<Configuration, bool> variable_handler(this);

    bool is_active = true;  // false in sections with host restrictions

    while (!feof(file)) {
        if (!fgets(line, sizeof(line), file)) {
            fclose(file);
            return;
        }
        lineno++;
        char *l = strip(line);
        if (l[0] == 0 || l[0] == '#' || l[0] == ';')
            continue;  // skip empty lines and comments
        int len = strlen(l);
        if (l[0] == '[' && l[len - 1] == ']') {
            // found section header
            l[len - 1] = 0;
            char *section = l + 1;
            if (!strcmp(section, "global"))
                variable_handler.setFunc(
                    &Configuration::handleGlobalConfigVariable);
            else if (!strcmp(section, "winperf"))
                variable_handler.setFunc(
                    &Configuration::handleWinperfConfigVariable);
            else if (!strcmp(section, "logwatch"))
                variable_handler.setFunc(
                    &Configuration::handleLogwatchConfigVariable);
            else if (!strcmp(section, "logfiles"))
                variable_handler.setFunc(
                    &Configuration::handleLogfilesConfigVariable);
            else if (!strcmp(section, "mrpe"))
                variable_handler.setFunc(
                    &Configuration::handleMrpeConfigVariable);
            else if (!strcmp(section, "fileinfo"))
                variable_handler.setFunc(
                    &Configuration::handleFileinfoConfigVariable);
            else if (!strcmp(section, "plugins"))
                variable_handler.setFunc(
                    &Configuration::handlePluginConfigVariable);
            else if (!strcmp(section, "local"))
                variable_handler.setFunc(
                    &Configuration::handleLocalConfigVariable);
            else if (!strcmp(section, "ps"))
                variable_handler.setFunc(
                    &Configuration::handlePSConfigVariable);
            else {
                fprintf(stderr, "Invalid section [%s] in %s in line %d.\r\n",
                        section, filename.c_str(), lineno);
                exit(1);
            }
            // forget host-restrictions if new section begins
            is_active = true;
        } else if (variable_handler.isUnset()) {
            fprintf(stderr, "Line %d is outside of any section.\r\n", lineno);
            exit(1);
        } else {
            // split up line at = sign
            char *s = l;
            while (*s && *s != '=') s++;
            if (*s != '=') {
                fprintf(stderr, "Invalid line %d in %s.\r\n", lineno,
                        filename.c_str());
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
                fprintf(stderr, "Invalid entry in %s line %d.\r\n",
                        filename.c_str(), lineno);
                exit(1);
            }
        }
    }

    fclose(file);
}
