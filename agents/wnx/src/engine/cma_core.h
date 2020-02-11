// core common functionaliaty
// probably "file" is better name

#pragma once

#include <fmt/format.h>
#include <time.h>

#include <chrono>
#include <filesystem>
#include <set>
#include <string>
#include <string_view>
#include <unordered_map>

#include "cfg.h"
#include "common/stop_watch.h"
#include "common/wtools.h"
#include "logger.h"
#include "tools/_misc.h"

namespace cma {
wtools::InternalUser ObtainInternalUser(std::wstring_view group);
void KillAllInternalUsers();
}  // namespace cma

namespace cma {
namespace tools {

// add content of file to the Buf
template <typename T>
bool AppendFileContent(T& Buf, HANDLE h, size_t Count) noexcept {
    // check what we have already inside
    auto buf_size = Buf.size();
    try {
        Buf.resize(buf_size + Count);
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FLINE + " exception: '{}'", e.what());
        return false;
    }

    // add new data
    auto read_buffer = Buf.data() + buf_size;
    DWORD read_in_fact = 0;
    auto count = static_cast<DWORD>(Count);
    auto result = ::ReadFile(h, read_buffer, count, &read_in_fact, nullptr);
    if (!result) false;

    if (buf_size + read_in_fact != Buf.size()) {
        Buf.resize(buf_size + read_in_fact);
    }

    return true;
}

template <typename T>
T ReadFromHandle(HANDLE Handle) {
    T buf;
    for (;;) {
        auto read_count = wtools::DataCountOnHandle(Handle);

        // now reading to the end
        if (read_count == 0) break;  // no data
        if (!cma::tools::AppendFileContent<T>(buf, Handle, read_count))
            break;  // io fail
    }
    return buf;
}

// primitive command line checker
bool CheckArgvForValue(int argc, const wchar_t* argv[], int pos,
                       std::string_view value) noexcept;
}  // namespace tools
using PathVector = std::vector<std::filesystem::path>;
PathVector GatherAllFiles(const PathVector& Folders);
// Scan one folder and add contents to the dirs and files
void GatherMatchingFilesAndDirs(
    const std::filesystem::path& SearchDir,    // c:\windows
    const std::filesystem::path& DirPattern,   // c:\windows\L*
    const std::filesystem::path& FilePattern,  // c:\windows\L*\*.log
    PathVector& FilesFound                     // output
);

void FilterPathByExtension(PathVector& Paths, std::vector<std::string> Exts);
void RemoveDuplicatedNames(PathVector& Paths);
PathVector SelectPathVectorByPattern(const PathVector& Paths,
                                     const std::string& Pattern);
const PathVector FilterPathVector(
    const PathVector& FoundFiles,
    const std::vector<cma::cfg::Plugins::ExeUnit>& Units, bool CheckExists);
};  // namespace cma

namespace cma {
inline bool IsValidFile(const std::filesystem::path& FileToExec) {
    if (std::filesystem::exists(FileToExec) &&
        !std::filesystem::is_directory(FileToExec))
        return true;
    return false;
}
// check is extension is valid for OS
inline bool IsExecutable(const std::filesystem::path& FileToExec) {
    static std::filesystem::path executables[] = {L".exe", L".bat", L".cmd"};
    auto actual_extension = FileToExec.extension();
    for (auto& ext : executables)
        if (ext == actual_extension) return true;

    return false;
}

inline std::wstring FindPowershellExe() noexcept {
    namespace fs = std::filesystem;
    constexpr std::wstring_view powershell_name = L"powershell.exe";
    wchar_t buffer[16];
    auto ret =
        ::SearchPathW(NULL, powershell_name.data(), NULL, 1, buffer, NULL);

    if (ret != 0) return std::wstring(powershell_name);

    // file not found on path
    auto powershell_path =
        cma::tools::win::GetSomeSystemFolder(FOLDERID_System);

    try {
        fs::path ps(powershell_path);
        ps /= L"WindowsPowerShell";
        ps /= L"v1.0";
        ps /= powershell_name;
        if (fs::exists(ps)) return ps;
        XLOG::l("Not found powershell");
    } catch (const std::exception& e) {
        XLOG::l("malformed name {} e:{}",
                wtools::ConvertToUTF8(powershell_path), e.what());
    }
    return {};
}

// either finds powershell on the path
// or build command
// gtest[+]
inline std::wstring MakePowershellWrapper() {
    namespace fs = std::filesystem;

    std::wstring powershell_exe = FindPowershellExe();

    // file found
    return powershell_exe +
           L" -NoLogo -NoProfile -ExecutionPolicy Bypass -File \"{}\"";
}

// add to scripts interpreter
// #TODO this is BAD PLACE
inline std::wstring ConstructCommandToExec(const std::filesystem::path& Path) {
    const auto extension = Path.extension().wstring();

    std::wstring wrapper;
    if (IsExecutable(Path)) {
        wrapper = L"\"{}\"";
    } else if (extension == L".pl") {
        wrapper = L"perl.exe \"{}\"";
    } else if (extension == L".py") {
        wrapper = L"python.exe \"{}\"";
    } else if (extension == L".vbs") {
        wrapper = L"cscript.exe //Nologo \"{}\"";
    } else if (extension == L".ps1") {
        wrapper = MakePowershellWrapper();
    } else {
        XLOG::l("Not supported extension file {}", Path.u8string());
        return {};
    }

    if (wrapper.empty()) {
        XLOG::l("impossible to find exe for file {}", Path.u8string());
        return {};
    }

    std::wstring out;
    try {
        return fmt::format(wrapper, Path.wstring());
    } catch (std::exception& e) {
        XLOG::l("impossible to format Data for file '{}' exception: '{}'",
                Path.u8string(), e.what());
    }
    return {};
}

}  // namespace cma

