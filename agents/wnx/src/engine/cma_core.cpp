// cma_core.cpp :
//
#include "stdafx.h"

#include "wnx/cma_core.h"

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
#include "tools/_misc.h"
#include "wnx/glob_match.h"
#include "wnx/section_header.h"  // we have logging here
#include "wnx/service_processor.h"
#include "wnx/windows_service_api.h"

namespace fs = std::filesystem;
namespace rs = std::ranges;
using namespace std::chrono_literals;
using namespace std::string_literals;
using namespace std::string_view_literals;

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
    constexpr std::wstring_view powershell_name{L"powershell.exe"};
    wchar_t buffer[16];
    if (::SearchPathW(nullptr, powershell_name.data(), nullptr, 1, buffer,
                      nullptr) != 0) {
        return std::wstring(powershell_name);
    }

    // file not found on path
    auto powershell_path = tools::win::GetSomeSystemFolder(FOLDERID_System);

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
        XLOG::l("malformed name {} e:{}", wtools::ToUtf8(powershell_path), e);
    }
    return {};
}

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
        return std::equal(std::istreambuf_iterator(f1.rdbuf()),
                          std::istreambuf_iterator<char>(),
                          std::istreambuf_iterator(f2.rdbuf()));
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " exception '{}'", e.what());
        return false;
    }
}

bool CheckArgvForValue(int argc, const wchar_t *argv[], int pos,
                       std::string_view value) noexcept {
    return argv != nullptr && argc > pos && pos > 0 && argv[pos] != nullptr &&
           std::wstring(argv[pos]) == wtools::ConvertToUtf16(value);
}

std::pair<std::string_view, std::optional<std::string_view>> SplitView(
    std::string_view data, std::string_view delimiter) {
    const auto found = std::ranges::search(data.begin(), data.end(),
                                           delimiter.begin(), delimiter.end());
    if (found.empty()) {
        return std::pair{std::string_view{data.begin(), data.end()},
                         std::nullopt};
    }
    return std::pair{std::string_view{data.begin(), found.end()},
                     std::string_view{found.end(), data.end()}};
}

bool IsUtf16BomLe(std::string_view data) noexcept {
    return data.size() > 1 && data[0] == '\xFF' && data[1] == '\xFE';
}

void ScanView(std::string_view data, std::string_view delimiter,
              ScanViewCallback callback) {
    std::optional left = data;
    while (left) {
        auto [work, l] = SplitView(*left, delimiter);
        left = l;
        callback(work);
    }
}

}  // namespace tools

bool MatchNameOrAbsolutePath(const std::string &input,
                             const fs::path &file_full_path) {
    fs::path pattern{input};
    auto name = file_full_path.filename();
    if (!pattern.is_absolute() &&
        tools::GlobMatch(input, wtools::ToUtf8(name.wstring()))) {
        return true;
    }

    // support for absolute path
    auto full_name = wtools::ToUtf8(file_full_path.wstring());
    return tools::GlobMatch(input, full_name);
}

namespace {
bool MatchPattern(const std::string &input, const fs::path &file_full_path) {
    fs::path pattern = input;

    if (pattern.is_absolute()) {
        return tools::GlobMatch(input,
                                wtools::ToUtf8(file_full_path.wstring()));
    }

    // non absolute path we are using only part of the name
    auto file_name = file_full_path.filename();
    auto pattern_name = pattern.filename();
    return tools::GlobMatch(pattern_name.wstring(), file_name.wstring());
}
}  // namespace

