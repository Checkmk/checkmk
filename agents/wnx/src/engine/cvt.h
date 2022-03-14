// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef cvt_h__
#define cvt_h__

#pragma once

#include <filesystem>
#include <string>
#include <string_view>

#include "cfg.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "common/yaml.h"
#include "logger.h"

namespace cma::cfg::cvt {
class ParserImplementation;
bool CheckIniFile(const std::filesystem::path &Path);

// Engine to parse ini and generate YAML
// implementation in the lwa folder
class Parser {
public:
    Parser() = default;
    virtual ~Parser();

    // no copy, no move
    Parser(const Parser &) = delete;
    Parser(Parser &&) = delete;
    Parser &operator=(const Parser &) = delete;
    Parser &operator=(Parser &&) = delete;

    void prepare();
    bool readIni(const std::filesystem::path &Path, bool Local);

    void emitYaml(std::ostream &Out);

    YAML::Node emitYaml() noexcept;

private:
    ParserImplementation *pi_ = nullptr;
};
}  // namespace cma::cfg::cvt

#endif  // cvt_h__
