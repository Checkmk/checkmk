// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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
#include <dirent.h>
#include <sys/types.h>
#include "Environment.h"
#include "ExternalCmd.h"
#include "Logger.h"
#include "SectionHeader.h"

namespace {

const size_t HEAP_BUFFER_MAX = 2097152L;
const size_t HEAP_BUFFER_DEFAULT = 16384L;

const char *typeToSection(script_type type) {
    switch (type) {
        case script_type::PLUGIN:
            return "plugins";
        case script_type::LOCAL:
            return "local";
        case script_type::MRPE:
            return "mrpe";
        default:
            return "unknown";
    }
}

void outputScript(const std::string &output, script_container *cont,
                  const WinApiInterface &winapi) {
    const auto count = output.size();
    cont->buffer_work.reset(reinterpret_cast<char *>(winapi.HeapAlloc(
        winapi.GetProcessHeap(), HEAP_ZERO_MEMORY, count + 1)));
    output.copy(cont->buffer_work.get(), count);
    cont->buffer_work.get()[count] = '\0';
}

int launch_program(script_container *cont) {
    enum { SUCCESS = 0, CANCELED, BUFFER_FULL, WORKING } result = WORKING;
    const auto &logger = cont->logger;
    const WinApiInterface &winapi = cont->winapi;

    try {
        ExternalCmd command(cont->path.c_str(), cont->env, logger, winapi);

        static const size_t BUFFER_SIZE = 16635;
        char buf[BUFFER_SIZE];  // i/o buffer
        memset(buf, 0, BUFFER_SIZE);
        time_t process_start = time(0);

        cont->buffer_work.reset(reinterpret_cast<char *>(winapi.HeapAlloc(
            winapi.GetProcessHeap(), HEAP_ZERO_MEMORY, HEAP_BUFFER_DEFAULT)));

        unsigned long current_heap_size = winapi.HeapSize(
            winapi.GetProcessHeap(), 0, cont->buffer_work.get());

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
                        cont->buffer_work.reset(
                            reinterpret_cast<char *>(winapi.HeapReAlloc(
                                winapi.GetProcessHeap(), HEAP_ZERO_MEMORY,
                                cont->buffer_work.release(),
                                current_heap_size * 2)));
                        current_heap_size =
                            winapi.HeapSize(winapi.GetProcessHeap(), 0,
                                            cont->buffer_work.get());
                    } else {
                        result = BUFFER_FULL;
                        break;
                    }
                }
                if (result != BUFFER_FULL) {
                    size_t max_read = std::min<size_t>(
                        BUFFER_SIZE - 1, current_heap_size - out_offset);

                    DWORD bread = command.readStdout(
                        cont->buffer_work.get() + out_offset, max_read, true);
                    if (bread == 0) {
                        result = BUFFER_FULL;
                    }
                    out_offset += bread;
                }
            }

            if (result == BUFFER_FULL) {
                Debug(logger)
                    << "plugin produced more than 2MB output -> dropped";
            }

            if (cont->exit_code != STILL_ACTIVE) {
                result = SUCCESS;
            }

            if (result == WORKING) {
                winapi.Sleep(10);  // 10 milliseconds
            }
        }

        // if the output has a utf-16 bom, we need to convert it now, as the
        // remaining code doesn't handle wide characters
        unsigned char *buf_u =
            reinterpret_cast<unsigned char *>(cont->buffer_work.get());
        if ((buf_u[0] == 0xFF) && (buf_u[1] == 0xFE)) {
            wchar_t *buffer_u16 =
                reinterpret_cast<wchar_t *>(cont->buffer_work.get() + 2);
            outputScript(to_utf8(buffer_u16), cont, winapi);
        }
    } catch (const AgentUpdaterError &e) {
        outputScript(e.what(), cont, winapi);
        result = SUCCESS;
    } catch (const std::exception &e) {
        Error(logger) << e.what();
        result = CANCELED;
    }
    return result;
}

