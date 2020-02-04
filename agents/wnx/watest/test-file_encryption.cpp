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
    static constexpr std::string_view pwd = "ABCD";

protected:
    void SetUp() override {
        OnStartTest();
        tst::SafeCleanTempDir();
        std::tie(in_, out_) = tst::CreateInOut();
        createWorkFile(in_ / name_in, content_.data());
    }

    void TearDown() override {
        //
        tst::SafeCleanTempDir();
    }

    static std::filesystem::path createWorkFile(
        const std::filesystem::path& Name, const std::string& Text) {
        namespace fs = std::filesystem;

        auto path = Name;

        std::ofstream ofs(path.u8string(), std::ios::binary);

        if (!ofs) {
            XLOG::l("Can't open file {} error {}", path.u8string(),
                    GetLastError());
            return {};
        }

        ofs << Text;
        return path;
    }
};

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

    ASSERT_TRUE(OnFile::Encode(pwd, in_ / name_in, out_ / name_out));
    EXPECT_FALSE(OnFile::Decode("", out_ / name_out, out_ / name_in));
    EXPECT_FALSE(OnFile::Decode("abcd", out_ / name_out, out_ / name_in));
    EXPECT_FALSE(OnFile::Decode(pwd, out_ / name_out, out_));
    EXPECT_FALSE(OnFile::Decode(pwd, out_, out_ / name_in));
    EXPECT_FALSE(OnFile::Decode(pwd, out_ / "not exists", out_ / name_in));

    ASSERT_TRUE(OnFile::Decode(pwd, out_ / name_out, out_ / name_in));
    auto decoded = OnFile::ReadFullFile(out_ / name_in);
    auto base = OnFile::ReadFullFile(out_ / name_in);
    ASSERT_EQ(decoded, base);
}

}  // namespace cma::encrypt