namespace cma {
class TheMiniBox {
public:
    TheMiniBox() : process_(nullptr), stop_set_(false), proc_id_(0) {
        stop_event_ = ::CreateEvent(nullptr, TRUE, FALSE, nullptr);
    }
    TheMiniBox(const TheMiniBox&) = delete;
    TheMiniBox& operator=(const TheMiniBox&) = delete;

    // #TODO implement movers!
    TheMiniBox(const TheMiniBox&&) = delete;
    TheMiniBox& operator=(const TheMiniBox&&) = delete;

    ~TheMiniBox() {
        clean();
        CloseHandle(stop_event_);
    }

    //
    bool startBlind(const std::string CommandLine, const std::string User) {
        int count = 0;

        std::lock_guard lk(lock_);
        if (process_) return false;
        sw_.start();
        id_ = L"blind";
        std::string command_line;
        if (!User.empty()) command_line = "runas /User:" + User + " ";
        command_line += CommandLine;

        exec_ = wtools::ConvertToUTF16(CommandLine);

        // send exec array entries to internal
        try {
            // now exec
            auto ar = new wtools::AppRunner;
            proc_id_ = ar->goExecAsJob(exec_);
            if (proc_id_) {
                process_ = ar;
                return true;
            }

            delete ar;  // start failed
        } catch (const std::exception& e) {
            XLOG::l(XLOG_FLINE + " exception {}", e.what());
        }
        sw_.stop();
        // cleaning up
        id_.clear();
        exec_.clear();

        return false;
    }
    enum class StartMode { job, updater };
    bool startEx(std::wstring_view Id, std::filesystem::path ExeFile,
                 StartMode start_mode, wtools::InternalUser internal_user);
    bool start(std::wstring_view Id, std::filesystem::path ExeFile,

               StartMode start_mode) {
        return startEx(Id, ExeFile, start_mode, {});
    }

    // strange?
    [[nodiscard]] uint32_t getProcessId() {
        uint32_t proc_id;
        std::unique_lock lk(lock_);
        proc_id = process_->processId();
        lk.unlock();
        return proc_id;
    }

    // really obtained proc id. Safe function
    [[nodiscard]] uint32_t startedProcId() const { return proc_id_; }

    bool appendResult(HANDLE Handle, std::vector<char>& Buf) {
        if (Buf.size() == 0) return true;

        std::lock_guard lk(lock_);
        {
            auto h = process_->getStdioRead();
            if (h && h == Handle) {
                cma::tools::AddVector(process_->getData(), Buf);
                return true;
            }
        }
        return false;
    }

    bool storeExitCode(uint32_t Pid, uint32_t Code) {
        std::lock_guard lk(lock_);
        if (process_->trySetExitCode(Pid, Code)) return true;
        return false;
    }

    [[nodiscard]] bool const failed() const noexcept { return failed_; }

    // very special, only used for cmk-updater
    bool waitForUpdater(std::chrono::milliseconds Timeout);

    // With kGrane interval tries to check running processes
    // returns true if all processes ended
    // returns false on timeout or break;
    bool waitForEnd(std::chrono::milliseconds Timeout);

