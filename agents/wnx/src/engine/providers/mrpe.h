
// provides basic api to start and stop service

// Code and logic mirrors functionality of LA

#pragma once
#ifndef mrpe_h__
#define mrpe_h__

#include <filesystem>
#include <regex>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "section_header.h"

#include "Logger.h"

#include "providers/internal.h"

namespace cma::provider {

// actual regex is ("([^"]+)"|'([^']+)'|[^" \t]+)
// verified https://regex101.com/r/p89I0B/1
// three groups "***" or '***' or
const std::regex RegexPossiblyQuoted{"(\"([^\"]+)\"|'([^']+)'|[^\" \\t]+)"};

inline std::vector<std::string> TokenizeString(const std::string &Val,
                                               const std::regex &Regex,
                                               int SubMatch) {
    // below a bit of magic
    // Basic approach is:
    // 1. std::sregex_token_iterator it(Val.begin(), Val.end(), Regex, 1);
    // 2. std::sregex_token_iterator reg_end; // <--end
    // 3. for (; it != reg_end; ++it) std::cout << it->str() << std::endl;
    // we are using a bit more shortened syntax just to show that
    // smart people works in MK.
    return {
        std::sregex_token_iterator{Val.cbegin(), Val.cend(), Regex, SubMatch},
        std::sregex_token_iterator{}};
}

inline void removeQuotes(std::string &Value) {
    if (Value.size() < 2) return;
    if (Value.back() == '\'' || Value.back() == '\"') Value.pop_back();
    if (Value[0] == '\'' || Value[0] == '\"')
        Value = Value.substr(1, Value.size() - 1);
}

struct MrpeEntry {
    MrpeEntry(const std::string &RunAsUser,    // only from cfg
              const std::string &CommandLine,  // parsed
              const std::string &ExeName,      // parsed
              const std::string &Description)
        : run_as_user_(RunAsUser)
        , command_line_(CommandLine)
        , exe_name_(ExeName)
        , description_(Description) {}

    MrpeEntry(const std::string &RunAsUser,  // only from cfg
              const std::string &Value)
        : run_as_user_(RunAsUser) {
        loadFromString(Value);
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

    MrpeProvider(const std::string_view &Name, char Separator)
        : Asynchronous(Name, Separator) {}

    virtual void loadConfig();

    virtual void updateSectionStatus();

    const auto entries() const noexcept { return entries_; }
    const auto &includes() const noexcept { return includes_; }
    const auto &checks() const noexcept { return checks_; }

protected:
    virtual std::string makeBody() const override;

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
    const std::string Entry);

void FixCrCnForMrpe(std::string &Data);

}  // namespace cma::provider

#endif  // mrpe_h__
