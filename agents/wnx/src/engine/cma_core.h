// core common functionaliaty
// probably "file" is better name

#pragma once

#include <time.h>

#include <chrono>
#include <filesystem>
#include <string>
#include <string_view>

#include "cfg.h"
#include "common/wtools.h"
#include "fmt/format.h"
#include "logger.h"
#include "tools/_misc.h"

namespace cma {
namespace tools {

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
    using namespace std::filesystem;
    static path executables[] = {L".exe", L".bat", L".cmd"};
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
    fs::path ps(powershell_path);
    ps /= L"WindowsPowerShell";
    ps /= L"v1.0";
    ps /= powershell_name;
    try {
        if (fs::exists(ps)) return ps;
        XLOG::l("Not found powershell");
    } catch (const std::exception& e) {
        XLOG::l("malformed name {} e:{}", ps.u8string(), e.what());
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
    TheMiniBox() : process_(nullptr), stop_set_(false), proc_id_(0) {}
    TheMiniBox(const TheMiniBox&) = delete;
    TheMiniBox& operator=(const TheMiniBox&) = delete;

    // #TODO implement movers!
    TheMiniBox(const TheMiniBox&&) = delete;
    TheMiniBox& operator=(const TheMiniBox&&) = delete;

    ~TheMiniBox() { clean(); }

    //
    bool startBlind(const std::string CommandLine, const std::string User) {
        int count = 0;
        std::lock_guard lk(lock_);
        if (process_) return false;
        id_ = L"blind";
        std::string command_line;
        if (User.empty()) command_line = "runas /User:" + User + " ";
        command_line += CommandLine;

        exec_ = wtools::ConvertToUTF16(CommandLine);

        // send exec array entries to internal
        try {
            // now exec
            auto ar = new wtools::AppRunner;
            proc_id_ = ar->goExec(exec_, false, true, true);
            if (proc_id_) {
                process_ = ar;
                return true;
            }

            delete ar;  // start failed
        } catch (const std::exception& e) {
            XLOG::l(XLOG_FLINE + " exception {}", e.what());
        }
        // cleaning up
        id_.clear();
        exec_.clear();

        return false;
    }

    bool start(const std::wstring Id, const std::filesystem::path ExeFile) {
        int count = 0;
        std::lock_guard lk(lock_);
        if (process_) return false;
        id_ = Id;
        exec_ = ExeFile.wstring();

        // send exec array entries to internal
        try {
            // now exec
            auto ar = new wtools::AppRunner;
            auto exec = cma::ConstructCommandToExec(exec_);
            proc_id_ = ar->goExec(exec, false, true, true);
            if (proc_id_) {
                process_ = ar;
                return true;
            }

            delete ar;  // start failed
        } catch (const std::exception& e) {
            XLOG::l(XLOG_FLINE + " exception {}", e.what());
        }
        // cleaning up
        id_.clear();
        exec_.clear();

        return false;
    }

    // strange?
    uint32_t getProcessId() {
        uint32_t proc_id;
        std::unique_lock lk(lock_);
        proc_id = process_->processId();
        lk.unlock();
        return proc_id;
    }

    // really obtained proc id. Safe function
    uint32_t startedProcId() const { return proc_id_; }

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

    // add content of file to the Buf
    template <typename T>
    bool appendFileContent(T& Buf, HANDLE h, size_t Count) const noexcept {
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

    // With kGrane interval tries to check running processes
    // returns true if all processes ended
    // returns false on timeout or break;
    bool waitForEnd(std::chrono::milliseconds Timeout, bool KillWhatLeft) {
        using namespace std::chrono;
        if (stop_set_) return false;
        ON_OUT_OF_SCOPE(readWhatLeft());

        constexpr std::chrono::milliseconds kGrane = 250ms;
        auto waiting_processes = getProcessId();
        auto read_handle = getReadHandle();
        for (;;) {
            auto ready = checkProcessExit(waiting_processes);
            {
                auto buf = readFromHandle<std::vector<char>>(read_handle);
                if (buf.size()) appendResult(read_handle, buf);
            }

            if (ready) return true;

            if (Timeout >= kGrane) {
                std::unique_lock lk(lock_);
                auto stop_time = std::chrono::steady_clock::now() + kGrane;
                auto stopped = cv_stop_.wait_until(
                    lk, stop_time, [this]() -> bool { return stop_set_; });

                if (stopped || stop_set_) {
                    XLOG::d(
                        "Plugin '{}' signaled to be stopped [{}] [{}] left timeout [{}ms]!",
                        wtools::ConvertToUTF8(exec_), stopped, stop_set_,
                        Timeout.count());
                } else {
                    Timeout -= kGrane;
                    continue;
                }
            }

            if (KillWhatLeft) {
                process_->kill(true);
                // cma::tools::win::KillProcess(waiting_processes, -1);
                XLOG::d("Process '{}' [{}] killed",
                        wtools::ConvertToUTF8(exec_),
                        waiting_processes);  // not normal situation
            }

            return false;
        }

        // never here
    }

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
    }

private:
    // get handle to read data from stdio
    HANDLE getReadHandle() {
        std::vector<HANDLE> handles;
        std::unique_lock lk(lock_);
        auto h = process_->getStdioRead();
        lk.unlock();
        return h;
    }

    // called AFTER process finished!
    void readWhatLeft() {
        using namespace std;
        auto read_handle = getReadHandle();
        auto buf = readFromHandle<vector<char>>(read_handle);
        if (buf.size()) appendResult(read_handle, buf);
    }

    template <typename T>
    T readFromHandle(HANDLE Handle) {
        T buf;
        for (;;) {
            auto read_count = wtools::DataCountOnHandle(Handle);

            // now reading to the end
            if (read_count == 0) break;                              // no data
            if (!appendFileContent(buf, Handle, read_count)) break;  // io fail
        }
        return buf;
    }

    static std::string formatProcessInLog(uint32_t pid, std::wstring name) {
        return fmt::format("Process '{}' pid [{}]", wtools::ConvertToUTF8(name),
                           pid);
    }

    // check processes for exit
    // updates object with exic code
    // returns true if process  exists or not accessible
    bool checkProcessExit(const uint32_t pid) {
        auto proc_string = formatProcessInLog(pid, exec_);

        auto h = ::OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION,  // not supported on XP
            FALSE, pid);
        if (!h) {
            storeExitCode(pid, 0);  // process died
            XLOG::d("{} is failed to open, error is [{}]", proc_string,
                    ::GetLastError());
            return true;
        }
        ON_OUT_OF_SCOPE(::CloseHandle(h));
        DWORD exit_code = 0;
        auto success = ::GetExitCodeProcess(h, &exit_code);
        if (!success) {
            XLOG::l("Error  [{}] accessing {}", ::GetLastError(), proc_string);
            return true;
        }

        // no logging for the case due to high noise
        if (exit_code == STILL_ACTIVE) return false;

        // success and valid exit code store exit code
        XLOG::t("{} exits, code is [{}]", proc_string, exit_code);
        storeExitCode(pid, exit_code);
        return true;
    }

