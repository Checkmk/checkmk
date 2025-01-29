// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// core common functionaliaty
// probably "file" is better name

#pragma once

#include <fmt/format.h>
#include <fmt/xchar.h>

#include <chrono>
#include <ctime>
#include <filesystem>
#include <set>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>

#include "cfg.h"
#include "common/stop_watch.h"
#include "common/wtools.h"
#include "logger.h"
#include "tools/_misc.h"

namespace cma {}  // namespace cma

namespace cma::srv {
class ServiceProcessor;
}  // namespace cma::srv

namespace cma {

namespace tools {

bool AreFilesSame(const std::filesystem::path &tgt,
                  const std::filesystem::path &src);

// primitive command line checker
bool CheckArgvForValue(int argc, const wchar_t *argv[], int pos,
                       std::string_view value) noexcept;

/// divide view into two parts gor delimitter and after
std::pair<std::string_view, std::optional<std::string_view>> SplitView(
    std::string_view data, std::string_view delimiter);
using ScanViewCallback = std::function<void(std::string_view work)>;

/// determines used algorithm to convert data into UTF-8
enum UtfConversionMode {
    basic,           /// whole block is converted
    repair_by_line,  /// every line converted individually
};

bool IsUtf16BomLe(std::string_view data) noexcept;

/// call callback for every string between begin, delimiter and end
void ScanView(std::string_view data, std::string_view delimiter,
              ScanViewCallback callback);

}  // namespace tools
using PathVector = std::vector<std::filesystem::path>;
PathVector GatherAllFiles(const PathVector &folders);
// Scan one folder and add contents to the dirs and files
void GatherMatchingFilesAndDirs(
    const std::filesystem::path &search_dir,    // c:\windows
    const std::filesystem::path &dir_pattern,   // c:\windows\L*
    const std::filesystem::path &file_pattern,  // c:\windows\L*\*.log
    PathVector &files_found                     // output
);

void FilterPathByExtension(PathVector &paths,
                           const std::vector<std::string> &exts);
void RemoveDuplicatedNames(PathVector &paths);

/// remove all forbidden files
///
/// Normally deletes only cmk-update-agent.exe
void RemoveForbiddenNames(PathVector &paths);

PathVector FilterPathVector(const PathVector &found_files,
                            const std::vector<cfg::Plugins::ExeUnit> &units,
                            bool check_exists);
}  // namespace cma

namespace cma {
enum class ExecType { plugin, local };
bool IsValidFile(const std::filesystem::path &file_to_exec);
bool IsExecutable(const std::filesystem::path &file_to_exec);
std::wstring FindPowershellExe() noexcept;
std::wstring LocatePs1Proxy();

std::wstring MakePowershellWrapper(
    const std::filesystem::path &script) noexcept;

// add to scripts interpreter
inline std::wstring ConstructCommandToExec(
    const std::filesystem::path &path) noexcept {
    try {
        const auto extension = path.extension().wstring();

        std::wstring wrapper;
        if (IsExecutable(path)) {
            return fmt::format(L"\"{}\"", path.wstring());
        } else if (extension == L".pl") {
            return fmt::format(L"perl.exe \"{}\"", path.wstring());
        } else if (extension == L".py") {
            return fmt::format(L"python.exe \"{}\"", path.wstring());
        } else if (extension == L".vbs") {
            return fmt::format(L"cscript.exe //Nologo \"{}\"", path.wstring());
        } else if (extension == L".ps1") {
            return MakePowershellWrapper(path);
        } else {
            XLOG::l("Not supported extension file {}", path);
            return {};
        }
    } catch (const std::exception &e) {
        XLOG::l("Format failed for file '{}' exception: '{}'", path, e);
    }
    return {};
}

}  // namespace cma

namespace cma {
class TheMiniBox {
public:
    TheMiniBox() noexcept
        : stop_event_{::CreateEvent(nullptr, TRUE, FALSE, nullptr)} {}
    TheMiniBox(const TheMiniBox &) = delete;
    TheMiniBox &operator=(const TheMiniBox &) = delete;

    // #TODO implement movers!
    TheMiniBox(const TheMiniBox &&) = delete;
    TheMiniBox &operator=(const TheMiniBox &&) = delete;

    ~TheMiniBox() {
        clean();
        ::CloseHandle(stop_event_);
    }