    bool waitForEndWindows(std::chrono::milliseconds Timeout);

    // normally kill process and associated data
    // also removes and resets other resources
    void clean() {
        // resources clean
        std::unique_lock lk(lock_);
        auto process = std::move(process_);
        process_ = nullptr;
        cmd_.clear();
        id_.clear();
        exec_.clear();
        stop_set_ = false;
        proc_id_ = 0;
        lk.unlock();

        delete process;
    }

    // stupid wrapper
    void processResults(
        std::function<void(const std::wstring CmdLine, uint32_t Pid,
                           uint32_t Code, const std::vector<char>& Data)>
            Func) {
        std::unique_lock lk(lock_);
        Func(process_->getCmdLine(), process_->processId(),
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
        auto h = process_->getStdioRead();
        lk.unlock();
        return h;
    }

private:
    HANDLE stop_event_;
    bool waitForStop(std::chrono::milliseconds Timeout);
    wtools::StopWatch sw_;
    // called AFTER process finished!
    void readWhatLeft() {
        using namespace std;
        auto read_handle = getReadHandle();
        auto buf = cma::tools::ReadFromHandle<vector<char>>(read_handle);
        if (buf.size()) appendResult(read_handle, buf);
    }

    static std::string formatProcessInLog(uint32_t pid,
                                          const std::wstring_view name) {
        return fmt::format("Process '{}' pid [{}]", wtools::ConvertToUTF8(name),
                           pid);
    }

    // check processes for exit
    // updates object with exit code
    // returns true if process  exists or not accessible
    bool checkProcessExit(const uint32_t pid) {
        auto [code, error] = wtools::GetProcessExitCode(pid);

        auto proc_string = formatProcessInLog(pid, exec_);
        // check for error
        if (error == 0) {
            if (code == STILL_ACTIVE) return false;

            // success and valid exit code store exit code
            XLOG::t("{} exits, code is [{}]", proc_string, code);
            storeExitCode(pid, code);
            return true;
        }

        if (code == 0) {
            storeExitCode(pid, 0);  // process rather died
            XLOG::d("{} is failed to open, error is [{}]", proc_string, error);
        } else
            XLOG::l("Error  [{}] accessing {}", error, proc_string);
        return true;
    }

    static inline bool isExecValid(const std::filesystem::path& FileExec) {
        if (!IsValidFile(FileExec)) return false;  // sanity

        auto execute_string = ConstructCommandToExec(FileExec);
        if (execute_string.empty()) {
            XLOG::l("Can't create exe string for the '{}'",
                    FileExec.u8string());
            return false;
        }

        return true;
    }

    bool isExecIn(const std::filesystem::path& FileExec) {
        // now check for duplicates:
        auto cmd_line = ConstructCommandToExec(FileExec);
        return exec_ == cmd_line;
    }

private:
    std::wstring cmd_;
    std::wstring id_;
    std::wstring exec_;

    std::mutex lock_;
    wtools::AppRunner* process_;  // #TODO ? replace with unique_ptr ?
    uint32_t proc_id_;
    std::condition_variable cv_stop_;
    bool stop_set_ = false;
    bool failed_ = false;
};

}  // namespace cma

namespace cma {
enum class HackDataMode { header, line };

// build correct string for patching
std::string ConstructPatchString(time_t time_now, int cache_age,
                                 HackDataMode mode) noexcept;

// 1. replaces '\r' with '\r\n'
// 2a. HackDataMode::header :
// <<<PLUGIN>>>\nsomething -> <<<PLUGIN:cached(123456789,3600)>>>\nsomething
//    if header bad or not found - nothing had been done
// true on success
// 2b. HackDataMode::line :
// hack every string with patch
// "string"
// "patch" + "string"
bool HackDataWithCacheInfo(std::vector<char>& Out,
                           const std::vector<char>& OriginalData,
                           const std::string& patch, HackDataMode mode);

// cleans \r from string
inline bool HackPluginDataRemoveCR(std::vector<char>& Out,
                                   const std::vector<char>& OriginalData) {
    return HackDataWithCacheInfo(Out, OriginalData, "", HackDataMode::header);
}

class PluginEntry : public cma::cfg::PluginInfo {
public:
    PluginEntry(const std::filesystem::path& Path)
        : failures_(0), process_id_(0), path_(Path), thread_on_(false) {}

    ~PluginEntry() {
        // sometimes we can have thread not blocked
        if (main_thread_) breakAsync();
    }