PathVector GatherAllFiles(const PathVector &folders) {
    PathVector paths;

    for (const auto &dir : folders) {
        std::error_code ec;
        if (!fs::exists(dir, ec)) {
            continue;
        }

        // #TODO potential error we need recursive here
        for (const auto &p : fs::directory_iterator(dir)) {
            // Found files must match the entire path pattern.
            const auto status = p.status();
            if (ec) {
                XLOG::d("Can't obtain status for dir {} path {}status is {}",
                        dir, p.path(), ec.value());
                continue;
            }

            if (fs::is_regular_file(status)) {
                paths.push_back(p.path());
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
        const auto status = p.status();  // CMK-1417, to be confirmed in ticket
        if (ec) {
            XLOG::d("Cant obtain status for dir {} path {}status is {}",
                    search_dir, p.path(), ec.value());
            continue;
        }

        // normal file
        if (fs::is_regular_file(status) &&
            tools::GlobMatch(file_pattern.wstring(), p.path().wstring())) {
            files_found.push_back(p.path());
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
            return ext == wtools::ConvertToUtf16(e);
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
    } catch (const std::out_of_range &) {
        return nullptr;
    }
}

PluginEntry *GetEntrySafe(PluginMap &plugin_map, const std::string &key) {
    try {
        return &plugin_map.at(key);
    } catch (const std::out_of_range &) {
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
cfg::Plugins::ExeUnit *GetEntrySafe(UnitMap &unit_map, const std::string &key) {
    try {
        return &unit_map.at(key);
    } catch (const std::out_of_range &) {
        return nullptr;
    }
}

void UpdatePluginMapWithUnitMap(PluginMap &out, UnitMap &um, ExecType exec_type,
                                wtools::InternalUsersDb *iu) {
    for (const auto &[name, unit] : um) {
        auto *ptr = GetEntrySafe(out, name);
        if (ptr != nullptr) {
            if (unit.run()) {
                ptr->applyConfigUnit(unit, exec_type, iu);
            } else {
                ptr->removeFromExecution();
            }
        } else {
            if (unit.run()) {
                out.try_emplace(name, name);
                ptr = GetEntrySafe(out, name);
                if (ptr != nullptr) {
                    ptr->applyConfigUnit(unit, exec_type, iu);
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
    for (const auto &name : um | std::views::keys) {
        const auto *ptr = GetEntrySafe(out, name);
        if (ptr == nullptr) {
            continue;
        }
        XLOG::d.i("{} '{}'  is  {} with age:{} timeout:{} retry:{}",
                  ptr->local() ? "Local" : "Plugin", name,
                  ptr->async() ? "async" : "sync", ptr->cacheAge(),
                  ptr->timeout(), ptr->retry());
    }
}
}  // namespace

namespace tools {
bool AddUniqStringToSetAsIs(StringSet &cache,
                            const std::string &value) noexcept {
    if (!cache.contains(value)) {
        cache.insert(value);
        return true;
    }

    return false;
}

bool AddUniqStringToSetIgnoreCase(StringSet &cache,
                                  const std::string &value) noexcept {
    std::string to_insert{value};
    tools::StringUpper(to_insert);

    return AddUniqStringToSetAsIs(cache, to_insert);
}

}  // namespace tools

namespace {
void ApplyEverythingLogResult(const std::string &format, std::string_view file,
                              ExecType exec_type) noexcept {
    XLOG::t(format, file,
            exec_type == ExecType::local ? "[local]" : "[plugins]");
}
}  // namespace

std::vector<fs::path> RemoveDuplicatedFilesByName(
    const std::vector<fs::path> &found_files, ExecType exec_type) {
    tools::StringSet cache;
    std::vector files{found_files};
    std::erase_if(files, [&cache, exec_type](const fs::path &candidate) {
        const auto fname = wtools::ToUtf8(candidate.filename().wstring());
        const auto new_file = tools::AddUniqStringToSetIgnoreCase(cache, fname);
        if (!new_file) {
            ApplyEverythingLogResult("Skipped duplicated file '{}'",
                                     wtools::ToUtf8(candidate.wstring()),
                                     exec_type);
        }
        return !new_file;
    });
    return files;
}

void RemoveDuplicatedEntriesByName(UnitMap &um, ExecType exec_type) {
    std::set<std::string, std::less<>> cache;
    std::vector<std::string> to_remove;
    for (const auto &[name, unit] : um) {
        fs::path p = unit.pattern();
        auto new_file = tools::AddUniqStringToSetIgnoreCase(
            cache, wtools::ToUtf8(p.filename().wstring()));
        if (!new_file) {
            ApplyEverythingLogResult("Skipped duplicated file '{}'",
                                     wtools::ToStr(p), exec_type);
            to_remove.emplace_back(name);
        }
    }
    for (const auto &str : to_remove) {
        um.erase(str);
    }
}

namespace {
std::optional<std::wstring> GetTrustee(const cfg::Plugins::ExeUnit &unit,
                                       wtools::InternalUsersDb *iu) {
    if (!unit.group().empty() && iu != nullptr) {
        return iu->obtainUser(wtools::ConvertToUtf16(unit.group())).first;
    }
    if (unit.user().empty()) {
        return {};
    }
    return PluginsExecutionUser2Iu(unit.user()).first;
}

void AllowAccess(const fs::path &f, std::wstring_view name) {
    wtools::ChangeAccessRights(
        f.wstring().c_str(), SE_FILE_OBJECT, name.data(), TRUSTEE_IS_NAME,
        STANDARD_RIGHTS_ALL | GENERIC_ALL, GRANT_ACCESS, OBJECT_INHERIT_ACE);
}
void ConditionallyAllowAccess(const fs::path &f,
                              const cfg::Plugins::ExeUnit &unit,
                              wtools::InternalUsersDb *iu) {
    if (const auto trustee = GetTrustee(unit, iu)) {
        AllowAccess(f, *trustee);
    }
}
}  // namespace

void ApplyEverythingToPluginMap(wtools::InternalUsersDb *iu,
                                PluginMap &plugin_map,
                                const std::vector<cfg::Plugins::ExeUnit> &units,
                                const std::vector<fs::path> &found_files,
                                ExecType exec_type) {
    UnitMap um;

    for (const auto &f : found_files) {
        for (auto it = units.rbegin(); it != units.rend(); ++it) {
            if (!MatchPattern(it->pattern(), f)) {
                continue;
            }

            const auto entry_full_name = wtools::ToUtf8(f.wstring());
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
                ConditionallyAllowAccess(f, *exe, iu);
            }

            ApplyEverythingLogResult(fmt_string, entry_full_name, exec_type);
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
        const auto fname = wtools::ToUtf8(f.filename().wstring());
        const auto added = tools::AddUniqStringToSetIgnoreCase(cache, fname);
        if (!added) {
            um.erase(entry_full_name);
            const auto *fmt_string =
                "Skipped duplicated file by name '{}' in {}";
            ApplyEverythingLogResult(fmt_string, entry_full_name, exec_type);
        }
    }
    // apply config for presented
    UpdatePluginMapWithUnitMap(plugin_map, um, exec_type, iu);
}

// Main API
void UpdatePluginMap(wtools::InternalUsersDb *iu, PluginMap &plugin_map,
                     ExecType exec_type, const PathVector &found_files,
                     const std::vector<cfg::Plugins::ExeUnit> &units,
                     bool check_exists) {
    if (found_files.empty() || units.empty()) {
        plugin_map.clear();  // nothing todo
        return;
    }

    const auto really_found =
        FilterPathVector(found_files, units, check_exists);
    FilterPluginMap(plugin_map, really_found);
    ApplyEverythingToPluginMap(iu, plugin_map, units, really_found, exec_type);
    RemoveDuplicatedPlugins(plugin_map, check_exists);
}

std::optional<std::string> GetPiggyBackName(const std::string &in_string) {
    if (in_string.find(section::kFooter4Left) != 0) {
        return {};
    }

    const auto end = in_string.find(section::kFooter4Right);
    if (end == std::string::npos) {
        return {};
    }
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
    const auto pos_start = in_string.find(section::kLeftBracket);
    const auto pos_end = in_string.find(section::kRightBracket);
    if (pos_start == 0 &&                // starting from <<<
        pos_end != std::string::npos &&  // >>> presented too
        pos_end > pos_start &&           //
        pos_end - pos_start < 100) {     // not very far away
        in_string.insert(pos_end, value_to_insert);
        return true;
    }

    return false;
}

constexpr bool g_config_remove_slash_r{false};

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
    const std::string stringized(original_data.data(), original_data.size());
    if (stringized.empty()) {
        return false;
    }

    if (patch.empty() && !g_config_remove_slash_r) {
        out = original_data;
        return true;
    }

    auto table = tools::SplitString(stringized, "\n");

    size_t data_count = 0;
    for (auto &t : table) {
        if constexpr (g_config_remove_slash_r) {
            while (t.back() == '\r') {
                t.pop_back();
            }
        }

        t.push_back('\n');
        data_count += t.size();

        // 2. try hack header if required
        if (patch.empty()) {
            continue;
        }

        if (mode == HackDataMode::line) {
            t = patch + t;  // NOLINT
            continue;
        }

        // check for piggyback
        if (auto piggyback_name = GetPiggyBackName(t);
            piggyback_name.has_value()) {
            XLOG::t.i("skip piggyback input {}", *piggyback_name);
            continue;
        }

        // hack code if not piggyback and we have something to patch
        if (TryToHackStringWithCachedInfo(t, patch)) {
            data_count += patch.size();
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

namespace {
constexpr auto CR_16 = "\x0D\x00"sv;
constexpr auto LF_16 = "\x0A\x00"sv;

/// check we do not have added additional CR
void EnsureCorrectLastChar(std::string_view input, std::string &output) {
    if (input.length() >= 2 && input.substr(input.length() - 2) != LF_16 &&
        !output.empty() && output.back() == '\n') {
        output.pop_back();
    }
}

namespace {

struct DisassembleView {
    std::string_view s;
    bool has_cr;
    bool has_lf;
};

/// Separate data view from the L'CR' and L'LF'
/// Info about cr & lf is stored to be used during re-assembling
DisassembleView DisassembleString(std::string_view s) {
    const auto has_cr =
        s.length() >= 4 && s.substr(s.length() - 4, s.length() - 2) == CR_16;
    const auto has_lf = s.length() >= 2 && s.substr(s.length() - 2) == LF_16;
    auto sz = s.size();
    if (has_cr) {
        sz -= 2;
    }
    if (has_lf) {
        sz -= 2;
    }
    return {.s = {s.data(), sz}, .has_cr = has_cr, .has_lf = has_lf};
}

void AppendDisassembledTail(std::string &data,
                            const DisassembleView &disassembled) {
    if (disassembled.has_cr) {
        data += '\x0D';
    }
    if (disassembled.has_lf) {
        data += '\x0A';
    }
}

void AppendDisassembled(std::string &data,
                        const DisassembleView &disassembled) {
    data += disassembled.s;
    AppendDisassembledTail(data, disassembled);
}

}  // namespace

std::string ConvertWithRepair(std::string_view data_block) {
    std::string data;
    if (tools::IsUtf16BomLe(data_block)) {
        data.reserve(data_block.size());
        tools::ScanView(data_block.substr(2), LF_16, [&data](auto s) {
            auto disassembled = DisassembleString(s);
            if (const auto wide_string = tools::ToWideView(s); wide_string) {
                if (auto utf8 = wtools::ToUtf8(*wide_string); !utf8.empty()) {
                    data += utf8;
                    return;
                }
            }
            AppendDisassembled(data, disassembled);
        });
    } else {
        data.assign(data_block.begin(), data_block.end());
    }
    wtools::AddSafetyEndingNull(data);
    return data;
}

std::string PostProcessPluginData(const std::vector<char> &datablock,
                                  tools::UtfConversionMode mode) {
    auto data = ConvertUtfData(datablock, mode);
    if (!data.empty() && data.back() == 0) {
        data.pop_back();  // conditional convert adds 0
    }
    return data;
}
}  // namespace

std::string ConvertUtfData(const std::vector<char> &data_block,
                           tools::UtfConversionMode mode) {
    switch (mode) {
        case tools::UtfConversionMode::basic:
            return wtools::ConditionallyConvertFromUtf16(data_block);
        case tools::UtfConversionMode::repair_by_line:
            return ConvertWithRepair(tools::ToView(data_block));
    }
    // unreachable
    return {};
}

// LOOP:
// register
// wait some time
// unregister
// read data
// Max Timeout < 0 use default
std::vector<char> PluginEntry::getResultsSync(const std::wstring &id,
                                              int max_timeout) {
    const auto exec =
        cmd_line_.empty() ? ConstructCommandToExec(path()) : cmd_line_;
    if (exec.empty()) {
        XLOG::l(
            "Failed to start minibox sync '{}', can't find executables for the '{}'",
            wtools::ToUtf8(id), path().u8string());
        return {};
    }

    if (!minibox_.startEx(L"id", exec, TheMiniBox::StartMode::job, iu_)) {
        XLOG::l("Failed to start minibox sync '{}'", wtools::ToUtf8(id));
        return {};
    }

    const int tout =
        max_timeout < 0 ? timeout() : std::min(timeout(), max_timeout);

    registerProcess(minibox_.getProcessId());
    const auto success = minibox_.waitForEnd(std::chrono::seconds(tout));

    std::vector<char> accu;

    if (success) {
        minibox_.processResults([&](const std::wstring &cmd_line, uint32_t pid,
                                    uint32_t code,
                                    const std::vector<char> &datablock) {
            auto data =
                PostProcessPluginData(datablock, getUtfConversionMode());
            tools::AddVector(accu, data);
            storeData(pid, accu);
            if (cfg::LogPluginOutput()) {
                XLOG::t("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                        wtools::ToUtf8(cmd_line), pid, code, data.data());
            }
        });

    } else {
        // process was either stopped or failed(timeout)
        const auto failed = minibox_.isFailed();
        unregisterProcess();
        XLOG::d("Sync Plugin '{}' is {}", path(),
                failed ? "Failed" : "Stopped");
        if (failed) {
            failures_++;
        }
    }

    minibox_.clean();
    return accu;
}

void PluginEntry::setCmdLine(std::wstring_view name) { cmd_line_ = name; }

void PluginEntry::breakAsync() noexcept {
    XLOG::t("breakAsync {}", path());
    joinAndReleaseMainThread();
}

void PluginEntry::joinAndReleaseMainThread() noexcept {
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
    const auto text = fmt::format(
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
    const auto stop_time = std::chrono::steady_clock::now() + interval;
    const auto stopped =
        cv_stop_.wait_until(lk, stop_time, [this] { return stop_set_; });

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
            case StartMode::controller:
                proc_id_ = ar->goExecAsController(exec);
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
        const auto ready =
            checkProcessExit(pi.waiting_processes) ||  // process exit?
            srv::IsGlobalStopSignaled();               // agent is exiting?

        if (auto buf = wtools::ReadFromHandle(read_handle); !buf.empty()) {
            pi.added += buf.size();
            pi.blocks++;
            appendResult(read_handle, buf);
            grane = grane_short;  // using short time period to poll
        }

        if (ready) {
            LogProcessStatus(true, sw_.stop(), pi);
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
        LogProcessStatus(false, sw_.stop(), pi);

        process_->kill(true);
        return false;
    }

    // never here
}

bool TheMiniBox::waitForEndWindows(std::chrono::milliseconds timeout) {
    if (stop_set_) {
        return false;
    }
    ON_OUT_OF_SCOPE(readWhatLeft());

    auto *read_handle = getReadHandle();
    ProcInfo pi = {getProcessId(), wtools::ToUtf8(exec_), 0, 0};
    constexpr auto time_grane_windows{250ms};

    while (true) {
        const auto ready = checkProcessExit(pi.waiting_processes);
        HANDLE handles[2] = {read_handle, stop_event_};
        const auto ret = ::WaitForMultipleObjects(
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
            LogProcessStatus(true, sw_.stop(), pi);
            return true;
        }

        if (ret == WAIT_OBJECT_0) {
            ::Sleep(10);
            continue;
        }

        if (ret == WAIT_TIMEOUT && timeout > time_grane_windows) {
            timeout -= time_grane_windows;
            continue;
        }

        // here we will break always

        // check that we are breaking by timeout
        if (timeout < time_grane_windows) {
            failed_ = true;
        } else {
            // stopped outside
            XLOG::d("Process '{}' signaled to be stopped, left timeout [{}ms]!",
                    pi.proc_name, timeout.count());
        }

        // not normal situation
        LogProcessStatus(false, sw_.stop(), pi);
        process_->kill(true);
        return false;
    }

    // never here
}

namespace {
constexpr std::chrono::milliseconds time_grane{250};
}  // namespace

void TheMiniBox::readAndAppend(HANDLE read_handle,
                               std::chrono::milliseconds timeout) {
    const auto buf = wtools::ReadFromHandle(read_handle);
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

    auto *read_handle = getReadHandle();

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

void PluginEntry::threadCore(const std::wstring &id) {
    // pre entry
    // thread counters block
    XLOG::d.i("Async Thread for {} is to be started", wtools::ToUtf8(id));
    ++g_tread_count;
    ON_OUT_OF_SCOPE(--g_tread_count);
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
    const auto mode = GetStartMode(path());

    const auto exec =
        cmd_line_.empty() ? ConstructCommandToExec(path()) : cmd_line_;
    if (exec.empty()) {
        XLOG::l(
            "Failed to start minibox '{}', can't find executables for the '{}'",
            wtools::ToUtf8(id), path().u8string());
        return;
    }

    const auto is_detached = mode == TheMiniBox::StartMode::detached;
    while (true) {
        if (!minibox_.startEx(id, exec, mode, iu_)) {
            XLOG::l("Failed to start minibox thread {}", wtools::ToUtf8(id));
            break;
        }

        registerProcess(minibox_.getProcessId());
        std::vector<char> accu;

        const auto success =
            is_detached
                ? minibox_.waitForUpdater(std::chrono::seconds(timeout()))
                : minibox_.waitForEnd(std::chrono::seconds(timeout()));
        if (success) {
            // we have probably data, try to get and and store
            minibox_.processResults([&](const std::wstring &cmd_line,
                                        uint32_t pid, uint32_t code,
                                        const std::vector<char> &datablock) {
                auto data = wtools::ConditionallyConvertFromUtf16(datablock);
                tools::AddVector(accu, data);
                {
                    std::lock_guard l(data_lock_);
                    storeData(pid, accu);
                }
                if (cfg::LogPluginOutput())
                    XLOG::t(
                        "Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                        wtools::ToUtf8(cmd_line), pid, code, data.data());
            });
            break;
        }
        // process was either stopped or failed(timeout)
        const auto failed = minibox_.isFailed();
        unregisterProcess();
        XLOG::d("Async Plugin '{}' is {}", path(),
                failed ? "failed" : "stopped");
        if (!failed || is_detached) {
            // we do not retry:
            // - not failed processes, i.e. forces to stop from outside
            // - detached processes, i.e. agent updater
            break;
        }
        failures_++;
        if (isTooManyRetries()) {
            XLOG::d("Async Plugin '{}' has too many failures {}", path(),
                    failures_);

            std::lock_guard l(data_lock_);
            resetData();
            failures_ = 0;
            break;
        }
    }

    XLOG::d.t("Thread OFF: '{}'", path());
}

wtools::InternalUser PluginsExecutionUser2Iu(std::string_view user) {
    const auto table =
        tools::SplitStringExact(wtools::ConvertToUtf16(user), L" ", 2);
    if (table.empty()) {
        return {};
    }
    if (table.size() == 2) {
        return {table[0], table[1]};
    }

    return {table[0], L""};
}

tools::UtfConversionMode PluginEntry::getUtfConversionMode() const {
    // TODO(sk): add global flag
    return repair_invalid_utf_ ? tools::UtfConversionMode::repair_by_line
                               : tools::UtfConversionMode::basic;
}

/// try to build user from fields group and user
wtools::InternalUser PluginEntry::getInternalUser(
    wtools::InternalUsersDb *user_database) const {
    if (!group_.empty() && (user_database != nullptr)) {
        const auto iu =
            user_database->obtainUser(wtools::ConvertToUtf16(group_));
        XLOG::t("Entry '{}' uses user '{}' as group config", path(),
                wtools::ToUtf8(iu_.first));
        return iu;
    }

    if (user_.empty()) {
        return {};
    }

    const auto iu = PluginsExecutionUser2Iu(user_);
    XLOG::t("Entry '{}' uses user '{}' as direct config", path(),
            wtools::ToUtf8(iu_.first));
    return iu;
}

// if thread finished join old and start new thread again
// if thread NOT finished quit
void PluginEntry::restartAsyncThreadIfFinished(const std::wstring &id) {
    std::unique_lock lk(lock_);
    const auto start_thread = !thread_on_;
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
    auto t = std::make_unique<std::thread>(&PluginEntry::threadCore, this, id);
    lk.lock();
    main_thread_ = std::move(t);
    lk.unlock();
    XLOG::d.i("restarted thread for plugin '{}'", path());
}

std::vector<char> PluginEntry::getResultsAsync(bool start_process_now) {
    // check is valid parameters
    if (cacheAge() < cfg::kMinimumCacheAge && cacheAge() != 0) {
        XLOG::l("Plugin '{}' requested to be async, but has no valid cache age",
                path());
        return {};
    }

    // check data are ready and new enough
    bool data_ok = false;
    const std::chrono::seconds allowed_age(cacheAge());
    const auto data_age = getDataAge();
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
        if (start_process_now) {
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

std::optional<std::string> PluginEntry::startProcessName() {
    std::lock_guard l(data_lock_);
    if (getDataAge() <= std::chrono::seconds{cacheAge()}) {
        return {};
    }
    data_time_ = std::chrono::steady_clock::now();  // update time of start
    return wtools::ToUtf8(path().wstring());
}

void PluginEntry::restartIfRequired() {
    // check is valid parameters
    if (cacheAge() < cfg::kMinimumCacheAge) {
        XLOG::l(
            "Plugin '{}' requested to be async restarted, but has no valid cache age",
            path());
        return;
    }
    // check data are ready and new enough
    auto filename = startProcessName();
    if (!filename) {
        return;
    }
    XLOG::d.t("Starting '{}'", *filename);
    if (tools::RunDetachedCommand(*filename).has_value()) {
        XLOG::d.i("Starting '{}' OK!", *filename);
    } else {
        XLOG::l("Starting '{}' FAILED with error [{}]", *filename,
                ::GetLastError());
    }
}

/// Corrects retry to be reasonable by timeout and cache_age
void PluginEntry::correctRetry() {
    if (!async()) {
        return;
    }

    if (timeout_ > 0) {
        // add 1 to reserve time for start process
        auto max_retries = cache_age_ / (timeout_ + 1);
        retry_ = std::min(max_retries, retry_);
    } else {
        retry_ = 0;
    }
}

void PluginEntry::registerProcess(uint32_t Id) {
    process_id_ = Id;
    start_time_ = std::chrono::steady_clock::now();
}

// this is not normal situation
// as a rule only after timeout
void PluginEntry::unregisterProcess() noexcept { process_id_ = 0; }

// on reading box
// MUST BE CALLED INSIDE LOCK_GUARD!
void PluginEntry::storeData(uint32_t proc_id, const std::vector<char> &data) {
    if (proc_id != process_id_ || proc_id == 0) {
        XLOG::d("Invalid process {}, can't store data {} ", proc_id, path());
        return;
    }

    process_id_ = 0;
    const auto now = std::chrono::steady_clock::now();
    const auto diff =
        std::chrono::duration_cast<std::chrono::seconds>(now - start_time_)
            .count();
    if (diff > static_cast<int64_t>(timeout())) {
        XLOG::d("Process '{}' timeout in {} when set {}", path(), diff,
                timeout());
    } else if (data.empty()) {
        // plugin failed
        XLOG::d("Process '{}' has no data", path());
    }

    data_time_ = std::chrono::steady_clock::now();
    const auto legacy_time = ::time(nullptr);

    if (cacheAge() > 0) {
        data_.clear();
        const auto mode = exec_type_ == ExecType::local ? HackDataMode::line
                                                        : HackDataMode::header;
        auto patch_string = ConstructPatchString(legacy_time, cacheAge(), mode);
        HackDataWithCacheInfo(data_, data, patch_string, mode);
    } else {
        // "sync plugin" or async with 0 as cache age
        // or "failed to hack"
        data_ = data;
    }
    legacy_time_ = legacy_time;

    // Remove trailing zero's looks weird, but nulls
    // can be created in some cases by plugin and processing(ConvertTo)
    // But must be removed in output
    while (!data_.empty() && data_.back() == '\0') {
        data_.pop_back();
    }
}

void PluginEntry::resetData() {
    data_time_ = std::chrono::steady_clock::now();
    auto diff = std::chrono::duration_cast<std::chrono::seconds>(data_time_ -
                                                                 start_time_);
    XLOG::d.i("Process '{}' resets data after {} seconds", path(),
              diff.count());
    legacy_time_ = ::time(nullptr);
    data_.clear();
}

// remove what not present in the file vector
void FilterPluginMap(PluginMap &out_map, const PathVector &found_files) {
    std::vector<std::string> to_delete;
    if (found_files.empty()) {
        out_map.clear();
        return;
    }

    // check every entry for presence in the found files vector
    // absent entries are in to_delete
    for (const auto &path : out_map | std::views::keys) {
        bool exists = false;
        for (const auto &ff : found_files) {
            if (path == wtools::ToUtf8(ff.wstring())) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            to_delete.push_back(path);  // store path to be removed
        }
    }

    // second deletion phase - we can't delete
    // while iterating through container
    for (const auto &del : to_delete) {
        out_map.erase(del);
    }
}

// check_exists - false is only for testing, true for production
// plugin_map is mutable
void RemoveDuplicatedPlugins(PluginMap &plugin_map, bool check_exists) {
    std::unordered_set<std::string> filename_set;  // mk_smth.vbs, smth.bat, etc

    std::error_code ec;
    for (auto it = plugin_map.begin(); it != plugin_map.end();) {
        fs::path p = it->first;

        if (it->second.path().empty() || check_exists && !fs::exists(p, ec)) {
            it = plugin_map.erase(it);
            continue;
        }

        if (filename_set.insert(wtools::ToUtf8(p.filename().wstring()))
                .second) {
            ++it;
        } else {
            it = plugin_map.erase(it);
        }
    }
}

namespace provider::config {

bool IsRunAsync(const PluginEntry &plugin) noexcept {
    const auto run_async = plugin.async();

    if constexpr (g_async_plugin_without_cache_age_run_async) {
        return run_async;
    }

    if (run_async && plugin.cacheAge() == 0) {
        return config::g_async_plugin_without_cache_age_run_async;
    }

    return run_async;
}
}  // namespace provider::config

using DataBlock = std::vector<char>;
void StartSyncPlugins(PluginMap &plugins,
                      std::vector<std::future<DataBlock>> &results,
                      int timeout) {
    for (auto &plugin : plugins | std::views::values) {
        if (provider::config::IsRunAsync(plugin)) {
            continue;
        }
        XLOG::t("Executing '{}'", plugin.path());
        results.emplace_back(std::async(
            std::launch::async,
            [](PluginEntry *e, int /*timeout*/) {
                return e->getResultsSync(e->path().wstring());
            },
            &plugin, timeout));
    }
}

std::pair<std::vector<char>, int> RunSyncPlugins(PluginMap &plugins,
                                                 int timeout) {
    XLOG::d.t("To start [{}] sync plugins", plugins.size());

    std::vector<std::future<DataBlock>> results;
    StartSyncPlugins(plugins, results, timeout);

    DataBlock out;
    int delivered_count = 0;
    for (auto &r : results) {
        auto result = r.get();
        if (!result.empty()) {
            ++delivered_count;
            if (result.back() != '\n') {
                XLOG::d("Sync plugin doesn't add <CR> at the end of output");
                result.push_back('\n');
            }
            tools::AddVector(out, result);
        }
    }

    return {out, delivered_count};
}

void RunDetachedPlugins(const PluginMap & /*plugins_map*/,
                        int & /*start_count*/) {}

// To get data from async plugins with cache_age=0
void PickupAsync0data(int timeout, PluginMap &plugins, std::vector<char> &out,
                      std::vector<std::pair<bool, std::string>> &async_nul_s) {
    timeout = std::max(timeout, 10);
    if (timeout != 0) {
        XLOG::d.i(
            "Picking up [{}] async-0"
            "plugins with timeout [{}]",
            async_nul_s.size(), timeout);
    }

    size_t async_count = 0;
    for (int i = 0; i < timeout; i++) {
        for (auto &[started, name] : async_nul_s) {
            if (started) {
                continue;
            }

            const auto *e = GetEntrySafe(plugins, name);
            if (e != nullptr && !e->running()) {
                tools::AddVector(out, e->data());
                started = false;
                async_count++;
            }
        }
        if (async_count >= async_nul_s.size()) {
            break;
        }
        tools::sleep(1000);
    }
}

std::pair<std::vector<char>, int> RunAsyncPlugins(PluginMap &plugins,
                                                  bool start_immediately) {
    std::vector<char> result;

    int count = 0;
    for (auto &plugin : plugins | std::views::values) {
        if (!plugin.async() || !provider::config::IsRunAsync(plugin)) {
            continue;
        }
        auto data = plugin.getResultsAsync(start_immediately);
        if (!data.empty()) {
            ++count;
            if (data.back() != '\n') {
                XLOG::d("Async plugin doesn't add <CR> at the end of output");
                data.push_back('\n');
            }
        }
        tools::AddVector(result, data);
    }
    return {result, count};
}
}  // namespace cma

namespace cma {
constexpr bool enable_ps1_proxy{true};

std::wstring LocatePs1Proxy() {
    if constexpr (!enable_ps1_proxy) {
        return L"";
    }

    const auto path_to_configure_and_exec =
        fs::path{cfg::GetRootInstallDir()} / cfg::files::kConfigureAndExecPs1;
    std::error_code ec;
    return fs::exists(path_to_configure_and_exec, ec)
               ? fmt::format(L" \"{}\"", path_to_configure_and_exec.wstring())
               : L"";
}

std::wstring MakePowershellWrapper(const fs::path &script) noexcept {
    try {
        const auto powershell_exe = FindPowershellExe();
        auto proxy = LocatePs1Proxy();

        return powershell_exe +
               fmt::format(
                   L" -NoLogo -NoProfile -ExecutionPolicy Bypass -File{} \"{}\"",
                   proxy, script.wstring());
    } catch (const std::exception &e) {
        XLOG::l("Exception when finding powershell e:{}", e);
        return L"";
    }
}

}  // namespace cma
