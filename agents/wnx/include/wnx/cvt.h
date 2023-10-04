// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CVT_H
#define CVT_H

#pragma once

#include <filesystem>

#include "cfg.h"
#include "common/wtools.h"

namespace cma::cfg::cvt {
class ParserImplementation;
bool CheckIniFile(const std::filesystem::path &ini_file_path);

// Engine to parse ini and generate YAML
// implementation in the lwa folder
class Parser final {
public:
    Parser() = default;
    ~Parser();

    // no copy, no move
    Parser(const Parser &) = delete;
    Parser(Parser &&) = delete;
    Parser &operator=(const Parser &) = delete;
    Parser &operator=(Parser &&) = delete;

    void prepare();
    bool readIni(const std::filesystem::path &path, bool local);

    void emitYaml(std::ostream &out);

    YAML::Node emitYaml() noexcept;

private:
    ParserImplementation *pi_ = nullptr;
};
}  // namespace cma::cfg::cvt

#endif  // CVT_H