    PluginEntry(const PluginEntry&) = delete;
    PluginEntry& operator=(const PluginEntry&) = delete;

    // SYNC

    // negative MaxTimeout  means usage of the timeout()
    // 0 or positive min(MaxTimeout, timeout())
    std::vector<char> getResultsSync(const std::wstring& Id,
                                     int MaxTimeout = -1);

    // ASYNC:
    // if StartProcessNow then process will be started immediately
    // otherwise entry will be marked as required to start
    std::vector<char> getResultsAsync(bool StartProcessNow);

    // AU:
    void restartIfRequired();

    // stop with asyncing
    void breakAsync();

    bool local() const {
        std::lock_guard lk(lock_);
        return local_;
    }

    int failures() const {
        std::lock_guard lk(lock_);
        return failures_;
    }

    bool failed() const {
        std::lock_guard lk(lock_);
        return retry_ && failures_ > retry_;
    }

    bool running() const {
        std::lock_guard lk(lock_);
        return thread_on_ && main_thread_;
    }

    // on reading box
    // MUST BE CALLED INSIDE LOCK_GUARD!
    void storeData(uint32_t Id, const std::vector<char>& Data);

    // looks as not used
    std::vector<char> cache() const {
        if (cacheAge() == 0) return {};

        auto now = std::chrono::steady_clock::now();
        auto diff =
            std::chrono::duration_cast<std::chrono::seconds>(now - data_time_)
                .count();
        if (diff > cacheAge()) return {};

        std::lock_guard l(data_lock_);
        return data_;
    }

    // time from time(0) when buffer were stored
    auto legacyTime() const {
        std::lock_guard l(data_lock_);
        return legacy_time_;
    }

    // which plugin
    std::filesystem::path path() const { return path_; }

    // stored data from plugin
    std::vector<char> data() const {
        std::lock_guard lk(data_lock_);
        return data_;
    }

    template <typename T>
    void applyConfigUnit(const T& Unit, bool Local) {
        if (retry() != Unit.retry() || timeout() != Unit.timeout()) {
            XLOG::t("Important params changed, reset retry '{}'",
                    path_.u8string());
            failures_ = 0;
        }

        retry_ = Unit.retry();
        cache_age_ = Unit.cacheAge();
        timeout_ = Unit.timeout();
        group_ = Unit.group();
        user_ = Unit.user();
        bool planned_async = Unit.async() || Unit.cacheAge() > 0;

        if (defined() && async() != planned_async) {
            XLOG::d.t("Plugin '{}' changes this mode to '{}'",
                      path().u8string(), Unit.async() ? "ASYNC" : "SYNC");
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
            cache_age_ = std::max(cacheAge(), cma::cfg::kMinimumCacheAge);
        } else {  // for sync cache_age is 0 always
            cache_age_ = 0;
        }

        fillInternalUser();

        local_ = Local;
        defined_ = true;
    }

    bool isGoingOld() const {
        std::lock_guard lk(lock_);
        return data_is_going_old_;
    }

    bool isNoDataAndNoThread() const {
        std::unique_lock lk_data(data_lock_);
        bool no_data = data_.empty();
        lk_data.unlock();

        std::unique_lock lk_thread(lock_);
        bool no_thread = !main_thread_ || !thread_on_;
        lk_thread.unlock();
        return no_data && no_thread;
    }

    // cache_age means always async, we have no guarantee that
    // invariant is ok 100% time, because bakery delivers us sync plugins
    // with cache age
    bool isRealAsync() const noexcept { return async() || cacheAge(); }

    void removeFromExecution() noexcept { path_ = ""; }

    static int threadCount() noexcept { return thread_count_.load(); }

protected:
    void fillInternalUser();
    void resetData() {
        std::lock_guard lk(data_lock_);
        return data_.clear();
    }
    void restartAsyncThreadIfFinished(const std::wstring& Id);

    void markAsForRestart() {
        XLOG::l.i("markAsForRestart {}", path().u8string());
        std::lock_guard lk(lock_);
        data_is_going_old_ = true;
    }

    auto getDataAge() const {
        auto current_time = std::chrono::steady_clock::now();
        return current_time - data_time_;
    }

    void joinAndReleaseMainThread();

    void threadCore(const std::wstring& Id);

    // after starting box
    bool registerProcess(uint32_t Id);

