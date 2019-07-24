#ifndef cvt_h__
#define cvt_h__

#pragma once

#include <filesystem>
#include <string>
#include <string_view>

#include "cfg.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "logger.h"
#include "yaml-cpp/yaml.h"

namespace cma::cfg::cvt {
//
[[deprecated]] YAML::Node LoadIni(const std::filesystem::path& IniFile);

}  // namespace cma::cfg::cvt

namespace cma::cfg::cvt {
class ParserImplementation;
bool CheckIniFile(const std::filesystem::path& Path);

// Engine to parse ini and generate YAML
// implementation in the lwa folder
class Parser {
public:
    Parser() = default;
    virtual ~Parser();

    // no copy, no move
    Parser(const Parser&) = delete;
    Parser(Parser&&) = delete;
    Parser& operator=(const Parser&) = delete;
    Parser& operator=(Parser&&) = delete;

    void prepare();
    bool readIni(std::filesystem::path Path, bool Local);

    void emitYaml(std::ostream& Out);

    YAML::Node emitYaml() noexcept;

private:
    ParserImplementation* pi_ = nullptr;
};
}  // namespace cma::cfg::cvt

#endif  // cvt_h__