    //
    bool startBlind(const std::string &cmd_line, const std::string &user) {
        std::lock_guard lk(lock_);
        if (process_ != nullptr) {
            return false;
        }
        sw_.start();
        id_ = L"blind";
        std::string command_line;
        if (!user.empty()) {
            command_line = "runas /User:" + user + " ";
        }
        command_line += cmd_line;

        exec_ = wtools::ConvertToUtf16(cmd_line);

        // send exec array entries to internal
        try {
            // now exec
            auto *ar = new wtools::AppRunner;
            proc_id_ = ar->goExecAsJob(exec_);
            if (proc_id_ != 0U) {
                process_ = ar;
                return true;
            }

            delete ar;  // start failed
        } catch (const std::exception &e) {
            XLOG::l(XLOG_FLINE + " exception {}", e.what());
        }
        sw_.stop();
        // cleaning up
        id_.clear();
        exec_.clear();

        return false;
    }
    enum class StartMode { job, detached, controller };
    bool startEx(std::wstring_view uniq_id, const std::wstring &exec,
                 StartMode start_mode,
                 const wtools::InternalUser &internal_user);
    bool startStd(std::wstring_view Id, const std::wstring &exec,
                  StartMode start_mode) {
        return startEx(Id, exec, start_mode, {});
    }

    [[nodiscard]] uint32_t getProcessId() {
        std::scoped_lock l(lock_);
        return process_->processId();
    }

    [[nodiscard]] uint32_t startedProcId() const noexcept { return proc_id_; }

    bool appendResult(HANDLE handle, const std::vector<char> &buf) {
        if (buf.empty()) {
            return true;
        }

        std::lock_guard lk(lock_);

        auto *h = process_->getStdioRead();
        if (h != nullptr && h == handle) {
            tools::AddVector(process_->getData(), buf);
            return true;
        }

        return false;
    }

    bool storeExitCode(uint32_t Pid, uint32_t Code) {
        std::lock_guard lk(lock_);
        return process_->trySetExitCode(Pid, Code);
    }

    [[nodiscard]] bool isFailed() const noexcept { return failed_; }

    // very special, only used for cmk-updater
    bool waitForUpdater(std::chrono::milliseconds timeout);

    // With kGrane interval tries to check running processes
    // returns true if all processes ended
    // returns false on timeout or break
    bool waitForEnd(std::chrono::milliseconds timeout);

    bool waitForEndWindows(std::chrono::milliseconds timeout);

    // normally kill process and associated data
    // also removes and resets other resources
    void clean() noexcept {
        // resources clean
        try {
            std::unique_lock lk(lock_);
            auto *process = process_;
            process_ = nullptr;
            cmd_.clear();
            id_.clear();
            exec_.clear();
            stop_set_ = false;
            proc_id_ = 0;
            lk.unlock();

            delete process;
        } catch (const std::exception & /*e*/) {
            // do nothing
        }
    }

    // stupid wrapper
    void processResults(
        const std::function<void(const std::wstring &cmd_line, uint32_t pid,
                                 uint32_t code,
                                 const std::vector<char> &data_block)> &func) {
        std::unique_lock lk(lock_);
        func(process_->getCmdLine(), process_->processId(),
             process_->exitCode(), process_->getData());
    }

    // signal to end, called by other public functions
    void stopWaiting() {
        std::lock_guard lk(lock_);
        stop_set_ = true;
        cv_stop_.notify_one();
        ::SetEvent(stop_event_);
    }

    // get handle to read data from stdio
    HANDLE getReadHandle() {
        std::vector<HANDLE> handles;
        std::unique_lock lk(lock_);
        auto *h = process_->getStdioRead();
        lk.unlock();
        return h;
    }

private:
    void readAndAppend(HANDLE read_handle, std::chrono::milliseconds timeout);
    [[nodiscard]] bool waitForBreakLoop(std::chrono::milliseconds timeout);
    HANDLE stop_event_;
    bool waitForStop(std::chrono::milliseconds interval);
    wtools::StopWatch sw_;
    // called AFTER process finished!
    void readWhatLeft() {
        auto *read_handle = getReadHandle();
        auto buf = wtools::ReadFromHandle(read_handle);
        if (!buf.empty()) {
            appendResult(read_handle, buf);
        }
    }

    static std::string formatProcessInLog(uint32_t pid,
                                          const std::wstring_view name) {
        return fmt::format("Process '{}' pid [{}]", wtools::ToUtf8(name), pid);
    }

