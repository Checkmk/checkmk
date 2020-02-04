#ifndef file_encryption_h__
#define file_encryption_h__
#pragma once

#include <filesystem>
#include <string_view>
#include <vector>

#include "encryption.h"

namespace cma::encrypt {

class OnFile {
public:
    static constexpr int kAlignment = 1024;  // 1024 bytes blocks
    static bool Encode(std::string_view password,
                       const std::filesystem::path& name);
    static bool Decode(std::string_view password,
                       const std::filesystem::path& name);
    static bool Encode(std::string_view password,
                       const std::filesystem::path& name,
                       const std::filesystem::path& name_out);
    static bool Decode(std::string_view password,
                       const std::filesystem::path& name,
                       const std::filesystem::path& name_out);

private:
    static std::vector<char> ReadFullFile(const std::filesystem::path& name);
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class FileEncryptionTest;
    FRIEND_TEST(FileEncryptionTest, ReadFile);
    FRIEND_TEST(FileEncryptionTest, All);
#endif
};
}  // namespace cma::encrypt
#endif  // file_encryption_h__
