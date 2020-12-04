
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/mrpe.h"

#include <fmt/format.h>

#include <execution>
#include <filesystem>
#include <regex>
#include <string>
#include <string_view>
#include <tuple>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "glob_match.h"
#include "logger.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::provider {

static std::optional<std::tuple<int, bool>> ParseCacheAgeToken(
    std::string_view text) {
    if (text.size() < 3) return {};

    if (text[0] != '(' || text[text.size() - 1] != ')') return {};

    auto tokens = cma::tools::SplitString(std::string(text), ":");
    if (tokens.size() != 2) return {};

    auto add_age = tokens[1] == "yes)";

    try {
        auto cache_age = std::stoi(tokens[0].c_str() + 1);

        return {{cache_age, add_age}};

    } catch (std::invalid_argument const &e) {
        XLOG::l("mrpe entry malformed '{}'", e.what());
    } catch (std::out_of_range const &e) {
        XLOG::l("mrpe entry malformed '{}'", e.what());
    }

    return {};
}

void MrpeEntry::loadFromString(const std::string &value) {
    full_path_name_ = "";
    namespace fs = std::filesystem;
    auto tokens = TokenizeString(value,  // string to tokenize
                                 RegexPossiblyQuoted,
                                 1);  // every passing will be added

    auto yml_name = cma::cfg::GetPathOfLoadedConfigAsString();
    if (tokens.size() < 2) {
        XLOG::l("Invalid command specification for '{}' in '{}' '{}'",
                cma::cfg::groups::kMrpe, yml_name, value);
        return;
    }

    int position_exe = 1;

    auto optional_cache_data = ParseCacheAgeToken(tokens[1]);

    if (optional_cache_data.has_value()) {
        position_exe++;
        std::tie(cache_max_age_, add_age_) = *optional_cache_data;
    }

    auto exe_name = tokens[position_exe];  // Intentional copy
    if (exe_name.size() <= 2) {
        XLOG::l("Invalid file specification for '{}' in '{}' '{}'",
                cma::cfg::groups::kMrpe, yml_name, value);
        return;
    }

    std::string argv;
    for (size_t i = position_exe + 1; i < tokens.size(); i++)
        argv += tokens[i] + " ";

    // remove last space
    if (!argv.empty()) argv.pop_back();
    auto p = cma::cfg::ReplacePredefinedMarkers(tokens[position_exe]);
    p = cma::tools::RemoveQuotes(p);
    fs::path exe_full_path = p;
    if (exe_full_path.is_relative()) {
        exe_full_path = cma::cfg::GetUserDir() / exe_full_path;
    }

    full_path_name_ = exe_full_path.u8string();

    exe_name_ = exe_full_path.filename().u8string();

    command_line_ = full_path_name_;
    if (!argv.empty()) command_line_ += " " + argv;

    description_ = tokens[0];
    description_ = cma::tools::RemoveQuotes(description_);
}

void MrpeProvider::addParsedConfig() {
    entries_.clear();
    addParsedChecks();
    addParsedIncludes();

    if constexpr (kMrpeRemoveAbsentFiles) {
        auto end = std::remove_if(
            entries_.begin(),             // from
            entries_.end(),               // to
            [](const MrpeEntry &entry) {  // lambda to delete
                auto ok = cma::tools::IsValidRegularFile(entry.full_path_name_);
                if (!ok) {
                    XLOG::d("The file '{}' is no valid", entry.full_path_name_);
                }
                return !ok;
            }  //
        );

        // actual remove
        entries_.erase(end, entries_.end());
    }
}

void MrpeProvider::addParsedChecks() {
    for (const auto &check : checks_) {
        entries_.emplace_back("", check);
    }
}

std::pair<std::string, std::filesystem::path> ParseIncludeEntry(
    const std::string &entry) {
    using namespace cma::tools;
    namespace fs = std::filesystem;

    auto table = SplitString(entry, "=", 2);
    auto yml_name = cma::cfg::GetPathOfLoadedConfigAsString();

    if (table.size() != 2) {
        XLOG::d("Invalid entry '{}' in '{}'", entry, yml_name);
        return {};
    }

    for (auto &e : table) AllTrim(e);

    auto include_user = table[0];
    auto potential_path = table[table.size() - 1];
    potential_path = cma::tools::RemoveQuotes(potential_path);
    potential_path = cma::cfg::ReplacePredefinedMarkers(potential_path);
    fs::path path = potential_path;  // last is path
    if (path.is_relative()) path = cma::cfg::GetUserDir() / path;

    return {include_user, path};
}

