// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

#include "SectionPluginGroup.h"
#include "../logging.h"
#include "../ExternalCmd.h"
#include <sys/types.h>
#include <dirent.h>


extern struct script_statistics_t {
    int pl_count;
    int pl_errors;
    int pl_timeouts;
    int lo_count;
    int lo_errors;
    int lo_timeouts;
} g_script_stat;


static const size_t HEAP_BUFFER_MAX = 2097152L;
static const size_t HEAP_BUFFER_DEFAULT = 16384L;


const char *typeToSection(script_type type) {
    switch(type) {
        case PLUGIN: return "plugins";
        case LOCAL: return "local";
        case MRPE: return "mrpe";
        default: return "unknown";
    }
}

static int launch_program(script_container *cont) {
    enum { SUCCESS = 0, CANCELED, BUFFER_FULL, WORKING } result = WORKING;
    try {
        ExternalCmd command(cont->path.c_str());

        static const size_t BUFFER_SIZE = 16635;
        char buf[BUFFER_SIZE];  // i/o buffer
        memset(buf, 0, BUFFER_SIZE);
        time_t process_start = time(0);

        if (cont->buffer_work != NULL) {
            HeapFree(GetProcessHeap(), 0, cont->buffer_work);
        }
        cont->buffer_work = (char *)HeapAlloc(
            GetProcessHeap(), HEAP_ZERO_MEMORY, HEAP_BUFFER_DEFAULT);

        unsigned long current_heap_size =
            HeapSize(GetProcessHeap(), 0, cont->buffer_work);

        int out_offset = 0;
        // outer loop -> wait until the process is finished, reading its output
        while (result == WORKING) {
            if (cont->should_terminate ||
                time(0) - process_start > cont->timeout) {
                result = CANCELED;
                continue;
            }

            cont->exit_code = command.exitCode();

            // inner loop without delay -> read all data available in
            // the pipe
            while (result == WORKING) {
                // drop stderr
                command.readStderr(buf, BUFFER_SIZE, false);

                DWORD available = command.stdoutAvailable();
                if (available == 0) {
                    break;
                }

                while (out_offset + available > current_heap_size) {
                    // Increase heap buffer
                    if (current_heap_size * 2 <= HEAP_BUFFER_MAX) {
                        cont->buffer_work = (char *)HeapReAlloc(
                            GetProcessHeap(), HEAP_ZERO_MEMORY,
                            cont->buffer_work, current_heap_size * 2);
                        current_heap_size =
                            HeapSize(GetProcessHeap(), 0, cont->buffer_work);
                    } else {
                        result = BUFFER_FULL;
                        break;
                    }
                }
                if (result != BUFFER_FULL) {
                    size_t max_read = std::min<size_t>(
                        BUFFER_SIZE - 1, current_heap_size - out_offset);

                    DWORD bread = command.readStdout(
                        cont->buffer_work + out_offset, max_read, true);
                    if (bread == 0) {
                        result = BUFFER_FULL;
                    }
                    out_offset += bread;
                }
            }

            if (result == BUFFER_FULL) {
                crash_log("plugin produced more than 2MB output -> dropped");
            }

            if (cont->exit_code != STILL_ACTIVE) {
                result = SUCCESS;
            }

            if (result == WORKING) {
                Sleep(10);  // 10 milliseconds
            }
        }

        // if the output has a utf-16 bom, we need to convert it now, as the
        // remaining code doesn't handle wide characters
        unsigned char *buf_u =
            reinterpret_cast<unsigned char *>(cont->buffer_work);
        if ((buf_u[0] == 0xFF) && (buf_u[1] == 0xFE)) {
            wchar_t *buffer_u16 =
                reinterpret_cast<wchar_t *>(cont->buffer_work + 2);
            std::string buffer_u8 = to_utf8(buffer_u16);
            HeapFree(GetProcessHeap(), 0, cont->buffer_work);
            cont->buffer_work =
                (char *)HeapAlloc(GetProcessHeap(), 0, buffer_u8.size() + 1);
            memcpy(cont->buffer_work, buffer_u8.c_str(), buffer_u8.size() + 1);
        }
    } catch (const std::exception &e) {
        crash_log("%s", e.what());
        result = CANCELED;
    }
    return result;
}

