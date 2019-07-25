
// provides basic api to start and stop service

// Code and logic mirrors functionality of LA

#pragma once
#ifndef mrpe_h__
#define mrpe_h__

#include <filesystem>
#include <regex>
#include <string>
#include <string_view>

#include "Logger.h"
#include "cma_core.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

// actual regex is ("([^"]+)"|'([^']+)'|[^" \t]+)
// verified https://regex101.com/r/p89I0B/1
// three groups "***" or '***' or
const std::regex RegexPossiblyQuoted{"(\"([^\"]+)\"|'([^']+)'|[^\" \\t]+)"};

inline std::vector<std::string> TokenizeString(const std::string &val,
                                               const std::regex &regex_val,
                                               int sub_match) {
    // below a bit of magic
    // Basic approach is:
    // 1. std::sregex_token_iterator it(Val.begin(), Val.end(), Regex, 1);
    // 2. std::sregex_token_iterator reg_end; // <--end
    // 3. for (; it != reg_end; ++it) std::cout << it->str() << std::endl;
    // we are using a bit more shortened syntax just to show that
    // smart people works in MK.
    return {std::sregex_token_iterator{val.cbegin(), val.cend(), regex_val,
                                       sub_match},
            std::sregex_token_iterator{}};
}

struct MrpeEntry {
    MrpeEntry(const std::string &run_as_user,  // only from cfg
              const std::string &cmd_line,     // parsed
              const std::string &exe_name,     // parsed
              const std::string &description)
        : run_as_user_(run_as_user)
        , command_line_(cmd_line)
        , exe_name_(exe_name)
        , description_(description) {}

    MrpeEntry(const std::string &run_as_user,  // only from cfg
              const std::string &value)
        : run_as_user_(run_as_user) {
        loadFromString(value);
    }

    void loadFromString(const std::string &Value);
    std::string run_as_user_;
    std::string command_line_;
    std::string exe_name_;
    std::string description_;
    std::string full_path_name_;
};

// mrpe:
class MrpeProvider : public Asynchronous {
public:
    MrpeProvider() : Asynchronous(cma::section::kMrpe) {}

    MrpeProvider(const std::string_view &name, char separator)
        : Asynchronous(name, separator) {}

    virtual void loadConfig();

    virtual void updateSectionStatus();

    const auto entries() const noexcept { return entries_; }
    const auto &includes() const noexcept { return includes_; }
    const auto &checks() const noexcept { return checks_; }

protected:
    std::string makeBody() override;

    // sub API
    void parseConfig();
    void addParsedConfig();  // includes_ and checks_ -> entries_

    // internal
    void addParsedChecks();    // checks_ -> entries_
    void addParsedIncludes();  // includes_ -> entries_
    bool parseAndLoadEntry(const std::string &Entry);

    std::vector<MrpeEntry> entries_;

    std::vector<std::string> checks_;    // "check = ...."
    std::vector<std::string> includes_;  // "include = ......"

    std::string accu_;  // filled by updateSectionStatus

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class SectionProviderOhm;
    FRIEND_TEST(SectionProviderMrpe, ConfigLoad);
    FRIEND_TEST(SectionProviderMrpe, Construction);
    FRIEND_TEST(SectionProviderMrpe, Run);
#endif
};
std::pair<std::string, std::filesystem::path> parseIncludeEntry(
    const std::string &entry);

void FixCrCnForMrpe(std::string &str);

}  // namespace cma::provider

#endif  // mrpe_h__
