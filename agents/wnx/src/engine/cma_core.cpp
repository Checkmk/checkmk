// cma_core.cpp :
//
#include "stdafx.h"

#include "cma_core.h"

#include <time.h>

#include <chrono>
#include <filesystem>
#include <set>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

#include "common/wtools.h"
#include "glob_match.h"
#include "section_header.h"  // we have logging here

namespace cma {
// we are counting threads in to have control exit/stop/wait
std::atomic<int> PluginEntry::thread_count_ = 0;

namespace tools {

bool CheckArgvForValue(int argc, const wchar_t* argv[], int pos,
                       std::string_view value) noexcept {
    return argv && argc > pos && pos > 0 && argv[pos] &&
           std::wstring(argv[pos]) == wtools::ConvertToUTF16(value);
}

}  // namespace tools

bool MatchNameOrAbsolutePath(const std::string& Pattern,
                             const std::filesystem::path file_full_path) {
    namespace fs = std::filesystem;

    fs::path pattern = Pattern;
    auto name = file_full_path.filename();
    if (!pattern.is_absolute()) {
        if (cma::tools::GlobMatch(Pattern, name.u8string())) return true;
    }

    // support for absolute path
    auto full_name = file_full_path.u8string();
    if (cma::tools::GlobMatch(Pattern, full_name)) return true;

    return false;
}

static bool MatchPattern(const std::string& Pattern,
                         const std::filesystem::path file_full_path) {
    namespace fs = std::filesystem;

    fs::path pattern = Pattern;

    // absolute path
    if (pattern.is_absolute())
        return cma::tools::GlobMatch(Pattern, file_full_path.u8string());

    // non absolute path we are using only name part
    auto file_name = file_full_path.filename();
    auto pattern_name = pattern.filename();
    return cma::tools::GlobMatch(pattern_name.u8string(), file_name.u8string());
}

PathVector GatherAllFiles(const PathVector& Folders) {
    namespace fs = std::filesystem;
    using namespace std;
    PathVector paths;

    for (auto& dir : Folders) {
        error_code ec;
        if (!fs::exists(dir, ec)) continue;
        // #TODO potential error we need recursive here
        for (const auto& p : fs::directory_iterator(dir)) {
            // Found files must match the entire path pattern.
            std::error_code ec;
            auto status = p.status();
            if (ec) {
                XLOG::d("Cant obtain status for dir {} path {}status is {}",
                        dir.u8string(), p.path().u8string(), ec.value());
                continue;
            }

            auto path = p.path();
            // normal file
            if (fs::is_regular_file(status)) {
                paths.push_back(path);
                continue;
            }
        }
    }

    return paths;
}

// Scan one folder and add contents to the dirs and files
void GatherMatchingFilesAndDirs(
    const std::filesystem::path& SearchDir,    // c:\windows
    const std::filesystem::path& DirPattern,   // c:\windows\L*
    const std::filesystem::path& FilePattern,  // c:\windows\L*\*.log
    PathVector& FilesFound                     // output
) {
    namespace fs = std::filesystem;
    for (const auto& p : fs::directory_iterator(SearchDir)) {
        // Found files must match the entire path pattern.
        std::error_code ec;
        auto status = p.status();  // CMK-1417, to be confirmed in ticket
        if (ec) {                  // ! error
            XLOG::d("Cant obtain status for dir {} path {}status is {}",
                    SearchDir.u8string(), p.path().u8string(), ec.value());
            continue;
        }

        auto path = p.path();
        // normal file
        if (fs::is_regular_file(status) &&
            cma::tools::GlobMatch(FilePattern.wstring(), path.wstring())) {
            FilesFound.push_back(path);
            continue;
        }
    }
}

void FilterPathByExtension(PathVector& Paths, std::vector<std::string> Exts) {
    namespace fs = std::filesystem;

    // black magic first param
    auto end = std::remove_if(Paths.begin(),        // from
                              Paths.end(),          // to
                              [Exts](fs::path P) {  // lambda to delete
                                  for (auto& ext : Exts) {
                                      auto cur_ext = P.extension().u8string();
                                      if (cur_ext == std::string(".") + ext)
                                          return false;  // do not remove
                                  }
                                  // extension is bad, remove
                                  return true;
                              }  //
    );

    // actual remove
    Paths.erase(end, Paths.end());
}

// remove all duplicated names
void RemoveDuplicatedNames(PathVector& Paths) {
    namespace fs = std::filesystem;
    using namespace std;
    std::unordered_set<std::string>
        filename_set;  // mk_inventory.vbs, smth.bat, etc
    auto end = std::remove_if(Paths.begin(), Paths.end(),
                              [&filename_set](fs::path const& p) {
                                  auto fname = p.filename().u8string();
                                  return !filename_set.insert(fname).second;
                              });

    Paths.erase(end, Paths.end());
}

// usually you have to apply this function per Exe
PathVector SelectPathVectorByPattern(const PathVector& Paths,
                                     const std::string& Pattern) {
    namespace fs = std::filesystem;
    return {};
}

// make a list of files to be run(check exists normally is true)
const PathVector FilterPathVector(
    const PathVector& FoundFiles,
    const std::vector<cma::cfg::Plugins::ExeUnit>& Units, bool CheckExists) {
    namespace fs = std::filesystem;
    PathVector really_found;
    for (auto& ff : FoundFiles) {
        for (auto& unit : Units) {
            if (CheckExists) {
                std::error_code ec;
                if (!fs::exists(ff, ec)) continue;
            }
            if (MatchNameOrAbsolutePath(unit.pattern(), ff)) {
                if (unit.run()) {
                    really_found.emplace_back(ff);
                }
                break;
            }
        }
    }
    return really_found;
}

TheMiniBox::StartMode GetStartMode(const std::filesystem::path& filepath) {
    auto fname = filepath.filename();
    auto filename = fname.u8string();
    cma::tools::StringLower(filename);
    if (filename == cma::cfg::files::kAgentUpdater)
        return TheMiniBox::StartMode::updater;

    return TheMiniBox::StartMode::job;
}

const PluginEntry* GetEntrySafe(const PluginMap& Pm, const std::string& Key) {
    try {
        auto& z = Pm.at(Key);
        return &z;
    } catch (...) {
        return nullptr;
    }
}

PluginEntry* GetEntrySafe(PluginMap& Pm, const std::string& Key) {
    try {
        auto& z = Pm.at(Key);
        return &z;
    } catch (...) {
        return nullptr;
    }
}

// NOT THREAD SAFE!
void InsertInPluginMap(PluginMap& Out, const PathVector& FoundFiles) {
    // remove what not present in the file vector
    for (auto& ff : FoundFiles) {
        auto ptr = GetEntrySafe(Out, ff.u8string());
        if (!ptr) {
            Out.emplace(std::make_pair(ff.u8string(), ff));
        }
    }
}

using UnitMap = std::unordered_map<std::string, cma::cfg::Plugins::ExeUnit>;
static cma::cfg::Plugins::ExeUnit* GetEntrySafe(UnitMap& Pm,
                                                const std::string& Key) {
    try {
        auto& z = Pm.at(Key);
        return &z;
    } catch (...) {
        return nullptr;
    }
}

static void UpdatePluginapWithUnitMap(PluginMap& out, UnitMap& um, bool local) {
    for (auto& [name, unit] : um) {
        auto ptr = GetEntrySafe(out, name);
        if (ptr) {
            if (unit.run())
                ptr->applyConfigUnit(unit, local);
            else
                ptr->removeFromExecution();
        } else {
            if (unit.run()) {
                out.emplace(name, name);
                ptr = GetEntrySafe(out, name);
                if (ptr) ptr->applyConfigUnit(unit, local);
            }
        }
    }

    // remove entries with missing configuration
    for (auto& [name, p] : out) {
        auto ptr = GetEntrySafe(um, name);
        if (!ptr) {
            p.removeFromExecution();
        }
    }
}

namespace tools {
bool AddUniqStringToSetIgnoreCase(std::set<std::string>& cache,
                                  const std::string value) noexcept {
    auto to_insert = value;
    cma::tools::StringUpper(to_insert);
    auto found = cache.find(to_insert);

    if (found == cache.end()) {
        cache.insert(to_insert);
        return true;
    }

    return false;
}

bool AddUniqStringToSetAsIs(std::set<std::string>& cache,
                            const std::string value) noexcept {
    auto found = cache.find(value);

    if (found == cache.end()) {
        cache.insert(value);
        return true;
    }

    return false;
}
}  // namespace tools

static void ApplyEverythingLogResult(const std::string& format,
                                     std::string_view file, bool local) {
    XLOG::d.t(format, file, local ? "[local]" : "[plugins]");
}

void ApplyEverythingToPluginMap(
    PluginMap& out, const std::vector<cma::cfg::Plugins::ExeUnit>& Units,
    const std::vector<std::filesystem::path>& found_files, bool local) {
    UnitMap um;
    std::set<std::string> cache;
    auto files = found_files;
    for (auto& unit : Units) {
        for (auto& f : files) {
            if (f == ".") continue;
            if (!MatchPattern(unit.pattern(), f)) continue;

            // string is match
            auto entry_full_name = f.u8string();
            auto ptr = GetEntrySafe(um, entry_full_name);
            std::string fmt_string;
            if (!ptr) {
                // check duplicated filename
                auto fname = f.filename().u8string();
                auto added = tools::AddUniqStringToSetIgnoreCase(cache, fname);
                if (added) {
                    um.emplace(std::make_pair(entry_full_name, unit));
                    fmt_string = "Plugin '{}' added to {}";
                } else {
                    fmt_string = "Skipped duplicated file by name '{}' in {}";
                }
            } else {
                fmt_string = "skipped duplicated file by full name'{}' in {}";
            }

            ApplyEverythingLogResult(fmt_string, entry_full_name, local);

            f = ".";
        }
    }

    // apply config for presented
    UpdatePluginapWithUnitMap(out, um, local);
}

// Main API
void UpdatePluginMap(PluginMap& Out,  // output is here
                     bool Local,      // type of plugin
                     const PathVector& FoundFiles,
                     const std::vector<cma::cfg::Plugins::ExeUnit>& Units,
                     bool CheckExists) {
    namespace fs = std::filesystem;
    if (FoundFiles.empty() || Units.empty()) {
        Out.clear();  // nothing todo
        return;
    }

    // remove from path vector not presented entries
    auto really_found = FilterPathVector(FoundFiles, Units, CheckExists);

    // remove absent entries from the map
    FilterPluginMap(Out, really_found);

    if constexpr (true) {
        ApplyEverythingToPluginMap(Out, Units, really_found, Local);

    } else {
        // Insert new items from the map
        InsertInPluginMap(Out, really_found);

        // Apply information from ExeUnits
        ApplyExeUnitToPluginMap(Out, Units, Local);
    }

    // last step is deletion of all duplicated names
    RemoveDuplicatedPlugins(Out, CheckExists);
}

// hacks a string
// '<<<plugin_super>>>' -> '<<<plugin_super:cached(11204124124:3600)>>>'
void TryToHackStringWithCachedInfo(std::string& in_string,
                                   const std::string& value_to_insert) {
    if (in_string.find(cma::section::kFooter4) != std::string::npos) {
        // no patch for the case
        XLOG::t("Footer 4 in input");
        return;
    }

    // probably regex better or even simple memcmp/strcmp
    auto pos_start = in_string.find(cma::section::kLeftBracket);
    auto pos_end = in_string.find(cma::section::kRightBracket);
    if (pos_start == 0 &&                // starting from <<<
        pos_end != std::string::npos &&  // >>> presented too
        pos_end > pos_start &&           //
        (pos_end - pos_start) < 100) {   // not very far away
        in_string.insert(pos_end, value_to_insert);
    }
}

static bool ConfigRemoveSlashR = false;

std::string ConstructPatchString(time_t time_now, int cache_age,
                                 HackDataMode mode) noexcept {
    if (time_now == 0 || cache_age == 0) return {};

    return mode == HackDataMode::line
               ? fmt::format("cached({},{}) ", time_now, cache_age)
               : fmt::format(":cached({},{})", time_now, cache_age);
}

bool HackDataWithCacheInfo(std::vector<char>& out,
                           const std::vector<char>& original_data,
                           const std::string& patch, HackDataMode mode) {
    if (original_data.empty()) return false;

    // check we have valid Data;
    std::string stringized(original_data.data(), original_data.size());
    if (!stringized.size()) return false;

    if (patch.empty() && !ConfigRemoveSlashR) {
        out = original_data;
        return true;
    }

    auto table = cma::tools::SplitString(stringized, "\n");

    size_t data_count = 0;
    for (auto& t : table) {
        if (ConfigRemoveSlashR) {
            while (t.back() == '\r') t.pop_back();
        }

        t.push_back('\n');

        // 2. try hack header if required
        if (!patch.empty()) {
            // ugly...
            if (mode == HackDataMode::line)
                t = patch + t;
            else
                TryToHackStringWithCachedInfo(t, patch);
        }

        data_count += t.size();
    }

    // gathering of everything
    out.reserve(data_count + 1);
    for (auto& t : table) {
        cma::tools::AddVector(out, t);
    }
    // remove potentially added '\n'
    if (original_data.back() != '\n') out.pop_back();

    return true;
}

// LOOP:
// register
// wait some time
// unregister
// read data
// Max Timeout < 0 use default
std::vector<char> PluginEntry::getResultsSync(const std::wstring& Id,
                                              int MaxTimeout) {
    if (failed()) return {};

    auto started = minibox_.start(L"id", path(), TheMiniBox::StartMode::job);
    if (!started) {
        XLOG::l("Failed to start minibox sync '{}'", wtools::ConvertToUTF8(Id));
        return {};
    }

    int tout = 0;
    if (MaxTimeout < 0)
        tout = timeout();
    else
        tout = std::min(timeout(), MaxTimeout);

    registerProcess(minibox_.getProcessId());
    auto success = minibox_.waitForEnd(std::chrono::seconds(tout), true);

    std::vector<char> accu;

    if (success) {
        minibox_.processResults([&](const std::wstring CmdLine, uint32_t Pid,
                                    uint32_t Code,
                                    const std::vector<char>& Data) {
            auto data = wtools::ConditionallyConvertFromUTF16(Data);
            if (!data.empty() && data.back() == 0)
                data.pop_back();  // conditional convert adds 0
            cma::tools::AddVector(accu, data);
            storeData(Pid, accu);
            if (cma::cfg::LogPluginOutput())
                XLOG::t("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                        wtools::ConvertToUTF8(CmdLine), Pid, Code, data.data());
        });

    } else {
        // process was either stopped or failed(timeout)
        auto failed = minibox_.failed();
        unregisterProcess();
        XLOG::d("Sync Plugin stopped '{}' Stopped: {} Failed: {}",
                path().u8string(), !failed, failed);
        if (failed) failures_++;
    }

    minibox_.clean();
    return accu;
}

// stop with asyncing
void PluginEntry::breakAsync() {
    XLOG::t("breakAsync {}", path().u8string());
    joinAndReleaseMainThread();
}

void PluginEntry::joinAndReleaseMainThread() {
    std::unique_lock lk(lock_);
    auto t = std::move(main_thread_);
    lk.unlock();
    if (!t || !t->joinable()) return;

    try {
        minibox_.stopWaiting();  // signal to stop thread
        t->join();
        minibox_.clean();  // critical to reset all after thread left
    } catch (const std::exception& e) {
        XLOG::l.bp("Join disaster {} out {}", path().u8string(), e.what());
    } catch (...) {
        XLOG::l.bp("JOIN{} out", path().u8string());
    }
}

bool TheMiniBox::waitForEnd(std::chrono::milliseconds Timeout,
                            bool KillWhatLeft) {
    using namespace std::chrono;
    if (stop_set_) return false;
    ON_OUT_OF_SCOPE(readWhatLeft());

    constexpr std::chrono::milliseconds kGrane = 250ms;
    auto waiting_processes = getProcessId();
    auto read_handle = getReadHandle();
    auto proc_name = wtools::ConvertToUTF8(exec_);
    for (;;) {
        auto ready = checkProcessExit(waiting_processes);

        auto buf = readFromHandle<std::vector<char>>(read_handle);
        if (buf.size()) appendResult(read_handle, buf);

        if (ready) {
            auto us_time = sw_.stop();
            XLOG::d.i(
                "perf: In [{}] milliseconds process  '{}'  generated [{}] bytes of data",
                us_time / 1000, proc_name, buf.size());
            return true;
        }

        if (Timeout >= kGrane) {
            std::unique_lock lk(lock_);
            auto stop_time = std::chrono::steady_clock::now() + kGrane;
            auto stopped = cv_stop_.wait_until(
                lk, stop_time, [this]() -> bool { return stop_set_; });

            if (stopped || stop_set_) {
                XLOG::d(
                    "Process '{}' signaled to be stopped [{}] [{}] left timeout [{}ms]!",
                    proc_name, stopped, stop_set_, Timeout.count());
            } else {
                Timeout -= kGrane;
                continue;
            }
        }
        auto us_time = sw_.stop();

        if (Timeout < kGrane) failed_ = true;

        if (KillWhatLeft) {
            process_->kill(true);
            // not normal situation
            XLOG::d("perf:  In [{}] milliseconds process '{}' pid:[{}] killed",
                    us_time / 1000, proc_name, waiting_processes);
        }

        return false;
    }

    // never here
}

constexpr bool G_KillUpdaterOnEnd = false;
bool TheMiniBox::waitForUpdater(std::chrono::milliseconds timeout) {
    using namespace std::chrono;
    if (stop_set_) return false;
    ON_OUT_OF_SCOPE(readWhatLeft());

    constexpr std::chrono::milliseconds kGrane = 250ms;
    auto waiting_processes = getProcessId();
    auto read_handle = getReadHandle();
    int safety_poll_count = 5;
    for (;;) {
        auto buf = readFromHandle<std::vector<char>>(read_handle);
        if (buf.size()) {
            appendResult(read_handle, buf);
            XLOG::d.t("Appended [{}] bytes from '{}'",
                      process_->getData().size(), wtools::ConvertToUTF8(exec_));
        } else {
            // we have data inside we have nothing from the cmk-update
            if (!process_->getData().empty()) {
                --safety_poll_count;
                if (safety_poll_count == 0) return true;
            }
        }

        // normal processing block
        if (timeout >= kGrane) {
            std::unique_lock lk(lock_);
            auto stop_time = std::chrono::steady_clock::now() + kGrane;
            auto stopped = cv_stop_.wait_until(
                lk, stop_time, [this]() -> bool { return stop_set_; });

            if (stopped || stop_set_) {
                XLOG::d(
                    "Plugin '{}' signaled to be stopped [{}] [{}] left timeout [{}ms]!",
                    wtools::ConvertToUTF8(exec_), stopped, stop_set_,
                    timeout.count());
            } else {
                timeout -= kGrane;
                continue;
            }
        }

        if (buf.size()) return true;

        if (timeout < kGrane) failed_ = true;

        if constexpr (G_KillUpdaterOnEnd) {
            // we do not kill updater normally
            process_->kill(true);
            // cma::tools::win::KillProcess(waiting_processes, -1);
            XLOG::d("Process '{}' [{}] killed", wtools::ConvertToUTF8(exec_),
                    waiting_processes);  // not normal situation
        }

        return false;
    }
}

void PluginEntry::threadCore(const std::wstring& Id) {
    // pre entry
    // thread counters block
    XLOG::d.i("Async Thread for {} is to be started",
              wtools::ConvertToUTF8(Id));
    thread_count_++;
    ON_OUT_OF_SCOPE(thread_count_--);
    std::unique_lock lk(lock_);
    if (!thread_on_) {
        XLOG::l(XLOG::kBp)("Attempt to start without resource acquiring");
        return;
    }
    lk.unlock();

    ON_OUT_OF_SCOPE({
        lk.lock();
        thread_on_ = false;
        lk.unlock();
    });

    // core
    auto mode = GetStartMode(path());
    auto started = minibox_.start(Id, path(), mode);
    if (!started) {
        XLOG::l("Failed to start minibox thread {}", wtools::ConvertToUTF8(Id));
        return;
    }

    registerProcess(minibox_.getProcessId());
    std::vector<char> accu;

    auto success =
        mode == TheMiniBox::StartMode::updater
            ? minibox_.waitForUpdater(std::chrono::seconds(timeout()))
            : minibox_.waitForEnd(std::chrono::seconds(timeout()), true);
    if (success) {
        // we have probably data, try to get and and store
        minibox_.processResults([&](const std::wstring CmdLine, uint32_t Pid,
                                    uint32_t Code,
                                    const std::vector<char>& Data) {
            auto data = wtools::ConditionallyConvertFromUTF16(Data);
            cma::tools::AddVector(accu, data);
            {
                std::lock_guard l(data_lock_);
                storeData(Pid, accu);
            }
            if (cma::cfg::LogPluginOutput())
                XLOG::t("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                        wtools::ConvertToUTF8(CmdLine), Pid, Code, data.data());
        });
    } else {
        // process was either stopped or failed(timeout)
        auto failed = minibox_.failed();
        unregisterProcess();
        XLOG::d("Async Plugin stopped '{}' Stopped: {} Failed: {}",
                path().u8string(), !failed, failed);
        if (failed) failures_++;
    }

    XLOG::d.t("Thread OFF: '{}'", path().u8string());
}

// if thread finished join old and start new thread again
// if thread NOT finished quit
void PluginEntry::restartAsyncThreadIfFinished(const std::wstring& Id) {
    std::unique_lock lk(lock_);
    auto start_thread = !thread_on_;
    thread_on_ = true;  // thread is always on
    if (start_thread) data_is_going_old_ = false;
    lk.unlock();

    if (!start_thread) {
        // when thread is still running
        XLOG::d.i(
            "Thread for plugin '{}' is still running, restart is not required",
            path().u8string());
        return;
    }

    // thread was finished  join(we must)
    joinAndReleaseMainThread();
    // restart
    auto t = std::make_unique<std::thread>(&PluginEntry::threadCore, this, Id);
    lk.lock();
    main_thread_ = std::move(t);
    lk.unlock();
    XLOG::d.i("restarted thread for plugin '{}'", path().u8string());
}

std::vector<char> PluginEntry::getResultsAsync(bool StartProcessNow) {
    using namespace std::chrono;
    if (failed()) return {};

    // check is valid parameters
    if (cacheAge() < cma::cfg::kMinimumCacheAge && cacheAge() != 0) {
        XLOG::l("Plugin '{}' requested to be async, but has no valid cache age",
                path().u8string());
        return {};
    }
    // check data are ready and new enough
    bool data_ok = false;
    seconds allowed_age(cacheAge());
    auto data_age = getDataAge();
    bool going_to_be_old = false;
    {
        std::lock_guard l(data_lock_);
        if (data_.empty()) {
            // no data i.e. data is old
            // command to restart thread
            going_to_be_old = true;
        } else {
            if (data_age <= allowed_age) {
                data_ok = true;
            }

            if (data_age + kRestartInterval > allowed_age) {
                going_to_be_old = true;
            }
        }
    }
    if (!data_ok)
        XLOG::d("Data '{}' is too old, age is '{}' seconds", path().u8string(),
                duration_cast<seconds>(data_age).count());

    // execution phase
    if (going_to_be_old) {
        if (StartProcessNow) {
            XLOG::d.i("restarting async plugin '{}'", path().u8string());
            restartAsyncThreadIfFinished(path().wstring());
        } else {
            XLOG::d.i("plugin '{}' is marked for restart", path().u8string());
            markAsForRestart();
        }
    }

    // we always return data even if data is OLD
    return data_;
}

void PluginEntry::restartIfRequired() {
    using namespace std::chrono;

    // check is valid parameters
    if (cacheAge() < cma::cfg::kMinimumCacheAge) {
        XLOG::l(
            "Plugin '{}' requested to be async restarted, but has no valid cache age",
            path().u8string());
        return;
    }
    // check data are ready and new enough
    seconds allowed_age(cacheAge());
    auto data_age = getDataAge();
    {
        std::lock_guard l(data_lock_);
        {
            if (data_age <= allowed_age) return;
            data_time_ = std::chrono::steady_clock::now();  // update time
                                                            // of start
        }
        auto filename = path().u8string();
        // execution phase
        XLOG::l.t("Starting '{}'", filename);
        auto result = cma::tools::RunDetachedCommand(filename);
        if (result)
            XLOG::l.i("Starting '{}' OK!", filename);
        else
            XLOG::l("Starting '{}' FAILED with error [{}]", filename,
                    GetLastError());
    }
}

// after starting box
bool PluginEntry::registerProcess(uint32_t Id) {
    if (failed()) {
        XLOG::d("RETRY FAILED!!!!!!!!!!! {}", retry(), failed());
        process_id_ = 0;
    } else {
        process_id_ = Id;
        start_time_ = std::chrono::steady_clock::now();
        return true;
    }
    return false;
}

// this is not normal situation
// as a rule only after timeout
void PluginEntry::unregisterProcess() {
    // killing process
    process_id_ = 0;
}

// on reading box
// MUST BE CALLED INSIDE LOCK_GUARD!
void PluginEntry::storeData(uint32_t Id, const std::vector<char>& Data) {
    if (Id != process_id_ || Id == 0) {
        XLOG::d("Invalid process {}, can't store data {} ", Id,
                path().u8string());
        return;
    }

    process_id_ = 0;
    auto end_time = std::chrono::steady_clock::now();
    auto now = std::chrono::steady_clock::now();
    auto diff =
        std::chrono::duration_cast<std::chrono::seconds>(now - start_time_)
            .count();
    if (diff > static_cast<int64_t>(timeout())) {
        XLOG::d("Process '{}' timeout in {} when set {}", path().u8string(),
                diff, timeout());
    } else if (Data.empty()) {
        // plugin failed
        XLOG::d("Process '{}' has no data", path().u8string());
    }

    if (failed()) {
        data_.clear();
        return;
    }

    data_time_ = std::chrono::steady_clock::now();
    auto legacy_time = time(0);

    if (cacheAge() > 0) {
        data_.clear();
        auto mode = local_ ? HackDataMode::line : HackDataMode::header;
        auto patch_string = ConstructPatchString(legacy_time, cacheAge(), mode);
        HackDataWithCacheInfo(data_, Data, patch_string, mode);
    } else  // "sync plugin" or async with 0 as cache age
    {
        // or "failed to hack"
        data_ = Data;
    }
    legacy_time_ = legacy_time;

    // remove trailing zero's
    // can be created in some cases by plugin and processing(ConvertTo)
    // But must be removed in output
    while (data_.size() && data_.back() == 0) data_.pop_back();
}  // namespace cma

// remove what not present in the file vector
void FilterPluginMap(PluginMap& Out, const PathVector& FoundFiles) {
    std::vector<std::string> to_delete;
    if (FoundFiles.size() == 0) {
        Out.clear();
        return;
    }

    // check every entry for presence in the foundfiles vector
    // absent entries are in to_delete
    for (auto& out : Out) {
        bool exists = false;
        for (auto& ff : FoundFiles) {
            if (out.first == ff.u8string()) {
                exists = true;
                break;
            }
        }
        if (!exists)
            to_delete.push_back(out.first);  // store path to be removed
    }

    // second deletion phase - we can't delete
    // while iterating through container
    for (auto& del : to_delete) {
        Out.erase(del);
    }
}

// gtest only partly(name, but not full path)
void ApplyExeUnitToPluginMap(
    PluginMap& Out, const std::vector<cma::cfg::Plugins::ExeUnit>& Units,
    bool Local) {
    for (auto& out : Out) {
        auto p = out.second.path();

        for (auto& unit : Units) {
            if (!MatchNameOrAbsolutePath(unit.pattern(), p)) continue;

            // string is match stop scanning exe units
            if (unit.run())
                out.second.applyConfigUnit(unit, Local);
            else {
                XLOG::d.t("Run is 'NO' for the '{}'", p.u8string());
                out.second.removeFromExecution();
            }
            break;
        }
    }
}

// CheckExists = false is only for testing,
// set true for Production
// Out is mutable
void RemoveDuplicatedPlugins(PluginMap& Out, bool CheckExists) {
    namespace fs = std::filesystem;
    using namespace std;
    std::unordered_set<std::string>
        filename_set;  // mk_inventory.vbs, smth.bat, etc

    std::error_code ec;
    for (auto it = Out.begin(); it != Out.end();) {
        fs::path p = it->first;

        if (it->second.path().empty()) {
            it = Out.erase(it);
            continue;
        }

        if (CheckExists && !fs::exists(p, ec)) {
            it = Out.erase(it);
            continue;
        }

        if (!filename_set.insert(p.filename().u8string()).second)
            it = Out.erase(it);
        else
            ++it;
    }
}

namespace provider::config {
const bool G_AsyncPluginWithoutCacheAge_RunAsync = true;

bool IsRunAsync(const PluginEntry& plugin) noexcept {
    auto run_async = plugin.async();

    if (G_AsyncPluginWithoutCacheAge_RunAsync) return run_async;

    if (run_async && plugin.cacheAge() == 0)
        return config::G_AsyncPluginWithoutCacheAge_RunAsync;

    return run_async;
}
}  // namespace provider::config

// #TODO simplify THIS TRASH, SK!
std::vector<char> RunSyncPlugins(PluginMap& Plugins, int& Count, int Timeout) {
    using namespace std;
    using DataBlock = vector<char>;
    XLOG::l.t("To start [{}] sync plugins", Plugins.size());

    vector<future<DataBlock>> results;
    int requested_count = 0;
    Count = 0;

    if (Timeout < 0) Timeout = 1;

    auto tm_to_stop =
        std::chrono::steady_clock::now() + std::chrono::seconds(Timeout);

    // sync part
    for (auto& entry_pair : Plugins) {
        auto& entry_name = entry_pair.first;
        auto& entry = entry_pair.second;

        // check that out plugin is ging to run as async
        auto run_async = cma::provider::config::IsRunAsync(entry);
        if (run_async) continue;

        XLOG::t("Executing '{}'", entry.path().u8string());

        // C++ async black magic
        results.emplace_back(std::async(
            std::launch::async,  // first param

            [](cma::PluginEntry* Entry,
               int Tout) -> DataBlock {  // lambda
                if (!Entry) return {};
                return Entry->getResultsSync(Entry->path().wstring());
            },  // lambda end

            &entry,  // lambda parameter
            Timeout));
        requested_count++;
    }

    // just check for ready futures
    DataBlock out;
    int delivered_count = 0;
    for (auto& r : results) {
        // auto status = r.wait_until(tm_to_stop);
        // if (status == future_status::ready) {
        auto result = r.get();
        if (result.size()) {
            ++delivered_count;
            cma::tools::AddVector(out, result);
        }
        //} else {
        //    XLOG::t("skipped plugin");
        //}
    }

    Count = delivered_count;
    return out;
}

// this mode is obsolete
bool IsDetachedPlugin(const std::filesystem::path& filepath) {
    auto fname = filepath.filename();
    auto filename = fname.u8string();
    cma::tools::StringLower(filename);
    return false;  // filename == cma::cfg::files::kAgentUpdater;
}

void RunDetachedPlugins(PluginMap& plugins_map, int& start_count) {
    using namespace std;
    using DataBlock = vector<char>;

    int requested_count = 0;
    start_count = 0;

    DataBlock out;
    // async part
    int count = 0;
    for (auto& entry_pair : plugins_map) {
        auto& entry_name = entry_pair.first;
        auto& entry = entry_pair.second;

        if (!entry.async()) continue;

        if (IsDetachedPlugin(entry.path())) {
            entry.restartIfRequired();
            ++count;
            continue;
        };
    }
    XLOG::t.i("Detached started: [{}]", count);
    start_count = count;

    return;
}

// To get data from async plugins with cache_age=0
void PickupAsync0data(int timeout, PluginMap& plugins, std::vector<char>& out,
                      std::vector<std::pair<bool, std::string>>& async_0s) {
    timeout = std::max(timeout, 10);
    if (timeout)
        XLOG::d.i(
            "Picking up [{}] async-0"
            "plugins with timeout [{}]",
            async_0s.size(), timeout);

    // pickup 0 async
    // plugin.first - status
    // plygin.second - name
    size_t async_count = 0;
    for (int i = 0; i < timeout; i++) {
        for (auto& plugin : async_0s) {
            if (plugin.first) continue;

            const auto e = GetEntrySafe(plugins, plugin.second);
            if (e && !e->running()) {
                cma::tools::AddVector(out, e->data());
                plugin.first = false;
                async_count++;
            }
        }
        if (async_count >= async_0s.size()) break;
        cma::tools::sleep(1000);
    }
}

std::vector<char> RunAsyncPlugins(PluginMap& Plugins, int& Count,
                                  bool StartImmediately) {
    using namespace std;
    using DataBlock = vector<char>;

    int requested_count = 0;
    Count = 0;

    DataBlock out;
    // async part
    int count = 0;
    // int timeout = 0;
    // std::vector<std::pair<bool, std::string>> async_0s;
    for (auto& entry_pair : Plugins) {
        auto& entry_name = entry_pair.first;
        auto& entry = entry_pair.second;

        if (!entry.async()) continue;

        auto run_async = cma::provider::config::IsRunAsync(entry);
        if (!run_async) continue;

        if (IsDetachedPlugin(entry.path())) continue;

        auto ret = entry.getResultsAsync(StartImmediately);
        if (ret.size()) ++count;
        cma::tools::AddVector(out, ret);

        /*
                if (provider::config::G_AsyncPluginWithoutCacheAge_RunAsync)
           { if (entry.cacheAge() == 0) { timeout = std::max(timeout,
           entry.timeout()); async_0s.emplace_back(false, entry_name);
                    }
                }
        */
    }

    Count = count;
    /*
        if (provider::config::G_AsyncPluginWithoutCacheAge_RunAsync) {
            PickupAsync0data(timeout, Plugins, out, async_0s);
        }
    */

    return out;
}

}  // namespace cma