DWORD WINAPI ScriptWorkerThread(LPVOID lpParam) {
    script_container *cont = reinterpret_cast<script_container *>(lpParam);

    // Execute script
    int result = launch_program(cont);

    // Set finished status
    switch (result) {
        case 0:
            cont->status = SCRIPT_FINISHED;
            cont->last_problem = SCRIPT_NONE;
            cont->retry_count = cont->max_retries;
            cont->buffer_time = time(0);
            break;
        case 1:
            cont->status = SCRIPT_ERROR;
            cont->last_problem = SCRIPT_ERROR;
            cont->retry_count--;
            break;
        case 2:
            cont->status = SCRIPT_TIMEOUT;
            cont->last_problem = SCRIPT_TIMEOUT;
            cont->retry_count--;
            break;
        default:
            cont->status = SCRIPT_ERROR;
            cont->last_problem = SCRIPT_ERROR;
            cont->retry_count--;
    }

    // Cleanup work buffer in case the script ran into a timeout / error
    if (cont->status == SCRIPT_TIMEOUT || cont->status == SCRIPT_ERROR) {
        HeapFree(GetProcessHeap(), 0, cont->buffer_work);
        cont->buffer_work = NULL;
    }
    return 0;
}

bool SectionPluginGroup::exists(script_container *cont) {
    DWORD dwAttr = GetFileAttributes(cont->script_path.c_str());
    return !(dwAttr == INVALID_FILE_ATTRIBUTES);
}

void SectionPluginGroup::runContainer(script_container *cont) {
    // Return if this script is no longer present
    // However, the script container is preserved
    if (!exists(cont)) {
        crash_log("script %s no longer exists", cont->script_path.c_str());
        return;
    }

    time_t now = time(0);
    if (now - cont->buffer_time >= cont->max_age) {
        // Check if the thread within this cont is still collecting data
        // or a thread has finished but its data wasnt processed yet
        if (cont->status == SCRIPT_COLLECT || cont->status == SCRIPT_FINISHED) {
            return;
        }
        cont->status = SCRIPT_COLLECT;

        if (cont->worker_thread != INVALID_HANDLE_VALUE)
            CloseHandle(cont->worker_thread);

        crash_log("invoke script %s", cont->script_path.c_str());
        cont->worker_thread =
            CreateThread(nullptr,             // default security attributes
                         0,                   // use default stack size
                         ScriptWorkerThread,  // thread function name
                         cont,                // argument to thread function
                         0,                   // use default creation flags
                         nullptr);            // returns the thread identifier
        if (cont->execution_mode == SYNC ||
            (cont->execution_mode == ASYNC &&
             *_async_execution == SEQUENTIAL))
            WaitForSingleObject(cont->worker_thread, INFINITE);

        crash_log("finished with status %d (exit code %" PRIudword ")",
                  cont->status, cont->exit_code);
    }
}