    bool isExecValid(const std::filesystem::path& FileExec) const {
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
    bool stop_set_;
};

}  // namespace cma

namespace cma {

// 1. replaces '\r' with '\r\n'
// 2. <<<PLUGIN>>>\nsomething -> <<<PLUGIN:cached(123456789,3600)>>>\nsomething
//    if header bad or not found - nothing had been done
// true on success
// if Legacy time and CacheAge set to 0, no hacking
bool HackPluginDataWithCacheInfo(std::vector<char>& Out,
                                 const std::vector<char>& OriginalData,
                                 time_t LegacyTime, long long CacheAge);

// cleans \r from string
inline bool HackPluginDataRemoveCR(std::vector<char>& Out,
                                   const std::vector<char>& OriginalData) {
    return HackPluginDataWithCacheInfo(Out, OriginalData, 0, 0);
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

    auto local() const {
        std::lock_guard lk(lock_);
        return local_;
    }

    auto failures() const { return failures_; }

    auto failed() const { return retry_ && (failures_ > retry_); }

    auto running() const {
        std::lock_guard lk(lock_);
        return thread_on_ && main_thread_;
    }

    // on reading box
    // MUST BE CALLED INSIDE LOCK_GUARD!
    void storeData(uint32_t Id, const std::vector<char>& Data);

    // looks as not used
    std::vector<char> cache() const {
        if (cache_age_ == 0) return {};

        auto now = std::chrono::steady_clock::now();
        auto diff =
            std::chrono::duration_cast<std::chrono::seconds>(now - data_time_)
                .count();
        if (diff > cache_age_) return {};

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
    std::vector<char> data() const { return data_; }

    template <typename T>
    void applyConfigUnit(const T& Unit, bool Local) {
        bool reset_failure = false;

        if (retry_ != Unit.retry() || cache_age_ != Unit.cacheAge() ||
            timeout_ != Unit.timeout() || async_ != Unit.async()) {
            XLOG::t("Important params changed, reset retry");
            reset_failure = true;
        }

        retry_ = Unit.retry();
        cache_age_ = Unit.cacheAge();
        timeout_ = Unit.timeout();
        if (async_ != Unit.async()) {
            XLOG::d.t("Plugin '{}' changes this mode to '{}'",
                      path().u8string(), Unit.async() ? "ASYNC" : "SYNC");
            if (async_) {
                // clearing data from async mode
                async_ = false;
                breakAsync();
                minibox_.clean();
                std::lock_guard lk(data_lock_);
                data_.clear();
            }
        }
        async_ = Unit.async();

        // post processing
        if (!async_ && cache_age_) {
            XLOG::d.t("Plugin '{}' forced as async", path().u8string());
            async_ = true;
        }

        if (async_ && cache_age_ < cma::cfg::kMinimumCacheAge)
            cache_age_ = cma::cfg::kMinimumCacheAge;

        if (reset_failure) failures_ = 0;
        local_ = Local;
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

    void markAsForRestart() {
        XLOG::l.i("markAsForRestart {}", path().u8string());
        std::lock_guard lk(lock_);
        data_is_going_old_ = true;
    }

    void restartAsyncThreadIfFinished(const std::wstring& Id);

    // cache_age means always async, we have no guarantee that
    // invariant is ok 100% time, because bakery delivers us sync plugins
    // with cache age
    bool isRealAsync() const noexcept { return async() || cacheAge(); }

protected:
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

    cma::TheMiniBox minibox_;

    std::filesystem::path path_;  // actual path to execute

    uint32_t process_id_ = 0;
    std::chrono::steady_clock::time_point start_time_;  // for timeout
    int failures_;

    bool local_;  // if set then we have deal with local groups

    // async part
    mutable std::mutex data_lock_;  // cache() and time to control

    std::vector<char> data_;                           // cache
    std::chrono::steady_clock::time_point data_time_;  // when
    time_t legacy_time_;                               // I'm nice guy

    mutable std::mutex lock_;  // thread control
    std::unique_ptr<std::thread> main_thread_;
    bool thread_on_;          // get before start thread, released inside thread
    bool data_is_going_old_;  // when plugin finds data obsolete

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class PluginTest;
    FRIEND_TEST(PluginTest, ApplyConfig);
#endif
};
}  // namespace cma

namespace cma {
// #TODO estimate class usage
using PluginMap = std::unordered_map<std::string, PluginEntry>;

const PluginEntry* GetEntrySafe(const PluginMap& Pm, const std::string& Key);
PluginEntry* GetEntrySafe(PluginMap& Pm, const std::string& Key);

void InsertInPluginMap(PluginMap& Out, const PathVector& FoundFiles);
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
}  // namespace cma
