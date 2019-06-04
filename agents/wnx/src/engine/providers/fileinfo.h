
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
    FileInfo() : Asynchronous(cma::section::kFileInfoName, '|') {}

    FileInfo(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

    virtual void loadConfig();

private:
    std::string makeBody() override;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class FileInfoTest;
    FRIEND_TEST(FileInfoTest, Base);
    FRIEND_TEST(FileInfoTest, CheckOutput);
#endif
};

// function is used to avoid error in MS VC 2017 with non-experimental
// filesystem last_write_time generates absurdly big numbers
// #TODO CHECK in 2019
// returns chrono::something
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
