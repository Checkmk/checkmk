
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/mrpe.h"

#include <filesystem>
#include <regex>
#include <string>
#include <string_view>
#include <tuple>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "fmt/format.h"
#include "glob_match.h"
#include "logger.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::provider {

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

    auto exe_name = tokens[1];  // Intentional copy
    if (exe_name.size() <= 2) {
        XLOG::l("Invalid file specification for '{}' in '{}' '{}'",
                cma::cfg::groups::kMrpe, yml_name, value);
        return;
    }

    std::string argv;
    for (size_t i = 2; i < tokens.size(); i++) argv += tokens[i] + " ";

    // remove last space
    if (argv.size()) argv.pop_back();
    auto p = cma::cfg::ReplacePredefinedMarkers(tokens[1]);
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

    auto end = std::remove_if(
        entries_.begin(),      // from
        entries_.end(),        // to
        [](MrpeEntry entry) {  // lambda to delete
            return !cma::tools::IsValidRegularFile(entry.full_path_name_);
        }  //
    );

    // actual remove
    entries_.erase(end, entries_.end());
}

void MrpeProvider::addParsedChecks() {
    for (const auto &check : checks_) {
        entries_.emplace_back("", check);
    }
}

std::pair<std::string, std::filesystem::path> parseIncludeEntry(
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
    potential_path = cma::cfg::ReplacePredefinedMarkers(potential_path);
    fs::path path = potential_path;  // last is path

    if (!cma::tools::IsValidRegularFile(path)) {
        XLOG::d(
            "File '{}' is not valid or missing for entry '{}' in config '{}'",
            path.u8string(), entry, yml_name);
        return {};
    }
    return {include_user, path};
}

void MrpeProvider::addParsedIncludes() {
    using namespace cma::tools;
    namespace fs = std::filesystem;

    auto yml_name = cma::cfg::GetPathOfLoadedConfigAsString();

    for (const auto &entry : includes_) {
        auto [user, path] = parseIncludeEntry(entry);

        if (path.empty()) continue;

        std::ifstream ifs(path);
        if (!ifs) {
            XLOG::d("File is bad for '{}' in '{}'", entry, yml_name);
            continue;
        }

        std::string line;
        for (unsigned lineno = 1; std::getline(ifs, line); ++lineno) {
            AllTrim(line);
            if (line.empty() || line[0] == '#' || line[0] == ';')
                continue;  // skip empty lines and comments

            // split up line at = sign
            auto tokens = SplitString(line, "=", 2);
            if (tokens.size() != 2) {
                XLOG::d("Invalid entry '{}' in '{}'", entry, yml_name);
                continue;
            }

            auto &var = tokens[0];
            auto &value = tokens[1];
            AllTrim(var);
            std::transform(var.cbegin(), var.cend(), var.begin(), tolower);

            if (var == "check") {
                AllTrim(value);
                entries_.emplace_back(user, value);
            } else {
                XLOG::t("Strange entry '{}' in '{}'", entry, yml_name);
            }
        }
    }
}

bool MrpeProvider::parseAndLoadEntry(const std::string &entry) {
    auto str = entry;
    auto table = cma::tools::SplitString(str, "=");
    if (table.size() != 2) {
        XLOG::t("Strange entry {} in {}", str,
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

        auto value = str.substr(len + pos, std::string::npos);
        cma::tools::AllTrim(value);
        if (!value.empty()) {
            includes_.emplace_back(value);
            return true;
        }

        XLOG::d("Strange include entry type '{}' '{}' ", type, str);
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

    XLOG::d("Strange check entry type '{}' '{}'", type, str);
    return false;
}

void MrpeProvider::parseConfig() {
    using namespace cma::cfg;
    // reset all
    entries_.clear();
    checks_.clear();
    includes_.clear();

    timeout_ = GetVal(groups::kMrpe, vars::kTimeout, 10);
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

void MrpeProvider::updateSectionStatus() {
    using namespace std::chrono;
    accu_.clear();
    for (const auto &entry : entries_) {
        auto hdr = fmt::format("({}) {} ", entry.exe_name_, entry.description_);
        XLOG::t("{} run", hdr);

        TheMiniBox minibox;
        auto started =
            minibox.startBlind(entry.command_line_, entry.run_as_user_);
        if (!started) {
            XLOG::l("Failed to start minibox sync {}", entry.command_line_);
            continue;
        }

        auto proc_id = minibox.getProcessId();
        auto success = minibox.waitForEnd(seconds(timeout_), true);

        if (success) {
            minibox.processResults([&](const std::wstring CmdLine, uint32_t Pid,
                                       uint32_t Code,
                                       const std::vector<char> &Data) {
                auto data = wtools::ConditionallyConvertFromUTF16(Data);
                cma::tools::AllTrim(data);
                // replace and fix output
                FixCrCnForMrpe(data);
                data += "\n";

                if (cma::cfg::LogMrpeOutput())
                    XLOG::t(
                        "Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                        wtools::ConvertToUTF8(CmdLine), Pid, Code, data.data());
                hdr += std::to_string(Code) + " ";
                accu_ += hdr;
                accu_ += data;
            });

        } else {
            //
            XLOG::d("Wait on Timeout or Broken {}", entry.command_line_);
        }

        minibox.clean();
    }
}

std::string MrpeProvider::makeBody() {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering");

    return accu_;
}

}  // namespace cma::provider
