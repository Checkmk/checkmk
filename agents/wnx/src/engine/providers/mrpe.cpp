
#include "stdafx.h"

#include "providers/mrpe.h"

#include <execution>
#include <filesystem>
#include <fstream>
#include <regex>
#include <string>
#include <tuple>

#include "common/wtools.h"
#include "tools/_raii.h"
#include "wnx/cfg.h"
#include "wnx/cma_core.h"
#include "wnx/glob_match.h"
#include "wnx/logger.h"

namespace fs = std::filesystem;
namespace rs = std::ranges;

namespace cma::provider {

std::vector<std::string> TokenizeString(const std::string &val, int sub_match) {
    // actual regex is ("([^"]+)"|'([^']+)'|[^" \t]+)
    // verified https://regex101.com/r/p89I0B/1
    // three groups "***" or '***' or
    static const std::regex regex_possibly_quoted{
        "(\"([^\"]+)\"|'([^']+)'|[^\" \\t]+)"};

    // below a bit of magic
    // Basic approach is:
    // 1. std::sregex_token_iterator it(Val.begin(), Val.end(), Regex, 1);
    // 2. std::sregex_token_iterator reg_end; // <--end
    // 3. for (; it != reg_end; ++it) std::cout << it->str() << std::endl;
    // we are using a bit more shortened syntax just to show that
    // smart people works in MK.
    return {std::sregex_token_iterator{val.cbegin(), val.cend(),
                                       regex_possibly_quoted, sub_match},
            std::sregex_token_iterator{}};
}

namespace {
std::optional<std::string> ExtractInterval(std::string_view text) {
    auto tokens = tools::SplitString(std::string(text), "=");
    if (tokens.size() == 2) {
        if (tokens[0] != "(interval") {
            XLOG::l(
                "mrpe entry malformed: Unknown directive '{}', expected '(interval=SECONDS)'",
                text);
            return {};
        }
        return tokens[1];
    }

    tokens = tools::SplitString(std::string(text), ":");
    if (tokens.size() == 2) {
        XLOG::l("Parsing legacy caching directive '{}', ignoring ADD_AGE flag.",
                text);

        return tokens[0].substr(1);
    }

    return {};
}

std::optional<int> ParseCacheAgeToken(std::string_view text) {
    if (text.size() < 3 || text[0] != '(' || text[text.size() - 1] != ')') {
        // Seems to be no interval spec, hence no caching.
        return {};
    }

    if (auto interval_token = ExtractInterval(text)) {
        try {
            return std::stoi(*interval_token);
        } catch (std::invalid_argument const &e) {
            XLOG::l("mrpe entry malformed '{}'", e.what());
        } catch (std::out_of_range const &e) {
            XLOG::l("mrpe entry malformed '{}'", e.what());
        }
    }

    return {};
}

std::string BuildValidPath(const std::string &path) {
    return cfg::ReplacePredefinedMarkers(tools::RemoveQuotes(path));
}
}  // namespace

void MrpeEntry::loadFromString(const std::string &value) {
    full_path_name_.clear();
    auto tokens = TokenizeString(value,  // string to tokenize
                                 1);     // every passing will be added

    auto yml_name = cfg::GetPathOfLoadedConfigAsString();
    if (tokens.size() < 2) {
        XLOG::l("Invalid command specification for '{}' in '{}' '{}'",
                cfg::groups::kMrpe, yml_name, value);
        return;
    }

    int position_exe = 1;

    caching_interval_ = ParseCacheAgeToken(tokens[1]);

    if (caching_interval_) {
        position_exe++;
    }

    auto exe_name = tokens[position_exe];  // Intentional copy
    if (exe_name.size() <= 2) {
        XLOG::l("Invalid file specification for '{}' in '{}' '{}'",
                cfg::groups::kMrpe, yml_name, value);
        return;
    }

    std::string argv;
    for (size_t i = position_exe + 1; i < tokens.size(); i++) {
        argv += tokens[i] + " ";
    }

    // remove last space
    if (!argv.empty()) {
        argv.pop_back();
    }

    fs::path exe_full_path{BuildValidPath(tokens[position_exe])};
    if (exe_full_path.is_relative()) {
        exe_full_path = cfg::GetUserDir() / exe_full_path;
    }

    full_path_name_ = wtools::ToUtf8(exe_full_path.wstring());

    exe_name_ = wtools::ToUtf8(exe_full_path.filename().wstring());

    command_line_ = full_path_name_;
    if (!argv.empty()) {
        command_line_ += " " + argv;
    }

    description_ = tokens[0];
    description_ = tools::RemoveQuotes(description_);
}

void MrpeProvider::addParsedConfig() {
    entries_.clear();
    addParsedChecks();
    addParsedIncludes();

    if constexpr (kMrpeRemoveAbsentFiles) {
        auto [a, b] = rs::remove_if(entries_, [](const MrpeEntry &entry) {
            auto ok = tools::IsValidRegularFile(entry.full_path_name_);
            if (!ok) {
                XLOG::d("The file '{}' is no valid", entry.full_path_name_);
            }
            return !ok;
        });
        entries_.erase(a, b);
    }
}

void MrpeProvider::addParsedChecks() {
    for (const auto &check : checks_) {
        entries_.emplace_back("", check);
    }
}

std::pair<std::string, fs::path> ParseIncludeEntry(const std::string &entry) {
    auto table = tools::SplitString(entry, "=", 2);
    auto yml_name = cfg::GetPathOfLoadedConfigAsString();

    if (table.size() != 2) {
        XLOG::d("Invalid entry '{}' in '{}'", entry, yml_name);
        return {};
    }

    for (auto &e : table) {
        tools::AllTrim(e);
    }

    auto include_user = table[0];

    fs::path path{BuildValidPath(table[table.size() - 1])};
    if (path.is_relative()) {
        path = cfg::GetUserDir() / path;
    }

    return {include_user, path};
}

void AddCfgFileToEntries(const std::string &user,
                         const std::filesystem::path &path,
                         std::vector<MrpeEntry> &entries) {
    std::ifstream ifs(path);
    if (!ifs) {
        XLOG::d("mrpe: File is bad '{}'", path);
        return;
    }

    std::string line;
    for (unsigned lineno = 1; std::getline(ifs, line); ++lineno) {
        tools::AllTrim(line);
        if (line.empty() || line[0] == '#' || line[0] == ';')
            continue;  // skip empty lines and comments

        // split up line at = sign
        auto tokens = tools::SplitString(line, "=", 2);
        if (tokens.size() != 2) {
            XLOG::d("mrpe: Invalid line '{}' in '{}:{}'", line, path, lineno);
            continue;
        }

        auto &var = tokens.at(0);
        auto &value = tokens.at(1);
        tools::AllTrim(var);
        tools::StringLower(var);

        if (var == "check") {
            tools::AllTrim(value);
            entries.emplace_back(user, value);
        } else {
            XLOG::d("mrpe: Strange entry '{}' in '{}:{}'", line, path, lineno);
        }
    }
}

void MrpeProvider::addParsedIncludes() {
    for (const auto &entry : includes_) {
        const auto [user, path] = ParseIncludeEntry(entry);
        if (path.empty()) {
            continue;
        }
        if (!tools::IsValidRegularFile(path)) {
            XLOG::d("File '{}' is not valid or missing for entry '{}'",
                    path.u8string(), entry);
            continue;
        }
        AddCfgFileToEntries(user, path, entries_);
    }
}

bool MrpeProvider::parseAndLoadEntry(const std::string &entry) {
    auto table = tools::SplitString(entry, "=", 1);

    // include entry determined when type is 'include' the type
    auto type = table.at(0);
    rs::transform(type, type.begin(), tolower);
    // include user = file   <-- src
    //        "user = file"  <-- value
    const auto pos = type.find("include");
    const auto len = ::strlen("include");
    if (pos != std::string::npos &&              // found
        (type[len] == 0 || type[len] == ' ')) {  // include has end

        auto value = entry.substr(len + pos, std::string::npos);
        tools::AllTrim(value);
        if (!value.empty()) {
            includes_.emplace_back(value);
            return true;
        }

        XLOG::d("Strange include entry type '{}' '{}' ", type, entry);
        return false;
    }

    // check entry determined when type is 'check'
    tools::AllTrim(type);
    rs::transform(type, type.begin(), tolower);
    if (type == "check") {
        // check = anything   <-- src
        //        "anything"  <-- value
        tools::AllTrim(table[1]);
        auto potential_path = cfg::ReplacePredefinedMarkers(table[1]);
        checks_.emplace_back(potential_path);
        return true;
    }

    XLOG::d("Strange check entry type '{}' '{}'", type, entry);
    return false;
}

void MrpeProvider::parseConfig() {
    // reset all
    entries_.clear();
    checks_.clear();
    includes_.clear();

    const auto strings =
        cfg::GetArray<std::string>(cfg::groups::kMrpe, cfg::vars::kMrpeConfig);

    if (strings.empty()) {
        XLOG::t("nothing to exec in the mrpe");
        return;
    }

    for (auto &str : strings) {
        parseAndLoadEntry(str);
    }
}

void MrpeProvider::loadTimeout() {
    const auto mrpe_timeout = cfg::GetVal(
        cfg::groups::kMrpe, cfg::vars::kTimeout, cfg::defaults::kMrpeTimeout);
    setTimeout(std::max(1U, mrpe_timeout));
}

void MrpeProvider::loadConfig() {
    loadTimeout();
    parseConfig();
    addParsedConfig();
}

void FixCrCnForMrpe(std::string &str) {
    rs::transform(str, str.begin(), [](char ch) {
        if (ch == '\n') {
            return '\1';
        }
        if (ch == '\r') {
            return ' ';
        }

        return ch;
    });
}

std::string ExecMrpeEntry(const MrpeEntry &entry,
                          std::chrono::milliseconds timeout) {
    auto result = fmt::format("({}) {} ", entry.exe_name_, entry.description_);
    XLOG::d.i("Run mrpe entry '{}'", result);

    TheMiniBox minibox;
    if (!minibox.startBlind(entry.command_line_, entry.run_as_user_)) {
        XLOG::d("Failed to start minibox sync {}", entry.command_line_);

        // string is form the legacy agent
        return result + "3 Unable to execute - plugin may be missing.";
    }

    auto success = minibox.waitForEnd(timeout);
    ON_OUT_OF_SCOPE(minibox.clean());
    if (!success) {
        XLOG::d("Minibox failed on Timeout or just Broken '{}'",
                entry.command_line_);
        return {};
    }

    minibox.processResults([&result](const std::wstring &cmd_line, uint32_t pid,
                                     uint32_t error_code,
                                     const std::vector<char> &data_block) {
        auto data = wtools::ConditionallyConvertFromUtf16(data_block);
        tools::AllTrim(data);

        // mrpe output must be patched in a bit strange way
        FixCrCnForMrpe(data);

        if (cfg::LogMrpeOutput()) {
            XLOG::t("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                    wtools::ToUtf8(cmd_line), pid, error_code, data.data());
        }

        result += std::to_string(error_code) + " " + data;
    });
    return result;
}

std::string MrpeEntryResult(const MrpeEntry &entry, MrpeCache &cache,
                            std::chrono::milliseconds timeout) {
    if (!entry.caching_interval_) {
        return ExecMrpeEntry(entry, timeout);
    }

    const auto &[cached_result, cached_state] =
        cache.getLineData(entry.description_, *entry.caching_interval_);

    switch (cached_state) {
        case MrpeCache::LineState::ready: {
            return cached_result;
        }
        case MrpeCache::LineState::absent: {
            cache.createLine(entry.description_);
        }
            [[fallthrough]];
        case MrpeCache::LineState::old: {
            auto result = std::format(
                "cached({},{}) {}", cma::tools::SecondsSinceEpoch(),
                *entry.caching_interval_, ExecMrpeEntry(entry, timeout));
            cache.updateLine(entry.description_, result);
            return result;
        }
    }
    // unreachable
    return {};
}

std::string MrpeProvider::makeBody() {
    std::string out;
    auto parallel = cfg::GetVal(cfg::groups::kMrpe, cfg::vars::kMrpeParallel,
                                kParallelMrpe);
    if (parallel) {
        std::mutex lock;
        std::for_each(std::execution::par_unseq, entries_.begin(),
                      entries_.end(), [&out, &lock, this](auto &&entry) {
                          auto ret = MrpeEntryResult(
                              entry, cache_, std::chrono::seconds(timeout()));
                          std::lock_guard lk(lock);
                          out += ret + "\n";
                      });
    } else
        for (const auto &entry : entries_) {
            out += MrpeEntryResult(entry, cache_,
                                   std::chrono::seconds(timeout())) +
                   "\n";
        }

    return out;
}

void MrpeCache::createLine(std::string_view key) {
    try {
        cache_.insert_or_assign(std::string{key}, Line{});
    } catch (const std::exception &e) {
        XLOG::l("exception '{}' in mrpe cache", e.what());
    }
}

bool MrpeCache::updateLine(std::string_view key, std::string_view data) {
    try {
        auto k = std::string(key);
        if (!cache_.contains(k)) {
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

std::tuple<std::string, MrpeCache::LineState> MrpeCache::getLineData(
    std::string_view key, int max_age) {
    try {
        auto k = std::string(key);
        auto it = cache_.find(k);
        if (it == cache_.end()) {
            return {"", LineState::absent};
        }

        auto &line = it->second;

        if (line.data.empty()) {
            return {"", LineState::old};
        }

        auto time_pos = std::chrono::steady_clock::now();
        auto diff = duration_cast<std::chrono::seconds>(time_pos - line.tp);
        auto status =
            diff.count() > max_age ? LineState::old : LineState::ready;

        return {line.data, status};
    } catch (const std::exception &e) {
        XLOG::l("exception '{}' in mrpe update cache", e.what());
    }

    return {"", LineState::absent};
}

}  // namespace cma::provider
