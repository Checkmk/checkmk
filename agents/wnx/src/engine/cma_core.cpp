// cma_core.cpp :
//
#include "stdafx.h"

#include "cma_core.h"

#include <chrono>
#include <ctime>
#include <filesystem>
#include <ranges>
#include <set>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

#include "common/wtools.h"
#include "glob_match.h"
#include "section_header.h"  // we have logging here
#include "service_processor.h"
#include "tools/_misc.h"
#include "windows_service_api.h"

namespace fs = std::filesystem;
namespace rs = std::ranges;
using namespace std::chrono_literals;
using namespace std::string_literals;

namespace cma {
bool IsValidFile(const fs::path &file_to_exec) {
    return fs::exists(file_to_exec) && !fs::is_directory(file_to_exec);
}
// check is extension is valid for OS
bool IsExecutable(const fs::path &file_to_exec) {
    const static std::vector<fs::path> executables = {L".exe", L".bat",
                                                      L".cmd"};
    return rs::any_of(executables, [file_to_exec](const auto &n) {
        return file_to_exec.extension() == n;
    });
}

std::wstring FindPowershellExe() noexcept {
    constexpr std::wstring_view powershell_name = L"powershell.exe";
    wchar_t buffer[16];
    if (::SearchPathW(nullptr, powershell_name.data(), nullptr, 1, buffer,
                      nullptr) != 0) {
        return std::wstring(powershell_name);
    }

    // file not found on path
    auto powershell_path =
        cma::tools::win::GetSomeSystemFolder(FOLDERID_System);

    try {
        fs::path ps(powershell_path);
        ps /= L"WindowsPowerShell";
        ps /= L"v1.0";
        ps /= powershell_name;
        if (fs::exists(ps)) {
            return ps;
        }
        XLOG::l("Not found powershell");
    } catch (const std::exception &e) {
        XLOG::l("malformed name {} e:{}", wtools::ToUtf8(powershell_path),
                e.what());
    }
    return {};
}

namespace security {
void ProtectFiles(const fs::path &root, std::vector<std::wstring> &commands) {
    for (const auto &p : {
             root / cfg::kAppDataAppName / cfg::files::kUserYmlFile,
             root / cfg::kAppDataAppName / cfg::dirs::kBakery /
                 cfg::files::kBakeryYmlFile,
             root / cfg::kAppDataAppName / cfg::dirs::kInstall,
             root / cfg::kAppDataAppName / cfg::dirs::kBackup,
             root / cfg::kAppDataAppName / cfg::dirs::kPluginConfig,
             root / cfg::kAppDataAppName / cfg::dirs::kUpdate,

         }) {
        wtools::ProtectPathFromUserAccess(p, commands);
    }
}

void ProtectAll(const fs::path &root, std::vector<std::wstring> &commands) {
    wtools::ProtectPathFromUserWrite(root, commands);

    ProtectFiles(root, commands);
}

}  // namespace security

// we are counting threads in to have control exit/stop/wait
std::atomic<int> PluginEntry::g_tread_count = 0;

namespace tools {

bool AreFilesSame(const fs::path &tgt, const fs::path &src) {
    try {
        std::ifstream f1(tgt, std::ifstream::binary | std::ifstream::ate);
        std::ifstream f2(src, std::ifstream::binary | std::ifstream::ate);

        if (f1.fail() || f2.fail()) {
            return false;  // file problem
        }

        if (f1.tellg() != f2.tellg()) {
            return false;  // size mismatch
        }

        // seek back to beginning and use std::equal to compare contents
        f1.seekg(0, std::ifstream::beg);
        f2.seekg(0, std::ifstream::beg);
        return std::equal(std::istreambuf_iterator<char>(f1.rdbuf()),
                          std::istreambuf_iterator<char>(),
                          std::istreambuf_iterator<char>(f2.rdbuf()));
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " exception '{}'", e.what());
        return false;
    }
}

bool CheckArgvForValue(int argc, const wchar_t *argv[], int pos,
                       std::string_view value) noexcept {
    return argv != nullptr && argc > pos && pos > 0 && argv[pos] != nullptr &&
           std::wstring(argv[pos]) == wtools::ConvertToUTF16(value);
}

}  // namespace tools

bool MatchNameOrAbsolutePath(const std::string &input,
                             const fs::path &file_full_path) {
    fs::path pattern = input;
    auto name = file_full_path.filename();
    if (!pattern.is_absolute()) {
        if (tools::GlobMatch(input, wtools::ToUtf8(name.wstring()))) {
            return true;
        }
    }

    // support for absolute path
    auto full_name = wtools::ToUtf8(file_full_path.wstring());
    return tools::GlobMatch(input, full_name);
}

namespace {
bool MatchPattern(const std::string &input, const fs::path &file_full_path) {
    fs::path pattern = input;

    // absolute path
    if (pattern.is_absolute()) {
        return tools::GlobMatch(input,
                                wtools::ToUtf8(file_full_path.wstring()));
    }

    // non absolute path we are using only name part
    auto file_name = file_full_path.filename();
    auto pattern_name = pattern.filename();
    return tools::GlobMatch(pattern_name.wstring(), file_name.wstring());
}
}  // namespace

PathVector GatherAllFiles(const PathVector &Folders) {
    PathVector paths;

    for (const auto &dir : Folders) {
        std::error_code ec;
        if (!fs::exists(dir, ec)) {
            continue;
        }

        // #TODO potential error we need recursive here
        for (const auto &p : fs::directory_iterator(dir)) {
            // Found files must match the entire path pattern.
            auto status = p.status();
            if (ec) {
                XLOG::d("Can't obtain status for dir {} path {}status is {}",
                        dir, p.path(), ec.value());
                continue;
            }

            if (fs::is_regular_file(status)) {
                paths.push_back(p.path());
                continue;
            }
        }
    }

    return paths;
}