void AddCfgFileToEntries(const std::string &user, std::filesystem::path &path,
                         std::vector<MrpeEntry> &entries) {
    std::ifstream ifs(path);
    if (!ifs) {
        XLOG::d("mrpe: File is bad '{}'", path);
        return;
    }

    std::string line;
    for (unsigned lineno = 1; std::getline(ifs, line); ++lineno) {
        cma::tools::AllTrim(line);
        if (line.empty() || line[0] == '#' || line[0] == ';')
            continue;  // skip empty lines and comments

        // split up line at = sign
        auto tokens = cma::tools::SplitString(line, "=", 2);
        if (tokens.size() != 2) {
            XLOG::d("mrpe: Invalid line '{}' in '{}:{}'", line, path, lineno);
            continue;
        }

        auto &var = tokens[0];
        auto &value = tokens[1];
        cma::tools::AllTrim(var);
        cma::tools::StringLower(var);

        if (var == "check") {
            cma::tools::AllTrim(value);
            entries.emplace_back(user, value);
        } else {
            XLOG::d("mrpe: Strange entry '{}' in '{}:{}'", line, path, lineno);
        }
    }
}

void MrpeProvider::addParsedIncludes() {
    using namespace cma::tools;

    for (const auto &entry : includes_) {
        auto [user, path] = ParseIncludeEntry(entry);

        if (path.empty()) continue;

        if (!cma::tools::IsValidRegularFile(path)) {
            XLOG::d("File '{}' is not valid or missing for entry '{}'",
                    path.u8string(), entry);
            continue;
        }

        AddCfgFileToEntries(user, path, entries_);
    }
}

bool MrpeProvider::parseAndLoadEntry(const std::string &entry) {
    auto table = cma::tools::SplitString(entry, "=");
    if (table.size() != 2) {
        XLOG::t("Strange entry {} in {}", entry,
                cma::cfg::GetPathOfLoadedConfigAsString());
        return false;
    }

    // include entry determined when type is 'include'
    // the type
    auto type = table[0];
    std::transform(type.cbegin(), type.cend(), type.begin(), tolower);
    // include user = file   <-- src
    //        "user = file"  <-- value
    auto pos = type.find("include", 0);
    auto len = ::strlen("include");
    if (pos != std::string::npos &&              // found
        (type[len] == 0 || type[len] == ' ')) {  // include has end

        auto value = entry.substr(len + pos, std::string::npos);
        cma::tools::AllTrim(value);
        if (!value.empty()) {
            includes_.emplace_back(value);
            return true;
        }

        XLOG::d("Strange include entry type '{}' '{}' ", type, entry);
        return false;
    }

    // check entry determined when type is 'check'
    cma::tools::AllTrim(type);
    std::transform(type.cbegin(), type.cend(), type.begin(), tolower);
    if (type == "check") {
        // check = anything   <-- src
        //        "anything"  <-- value
        cma::tools::AllTrim(table[1]);
        auto potential_path = cma::cfg::ReplacePredefinedMarkers(table[1]);
        checks_.emplace_back(potential_path);
        return true;
    }

    XLOG::d("Strange check entry type '{}' '{}'", type, entry);
    return false;
}

void MrpeProvider::parseConfig() {
    using namespace cma::cfg;
    // reset all
    entries_.clear();
    checks_.clear();
    includes_.clear();

    timeout_ = GetVal(groups::kMrpe, vars::kTimeout, defaults::kMrpeTimeout);
    if (timeout_ < 1) timeout_ = 1;

    auto strings = GetArray<std::string>(groups::kMrpe, vars::kMrpeConfig);
    if (strings.empty()) {
        XLOG::t("nothing to exec in the mrpe");
        return;
    }

    for (auto &str : strings) {
        parseAndLoadEntry(str);
    }
}
// standard loader
// include and check entries loaded into two member variables

void MrpeProvider::loadConfig() {
    XLOG::t(XLOG_FUNC + " entering");
    parseConfig();
    addParsedConfig();
}

void FixCrCnForMrpe(std::string &str) {
    std::transform(str.cbegin(), str.cend(), str.begin(), [](char ch) {
        if (ch == '\n') return '\1';
        if (ch == '\r') return ' ';

        return ch;
    });
}