    // this is not normal situation
    // as a rule only after timeout
    void unregisterProcess();

private:
    wtools::InternalUser iu_;
    cma::TheMiniBox minibox_;

    std::filesystem::path path_;  // actual path to execute

    uint32_t process_id_ = 0;
    std::chrono::steady_clock::time_point start_time_;  // for timeout
    int failures_ = 0;

    bool local_ = false;  // if set then we have deal with local groups

    // async part
    mutable std::mutex data_lock_;  // cache() and time to control

    std::vector<char> data_;                           // cache
    std::chrono::steady_clock::time_point data_time_;  // when
    time_t legacy_time_ = 0;                           // I'm nice guy

    mutable std::mutex lock_;  // thread control
    std::unique_ptr<std::thread> main_thread_;
    bool thread_on_ = false;  // get before start thread, released inside thread
    bool data_is_going_old_ = false;  // when plugin finds data obsolete

    static std::atomic<int> thread_count_;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class PluginTest;
    FRIEND_TEST(PluginTest, ApplyConfig);
    FRIEND_TEST(PluginTest, TimeoutCalc);
    FRIEND_TEST(PluginTest, AsyncStartSimulation_Long);
    FRIEND_TEST(PluginTest, Async0DataPickup);
    FRIEND_TEST(PluginTest, AsyncLocal);
    FRIEND_TEST(PluginTest, SyncLocal);
#endif
};
wtools::InternalUser PluginsExecutionUser2Iu(std::string_view user);

TheMiniBox::StartMode GetStartMode(const std::filesystem::path& filepath);

// #TODO estimate class usage
using PluginMap = std::unordered_map<std::string, cma::PluginEntry>;

const PluginEntry* GetEntrySafe(const PluginMap& Pm, const std::string& Key);
PluginEntry* GetEntrySafe(PluginMap& Pm, const std::string& Key);

void InsertInPluginMap(PluginMap& Out, const PathVector& FoundFiles);

using UnitMap = std::unordered_map<std::string, cma::cfg::Plugins::ExeUnit>;

void RemoveDuplicatedEntriesByName(UnitMap& um, bool local);
std::vector<std::filesystem::path> RemoveDuplicatedFilesByName(
    const std::vector<std::filesystem::path>& found_files, bool local);

void ApplyEverythingToPluginMap(
    PluginMap& Out, const std::vector<cma::cfg::Plugins::ExeUnit>& Units,
    const std::vector<std::filesystem::path>& files, bool Local);

void ApplyEverythingToPluginMapDeprecated(
    PluginMap& Out, const std::vector<cma::cfg::Plugins::ExeUnit>& Units,
    const std::vector<std::filesystem::path>& files, bool Local);

void FilterPluginMap(PluginMap& Out, const PathVector& FoundFiles);

void ApplyExeUnitToPluginMap(
    PluginMap& Out, const std::vector<cma::cfg::Plugins::ExeUnit>& Units,
    bool Local);

void RemoveDuplicatedPlugins(PluginMap& Out, bool CheckExists);

void UpdatePluginMap(PluginMap& Out,  // output is here
                     bool Local, const PathVector& FoundFiles,
                     const std::vector<cma::cfg::Plugins::ExeUnit>& Units,
                     bool CheckExists = true);

// API call to exec all plugins and get back data and count
std::vector<char> RunSyncPlugins(PluginMap& Plugins, int& Count, int Timeout);
std::vector<char> RunAsyncPlugins(PluginMap& Plugins, int& Count,
                                  bool StartImmediately);

constexpr std::chrono::seconds kRestartInterval{60};

void RunDetachedPlugins(PluginMap& plugins_map, int& start_count);
namespace provider::config {
extern const bool G_AsyncPluginWithoutCacheAge_RunAsync;
extern const bool G_SetLogwatchPosToEnd;

bool IsRunAsync(const PluginEntry& plugin) noexcept;
}  // namespace provider::config

namespace tools {
using StringSet = std::set<std::string>;
// returns true if string added
bool AddUniqStringToSetIgnoreCase(StringSet& cache,
                                  const std::string& value) noexcept;
// returns true if string added
bool AddUniqStringToSetAsIs(StringSet& cache,
                            const std::string& value) noexcept;
}  // namespace tools

// finds piggyback template <<<<name>>>>, if found returns 'name'
std::optional<std::string> GetPiggyBackName(const std::string& in_string);

bool TryToHackStringWithCachedInfo(std::string& in_string,
                                   const std::string& value_to_insert);
}  // namespace cma
