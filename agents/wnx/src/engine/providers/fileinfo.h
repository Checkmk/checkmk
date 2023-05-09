// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef fileinfo_h__
#define fileinfo_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {
class FileInfo : public Asynchronous {
public:
    static constexpr std::string_view kMissing = "missing";
    static constexpr std::string_view kStatFailed = "stat failed";
    static constexpr std::string_view kOk = "ok";
    static constexpr char kSep = '|';

    static bool ContainsGlobSymbols(std::string_view name);

    enum class Mode {
        legacy,  // #deprecated
        modern
    };
    FileInfo() : Asynchronous(section::kFileInfoName, kSep) {}
    explicit FileInfo(Mode mode)
        : Asynchronous(section::kFileInfoName, kSep), mode_{mode} {}

    FileInfo(const std::string &name, char separator)
        : Asynchronous(name, separator) {}

    virtual void loadConfig();

protected:
    std::string makeBody() override;
    std::string generateFileList(const YAML::Node &path_array_val);
    Mode mode_{Mode::legacy};
};
}  // namespace provider

}  // namespace cma

#endif  // fileinfo_h__