void SectionPluginGroup::outputContainers(std::ostream &out) {
    // Collect and output data
    for (const auto &kv : _containers) {
        std::shared_ptr<script_container> cont = kv.second;
        if (!exists(cont.get())) {
            crash_log("script %s missing", cont->script_path.c_str());
            continue;
        }

        if (cont->status == SCRIPT_FINISHED) {
            // Free buffer
            if (cont->buffer != NULL) {
                HeapFree(GetProcessHeap(), 0, cont->buffer);
                cont->buffer = NULL;
            }

            // Replace BOM with newlines.
            // At this point the buffer must not contain a wide character
            // encoding as the code can't handle it!
            if (strlen(cont->buffer_work) >= 3 &&
                    (unsigned char)cont->buffer_work[0] == 0xEF &&
                    (unsigned char)cont->buffer_work[1] == 0xBB &&
                    (unsigned char)cont->buffer_work[2] == 0xBF) {
                cont->buffer_work[0] = '\n';
                cont->buffer_work[1] = '\n';
                cont->buffer_work[2] = '\n';
            }

            if (cont->max_age == 0) {
                cont->buffer = cont->buffer_work;
            } else {
                // Determine chache_info text
                char cache_info[32];
                snprintf(cache_info, sizeof(cache_info), ":cached(%d,%d)",
                        (int)cont->buffer_time, cont->max_age);
                int cache_len = strlen(cache_info) + 1;

                // We need to parse each line and replace any <<<section>>>
                // with <<<section:cached(123455678,3600)>>>
                // Allocate new buffer, process/modify each line of the
                // original buffer and write it into the new buffer
                // We increase this new buffer by a good amount, because
                // there might be several hundred
                // sections (e.g. veeam_backup status piggyback) within this
                // plugin output.
                // TODO: Maybe add a dry run mode. Count the number of
                // section lines and reserve a fitting extra heap
                int buffer_heap_size =
                    HeapSize(GetProcessHeap(), 0, cont->buffer_work);
                char *cache_buffer =
                    (char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
                            buffer_heap_size + 262144);
                int cache_buffer_offset = 0;

                char *line = strtok(cont->buffer_work, "\n");
                int write_bytes = 0;
                while (line) {
                    int length = strlen(line);
                    int cr_offset = line[length - 1] == '\r' ? 1 : 0;
                    if (length >= 8 && strncmp(line, "<<<<", 4) &&
                            (!strncmp(line, "<<<", 3) &&
                             !strncmp(line + length - cr_offset - 3, ">>>",
                                 3))) {
                        // The return value of snprintf seems broken (off by
                        // 3?). Great...
                        write_bytes = length - cr_offset - 3 +
                            1;  // length - \r - <<< + \0
                        snprintf(cache_buffer + cache_buffer_offset,
                                write_bytes, "%s", line);
                        cache_buffer_offset += write_bytes - 1;

                        snprintf(cache_buffer + cache_buffer_offset,
                                cache_len, "%s", cache_info);
                        cache_buffer_offset += cache_len - 1;

                        write_bytes =
                            3 + cr_offset + 1 + 1;  // >>> + \r + \n + \0
                        snprintf(cache_buffer + cache_buffer_offset,
                                write_bytes, "%s\n",
                                line + length - cr_offset - 3);
                        cache_buffer_offset += write_bytes - 1;
                    } else {
                        write_bytes = length + 1 + 1;  // length + \n + \0
                        snprintf(cache_buffer + cache_buffer_offset,
                                write_bytes, "%s\n", line);
                        cache_buffer_offset += write_bytes - 1;
                    }
                    line = strtok(NULL, "\n");
                }
                HeapFree(GetProcessHeap(), 0, cont->buffer_work);
                cont->buffer = cache_buffer;
            }
            cont->buffer_work = NULL;
            cont->status = SCRIPT_IDLE;
        } else if (cont->retry_count < 0 && cont->buffer != NULL) {
            // Remove outdated cache entries
            HeapFree(GetProcessHeap(), 0, cont->buffer);
            cont->buffer = NULL;
        }
        if (cont->buffer) out << cont->buffer;
    }
}

SectionPluginGroup::SectionPluginGroup(Configuration &config, const std::string &path, script_type type,
                               const std::string &user)
    : Section(typeToSection(type), typeToSection(type))
    , _path(path)
    , _type(type)
    , _user(user)
    , _default_execution_mode(config, "global", "caching_method", SYNC)
    , _async_execution(config, "global", "async_script_execution", SEQUENTIAL)
    , _execute_suffixes(config, "global", "execute")
    , _timeout(config, typeToSection(type), "timeout")
    , _cache_age(config, typeToSection(type), "cache_age")
    , _retry_count(config, typeToSection(type), "retry_count")
    , _execution_mode(config, typeToSection(type), "execution")
{
    if (type == PLUGIN) {
        // plugins don't have a "collective" header
        withHiddenHeader();
    }
}

SectionPluginGroup::~SectionPluginGroup()
{
    _containers.clear();
    CloseHandle(_collection_thread);
}

void SectionPluginGroup::startIfAsync()
{
    updateScripts();
    collectData(ASYNC);
}

void SectionPluginGroup::waitForCompletion() {
    DWORD dwExitCode = 0;
    while (true) {
        if (GetExitCodeThread(_collection_thread, &dwExitCode)) {
            if (dwExitCode != STILL_ACTIVE) break;
            Sleep(200);
        } else
            break;
    }
}

std::vector<HANDLE> SectionPluginGroup::stopAsync() {
    std::vector<HANDLE> result;
    for (const auto &kv : _containers) {
        if (kv.second->status == SCRIPT_COLLECT) {
            result.push_back(kv.second->worker_thread);
            kv.second->should_terminate = true;
        }
    }
    return result;
}

