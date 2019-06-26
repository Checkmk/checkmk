
// provides basic api to start and stop service

#pragma once
#ifndef fileinfo_h__
#define fileinfo_h__

#if defined(USE_EXPERIMENTAL_FILESYSTEM)
#include <experimental/filesystem>
#endif

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

// function is used to avoid error in MS VC 2017 with non-experimental
// filesystem, because last_write_time generates absurdly big numbers
// #TODO CHECK in 2019
// returns chrono::duration::* probably dependent from the experimental/not
// experimental this function is temporary by nature, so we do not care much
// about C++ Guide
inline auto GetFileTimeSinceEpoch(const std::filesystem::path& file) noexcept {
    std::error_code ec;
#if defined(USE_EXPERIMENTAL_FILESYSTEM)
    std::experimental::filesystem::v1::path fp = file.c_str();
    auto file_last_touch_full =
        std::experimental::filesystem::v1::last_write_time(fp, ec);
    return file_last_touch_full.time_since_epoch();
#else
    auto file_last_touch_full = std::filesystem::last_write_time(file, ec);
    return file_last_touch_full.time_since_epoch();
#endif
}

}  // namespace provider

};  // namespace cma

#endif  // fileinfo_h__
