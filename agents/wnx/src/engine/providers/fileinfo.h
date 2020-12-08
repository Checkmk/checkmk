// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef fileinfo_h__
#define fileinfo_h__

#include <filesystem>
#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

class FileInfo : public Asynchronous {
public:
    // check for * and ? in text
    static bool ContainsGlobSymbols(std::string_view name);

    // internal fixed defines
    static constexpr std::string_view kMissing = "missing";
    static constexpr std::string_view kStatFailed = "stat failed";
    static constexpr std::string_view kOk = "ok";
    static constexpr char kSep = '|';

    enum class Mode {
        legacy,  // #deprecated
        modern
    };
    FileInfo() : Asynchronous(cma::section::kFileInfoName, kSep) {}

    FileInfo(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

    virtual void loadConfig();

protected:
    std::string makeBody() override;
    std::string generateFileList(YAML::Node path_array_val);
    Mode mode_ = Mode::legacy;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class FileInfoTest;
    FRIEND_TEST(FileInfoTest, Base);
    FRIEND_TEST(FileInfoTest, CheckOutput);
    FRIEND_TEST(FileInfoTest, CheckDriveLetter);
#endif
};

}  // namespace provider

};  // namespace cma

#endif  // fileinfo_h__
