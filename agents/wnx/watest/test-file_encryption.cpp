// test-encryption.cpp

// Test encryption
//
#include "pch.h"

#include <filesystem>
#include <fstream>
#include <strstream>
#include <tuple>

#include "cfg.h"
#include "common/cfg_info.h"
#include "file_encryption.h"
#include "test_tools.h"

namespace cma::encrypt {

// The fixture for testing class Foo.
class FileEncryptionTest : public ::testing::Test {
public:
    std::filesystem::path in_;
    std::filesystem::path out_;
    static constexpr std::string_view content_ = "123456789\n123456789";
    static constexpr std::string_view name_in = "base.in";
    static constexpr std::string_view name_out = "base.out";
    static constexpr std::string_view pwd = kObfuscateWord;

protected:
    void SetUp() override {
        OnStartTest();
        tst::SafeCleanTempDir();
        std::tie(in_, out_) = tst::CreateInOut();
        createWorkFile(in_ / name_in, content_.data());
    }

    void TearDown() override {
        //
        // tst::SafeCleanTempDir();
    }

    static std::filesystem::path createWorkFile(
        const std::filesystem::path& name, const std::string& content) {
        namespace fs = std::filesystem;

        auto path = name;

        std::ofstream ofs(path.u8string(), std::ios::binary);

        if (!ofs) {
            XLOG::l("Can't open file {} error {}", path.u8string(),
                    GetLastError());
            return {};
        }

        ofs << content;
        return path;
    }

    static bool isFileSame(const std::filesystem::path& name_1,
                           const std::filesystem::path& name_2) {
        namespace fs = std::filesystem;
        auto file_1 = OnFile::ReadFullFile(name_1);
        auto file_2 = OnFile::ReadFullFile(name_2);
        return file_1 == file_2;
    }
};

TEST_F(FileEncryptionTest, LiveData) {
    namespace fs = std::filesystem;

    fs::path expected[] = {R"(c:\dev\shared\test_file.txt)",
                           R"(c:\dev\shared\test_file.txt.enc)",
                           R"(c:\dev\shared\test_file.txt.dec)"};

    for (auto& e : expected)
        if (!fs::exists(e)) {
            XLOG::l.t("Test is skipped, there is no data");
            return;
        }

    ASSERT_TRUE(OnFile::Decode(kObfuscateWord, expected[1],
                               R"(c:\dev\shared\zzz.zzz)", SourceType::python));
}

TEST_F(FileEncryptionTest, LiveData2) {
    namespace fs = std::filesystem;

    fs::path expected[] = {R"(c:\dev\shared\cmk-update-agent.exe)",
                           R"(c:\dev\shared\cmk-update-agent.exe.enc)"};

    for (auto& e : expected)
        if (!fs::exists(e)) {
            XLOG::l.t("Test is skipped, there is no data");
            return;
        }

    ASSERT_TRUE(OnFile::Decode(kObfuscateWord, expected[1],
                               R"(c:\dev\shared\cmk-update-agent.exe.dec)",
                               SourceType::python));
}

TEST_F(FileEncryptionTest, ReadFile) {
    auto checks = std::move(OnFile::ReadFullFile(in_ / name_in));
    ASSERT_TRUE(!checks.empty());
    std::string_view checks_view = checks.data();
    ASSERT_EQ(checks.size(), content_.length());
    EXPECT_TRUE(
        memcmp(checks_view.data(), content_.data(), content_.length()) == 0);
}

TEST_F(FileEncryptionTest, All) {
    // bad data failure
    EXPECT_FALSE(OnFile::Encode(pwd, in_ / "not exists", out_ / name_out));
    EXPECT_FALSE(OnFile::Encode(pwd, in_ / name_in, out_));
    EXPECT_FALSE(OnFile::Encode(pwd, in_, out_ / name_out));
    EXPECT_FALSE(OnFile::Encode("", in_ / name_in, out_ / name_out));

    EXPECT_FALSE(
        OnFile::Decode("", out_ / name_out, out_ / name_in, SourceType::cpp));
    EXPECT_FALSE(OnFile::Decode("abcd", out_ / name_out, out_ / name_in,
                                SourceType::cpp));
    EXPECT_FALSE(OnFile::Decode(pwd, out_ / name_out, out_, SourceType::cpp));
    EXPECT_FALSE(OnFile::Decode(pwd, out_, out_ / name_in, SourceType::cpp));
    EXPECT_FALSE(OnFile::Decode(pwd, out_ / "not exists", out_ / name_in,
                                SourceType::cpp));

    // valid encryption
    auto encoded_file = out_ / name_out;
    ASSERT_TRUE(OnFile::Encode(pwd, in_ / name_in, encoded_file));

    // valid decryption
    auto decoded_file = out_ / name_in;
    ASSERT_TRUE(
        OnFile::Decode(pwd, out_ / name_out, decoded_file, SourceType::cpp));

    EXPECT_TRUE(isFileSame(in_ / name_in, decoded_file));

    ASSERT_TRUE(OnFile::Encode(pwd, in_ / name_in));
    EXPECT_TRUE(isFileSame(in_ / name_in, encoded_file));

    ASSERT_TRUE(OnFile::Decode(pwd, in_ / name_in, SourceType::cpp));
    EXPECT_TRUE(isFileSame(in_ / name_in, decoded_file));
}

TEST_F(FileEncryptionTest, DecodeTree) {
    // bad data failure
    // valid encryption
    auto encoded_file = out_ / "1.exe";
    ASSERT_TRUE(OnFile::Encode(pwd, in_ / name_in, encoded_file));
    encoded_file = out_ / "2.exe";
    ASSERT_TRUE(OnFile::Encode(pwd, in_ / name_in, encoded_file));

    std::filesystem::copy_file(in_ / name_in, out_ / "3.exe");

    EXPECT_EQ(0, OnFile::DecodeAll(out_, L"*.com", SourceType::cpp));
    EXPECT_EQ(2, OnFile::DecodeAll(out_, L"*.exe", SourceType::cpp));
    EXPECT_EQ(0, OnFile::DecodeAll(in_, L"*.in", SourceType::cpp));
}

}  // namespace cma::encrypt