bool SectionPluginGroup::produceOutputInner(std::ostream &out,
                                        const Environment &env) {
    // gather the data for the sync sections
    collectData(SYNC);
    if (_type == PLUGIN) {
        // prevent errors from plugins missing their section header
        out << "<<<>>>\n";
    }

    outputContainers(out);

    if (_type == PLUGIN) {
        // prevent errors from plugins without final newline
        // TODO this may no longer be necessary as Section::produceOutput
        // appends a newline to any section not ending on one.
        out << "\n<<<>>>\n";
    }

    updateStatistics();

    return true;
}

int SectionPluginGroup::getTimeout(const char *name) const {
    for (const auto &cfg : *_timeout) {
        if (globmatch(cfg.first.c_str(), name)) {
            return cfg.second;
        }
    }
    return _type == PLUGIN ? DEFAULT_PLUGIN_TIMEOUT : DEFAULT_LOCAL_TIMEOUT;
}

int SectionPluginGroup::getCacheAge(const char *name) const {
    for (const auto &cfg : *_cache_age) {
        if (globmatch(cfg.first.c_str(), name)) {
            return cfg.second;
        }
    }
    return 0;
}

int SectionPluginGroup::getMaxRetries(const char *name) const {
    for (const auto &cfg : *_retry_count) {
        if (globmatch(cfg.first.c_str(), name)) {
            return cfg.second;
        }
    }
    return 0;
}

script_execution_mode SectionPluginGroup::getExecutionMode(
    const char *name) const {
    for (const auto &cfg : *_execution_mode) {
        if (globmatch(cfg.first.c_str(), name)) {
            return cfg.second;
        }
    }
    return *_default_execution_mode;
}

bool SectionPluginGroup::fileInvalid(const char *name) const {
    if (strlen(name) < 5) return false;

    const char *extension = strrchr(name, '.');
    if (extension == nullptr) {
        // ban files without extension
        return true;
    }

    if (_execute_suffixes.wasAssigned()) {
        ++extension;
        auto iter = std::find_if(
            _execute_suffixes->begin(), _execute_suffixes->end(),
            [extension](const std::string &valid_ext) {
                return strcasecmp(extension, valid_ext.c_str()) == 0;
            });
        return iter == _execute_suffixes->end();
    } else {
        return (!strcasecmp(extension, ".dir") ||
                !strcasecmp(extension, ".txt"));
    }
}

std::string SectionPluginGroup::withInterpreter(const char *path) const {
    size_t path_len = strlen(path);
    if (!strcmp(path + path_len - 3, ".pl")) {
        return std::string("perl.exe \"") + path + "\"";
    } else if (!strcmp(path + path_len - 3, ".py")) {
        return std::string("python.exe \"") + path + "\"";
    } else if (!strcmp(path + path_len - 4, ".vbs")) {
        // If this is a vbscript don't rely on the default handler for this
        // file extensions. This might be notepad or some other editor by
        // default on a lot of systems. So better add cscript as interpreter.
        return std::string("cscript.exe //Nologo \"") + path + "\"";
    } else if (!strcmp(path + path_len - 4, ".ps1")) {
        // Same for the powershell scripts. Add the powershell interpreter.
        // To make this work properly two things are needed:
        //   1.) The powershell interpreter needs to be in PATH
        //   2.) The execution policy needs to allow the script execution
        //       -> Get-ExecutionPolicy / Set-ExecutionPolicy
        //
        // actually, microsoft always installs the powershell interpreter to the
        // same directory (independent of the version) so even if it's not in
        // the path, we have a good chance with this fallback.
        const char *fallback =
            "C:\\Windows\\System32\\WindowsPowershell\\v1.0\\powershell.exe";

        char dummy;
        ::SearchPathA(NULL, "powershell.exe", NULL, 1, &dummy, NULL);
        std::string interpreter = ::GetLastError() != ERROR_FILE_NOT_FOUND
                                      ? "powershell.exe"
                                      : fallback;

        return interpreter + " -NoLogo -ExecutionPolicy RemoteSigned \"& \'" +
               path + "\'\"";
    } else {
        return std::string("\"") + path + "\"";
    }
}