DWORD
#if defined(_WIN32) || defined(_WIN64)
__attribute__((__stdcall__))
#endif  // _WIN32 || _WIN64
ScriptWorkerThread(LPVOID lpParam) {
    script_container *cont = reinterpret_cast<script_container *>(lpParam);

    // Execute script
    int result = launch_program(cont);

    // Set finished status
    switch (result) {
        case 0:
            cont->status = script_status::SCRIPT_FINISHED;
            cont->last_problem = script_status::SCRIPT_NONE;
            cont->retry_count = cont->max_retries;
            cont->buffer_time = time(0);
            break;
        case 1:
            cont->status = script_status::SCRIPT_ERROR;
            cont->last_problem = script_status::SCRIPT_ERROR;
            cont->retry_count--;
            break;
        case 2:
            cont->status = script_status::SCRIPT_TIMEOUT;
            cont->last_problem = script_status::SCRIPT_TIMEOUT;
            cont->retry_count--;
            break;
        default:
            cont->status = script_status::SCRIPT_ERROR;
            cont->last_problem = script_status::SCRIPT_ERROR;
            cont->retry_count--;
    }

    // Cleanup work buffer in case the script ran into a timeout / error
    if (cont->status == script_status::SCRIPT_TIMEOUT ||
        cont->status == script_status::SCRIPT_ERROR) {
        cont->buffer_work.reset();
    }
    return 0;
}

std::unique_ptr<SectionHeaderBase> makeHeader(script_type type,
                                              Logger *logger) {
    if (type != script_type::PLUGIN)
        return std::make_unique<DefaultHeader>(typeToSection(type), logger);
    else  // plugin -> no collective header
        return std::make_unique<HiddenHeader>(logger);
}

}  // namespace

script_container::script_container(
    const std::string &_path,  // full path with interpreter, cscript, etc.
    const std::string &_script_path,  // path of script
    int _max_age, int _timeout, int _max_entries, const std::string &_user,
    script_type _type, script_execution_mode _execution_mode,
    const Environment &_env, Logger *_logger, const WinApiInterface &_winapi)
    : path(_path)
    , script_path(_script_path)
    , max_age(_max_age)
    , timeout(_timeout)
    , max_retries(_max_entries)
    , buffer(_winapi)
    , buffer_work(_winapi)
    , run_as_user(_user)
    , type(_type)
    , execution_mode(_execution_mode)
    , worker_thread(_winapi)
    , env(_env)
    , logger(_logger)
    , winapi(_winapi) {}

script_container::~script_container() {}

bool SectionPluginGroup::exists(script_container *cont) const {
    DWORD dwAttr = _winapi.GetFileAttributes(cont->script_path.c_str());
    return !(dwAttr == INVALID_FILE_ATTRIBUTES);
}

void SectionPluginGroup::runContainer(script_container *cont) {
    // Return if this script is no longer present
    // However, the script container is preserved
    if (!exists(cont)) {
        Warning(_logger) << "script " << cont->script_path
                         << " no longer exists";
        return;
    }

    time_t now = time(0);
    if (now - cont->buffer_time >= cont->max_age) {
        // Check if the thread within this cont is still collecting data
        // or a thread has finished but its data wasnt processed yet
        if (cont->status == script_status::SCRIPT_COLLECT ||
            cont->status == script_status::SCRIPT_FINISHED) {
            return;
        }
        cont->status = script_status::SCRIPT_COLLECT;

        Debug(_logger) << "invoke script " << cont->script_path;
        cont->worker_thread = {
            _winapi.CreateThread(nullptr,  // default security attributes
                                 0,        // use default stack size
                                 ScriptWorkerThread,  // thread function name
                                 cont,      // argument to thread function
                                 0,         // use default creation flags
                                 nullptr),  // returns the thread identifier
            _winapi};
        if (cont->execution_mode == script_execution_mode::SYNC ||
            (cont->execution_mode == script_execution_mode::ASYNC &&
             *_async_execution == script_async_execution::SEQUENTIAL))
            _winapi.WaitForSingleObject(cont->worker_thread.get(), INFINITE);

        Debug(_logger) << "finished with status " << cont->status
                       << " (exit code " << cont->exit_code << ")";
    }
}