std::string ExecMrpeEntry(const MrpeEntry &entry,
                          std::chrono::milliseconds timeout) {
    using namespace std::chrono;
    auto hdr = fmt::format("({}) {} ", entry.exe_name_, entry.description_);
    XLOG::t("{} run", hdr);

    TheMiniBox minibox;
    auto started = minibox.startBlind(entry.command_line_, entry.run_as_user_);
    if (!started) {
        XLOG::l("Failed to start minibox sync {}", entry.command_line_);
        // result is copy-pasted from the legacy agent
        return hdr + "3 Unable to execute - plugin may be missing.\n";
    }

    auto success = minibox.waitForEnd(timeout);
    ON_OUT_OF_SCOPE(minibox.clean());
    if (!success) {
        //
        XLOG::d("Wait on Timeout or Broken '{}'", entry.command_line_);
        return {};
    }

    std::string accu;
    minibox.processResults([&](const std::wstring &CmdLine, uint32_t Pid,
                               uint32_t Code, const std::vector<char> &Data) {
        auto data = wtools::ConditionallyConvertFromUTF16(Data);
        cma::tools::AllTrim(data);
        // replace and fix output
        FixCrCnForMrpe(data);
        data += "\n";

        if (cma::cfg::LogMrpeOutput())
            XLOG::t("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                    wtools::ConvertToUTF8(CmdLine), Pid, Code, data.data());
        hdr += std::to_string(Code) + " ";
        accu = hdr + data;
    });
    return accu;
}

void MrpeProvider::updateSectionStatus() {}

std::string MrpeProvider::makeBody() {
    using namespace cma::cfg;
    using namespace std::chrono;
    XLOG::t(XLOG_FUNC + " entering");

    std::string out;
    std::mutex lock;
    auto parallel = GetVal(groups::kMrpe, vars::kMrpeParallel, kParallelMrpe);
    if (parallel) {
        std::for_each(std::execution::par_unseq, entries_.begin(),
                      entries_.end(), [&out, &lock, this](auto &&entry) {
                          auto ret = ExecMrpeEntry(entry, seconds(timeout_));
                          std::lock_guard lk(lock);
                          out += ret;
                      });
    } else
        for (const auto &entry : entries_) {
            out += ExecMrpeEntry(entry, seconds(timeout_));
        }

    return out;
}

void MrpeCache::createLine(std::string_view key, int max_age,
                           bool add_age) noexcept {
    try {
        Line l;
        l.add_age = add_age;
        l.max_age = max_age;
        cache_[std::string(key)] = l;
    } catch (const std::exception &e) {
        XLOG::l("exception '{}' in mrpe cache", e.what());
    }
}

bool MrpeCache::updateLine(std::string_view key,
                           std::string_view data) noexcept {
    try {
        auto k = std::string(key);
        if (cache_.find(k) == cache_.end()) {
            XLOG::d("Suspicious attempt to cache unknown mrpe line '{}'", k);
            return false;
        }

        cache_[k].data = data;
        cache_[k].tp = std::chrono::steady_clock::now();
        return true;
    } catch (const std::exception &e) {
        XLOG::l("exception '{}' in mrpe update cache", e.what());
    }

    return false;
}

// returns true if erased
bool MrpeCache::eraseLine(std::string_view key) noexcept {
    try {
        auto k = std::string(key);
        if (cache_.find(k) == cache_.end()) return false;
        cache_.erase(k);
        return true;
    } catch (const std::exception &e) {
        XLOG::l("exception '{}' in mrpe update cache", e.what());
    }

    return false;
}

std::tuple<std::string, MrpeCache::LineState> MrpeCache::getLineData(
    std::string_view key) noexcept {
    using namespace std::chrono;
    try {
        auto k = std::string(key);
        auto it = cache_.find(k);
        if (it == cache_.end()) return {"", LineState::absent};

        auto &line = it->second;

        if (line.data.empty()) return {"", LineState::old};

        auto time_pos = steady_clock::now();

        auto diff = duration_cast<seconds>(time_pos - line.tp);

        auto result = line.data;
        if (line.add_age)
            result += fmt::format(" ({};{})", diff.count(), line.max_age);

        auto status =
            diff.count() > line.max_age ? LineState::old : LineState::ready;

        return {result, status};
    } catch (const std::exception &e) {
        XLOG::l("exception '{}' in mrpe update cache", e.what());
    }

    return {"", LineState::absent};
    ;
}

}  // namespace cma::provider