    // check processes for exit
    // updates object with exit code
    // returns true if process  exists or not accessible
    bool checkProcessExit(const uint32_t pid) {
        auto [code, error] = wtools::GetProcessExitCode(pid);

        auto proc_string = formatProcessInLog(pid, exec_);
        // check for error
        if (error == 0) {
            if (code == STILL_ACTIVE) {
                return false;
            }

            // success and valid exit code store exit code
            XLOG::t("{} exits, code is [{}]", proc_string, code);
            storeExitCode(pid, code);
            return true;
        }

        if (code == 0) {
            storeExitCode(pid, 0);  // process rather died
            XLOG::d("{} is failed to open, error is [{}]", proc_string, error);
        } else {
            XLOG::l("Error  [{}] accessing {}", error, proc_string);
        }
        return true;
    }

    static bool isExecValid(const std::filesystem::path &file_exec) {
        if (!IsValidFile(file_exec)) {
            return false;
        }

        if (ConstructCommandToExec(file_exec).empty()) {
            XLOG::l("Can't create exe string for the '{}'", file_exec);
            return false;
        }

        return true;
    }

    bool isExecIn(const std::filesystem::path &file_exec) const {
        // now check for duplicates:
        auto cmd_line = ConstructCommandToExec(file_exec);
        return exec_ == cmd_line;
    }

    std::wstring cmd_;
    std::wstring id_;
    std::wstring exec_;

    std::mutex lock_;
    wtools::AppRunner *process_{nullptr};  // #TODO ? replace with unique_ptr ?
    uint32_t proc_id_{0};
    std::condition_variable cv_stop_;
    bool stop_set_{false};
    bool failed_{false};
};

}  // namespace cma

namespace cma {
enum class HackDataMode { header, line };

// build correct string for patching
std::string ConstructPatchString(time_t time_now, int cache_age,
                                 HackDataMode mode);

// 1. replaces '\r' with '\r\n'
// 2a. HackDataMode::header :
// <<<PLUGIN>>>\nsomething -> <<<PLUGIN:cached(123456789,3600)>>>\nsomething
//    if header bad or not found - nothing had been done
// true on success
// 2b. HackDataMode::line :
// hack every string with patch
// "string"
// "patch" + "string"
bool HackDataWithCacheInfo(std::vector<char> &out,
                           const std::vector<char> &original_data,
                           const std::string &patch, HackDataMode mode);

// cleans \r from string
inline bool HackPluginDataRemoveCr(std::vector<char> &out,
                                   const std::vector<char> &original_data) {
    return HackDataWithCacheInfo(out, original_data, "", HackDataMode::header);
}

std::string ConvertUtfData(const std::vector<char> &data_block,
                           tools::UtfConversionMode mode);

class PluginEntry : public cfg::PluginInfo {
public:
    explicit PluginEntry(std::filesystem::path path) : path_(std::move(path)) {}

    ~PluginEntry() {
        if (main_thread_) {
            breakAsync();
        }
    }

    PluginEntry(const PluginEntry &) = delete;
    PluginEntry &operator=(const PluginEntry &) = delete;
    PluginEntry(PluginEntry &&) = delete;
    PluginEntry &operator=(PluginEntry &&) = delete;

    // SYNC

    // negative MaxTimeout  means usage of the timeout()
    // 0 or positive min(MaxTimeout, timeout())
    std::vector<char> getResultsSync(const std::wstring &id, int max_timeout);
    std::vector<char> getResultsSync(const std::wstring &id) {
        return getResultsSync(id, -1);
    }

    // ASYNC:
    // if StartProcessNow then process will be started immediately
    // otherwise entry will be marked as required to start
    std::vector<char> getResultsAsync(bool start_process_now);

    // AU:
    void restartIfRequired();

    // stop with asyncing
    void breakAsync() noexcept;

    bool local() const {
        std::lock_guard lk(lock_);
        return exec_type_ == ExecType::local;
    }

    int failures() const {
        std::lock_guard lk(lock_);
        return failures_;
    }

    /// Check that failures count exceeds retry_ under condition
    /// retry_ is set(not 0)
    bool isTooManyRetries() const {
        std::lock_guard lk(lock_);
        return retry_ != 0 && failures_ > retry_;
    }

    bool running() const {
        std::lock_guard lk(lock_);
        return thread_on_ && main_thread_;
    }

    std::vector<char> cache() const {
        if (cacheAge() == 0) {
            return {};
        }

        const auto now = std::chrono::steady_clock::now();
        auto diff =
            std::chrono::duration_cast<std::chrono::seconds>(now - data_time_)
                .count();
        if (diff > cacheAge()) {
            return {};
        }

        std::lock_guard l(data_lock_);
        return data_;
    }