void SectionPluginGroup::outputContainers(std::ostream &out) {
    // Collect and output data
    for (const auto &kv : _containers) {
        std::shared_ptr<script_container> cont = kv.second;
        if (!exists(cont.get())) {
            Warning(_logger) << "script " << cont->script_path << " missing";
            continue;
        }

        if (cont->status == script_status::SCRIPT_FINISHED) {
            // Free buffer
            cont->buffer.reset();

            // Replace BOM with newlines.
            // At this point the buffer must not contain a wide character
            // encoding as the code can't handle it!
            if (strlen(cont->buffer_work.get()) >= 3 &&
                static_cast<unsigned char>(cont->buffer_work.get()[0]) ==
                    0xEF &&
                static_cast<unsigned char>(cont->buffer_work.get()[1]) ==
                    0xBB &&
                static_cast<unsigned char>(cont->buffer_work.get()[2]) ==
                    0xBF) {
                cont->buffer_work.get()[0] = '\n';
                cont->buffer_work.get()[1] = '\n';
                cont->buffer_work.get()[2] = '\n';
            }

            if (cont->max_age == 0) {
                cont->buffer.reset(cont->buffer_work.release());
            } else {
                // Determine chache_info text
                char cache_info[32];
                snprintf(cache_info, sizeof(cache_info), ":cached(%d,%d)",
                         static_cast<int>(cont->buffer_time), cont->max_age);
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
                int buffer_heap_size = _winapi.HeapSize(
                    _winapi.GetProcessHeap(), 0, cont->buffer_work.get());
                HeapBufferHandle cache_buffer(
                    reinterpret_cast<char *>(_winapi.HeapAlloc(
                        _winapi.GetProcessHeap(), HEAP_ZERO_MEMORY,
                        buffer_heap_size + 262144)),
                    _winapi);
                int cache_buffer_offset = 0;

                char *line = strtok(cont->buffer_work.get(), "\n");
                int write_bytes = 0;
                while (line) {
                    int length = strlen(line);
                    int cr_offset = line[length - 1] == '\r' ? 1 : 0;
                    if (length >= 8 && strncmp(line, "<<<<", 4) &&
                        (!strncmp(line, "<<<", 3) &&
                         !strncmp(line + length - cr_offset - 3, ">>>", 3))) {
                        // The return value of snprintf seems broken (off by
                        // 3?). Great...
                        write_bytes = length - cr_offset - 3 +
                                      1;  // length - \r - <<< + \0
                        snprintf(cache_buffer.get() + cache_buffer_offset,
                                 write_bytes, "%s", line);
                        cache_buffer_offset += write_bytes - 1;

                        snprintf(cache_buffer.get() + cache_buffer_offset,
                                 cache_len, "%s", cache_info);
                        cache_buffer_offset += cache_len - 1;

                        write_bytes =
                            3 + cr_offset + 1 + 1;  // >>> + \r + \n + \0
                        snprintf(cache_buffer.get() + cache_buffer_offset,
                                 write_bytes, "%s\n",
                                 line + length - cr_offset - 3);
                        cache_buffer_offset += write_bytes - 1;
                    } else {
                        write_bytes = length + 1 + 1;  // length + \n + \0
                        snprintf(cache_buffer.get() + cache_buffer_offset,
                                 write_bytes, "%s\n", line);
                        cache_buffer_offset += write_bytes - 1;
                    }
                    line = strtok(NULL, "\n");
                }
                cont->buffer.reset(cache_buffer.release());
            }
            cont->buffer_work.reset();
            cont->status = script_status::SCRIPT_IDLE;
        } else if (cont->retry_count < 0) {
            // Remove outdated cache entries
            cont->buffer.reset();
        }
        if (cont->buffer) {
            out << cont->buffer.get();
        }
    }
}

SectionPluginGroup::SectionPluginGroup(
    Configuration &config, const std::string &path, script_type type,
    script_statistics_t &script_statistics, Logger *logger,
    const WinApiInterface &winapi, const std::string &user)
    : Section(typeToSection(type), config.getEnvironment(), logger, winapi,
              makeHeader(type, logger))
    , _path(path)
    , _type(type)
    , _user(user)
    , _collection_thread(_winapi)
    , _default_execution_mode(config, "global", "caching_method",
                              script_execution_mode::SYNC, _winapi)
    , _async_execution(config, "global", "async_script_execution",
                       script_async_execution::SEQUENTIAL, _winapi)
    , _execute_suffixes(config, "global", "execute", _winapi)
    , _timeout(config, typeToSection(type), "timeout", _winapi)
    , _cache_age(config, typeToSection(type), "cache_age", _winapi)
    , _retry_count(config, typeToSection(type), "retry_count", _winapi)
    , _execution_mode(config, typeToSection(type), "execution", _winapi)
    , _script_statistics(script_statistics) {}

SectionPluginGroup::~SectionPluginGroup() { _containers.clear(); }

void SectionPluginGroup::startIfAsync() {
    updateScripts();
    collectData(script_execution_mode::ASYNC);
}