// Scan one folder and add contents to the dirs and files
void GatherMatchingFilesAndDirs(
    const fs::path &search_dir,        // c:\windows
    const fs::path & /*dir_pattern*/,  // c:\windows\L*
    const fs::path &file_pattern,      // c:\windows\L*\*.log
    PathVector &files_found            // output
) {
    for (const auto &p : fs::directory_iterator(search_dir)) {
        // Found files must match the entire path pattern.
        std::error_code ec;
        auto status = p.status();  // CMK-1417, to be confirmed in ticket
        if (ec) {                  // ! error
            XLOG::d("Cant obtain status for dir {} path {}status is {}",
                    search_dir, p.path(), ec.value());
            continue;
        }

        // normal file
        if (fs::is_regular_file(status) &&
            tools::GlobMatch(file_pattern.wstring(), p.path().wstring())) {
            files_found.push_back(p.path());
            continue;
        }
    }
}

namespace {
std::wstring RemoveDot(const std::wstring_view ext) {
    if (ext.empty()) {
        return std::wstring{ext};
    }
    if (ext[0] == L'.') {
        return std::wstring{ext.data() + 1};
    }
    return std::wstring{ext};
}
}  // namespace

void FilterPathByExtension(PathVector &paths,
                           const std::vector<std::string> &exts) {
    std::erase_if(paths, [exts](const auto &path) {
        auto ext = RemoveDot(path.extension().wstring());
        return rs::none_of(exts, [&](const auto &e) {
            return ext == wtools::ConvertToUTF16(e);
        });
    });
}

// remove all duplicated names
void RemoveDuplicatedNames(PathVector &paths) {
    std::unordered_set<std::wstring> filenames;  // mk_smth.vbs, smth.bat
    std::erase_if(paths, [&filenames](const fs::path &p) {
        auto fname = p.filename().wstring();
        return !filenames.insert(fname).second;
    });
}

// remove so-called forbidden files, we do not want to execute
void RemoveForbiddenNames(PathVector &paths) {
    std::erase_if(paths, [](const auto &p) {
        return tools::IsEqual(p.filename().wstring(), L"cmk-update-agent.exe");
    });
}

// make a list of files to be run(check exists normally is true)
PathVector FilterPathVector(const PathVector &found_files,
                            const std::vector<cfg::Plugins::ExeUnit> &units,
                            bool check_exists) {
    PathVector really_found;
    for (const auto &ff : found_files) {
        if (std::error_code ec; check_exists && !fs::exists(ff, ec)) {
            continue;
        }
        for (const auto &unit : units) {
            if (!MatchNameOrAbsolutePath(unit.pattern(), ff)) {
                continue;
            }
            if (unit.run()) {
                really_found.emplace_back(ff);
            }
            break;
        }
    }
    return really_found;
}

TheMiniBox::StartMode GetStartMode(const fs::path &filepath) {
    auto filename = wtools::ToUtf8(filepath.filename().wstring());
    tools::StringLower(filename);
    if (filename == wtools::ToUtf8(cfg::files::kAgentUpdaterPython) ||
        filename == wtools::ToUtf8(cfg::files::kAgentCtl)) {
        XLOG::d.i("Plugin '{}' has updater start mode", filepath);
        return TheMiniBox::StartMode::detached;
    }

    return TheMiniBox::StartMode::job;
}

const PluginEntry *GetEntrySafe(const PluginMap &plugin_map,
                                const std::string &key) {
    try {
        return &plugin_map.at(key);
    } catch (...) {
        return nullptr;
    }
}

PluginEntry *GetEntrySafe(PluginMap &plugin_map, const std::string &key) {
    try {
        return &plugin_map.at(key);
    } catch (...) {
        return nullptr;
    }
}

const PluginEntry *GetEntrySafe(const PluginMap &plugin_map,
                                const fs::path &f) {
    return GetEntrySafe(plugin_map, wtools::ToUtf8(f.wstring()));
}

PluginEntry *GetEntrySafe(PluginMap &plugin_map, const fs::path &f) {
    return GetEntrySafe(plugin_map, wtools::ToUtf8(f.wstring()));
}

void InsertInPluginMap(PluginMap &plugin_map, const PathVector &found_files) {
    for (const auto &ff : found_files) {
        plugin_map.try_emplace(wtools::ToUtf8(ff.wstring()), ff);
    }
}

namespace {
cma::cfg::Plugins::ExeUnit *GetEntrySafe(UnitMap &unit_map,
                                         const std::string &key) {
    try {
        return &unit_map.at(key);
    } catch (...) {
        return nullptr;
    }
}

void UpdatePluginMapWithUnitMap(PluginMap &out, UnitMap &um, bool local) {
    for (const auto &[name, unit] : um) {
        auto *ptr = GetEntrySafe(out, name);
        if (ptr != nullptr) {
            if (unit.run()) {
                ptr->applyConfigUnit(unit, local);
            } else {
                ptr->removeFromExecution();
            }
        } else {
            if (unit.run()) {
                out.try_emplace(name, name);
                ptr = GetEntrySafe(out, name);
                if (ptr != nullptr) {
                    ptr->applyConfigUnit(unit, local);
                }
            }
        }
    }

    // remove entries with missing configuration
    for (auto &[name, p] : out) {
        const auto *ptr = GetEntrySafe(um, name);
        if (ptr == nullptr) {
            p.removeFromExecution();
        }
    }

    // reporting
    for (const auto &[name, unit] : um) {
        const auto *ptr = GetEntrySafe(out, name);
        if (ptr == nullptr) {
            continue;
        }
        XLOG::d.i("{} '{}'  is  {} with age:{} timeout:{} retry:{}",
                  local ? "Local" : "Plugin", name,
                  ptr->async() ? "async" : "sync", ptr->cacheAge(),
                  ptr->timeout(), ptr->retry());
    }
}
}  // namespace