    // time from time(0) when buffer were stored
    auto legacyTime() const {
        std::lock_guard l(data_lock_);
        return legacy_time_;
    }

    std::filesystem::path path() const { return path_; }
    void setCmdLine(std::wstring_view name);
    std::vector<char> data() const {
        std::lock_guard lk(data_lock_);
        return data_;
    }

    template <typename T>
    void applyConfigUnit(const T &unit, ExecType exec_type,
                         wtools::InternalUsersDb *iu) {
        if (retry() != unit.retry() || timeout() != unit.timeout()) {
            XLOG::t("Important params changed, reset retry '{}'", path_);
            failures_ = 0;
        }

        retry_ = unit.retry();
        repair_invalid_utf_ = unit.repairInvalidUtf();
        cache_age_ = unit.cacheAge();
        timeout_ = unit.timeout();
        group_ = unit.group();
        user_ = unit.user();
        bool planned_async = unit.async() || unit.cacheAge() > 0;

        if (defined() && async() != planned_async) {
            XLOG::d.t("Plugin '{}' changes this mode to '{}'",
                      path().u8string(), unit.async() ? "ASYNC" : "SYNC");
            failures_ = 0;
            if (async()) {
                // clearing data from async mode
                async_ = false;
                breakAsync();
                minibox_.clean();
                std::lock_guard lk(data_lock_);
                data_.clear();
            }
        }
        async_ = planned_async;

        if (async() &&
            cacheAge()) {  // for async we have cache_age either 0 or > 120
            cache_age_ = std::max(cacheAge(), cfg::kMinimumCacheAge);
        } else {  // for sync cache_age is 0 always
            cache_age_ = 0;
        }

        correctRetry();
        iu_ = getInternalUser(iu);

        exec_type_ = exec_type;
        defined_ = true;
    }

    bool isGoingOld() const {
        std::lock_guard lk(lock_);
        return data_is_going_old_;
    }

    bool isNoDataAndNoThread() const {
        std::unique_lock lk_data(data_lock_);
        const bool no_data = data_.empty();
        lk_data.unlock();

        std::unique_lock lk_thread(lock_);
        const bool no_thread = !main_thread_ || !thread_on_;
        lk_thread.unlock();
        return no_data && no_thread;
    }

    // cache_age means always async, we have no guarantee that
    // invariant is ok 100% time, because bakery delivers us sync plugins
    // with cache age
    bool isRealAsync() const noexcept { return async() || cacheAge() != 0; }

    void removeFromExecution() noexcept { path_ = ""; }

    static int threadCount() noexcept { return g_tread_count.load(); }

    std::wstring cmdLine() const noexcept { return cmd_line_; }

    const wtools::InternalUser &getUser() const noexcept { return iu_; }

protected:
    tools::UtfConversionMode getUtfConversionMode() const;
    [[nodiscard]] wtools::InternalUser getInternalUser(
        wtools::InternalUsersDb *user_database) const;
    std::optional<std::string> startProcessName();
    void restartAsyncThreadIfFinished(const std::wstring &id);
    void markAsForRestart() {
        XLOG::l.i("markAsForRestart {}", path());
        std::lock_guard lk(lock_);
        data_is_going_old_ = true;
    }
    auto getDataAge() const noexcept {
        const auto current_time = std::chrono::steady_clock::now();
        return current_time - data_time_;
    }

    void joinAndReleaseMainThread() noexcept;
    void threadCore(const std::wstring &id);
    void registerProcess(uint32_t Id);

    // this is not normal situation
    // as a rule only after timeout
    void unregisterProcess() noexcept;

private:
    void correctRetry();
    /// on reading box
    /// MUST BE CALLED INSIDE LOCK_GUARD!
    void storeData(uint32_t proc_id, const std::vector<char> &data);
    /// on fail async
    /// MUST BE CALLED INSIDE LOCK_GUARD!
    void resetData();

    wtools::InternalUser iu_;
    TheMiniBox minibox_;

    std::filesystem::path path_;  // actual path to execute

    uint32_t process_id_{0};
    std::chrono::steady_clock::time_point start_time_;  // for timeout
    /// counter of fails, used by async, ignored by sync
    int failures_{0};

    ExecType exec_type_{ExecType::plugin};

    // async part
    mutable std::mutex data_lock_;  // cache() and time to control

    std::vector<char> data_;                           // cache
    std::chrono::steady_clock::time_point data_time_;  // when
    time_t legacy_time_ = 0;                           // I'm nice guy

