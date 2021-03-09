#ifndef file_encryption_h__
#define file_encryption_h__
#pragma once

#include <filesystem>
#include <string_view>
#include <vector>

#include "encryption.h"

namespace cma::encrypt {

enum class SourceType { cpp, python };

constexpr std::string_view kObfuscateWord = "HideAll";
constexpr std::string_view kObfuscateMark = "CMKE";
constexpr int kObfuscatedWordSize = 4;
constexpr int kObfuscatedLengthSize = 8;
constexpr int kObfuscatedSuffixSize =
    kObfuscatedWordSize + kObfuscatedLengthSize;

class OnFile {
public:
    static constexpr int kAlignment = 1024;  // 1024 bytes blocks
    [[nodiscard]] static bool Encode(std::string_view password,
                                     const std::filesystem::path& name);
    [[nodiscard]] static bool Decode(std::string_view password,
                                     const std::filesystem::path& name,
                                     SourceType type);
    [[nodiscard]] static bool Encode(std::string_view password,
                                     const std::filesystem::path& name,
                                     const std::filesystem::path& name_out);
    [[nodiscard]] static bool Decode(std::string_view password,
                                     const std::filesystem::path& name,
                                     const std::filesystem::path& name_out,
                                     SourceType type);

    [[nodiscard]] static int DecodeAll(const std::filesystem::path& dir,
                                       std::wstring_view mask, SourceType type);
    [[nodiscard]] static bool DecodeBuffer(std::string_view password,
                                           std::vector<char>& result,
                                           SourceType type,
                                           std::string_view name);
    [[nodiscard]] static bool IsEncodedBuffer(const std::vector<char>& result,
                                              std::string_view name);

private:
    static std::vector<char> ReadFullFile(const std::filesystem::path& name);
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class FileEncryptionTest;
    FRIEND_TEST(FileEncryptionTest, ReadFile);
    FRIEND_TEST(FileEncryptionTest, DecodeBuffer);
    FRIEND_TEST(FileEncryptionTest, All);
#endif
};
}  // namespace cma::encrypt
#endif  // file_encryption_h__