namespace tools {
bool AddUniqStringToSetIgnoreCase(StringSet &cache,
                                  const std::string &value) noexcept {
    std::string to_insert{value};
    tools::StringUpper(to_insert);

    if (!cache.contains(to_insert)) {
        cache.insert(to_insert);
        return true;
    }

    return false;
}

bool AddUniqStringToSetAsIs(StringSet &cache,
                            const std::string &value) noexcept {
    if (!cache.contains(value)) {
        cache.insert(value);
        return true;
    }

    return false;
}
}  // namespace tools

static void ApplyEverythingLogResult(const std::string &format,
                                     std::string_view file, bool local) {
    XLOG::t(format, file, local ? "[local]" : "[plugins]");
}

std::vector<fs::path> RemoveDuplicatedFilesByName(
    const std::vector<fs::path> &found_files, bool local) {
    cma::tools::StringSet cache;
    std::vector<fs::path> files{found_files};
    std::erase_if(files, [&cache, local](const fs::path &candidate) {
        auto fname = wtools::ToUtf8(candidate.filename().wstring());
        auto new_file = tools::AddUniqStringToSetIgnoreCase(cache, fname);
        if (!new_file) {
            ApplyEverythingLogResult("Skipped duplicated file '{}'",
                                     wtools::ToUtf8(candidate.wstring()),
                                     local);
        }
        return !new_file;
    });
    return files;
}

void RemoveDuplicatedEntriesByName(UnitMap &um, bool local) {
    std::set<std::string, std::less<>> cache;
    std::vector<std::string> to_remove;
    for (const auto &[name, unit] : um) {
        fs::path p = unit.pattern();
        auto new_file = tools::AddUniqStringToSetIgnoreCase(
            cache, wtools::ToUtf8(p.filename().wstring()));
        if (!new_file) {
            ApplyEverythingLogResult("Skipped duplicated file '{}'",
                                     wtools::ToUtf8(p.wstring()), local);
            to_remove.emplace_back(name);
        }
    }
    for (const auto &str : to_remove) {
        um.erase(str);
    }
}

namespace {

void AllowAccess(const fs::path &f, std::wstring_view name) {
    wtools::ChangeAccessRights(
        f.wstring().c_str(), SE_FILE_OBJECT, name.data(), TRUSTEE_IS_NAME,
        STANDARD_RIGHTS_ALL | GENERIC_ALL, GRANT_ACCESS, OBJECT_INHERIT_ACE);
}

void ConditionallyAllowAccess(const fs::path &f,
                              const cfg::Plugins::ExeUnit &unit) {
    if (!unit.group().empty()) {
        AllowAccess(f, wtools::ConvertToUTF16(unit.group()));
    } else if (!unit.user().empty()) {
        AllowAccess(f, wtools::ConvertToUTF16(unit.user()));
    }
}
}  // namespace

void ApplyEverythingToPluginMap(PluginMap &plugin_map,
                                const std::vector<cfg::Plugins::ExeUnit> &units,
                                const std::vector<fs::path> &found_files,
                                bool local) {
    UnitMap um;

    for (const auto &f : found_files) {
        for (auto it = units.rbegin(); it != units.rend(); ++it) {
            if (!MatchPattern(it->pattern(), f)) {
                continue;
            }

            auto entry_full_name = wtools::ToUtf8(f.wstring());
            auto *exe = GetEntrySafe(um, entry_full_name);
            std::string fmt_string;
            if (exe != nullptr) {
                fmt_string = "Plugin '{}' to be updated to {}";
            } else {
                // check duplicated filename
                um.try_emplace(entry_full_name);
                fmt_string = "Plugin '{}' added to {}";
                exe = GetEntrySafe(um, entry_full_name);
            }

            if (exe != nullptr) {
                XLOG::t("To plugin '{}' to be applied rule '{}'", f,
                        it->sourceText());
                exe->apply(entry_full_name, it->source());
                ConditionallyAllowAccess(f, *exe);
            }

            ApplyEverythingLogResult(fmt_string, entry_full_name, local);
        }
    }

    std::set<std::string, std::less<>> cache;
    for (const auto &f : found_files) {
        auto entry_full_name = wtools::ToUtf8(f.wstring());
        tools::StringLower(entry_full_name);

        if (const auto *exe = GetEntrySafe(um, entry_full_name);
            exe == nullptr || !exe->run()) {
            continue;
        }
        auto fname = wtools::ToUtf8(f.filename().wstring());
        auto added = tools::AddUniqStringToSetIgnoreCase(cache, fname);
        if (!added) {
            um.erase(entry_full_name);
            const auto *fmt_string =
                "Skipped duplicated file by name '{}' in {}";
            ApplyEverythingLogResult(fmt_string, entry_full_name, local);
        }
    }
    // apply config for presented
    UpdatePluginMapWithUnitMap(plugin_map, um, local);
}