    mutable std::mutex lock_;  // thread control
    std::unique_ptr<std::thread> main_thread_;
    bool thread_on_{false};  // get before start thread, released inside thread
    bool data_is_going_old_{false};  // when plugin finds data obsolete

    static std::atomic<int> g_tread_count;

    std::wstring cmd_line_;

#if defined(ENABLE_WHITE_BOX_TESTING)
    friend class PluginTest;
    FRIEND_TEST(PluginTest, ApplyConfig);
    FRIEND_TEST(PluginTest, TimeoutCalc);
    FRIEND_TEST(PluginTest, AsyncStartSimulation_Simulation);
    FRIEND_TEST(PluginTest, AsyncDataPickup_Component);
    FRIEND_TEST(PluginTest, AsyncLocal_Component);
    FRIEND_TEST(PluginTest, SyncLocal_Component);

    FRIEND_TEST(PluginTest, Entry);
#endif
};
wtools::InternalUser PluginsExecutionUser2Iu(std::string_view user);

TheMiniBox::StartMode GetStartMode(const std::filesystem::path &filepath);

// #TODO estimate class usage
using PluginMap = std::unordered_map<std::string, PluginEntry>;

const PluginEntry *GetEntrySafe(const PluginMap &plugin_map,
                                const std::string &key);
PluginEntry *GetEntrySafe(PluginMap &plugin_map, const std::string &key);

const PluginEntry *GetEntrySafe(const PluginMap &plugin_map,
                                const std::filesystem::path &f);
PluginEntry *GetEntrySafe(PluginMap &plugin_map,
                          const std::filesystem::path &f);

void InsertInPluginMap(PluginMap &plugin_map, const PathVector &found_files);

using UnitMap = std::unordered_map<std::string, cfg::Plugins::ExeUnit>;

void RemoveDuplicatedEntriesByName(UnitMap &um, ExecType exec_type);
std::vector<std::filesystem::path> RemoveDuplicatedFilesByName(
    const std::vector<std::filesystem::path> &found_files, ExecType exec_type);

void ApplyEverythingToPluginMap(
    wtools::InternalUsersDb *iu, PluginMap &plugin_map,
    const std::vector<cfg::Plugins::ExeUnit> &units,
    const std::vector<std::filesystem::path> &found_files, ExecType exec_type);

void FilterPluginMap(PluginMap &out_map, const PathVector &found_files);

void RemoveDuplicatedPlugins(PluginMap &plugin_map, bool check_exists);

void UpdatePluginMap(wtools::InternalUsersDb *iu, PluginMap &plugin_map,
                     ExecType exec_type, const PathVector &found_files,
                     const std::vector<cfg::Plugins::ExeUnit> &units,
                     bool check_exists);

inline void UpdatePluginMap(wtools::InternalUsersDb *iu, PluginMap &plugin_map,
                            ExecType exec_type, const PathVector &found_files,
                            const std::vector<cfg::Plugins::ExeUnit> &units) {
    return UpdatePluginMap(iu, plugin_map, exec_type, found_files, units, true);
}

void UpdatePluginMapCmdLine(PluginMap &plugin_map, srv::ServiceProcessor *sp);

// API call to exec all plugins and get back data and count
std::pair<std::vector<char>, int> RunSyncPlugins(PluginMap &plugins,
                                                 int timeout);
std::pair<std::vector<char>, int> RunAsyncPlugins(PluginMap &plugins,

                                                  bool start_immediately);

constexpr std::chrono::seconds kRestartInterval{60};

void RunDetachedPlugins(const PluginMap &plugins_map, int &start_count);
namespace provider::config {
constexpr bool g_async_plugin_without_cache_age_run_async = true;
constexpr bool g_set_logwatch_pos_to_end = true;

bool IsRunAsync(const PluginEntry &plugin) noexcept;
}  // namespace provider::config

namespace tools {
using StringSet = std::set<std::string, std::less<>>;
// returns true if string added
bool AddUniqStringToSetIgnoreCase(StringSet &cache,
                                  const std::string &value) noexcept;
// returns true if string added
bool AddUniqStringToSetAsIs(StringSet &cache,
                            const std::string &value) noexcept;
}  // namespace tools

// finds piggyback template <<<<name>>>>, if found returns 'name'
std::optional<std::string> GetPiggyBackName(const std::string &in_string);

bool TryToHackStringWithCachedInfo(std::string &in_string,
                                   const std::string &value_to_insert);

}  // namespace cma