std::string SectionPluginGroup::deriveCommand(const char *filename) const {
    std::string full_path = _path + "\\" + filename;
    // If the path in question is a directory -> continue
    DWORD dwAttr = GetFileAttributes(full_path.c_str());
    if (dwAttr != INVALID_FILE_ATTRIBUTES &&
        (dwAttr & FILE_ATTRIBUTE_DIRECTORY)) {
        return std::string();
    }

    std::string command = withInterpreter(full_path.c_str());

    std::string command_with_user;
    if (!_user.empty())
        return std::string("runas /User:") + _user + " " + command;
    else
        return command;
}

script_container *SectionPluginGroup::createContainer(
    const char *filename) const {
    script_container *result = new script_container();

    result->path = deriveCommand(filename);
    result->script_path = _path + "\\" + filename;
    result->buffer_time = 0;
    result->buffer = nullptr;
    result->buffer_work = nullptr;
    result->type = _type;
    result->should_terminate = 0;
    result->run_as_user = _user;
    result->execution_mode = getExecutionMode(filename);
    result->timeout = getTimeout(filename);
    result->max_retries = getMaxRetries(filename);
    result->max_age = getCacheAge(filename);
    result->status = SCRIPT_IDLE;
    result->last_problem = SCRIPT_NONE;

    return result;
}

void SectionPluginGroup::updateScripts() {
    DIR *dir = opendir(_path.c_str());
    if (dir) {
        struct dirent *de;
        while ((de = readdir(dir)) != 0) {
            char *name = de->d_name;

            if (name[0] != '.' && !fileInvalid(name)) {
                std::string full_command = deriveCommand(name);

                // Look if there is already an section for this program
                if (!full_command.empty() &&
                    (_containers.find(full_command) == _containers.end())) {
                    _containers[full_command].reset(createContainer(name));
                }
            }
        }
        closedir(dir);
    }
}

void SectionPluginGroup::updateStatistics() {
    for (const auto &kv : _containers) {
        std::shared_ptr<script_container> cont = kv.second;
        if (cont->type == PLUGIN)
            g_script_stat.pl_count++;
        else
            g_script_stat.lo_count++;

        switch (cont->last_problem) {
            case SCRIPT_TIMEOUT:
                if (cont->type == PLUGIN)
                    g_script_stat.pl_timeouts++;
                else
                    g_script_stat.lo_timeouts++;
                break;
            case SCRIPT_ERROR:
                if (cont->type == PLUGIN)
                    g_script_stat.pl_errors++;
                else
                    g_script_stat.lo_errors++;
                break;
            default:
                break;
        }
    }
}

DWORD WINAPI DataCollectionThread(LPVOID lpParam) {
    SectionPluginGroup *self = reinterpret_cast<SectionPluginGroup*>(lpParam);
    do {
        self->_data_collection_retriggered = false;
        for (const auto &kv : self->_containers) {
            if (kv.second->execution_mode == ASYNC) {
                self->runContainer(kv.second.get());
            }
        }
    } while (self->_data_collection_retriggered);
    return 0;
}

void SectionPluginGroup::collectData(script_execution_mode mode) {
    if (mode == SYNC) {
        crash_log("Collecting sync %s data",
                  _type == PLUGIN ? "plugin" : "local");
        for (const auto &kv : _containers) {
            if (kv.second->execution_mode == SYNC)
                runContainer(kv.second.get());
        }
    } else if (mode == ASYNC) {
        // If the thread is still running, just tell it to do another cycle
        DWORD dwExitCode = 0;
        if (GetExitCodeThread(_collection_thread, &dwExitCode)) {
            if (dwExitCode == STILL_ACTIVE) {
                _data_collection_retriggered = true;
                return;
            }
        }

        if (_collection_thread != INVALID_HANDLE_VALUE)
            CloseHandle(_collection_thread);
        crash_log("Start async thread for collecting %s data",
                  _type == PLUGIN ? "plugin" : "local");
        _collection_thread =
            CreateThread(nullptr,               // default security attributes
                         0,                     // use default stack size
                         DataCollectionThread,  // thread function name
                         this,                  // argument to thread function
                         0,                     // use default creation flags
                         nullptr);              // returns the thread identifier
    }
}