// Main API
void UpdatePluginMap(PluginMap &plugin_map,  // output is here
                     bool local,             // type of plugin
                     const PathVector &found_files,
                     const std::vector<cma::cfg::Plugins::ExeUnit> &units,
                     bool check_exists) {
    if (found_files.empty() || units.empty()) {
        plugin_map.clear();  // nothing todo
        return;
    }

    auto really_found = FilterPathVector(found_files, units, check_exists);
    FilterPluginMap(plugin_map, really_found);
    ApplyEverythingToPluginMap(plugin_map, units, really_found, local);
    RemoveDuplicatedPlugins(plugin_map, check_exists);
}

std::optional<std::string> GetPiggyBackName(const std::string &in_string) {
    if (in_string.find(section::kFooter4Left) != 0) {
        return {};
    }

    auto end = in_string.find(section::kFooter4Right);
    if (end == std::string::npos) return {};
    constexpr auto footer_len = section::kFooter4Left.length();
    if (footer_len > end) {
        XLOG::l(XLOG_FUNC + " impossible");
        return {};
    }

    return in_string.substr(footer_len, end - footer_len);
}

// hacks a plugin header with another string, usually cached info
// '<<<plugin_super>>>': '<<<plugin_super:cached(11204124124:3600)>>>'
// '<<<>>>': '<<<:cached(11204124124:3600)>>>' returns nothing
// returns true if patch happened
bool TryToHackStringWithCachedInfo(std::string &in_string,
                                   const std::string &value_to_insert) {
    // probably regex better or even simple memcmp/strcmp
    auto pos_start = in_string.find(cma::section::kLeftBracket);
    auto pos_end = in_string.find(cma::section::kRightBracket);
    if (pos_start == 0 &&                // starting from <<<
        pos_end != std::string::npos &&  // >>> presented too
        pos_end > pos_start &&           //
        (pos_end - pos_start) < 100) {   // not very far away
        in_string.insert(pos_end, value_to_insert);
        return true;
    }

    return false;
}

static const bool g_config_remove_slash_r = false;

std::string ConstructPatchString(time_t time_now, int cache_age,
                                 HackDataMode mode) {
    if (time_now == 0 || cache_age == 0) {
        return {};
    }

    return mode == HackDataMode::line
               ? fmt::format("cached({},{}) ", time_now, cache_age)
               : fmt::format(":cached({},{})", time_now, cache_age);
}

// #TODO refactor this function
bool HackDataWithCacheInfo(std::vector<char> &out,
                           const std::vector<char> &original_data,
                           const std::string &patch, HackDataMode mode) {
    if (original_data.empty()) {
        return false;
    }

    // check we have valid Data
    std::string stringized(original_data.data(), original_data.size());
    if (stringized.empty()) {
        return false;
    }

    if (patch.empty() && !g_config_remove_slash_r) {
        out = original_data;
        return true;
    }

    auto table = tools::SplitString(stringized, "\n");

    size_t data_count = 0;
    bool hack_allowed = true;
    for (auto &t : table) {
        if (g_config_remove_slash_r) {
            while (t.back() == '\r') {
                t.pop_back();
            }
        }

        t.push_back('\n');
        data_count += t.size();

        // 2. try hack header if required
        if (patch.empty()) continue;

        if (mode == HackDataMode::line) {
            t = patch + t;  // NOLINT
            continue;
        }

        // check for piggyback
        auto piggyback_name = GetPiggyBackName(t);
        if (piggyback_name) {
            if (piggyback_name->empty()) {
                XLOG::t.i("piggyback input ended");
                hack_allowed = true;
            } else {
                XLOG::t.i("piggyback input '{}' started", *piggyback_name);
                hack_allowed = false;
            }
            continue;
        }

        // hack code if not piggyback and we have something to patch
        if (hack_allowed) {
            auto patched = TryToHackStringWithCachedInfo(t, patch);
            if (patched) {
                data_count += patch.size();
            }
        }
    }

    out.reserve(data_count + 1);
    for (const auto &t : table) {
        tools::AddVector(out, t);
    }
    if (original_data.back() != '\n') {
        out.pop_back();
    }

    return true;
}