void SectionPluginGroup::waitForCompletion() {
    DWORD dwExitCode = 0;
    while (true) {
        if (_winapi.GetExitCodeThread(_collection_thread.get(), &dwExitCode)) {
            if (dwExitCode != STILL_ACTIVE) break;
            _winapi.Sleep(200);
        } else
            break;
    }
}

std::vector<HANDLE> SectionPluginGroup::stopAsync() {
    std::vector<HANDLE> result;
    for (const auto &kv : _containers) {
        if (kv.second->status == script_status::SCRIPT_COLLECT) {
            result.push_back(kv.second->worker_thread.get());
            kv.second->should_terminate = true;
        }
    }
    return result;
}

bool SectionPluginGroup::produceOutputInner(
    std::ostream &out, const std::optional<std::string> &) {
    Debug(_logger) << "SectionPluginGroup::produceOutputInner";
    // gather the data for the sync sections
    collectData(script_execution_mode::SYNC);
    if (_type == script_type::PLUGIN) {
        // prevent errors from plugins missing their section header
        out << "<<<>>>\n";
    }

    outputContainers(out);

    if (_type == script_type::PLUGIN) {
        // prevent errors from plugins without final newline
        // TODO this may no longer be necessary as Section::produceOutput
        // appends a newline to any section not ending on one.
        out << "\n<<<>>>\n";
    }

    updateStatistics();

    return true;
}

int SectionPluginGroup::getTimeout(const std::string &name) const {
    for (const auto & [ plugin, timeout ] : *_timeout) {
        if (globmatch(plugin, name)) {
            return timeout;
        }
    }
    return _type == script_type::PLUGIN ? DEFAULT_PLUGIN_TIMEOUT
                                        : DEFAULT_LOCAL_TIMEOUT;
}

int SectionPluginGroup::getCacheAge(const std::string &name) const {
    for (const auto & [ plugin, age ] : *_cache_age) {
        if (globmatch(plugin, name)) {
            return age;
        }
    }
    return 0;
}

int SectionPluginGroup::getMaxRetries(const std::string &name) const {
    for (const auto & [ plugin, count ] : *_retry_count) {
        if (globmatch(plugin, name)) {
            return count;
        }
    }
    return 0;
}

script_execution_mode SectionPluginGroup::getExecutionMode(
    const std::string &name) const {
    for (const auto & [ plugin, mode ] : *_execution_mode) {
        if (globmatch(plugin, name)) {
            return mode;
        }
    }
    return *_default_execution_mode;
}

bool SectionPluginGroup::fileInvalid(const fs::path &filename) const {
    if (filename.string().size() < 5) return false;

    const auto extension = filename.extension();
    if (extension.empty()) {
        // ban files without extension
        return true;
    }
    const std::vector<std::string> defaultSuffixes{"dir", "txt"};
    bool negativeMatch = _execute_suffixes.wasAssigned();
    const auto &suffixes = negativeMatch ? *_execute_suffixes : defaultSuffixes;
    const auto extString = extension.string().substr(1);
    bool match = std::any_of(suffixes.cbegin(), suffixes.cend(),
                             [&extString](const std::string &suffix) {
                                 return ci_equal(extString, suffix);
                             });
    return negativeMatch ? !match : match;
}

std::string SectionPluginGroup::withInterpreter(const fs::path &path) const {
    const auto extString = path.extension().string();
    if (extString == ".pl") {
        return std::string("perl.exe \"") + path.string() + "\"";
    } else if (extString == ".py") {
        return std::string("python.exe \"") + path.string() + "\"";
    } else if (extString == ".vbs") {
        // If this is a vbscript don't rely on the default handler for this
        // file extensions. This might be notepad or some other editor by
        // default on a lot of systems. So better add cscript as interpreter.
        return std::string("cscript.exe //Nologo \"") + path.string() + "\"";
    } else if (extString == ".ps1") {
        // Same for the powershell scripts. Add the powershell interpreter.
        // To make this work properly two things are needed:
        //   1.) The powershell interpreter needs to be in PATH
        //   2.) The execution policy needs to allow the script execution
        //       -> Get-ExecutionPolicy / Set-ExecutionPolicy
        //
        // actually, microsoft always installs the powershell interpreter to the
        // same directory (independent of the version) so even if it's not in
        // the path, we have a good chance with this fallback.
        const std::string fallback{
            "C:\\Windows\\System32\\WindowsPowershell\\v1.0\\powershell.exe"};

        char dummy;
        _winapi.SearchPathA(NULL, "powershell.exe", NULL, 1, &dummy, NULL);
        std::string interpreter = _winapi.GetLastError() != ERROR_FILE_NOT_FOUND
                                      ? "powershell.exe"
                                      : fallback;

        return interpreter + " -NoLogo -Noprofile -ExecutionPolicy Bypass \"& \'" +
               path.string() + "\'\"";
    } else {
        return std::string("\"") + path.string() + "\"";
    }
}

