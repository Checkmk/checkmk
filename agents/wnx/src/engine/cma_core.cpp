// cma_core.cpp :
//
#include "stdafx.h"

#include "cma_core.h"

#include <time.h>

#include <chrono>
#include <filesystem>
#include <string>
#include <unordered_set>
#include <vector>

#include "glob_match.h"
#include "section_header.h"  // we have logging here

namespace cma {
bool MatchNameOrAbsolutePath(const std::string& Pattern,
                             const std::filesystem::path FullPath) {
    auto name = FullPath.filename();
    if (cma::tools::GlobMatch(Pattern, name.u8string())) return true;

    // support for absolute path
    auto full_name = FullPath.u8string();
    if (cma::tools::GlobMatch(Pattern, full_name)) return true;

    return false;
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

}  // namespace cma

namespace cma {

// see header about description
bool HackPluginDataWithCacheInfo(std::vector<char>& Out,
                                 const std::vector<char>& OriginalData,
                                 time_t LegacyTime, long long CacheAge) {
    if (!OriginalData.size()) return false;
    // check we have valid Data;
    std::string stringized(OriginalData.data(), OriginalData.size());
    if (!stringized.size()) return false;

    auto table = cma::tools::SplitString(stringized, "\n");

    size_t data_count = 0;
    auto to_insert = fmt::format(":cached({},{})", LegacyTime, CacheAge);
    for (auto& t : table) {
        // 1. remove \r
        if (t.back() == '\r')
            t.back() = '\n';
        else
            t.push_back('\n');

        // 2. optionally hack header
        if (LegacyTime && CacheAge) {
            // find a header
            auto pos_start = t.find(cma::section::kLeftBracket);
            auto pos_end = t.find(cma::section::kRightBracket);
            if (pos_start == 0 &&                // starting from <<<
                pos_end != std::string::npos &&  // >>> presented too
                pos_end > pos_start &&           //
                (pos_end - pos_start) < 100) {   // not very far away
                t.insert(pos_end, to_insert);
            }
        }
        data_count += t.size();
    }

    // gathering of everything
    Out.reserve(data_count + 1);
    for (auto& t : table) {
        cma::tools::AddVector(Out, t);
    }
    // remove potentially added '\n'
    if (OriginalData.back() != '\n') Out.pop_back();

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

    auto started = minibox_.start(L"id", path());
    if (!started) {
        XLOG::l("Failed to start minibox sync {}", wtools::ConvertToUTF8(Id));
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
            if (data.size() && data.back() == 0)
                data.pop_back();  // conditional convert adds 0
            cma::tools::AddVector(accu, data);
            storeData(Pid, accu);
            if (cma::cfg::LogPluginOutput())
                XLOG::t("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                        wtools::ConvertToUTF8(CmdLine), Pid, Code, data.data());
        });

    } else {
        //
        XLOG::d("Wait on Timeout or Broken {}", path().u8string());
        unregisterProcess();
        failures_++;
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

void PluginEntry::threadCore(const std::wstring& Id) {
    // pre entry
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
    auto started = minibox_.start(Id, path());
    if (!started) {
        XLOG::l("Failed to start minibox thread {}", wtools::ConvertToUTF8(Id));
        return;
    }

    registerProcess(minibox_.getProcessId());
    std::vector<char> accu;
    auto success = minibox_.waitForEnd(std::chrono::seconds(timeout()), true);
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
        // timeout or break signaled
        unregisterProcess();
        XLOG::t("Failed waiting or Broken in {}", path().u8string());
        failures_++;
    }

    XLOG::d()("Thread OFF: {}", path().u8string());
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
    if (cache_age_ < cma::cfg::kMinimumCacheAge) {
        XLOG::l("Plugin '{}' requested to be async, but has no valid cache age",
                path().u8string());
        return {};
    }
    // check data are ready and new enough
    bool data_ok = false;
    seconds allowed_age(cache_age_);
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
        XLOG::d("Data '{}' is obsolete, age is '{}' seconds", path().u8string(),
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
    if (cache_age_ < cma::cfg::kMinimumCacheAge) {
        XLOG::l(
            "Plugin '{}' requested to be async restarted, but has no valid cache age",
            path().u8string());
        return;
    }
    // check data are ready and new enough
    seconds allowed_age(cache_age_);
    auto data_age = getDataAge();
    {
        std::lock_guard l(data_lock_);
        {
            if (data_age <= allowed_age) return;
            data_time_ =
                std::chrono::steady_clock::now();  // update time of start
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
        XLOG::d("RETRY FAILED!!!!!!!!!!! {}", retry_, failed());
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
    if (diff > timeout_) {
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

    if (cache_age_ > cma::cfg::kMinimumCacheAge) {
        data_.clear();
        if (local_)
            HackPluginDataRemoveCR(data_, Data);
        else
            HackPluginDataWithCacheInfo(data_, Data, legacy_time, cache_age_);
    } else  // "sync plugin"
    {
        // or "failed to hack"
        data_ = Data;
    }
    legacy_time_ = legacy_time;

    // remove trailing zero's
    // can be createdin some cases by plugin and processing(ConvertTo)
    // But must be removed in output
    while (data_.size() && data_.back() == 0) data_.pop_back();
}

PluginEntry* GetEntrySafe(PluginMap& Pm, const std::string& Key) {
    try {
        auto& z = Pm.at(Key);
        return &z;
    } catch (...) {
        return nullptr;
    }
}

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

// gtest only partly(name, but not full path)
void ApplyExeUnitToPluginMap(
    PluginMap& Out, const std::vector<cma::cfg::Plugins::ExeUnit>& Units,
    bool Local) {
    for (auto& out : Out) {
        auto p = out.second.path();

        for (auto& unit : Units) {
            if (MatchNameOrAbsolutePath(unit.pattern(), p)) {
                // string is match stop scanning exe units
                out.second.applyConfigUnit(unit, Local);
                break;
            }
        }
    }
}

// CheckExists = false is mostly for testing, set true if you have doubts
// Out is mutable, gtested
void RemoveDuplicatedPlugins(PluginMap& Out, bool CheckExists) {
    namespace fs = std::filesystem;
    using namespace std;
    std::unordered_set<std::string>
        filename_set;  // mk_inventory.vbs, smth.bat, etc

    std::error_code ec;
    for (auto it = Out.begin(); it != Out.end();) {
        fs::path p = it->first;

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

    // Insert new items from the map
    InsertInPluginMap(Out, really_found);

    // Apply information from ExeUnits
    ApplyExeUnitToPluginMap(Out, Units, Local);

    // last step is deletion of all duplicated names
    RemoveDuplicatedPlugins(Out, CheckExists);
}

// #TODO simplify THIS TRASH, SK!
std::vector<char> RunSyncPlugins(PluginMap& Plugins, int& Count, int Timeout) {
    using namespace std;
    using DataBlock = vector<char>;
    XLOG::d.i("To start [{}] sync plugins", Plugins.size());

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

        if (entry.async()) continue;

        XLOG::d.t(XLOG_FUNC + " {}", entry.path().u8string());

        // C++ async black magic
        results.emplace_back(std::async(
            std::launch::async,  // first param

            [](cma::PluginEntry* Entry, int Tout) -> DataBlock {  // lambda
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

bool IsDetachedPlugin(const std::filesystem::path& filepath) {
    auto fname = filepath.filename();
    auto filename = fname.u8string();
    cma::tools::StringLower(filename);
    return filename == cma::cfg::files::kAgentUpdater;
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
    XLOG::l.i("Detached started: [{}]", count);
    start_count = count;

    return;
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
    for (auto& entry_pair : Plugins) {
        auto& entry_name = entry_pair.first;
        auto& entry = entry_pair.second;

        if (!entry.async()) continue;

        if (IsDetachedPlugin(entry.path())) continue;

        auto ret = entry.getResultsAsync(StartImmediately);
        if (ret.size()) ++count;
        cma::tools::AddVector(out, ret);
    }

    Count = count;

    return out;
}

}  // namespace cma
