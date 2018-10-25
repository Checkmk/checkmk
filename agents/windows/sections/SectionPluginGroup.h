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

#ifndef SectionPluginGroup_h
#define SectionPluginGroup_h

#include <experimental/filesystem>
#include <map>
#include <string>
#include "Configurable.h"
#include "Section.h"
#include "types.h"

namespace fs = std::experimental::filesystem;

class Environment;
class SectionPlugin;

// How single scripts are executed
enum class script_execution_mode {
    SYNC,  // inline
    ASYNC  // delayed
};

inline std::ostream &operator<<(std::ostream &os,
                                const script_execution_mode mode) {
    return os << static_cast<unsigned>(mode);
}

// How delayed scripts are executed
enum class script_async_execution { PARALLEL, SEQUENTIAL };

inline std::ostream &operator<<(std::ostream &os,
                                const script_async_execution async) {
    return os << static_cast<unsigned>(async);
}

template <>
inline script_execution_mode from_string<script_execution_mode>(
    const WinApiInterface &, const std::string &value) {
    if (value == "async")
        return script_execution_mode::ASYNC;
    else if (value == "sync")
        return script_execution_mode::SYNC;
    throw std::runtime_error("invalid execution mode");
}

template <>
inline script_async_execution from_string<script_async_execution>(
    const WinApiInterface &, const std::string &value) {
    if (value == "parallel")
        return script_async_execution::PARALLEL;
    else if (value == "sequential")
        return script_async_execution::SEQUENTIAL;
    throw std::runtime_error("invalid async mode");
}

// States for plugin and local scripts
enum class script_status {
    SCRIPT_IDLE,
    SCRIPT_FINISHED,
    SCRIPT_COLLECT,
    SCRIPT_ERROR,
    SCRIPT_TIMEOUT,
    SCRIPT_NONE,
};

inline std::ostream &operator<<(std::ostream &os, const script_status status) {
    return os << static_cast<unsigned>(status);
}

enum class script_type { PLUGIN, LOCAL, MRPE };

struct HeapBufferHandleTraits {
    using HandleT = char *;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.HeapFree(winapi.GetProcessHeap(), 0, value);
    }
};

using HeapBufferHandle = WrappedHandle<HeapBufferHandleTraits>;

struct script_container {
    script_container(
        const std::string &_path,  // full path with interpreter, cscript, etc.
        const std::string &_script_path,  // path of script
        int _max_age, int _timeout, int _max_entries, const std::string &_user,
        script_type _type, script_execution_mode _execution_mode,
        const Environment &_env, Logger *_logger,
        const WinApiInterface &_winapi);

    script_container(const script_container &) = delete;
    ~script_container();
    script_container &operator=(const script_container &) = delete;

    const std::string path;         // full path with interpreter, cscript, etc.
    const std::string script_path;  // path of script
    const int max_age;
    const int timeout;
    const int max_retries;
    int retry_count{0};
    time_t buffer_time{0};
    HeapBufferHandle buffer;
    HeapBufferHandle buffer_work;
    const std::string run_as_user;
    const script_type type;
    const script_execution_mode execution_mode;
    script_status status{script_status::SCRIPT_IDLE};
    script_status last_problem{script_status::SCRIPT_NONE};
    volatile bool should_terminate{0};
    WrappedHandle<NullHandleTraits> worker_thread;
    DWORD exit_code{0};
    const Environment &env;
    Logger *logger;
    const WinApiInterface &winapi;
};

class SectionPluginGroup : public Section {
    friend DWORD
#if defined(_WIN32) || defined(_WIN64)
#if defined(_MSC_BUILD)
        __stdcall
#else
        __attribute__((__stdcall__))
#endif
#endif  // _WIN32 || _WIN64
        DataCollectionThread(LPVOID lpParam);

    using containers_t =
        std::map<std::string, std::shared_ptr<script_container>>;

    static const int DEFAULT_PLUGIN_TIMEOUT = 60;
    static const int DEFAULT_LOCAL_TIMEOUT = 60;

public:
    SectionPluginGroup(Configuration &config, const std::string &path,
                       script_type type, script_statistics_t &script_statistics,
                       Logger *logger, const WinApiInterface &winapi,
                       const std::string &user = std::string());

    virtual ~SectionPluginGroup();

    virtual void startIfAsync() override;
    virtual void waitForCompletion() override;
    virtual std::vector<HANDLE> stopAsync() override;

protected:
    virtual bool produceOutputInner(
        std::ostream &out, const std::optional<std::string> &) override;

private:
    void collectData(script_execution_mode mode);
    void runContainer(script_container *cont);
    void outputContainers(std::ostream &out);

    void updateStatistics();

    bool exists(script_container *cont) const;
    bool fileInvalid(const fs::path &filename) const;
    std::string deriveCommand(const fs::path &path) const;
    inline script_container *createContainer(const fs::path &path) const;
    void updateScripts();
    std::string withInterpreter(const fs::path &path) const;

    int getTimeout(const std::string &name) const;
    int getCacheAge(const std::string &name) const;
    int getMaxRetries(const std::string &name) const;
    script_execution_mode getExecutionMode(const std::string &name) const;

    std::string _path;
    script_type _type;
    std::string _user;
    WrappedHandle<NullHandleTraits> _collection_thread;
    std::atomic<bool> _data_collection_retriggered{false};
    containers_t _containers;
    Configurable<script_execution_mode> _default_execution_mode;
    Configurable<script_async_execution> _async_execution;
    SplittingListConfigurable<
        std::vector<std::string>,
        BlockMode::BlockExclusive<std::vector<std::string>>>
        _execute_suffixes;
    KeyedListConfigurable<int> _timeout;
    KeyedListConfigurable<int> _cache_age;
    KeyedListConfigurable<int> _retry_count;
    KeyedListConfigurable<script_execution_mode> _execution_mode;
    script_statistics_t &_script_statistics;
};

#endif  // SectionPluginGroup_h