std::string SectionPluginGroup::deriveCommand(const fs::path &path) const {
    std::string full_path = path.string();
    // If the path in question is a directory -> continue
    DWORD dwAttr = _winapi.GetFileAttributes(full_path.c_str());
    if (dwAttr != INVALID_FILE_ATTRIBUTES &&
        (dwAttr & FILE_ATTRIBUTE_DIRECTORY)) {
        return std::string();
    }

    std::string command = withInterpreter(path);

    std::string command_with_user;
    if (!_user.empty())
        return std::string("runas /User:") + _user + " " + command;
    else
        return command;
}

script_container *SectionPluginGroup::createContainer(
    const fs::path &path) const {
    const auto filename = path.filename().string();
    return new script_container(
        deriveCommand(path), path.string(), getCacheAge(filename),
        getTimeout(filename), getMaxRetries(filename), _user, _type,
        getExecutionMode(filename), _env, _logger, _winapi);
}

void SectionPluginGroup::updateScripts() {
    for (const auto &de : fs::directory_iterator(_path)) {
        const auto filename = de.path().filename();

        if (filename.string().front() != '.' && !fileInvalid(filename)) {
            std::string full_command = deriveCommand(de.path());

            // Look if there is already an section for this program
            if (!full_command.empty() &&
                (_containers.find(full_command) == _containers.end())) {
                _containers[full_command].reset(createContainer(de.path()));
            }
        }
    }
}

void SectionPluginGroup::updateStatistics() {
    for (const auto &kv : _containers) {
        std::shared_ptr<script_container> cont = kv.second;
        if (cont->type == script_type::PLUGIN)
            ++_script_statistics["plugin_count"];
        else
            ++_script_statistics["local_count"];

        switch (cont->last_problem) {
            case script_status::SCRIPT_TIMEOUT:
                if (cont->type == script_type::PLUGIN)
                    ++_script_statistics["plugin_timeouts"];
                else
                    ++_script_statistics["local_timeouts"];
                break;
            case script_status::SCRIPT_ERROR:
                if (cont->type == script_type::PLUGIN)
                    ++_script_statistics["plugin_errors"];
                else
                    ++_script_statistics["local_errors"];
                break;
            default:
                break;
        }
    }
}

DWORD
#if defined(_WIN32) || defined(_WIN64)
__attribute__((__stdcall__))
#endif  // _WIN32 || _WIN64
DataCollectionThread(LPVOID lpParam) {
    SectionPluginGroup *self = reinterpret_cast<SectionPluginGroup *>(lpParam);
    do {
        self->_data_collection_retriggered = false;
        for (const auto &kv : self->_containers) {
            if (kv.second->execution_mode == script_execution_mode::ASYNC) {
                self->runContainer(kv.second.get());
            }
        }
    } while (self->_data_collection_retriggered);
    return 0;
}

void SectionPluginGroup::collectData(script_execution_mode mode) {
    const std::string typeName =
        _type == script_type::PLUGIN ? "plugin" : "local";
    if (mode == script_execution_mode::SYNC) {
        Debug(_logger) << "Collecting sync " << typeName << " data";
        for (const auto &kv : _containers) {
            if (kv.second->execution_mode == script_execution_mode::SYNC)
                runContainer(kv.second.get());
        }
    } else if (mode == script_execution_mode::ASYNC) {
        // If the thread is still running, just tell it to do another cycle
        DWORD dwExitCode = 0;
        if (_winapi.GetExitCodeThread(_collection_thread.get(), &dwExitCode)) {
            if (dwExitCode == STILL_ACTIVE) {
                _data_collection_retriggered = true;
                return;
            }
        }

        Debug(_logger) << "Start async thread for collecting " << typeName
                       << " data";
        _collection_thread = {
            _winapi.CreateThread(nullptr,  // default security attributes
                                 0,        // use default stack size
                                 DataCollectionThread,  // thread function name
                                 this,      // argument to thread function
                                 0,         // use default creation flags
                                 nullptr),  // returns the thread identifier
            _winapi};
    }
}