// LOOP:
// register
// wait some time
// unregister
// read data
// Max Timeout < 0 use default
std::vector<char> PluginEntry::getResultsSync(const std::wstring &id,
                                              int max_timeout) {
    if (failed()) {
        return {};
    }

    auto exec = cmd_line_.empty() ? ConstructCommandToExec(path()) : cmd_line_;
    if (exec.empty()) {
        XLOG::l(
            "Failed to start minibox sync '{}', can't find executables for the '{}'",
            wtools::ToUtf8(id), path().u8string());
        return {};
    }

    auto started =
        minibox_.startEx(L"id", exec, TheMiniBox::StartMode::job, iu_);
    if (!started) {
        XLOG::l("Failed to start minibox sync '{}'", wtools::ToUtf8(id));
        return {};
    }

    int tout = 0;
    if (max_timeout < 0) {
        tout = timeout();
    } else {
        tout = std::min(timeout(), max_timeout);
    }

    registerProcess(minibox_.getProcessId());
    auto success = minibox_.waitForEnd(std::chrono::seconds(tout));

    std::vector<char> accu;

    if (success) {
        minibox_.processResults([&](const std::wstring &cmd_line, uint32_t pid,
                                    uint32_t code,
                                    const std::vector<char> &datablock) {
            auto data = wtools::ConditionallyConvertFromUTF16(datablock);
            if (!data.empty() && data.back() == 0) {
                data.pop_back();  // conditional convert adds 0
            }
            tools::AddVector(accu, data);
            storeData(pid, accu);
            if (cma::cfg::LogPluginOutput()) {
                XLOG::t("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                        wtools::ToUtf8(cmd_line), pid, code, data.data());
            }
        });

    } else {
        // process was either stopped or failed(timeout)
        auto failed = minibox_.failed();
        unregisterProcess();
        XLOG::d("Sync Plugin stopped '{}' Stopped: {} Failed: {}", path(),
                !failed, failed);
        if (failed) {
            failures_++;
        }
    }

    minibox_.clean();
    return accu;
}

void PluginEntry::setCmdLine(std::wstring_view name) { cmd_line_ = name; }

void PluginEntry::breakAsync() {
    XLOG::t("breakAsync {}", path());
    joinAndReleaseMainThread();
}

void PluginEntry::joinAndReleaseMainThread() {
    std::unique_lock lk(lock_);
    auto t = std::move(main_thread_);
    lk.unlock();
    if (!t || !t->joinable()) {
        return;
    }

    try {
        minibox_.stopWaiting();
        t->join();
        minibox_.clean();
    } catch (const std::exception &e) {
        XLOG::l("Join disaster '{}' out {}", path(), e.what());
    } catch (...) {
        XLOG::l.bp("JOIN '{}' out", path());
    }
}

namespace {
struct ProcInfo {
    uint32_t waiting_processes{0};
    std::string proc_name;
    size_t added{0};
    int blocks{0};
};

void LogProcessStatus(bool success, uint64_t ustime, ProcInfo &pi) {
    auto text = fmt::format(
        "perf:  In [{}] milliseconds process '{}' pid:[{}] {} - generated [{}] bytes of data in [{}] blocks",
        ustime / 1000, pi.proc_name, pi.waiting_processes,
        success ? "SUCCEDED" : "FAILED", pi.added, pi.blocks);
    if (success) {
        XLOG::d.i(text);
    } else {
        XLOG::d(text);
    }
}
}  // namespace

bool TheMiniBox::waitForStop(std::chrono::milliseconds interval) {
    std::unique_lock lk(lock_);
    auto stop_time = std::chrono::steady_clock::now() + interval;
    auto stopped =
        cv_stop_.wait_until(lk, stop_time, [this]() { return stop_set_; });

    return stopped || stop_set_;
}

bool TheMiniBox::startEx(std::wstring_view uniq_id, const std::wstring &exec,
                         StartMode start_mode,
                         const wtools::InternalUser &internal_user) {
    std::lock_guard lk(lock_);
    if (process_ != nullptr) {
        return false;
    }

    sw_.start();
    id_ = uniq_id;
    exec_ = exec;

    // send exec array entries to internal
    try {
        // now exec
        auto ar = std::make_unique<wtools::AppRunner>();
        XLOG::d.t("Exec app '{}', mode [{}]", wtools::ToUtf8(exec),
                  static_cast<int>(start_mode));

        switch (start_mode) {
            case StartMode::job:
                if (internal_user.first.empty()) {
                    proc_id_ = ar->goExecAsJob(exec);
                } else {
                    proc_id_ = ar->goExecAsJobAndUser(
                        internal_user.first, internal_user.second, exec);
                }
                break;
            case StartMode::detached:
                proc_id_ = ar->goExecAsDetached(exec);
                break;
        }

        if (proc_id_ != 0) {
            process_ = ar.release();
            return true;
        }

    } catch (const std::exception &e) {
        XLOG::l(XLOG_FLINE + " exception {}", e.what());
    }
    sw_.stop();
    // cleaning up
    id_.clear();
    exec_.clear();

    return false;
}

bool TheMiniBox::waitForEnd(std::chrono::milliseconds timeout) {
    if (stop_set_) {
        return false;
    }
    ON_OUT_OF_SCOPE(readWhatLeft());

    constexpr auto grane_long = 50ms;
    constexpr auto grane_short = 20ms;
    auto *read_handle = getReadHandle();
    ProcInfo pi = {getProcessId(), wtools::ToUtf8(exec_), 0, 0};

    while (true) {
        auto grane = grane_long;
        auto ready = checkProcessExit(pi.waiting_processes) ||  // process exit?
                     srv::IsGlobalStopSignaled();  // agent is exiting?
        auto buf = wtools::ReadFromHandle(read_handle);
        if (!buf.empty()) {
            pi.added += buf.size();
            pi.blocks++;
            appendResult(read_handle, buf);
            grane = grane_short;  // using short time period to poll
        }

        if (ready) {
            auto us_time = sw_.stop();
            LogProcessStatus(true, us_time, pi);
            return true;
        }

        if (timeout >= grane) {
            timeout -= grane;
            if (waitForStop(grane)) {
                // stopped outside
                XLOG::d(
                    "Process '{}' to be stopped outside, left timeout [{}ms]!",
                    pi.proc_name, timeout.count());
            } else {
                continue;
            }
        } else {
            failed_ = true;
        }

        // not normal situation
        auto us_time = sw_.stop();  // get time asap
        LogProcessStatus(false, us_time, pi);

        process_->kill(true);
        return false;
    }

    // never here
}

bool TheMiniBox::waitForEndWindows(std::chrono::milliseconds Timeout) {
    if (stop_set_) {
        return false;
    }
    ON_OUT_OF_SCOPE(readWhatLeft());

    auto *read_handle = getReadHandle();
    ProcInfo pi = {getProcessId(), wtools::ToUtf8(exec_), 0, 0};
    constexpr std::chrono::milliseconds time_grane_windows = 250ms;

    while (true) {
        auto ready = checkProcessExit(pi.waiting_processes);
        HANDLE handles[2] = {read_handle, stop_event_};
        auto ret = ::WaitForMultipleObjects(
            2, handles, FALSE, static_cast<DWORD>(time_grane_windows.count()));

        if (ret == WAIT_OBJECT_0) {
            auto buf = wtools::ReadFromHandle(read_handle);
            if (!buf.empty()) {
                pi.added += buf.size();
                pi.blocks++;
                appendResult(read_handle, buf);
            }
        }

        if (ready) {
            auto us_time = sw_.stop();
            LogProcessStatus(true, us_time, pi);
            return true;
        }

        if (ret == WAIT_OBJECT_0) {
            ::Sleep(10);
            continue;
        }

        if (ret == WAIT_TIMEOUT && Timeout > time_grane_windows) {
            Timeout -= time_grane_windows;
            continue;
        }

        // here we will break always

        // check that we are breaking by timeout
        if (Timeout < time_grane_windows) {
            failed_ = true;
        } else {
            // stopped outside
            XLOG::d("Process '{}' signaled to be stopped, left timeout [{}ms]!",
                    pi.proc_name, Timeout.count());
        }

        // not normal situation
        auto us_time = sw_.stop();  // get time asap
        LogProcessStatus(false, us_time, pi);

        process_->kill(true);

        return false;
    }

    // never here
}

namespace {
constexpr std::chrono::milliseconds time_grane{250};
}

void TheMiniBox::readAndAppend(HANDLE read_handle,
                               std::chrono::milliseconds timeout) {
    auto buf = wtools::ReadFromHandle(read_handle);
    if (buf.empty()) {
        return;
    }

    if (process_->getData().empty()) {
        // after getting first data, we need to decrease timeout to
        // prevent too long waiting for nothing
        timeout = std::min(timeout, 10 * time_grane);
    }
    appendResult(read_handle, buf);
    XLOG::d.t("Appended [{}] bytes from '{}', timeout is [{}ms]", buf.size(),
              wtools::ToUtf8(exec_), timeout.count());
}

bool TheMiniBox::waitForBreakLoop(std::chrono::milliseconds timeout) {
    if (timeout < time_grane) {
        XLOG::d("Plugin '{}' hits timeout", wtools::ToUtf8(exec_));
        return true;
    }

    if (waitForStop(time_grane)) {
        XLOG::d("Plugin '{}' gets signal stop [{}], timeout left [{}ms]!",
                wtools::ToUtf8(exec_), stop_set_, timeout.count());
        return true;
    }

    return false;
}

/// Modified version to be used by Updater
bool TheMiniBox::waitForUpdater(std::chrono::milliseconds timeout) {
    if (stop_set_) {
        return false;
    }

    auto read_handle = getReadHandle();

    while (true) {
        readAndAppend(read_handle, timeout);

        if (waitForBreakLoop(timeout)) {
            break;
        }

        timeout -= time_grane;
    }

    if (process_->getData().empty()) {
        auto process_id = getProcessId();
        failed_ = timeout < time_grane;
        process_->kill(true);
        XLOG::l("Process '{}' [{}] is killed", wtools::ToUtf8(exec_),
                process_id);
        return false;
    }

    readWhatLeft();
    return true;
}

void PluginEntry::threadCore(const std::wstring &Id) {
    // pre entry
    // thread counters block
    XLOG::d.i("Async Thread for {} is to be started", wtools::ToUtf8(Id));
    g_tread_count++;
    ON_OUT_OF_SCOPE(g_tread_count--);
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

    auto exec = cmd_line_.empty() ? ConstructCommandToExec(path()) : cmd_line_;
    if (exec.empty()) {
        XLOG::l(
            "Failed to start minibox '{}', can't find executables for the '{}'",
            wtools::ToUtf8(Id), path().u8string());
        return;
    }

    auto started = minibox_.startEx(Id, exec, mode, iu_);
    if (!started) {
        XLOG::l("Failed to start minibox thread {}", wtools::ToUtf8(Id));
        return;
    }

    registerProcess(minibox_.getProcessId());
    std::vector<char> accu;

    auto success =
        mode == TheMiniBox::StartMode::detached
            ? minibox_.waitForUpdater(std::chrono::seconds(timeout()))
            : minibox_.waitForEnd(std::chrono::seconds(timeout()));
    if (success) {
        // we have probably data, try to get and and store
        minibox_.processResults([&](const std::wstring &cmd_line, uint32_t pid,
                                    uint32_t code,
                                    const std::vector<char> &datablock) {
            auto data = wtools::ConditionallyConvertFromUTF16(datablock);
            tools::AddVector(accu, data);
            {
                std::lock_guard l(data_lock_);
                storeData(pid, accu);
            }
            if (cma::cfg::LogPluginOutput()) {
                XLOG::t("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                        wtools::ToUtf8(cmd_line), pid, code, data.data());
            }
        });
    } else {
        // process was either stopped or failed(timeout)
        auto failed = minibox_.failed();
        unregisterProcess();
        XLOG::d("Async Plugin stopped '{}' Stopped: {} Failed: {}", path(),
                !failed, failed);
        if (failed) {
            failures_++;
        }
    }

    XLOG::d.t("Thread OFF: '{}'", path());
}

wtools::InternalUser PluginsExecutionUser2Iu(std::string_view user) {
    auto table = tools::SplitStringExact(wtools::ConvertToUTF16(user), L" ", 2);
    if (table.empty()) {
        return {};
    }
    if (table.size() == 2) {
        return {table[0], table[1]};
    }

    return {table[0], L""};
}

void PluginEntry::fillInternalUser() {
    // reset all to be safe due to possible future errors in logic
    iu_.first.clear();
    iu_.second.clear();

    // group is coming first
    if (!group_.empty()) {
        iu_ = ObtainInternalUser(wtools::ConvertToUTF16(group_));
        XLOG::t("Entry '{}' uses user '{}' as group config", path(),
                wtools::ToUtf8(iu_.first));
        return;
    }

    if (user_.empty()) return;  // situation when both fields are empty

    // user
    iu_ = PluginsExecutionUser2Iu(user_);
    XLOG::t("Entry '{}' uses user '{}' as direct config", path(),
            wtools::ToUtf8(iu_.first));
}

// if thread finished join old and start new thread again
// if thread NOT finished quit
void PluginEntry::restartAsyncThreadIfFinished(const std::wstring &Id) {
    std::unique_lock lk(lock_);
    auto start_thread = !thread_on_;
    thread_on_ = true;  // thread is always on
    if (start_thread) {
        data_is_going_old_ = false;
    }
    lk.unlock();

    if (!start_thread) {
        // when thread is still running
        XLOG::d.i(
            "Thread for plugin '{}' is still running, restart is not required",
            path());
        return;
    }

    // thread was finished  join(we must)
    joinAndReleaseMainThread();
    // restart
    auto t = std::make_unique<std::thread>(&PluginEntry::threadCore, this, Id);
    lk.lock();
    main_thread_ = std::move(t);
    lk.unlock();
    XLOG::d.i("restarted thread for plugin '{}'", path());
}

std::vector<char> PluginEntry::getResultsAsync(bool StartProcessNow) {
    if (failed()) {
        return {};
    }

    // check is valid parameters
    if (cacheAge() < cma::cfg::kMinimumCacheAge && cacheAge() != 0) {
        XLOG::l("Plugin '{}' requested to be async, but has no valid cache age",
                path());
        return {};
    }
    // check data are ready and new enough
    bool data_ok = false;
    std::chrono::seconds allowed_age(cacheAge());
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
    if (!data_ok) {
        XLOG::d("Data '{}' is too old, age is '{}' seconds", path(),
                duration_cast<std::chrono::seconds>(data_age).count());
    }

    // execution phase
    if (going_to_be_old) {
        if (StartProcessNow) {
            XLOG::d.i("restarting async plugin '{}'", path());
            restartAsyncThreadIfFinished(path().wstring());
        } else {
            XLOG::d.i("plugin '{}' is marked for restart", path());
            markAsForRestart();
        }
    }

    // we always return data even if data is OLD
    return data_;
}

void PluginEntry::restartIfRequired() {
    // check is valid parameters
    if (cacheAge() < cma::cfg::kMinimumCacheAge) {
        XLOG::l(
            "Plugin '{}' requested to be async restarted, but has no valid cache age",
            path());
        return;
    }
    // check data are ready and new enough
    std::chrono::seconds allowed_age{cacheAge()};
    auto data_age = getDataAge();

    std::lock_guard l(data_lock_);
    {
        if (data_age <= allowed_age) {
            return;
        }
        data_time_ = std::chrono::steady_clock::now();  // update time
                                                        // of start
    }
    auto filename = wtools::ToUtf8(path().wstring());
    // execution phase
    XLOG::d.t("Starting '{}'", filename);
    auto result = tools::RunDetachedCommand(filename);
    if (result) {
        XLOG::d.i("Starting '{}' OK!", filename);
    } else {
        XLOG::l("Starting '{}' FAILED with error [{}]", filename,
                GetLastError());
    }
}

// after starting box
bool PluginEntry::registerProcess(uint32_t Id) {
    if (failed()) {
        XLOG::d("RETRY FAILED!!!!!!!!!!! {}", retry(), failed());
        process_id_ = 0;
        return false;
    }
    process_id_ = Id;
    start_time_ = std::chrono::steady_clock::now();
    return true;
}

// this is not normal situation
// as a rule only after timeout
void PluginEntry::unregisterProcess() {
    // killing process
    process_id_ = 0;
}

// on reading box
// MUST BE CALLED INSIDE LOCK_GUARD!
void PluginEntry::storeData(uint32_t proc_id, const std::vector<char> &data) {
    if (proc_id != process_id_ || proc_id == 0) {
        XLOG::d("Invalid process {}, can't store data {} ", proc_id, path());
        return;
    }

    process_id_ = 0;
    auto now = std::chrono::steady_clock::now();
    auto diff =
        std::chrono::duration_cast<std::chrono::seconds>(now - start_time_)
            .count();
    if (diff > static_cast<int64_t>(timeout())) {
        XLOG::d("Process '{}' timeout in {} when set {}", path(), diff,
                timeout());
    } else if (data.empty()) {
        // plugin failed
        XLOG::d("Process '{}' has no data", path());
    }

    if (failed()) {
        data_.clear();
        return;
    }

    data_time_ = std::chrono::steady_clock::now();
    auto legacy_time = ::time(nullptr);

    if (cacheAge() > 0) {
        data_.clear();
        auto mode = local_ ? HackDataMode::line : HackDataMode::header;
        auto patch_string = ConstructPatchString(legacy_time, cacheAge(), mode);
        HackDataWithCacheInfo(data_, data, patch_string, mode);
    } else  // "sync plugin" or async with 0 as cache age
    {
        // or "failed to hack"
        data_ = data;
    }
    legacy_time_ = legacy_time;

    // Remove trailing zero's looks weird, but nulls
    // can be created in some cases by plugin and processing(ConvertTo)
    // But must be removed in output
    while (!data_.empty() && data_.back() == '\0') data_.pop_back();
}  // namespace cma

// remove what not present in the file vector
void FilterPluginMap(PluginMap &out_map, const PathVector &found_files) {
    std::vector<std::string> to_delete;
    if (found_files.empty()) {
        out_map.clear();
        return;
    }

    // check every entry for presence in the foundfiles vector
    // absent entries are in to_delete
    for (const auto &out : out_map) {
        bool exists = false;
        for (const auto &ff : found_files) {
            if (out.first == wtools::ToUtf8(ff.wstring())) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            to_delete.push_back(out.first);  // store path to be removed
        }
    }

    // second deletion phase - we can't delete
    // while iterating through container
    for (const auto &del : to_delete) {
        out_map.erase(del);
    }
}

// CheckExists = false is only for testing,
// set true for Production
// Out is mutable
void RemoveDuplicatedPlugins(PluginMap &plugin_map, bool check_exists) {
    std::unordered_set<std::string> filename_set;  // mk_smth.vbs, smth.bat, etc

    std::error_code ec;
    for (auto it = plugin_map.begin(); it != plugin_map.end();) {
        fs::path p = it->first;

        if (it->second.path().empty()) {
            it = plugin_map.erase(it);
            continue;
        }

        if (check_exists && !fs::exists(p, ec)) {
            it = plugin_map.erase(it);
            continue;
        }

        if (!filename_set.insert(wtools::ToUtf8(p.filename().wstring())).second)
            it = plugin_map.erase(it);
        else
            ++it;
    }
}

namespace provider::config {
const bool g_async_plugin_without_cache_age_run_async = true;
const bool g_set_logwatch_pos_to_end = true;

bool IsRunAsync(const PluginEntry &plugin) noexcept {
    auto run_async = plugin.async();

    if (g_async_plugin_without_cache_age_run_async) return run_async;

    if (run_async && plugin.cacheAge() == 0)
        return config::g_async_plugin_without_cache_age_run_async;

    return run_async;
}
}  // namespace provider::config

using DataBlock = std::vector<char>;
void StartSyncPlugins(PluginMap &plugins,
                      std::vector<std::future<DataBlock>> &results,
                      int timeout) {
    for (auto &entry_pair : plugins) {
        auto &entry = entry_pair.second;
        if (provider::config::IsRunAsync(entry)) {
            continue;
        }
        XLOG::t("Executing '{}'", entry.path());
        results.emplace_back(std::async(
            std::launch::async,
            [](cma::PluginEntry *e, int /*timeout*/) -> DataBlock {
                if (e == nullptr) {
                    return {};
                }
                return e->getResultsSync(e->path().wstring());
            },
            &entry, timeout));
    }
}

DataBlock RunSyncPlugins(PluginMap &plugins, int &total, int timeout) {
    XLOG::d.t("To start [{}] sync plugins", plugins.size());

    std::vector<std::future<DataBlock>> results;
    StartSyncPlugins(plugins, results, timeout);

    DataBlock out;
    int delivered_count = 0;
    for (auto &r : results) {
        auto result = r.get();
        if (!result.empty()) {
            ++delivered_count;
            tools::AddVector(out, result);
        }
    }

    total = delivered_count;
    return out;
}

void RunDetachedPlugins(const PluginMap &plugins_map, int &start_count) {
    start_count = 0;

    // async part
    int count = 0;
    for (const auto &[_, entry] : plugins_map) {
        if (!entry.async()) {
            continue;
        }
    }
    XLOG::t.i("Detached started: [{}]", count);
    start_count = count;
}

// To get data from async plugins with cache_age=0
void PickupAsync0data(int timeout, PluginMap &plugins, std::vector<char> &out,
                      std::vector<std::pair<bool, std::string>> &async_0s) {
    timeout = std::max(timeout, 10);
    if (timeout != 0) {
        XLOG::d.i(
            "Picking up [{}] async-0"
            "plugins with timeout [{}]",
            async_0s.size(), timeout);
    }

    // pickup 0 async
    // plugin.first - status
    // plygin.second - name
    size_t async_count = 0;
    for (int i = 0; i < timeout; i++) {
        for (auto &plugin : async_0s) {
            if (plugin.first) {
                continue;
            }

            const auto *e = GetEntrySafe(plugins, plugin.second);
            if (e != nullptr && !e->running()) {
                tools::AddVector(out, e->data());
                plugin.first = false;
                async_count++;
            }
        }
        if (async_count >= async_0s.size()) {
            break;
        }
        tools::sleep(1000);
    }
}

std::vector<char> RunAsyncPlugins(PluginMap &plugins, int &total,
                                  bool start_immediately) {
    total = 0;

    std::vector<char> out;

    int count = 0;
    for (auto &entry_pair : plugins) {
        auto &entry = entry_pair.second;

        if (!entry.async()) {
            continue;
        }

        auto run_async = provider::config::IsRunAsync(entry);
        if (!run_async) {
            continue;
        }

        auto ret = entry.getResultsAsync(start_immediately);
        if (!ret.empty()) {
            ++count;
        }
        tools::AddVector(out, ret);
    }

    total = count;

    return out;
}
}  // namespace cma

namespace cma {
std::mutex g_users_lock;
std::unordered_map<std::wstring, wtools::InternalUser> g_users;

wtools::InternalUser ObtainInternalUser(std::wstring_view group) {
    std::wstring group_name(group);
    std::lock_guard lk(g_users_lock);
    auto it = g_users.find(group_name);
    if (it != g_users.end()) {
        return it->second;
    }

    auto iu = wtools::CreateCmaUserInGroup(group_name);
    if (iu.first.empty()) {
        return {};
    }

    g_users[group_name] = iu;

    return iu;
}

void KillAllInternalUsers() {
    std::lock_guard lk(g_users_lock);
    for (const auto &iu : g_users) {
        wtools::RemoveCmaUser(iu.second.first);
    }
    g_users.clear();
}

}  // namespace cma
