#include <algorithm>
#include <chrono>
#include <climits>
#include <cstdio>
#include <ctime>
#include <exception>
#include <functional>
#include <random>
#include <unordered_map>
#include <vector>
#include "RotatingFileHandler.h"
#include "errno.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

using hrc = std::chrono::high_resolution_clock;
using std::chrono::duration_cast;
using std::function;
using std::chrono::milliseconds;
using std::ifstream;
using std::istreambuf_iterator;
using std::make_unique;
using std::ostringstream;
using std::string;
using std::unique_ptr;
using std::unordered_map;
using std::vector;

using ::testing::MatchesRegex;
using ::testing::Return;
using ::testing::SetErrnoAndReturn;
using ::testing::StrictMock;
using ::testing::Test;

class MockFileApi : public FileRotationApi {
public:
    MOCK_CONST_METHOD1(fileExists, bool(const string &));
    MOCK_CONST_METHOD1(remove, bool(const string &));
    MOCK_CONST_METHOD2(rename, bool(const string &, const string &));
};

// Represents an indexed array of the alphanumeric characters [0-9A-Za-z].
// Individual characters can be fetched by giving the corresponding index.
class AlphaNum {
public:
    static char get(size_t index) {
        if (index >= total) throw std::out_of_range("Index out of range");

        if (index >= lowercaseStart)
            return 'a' + static_cast<char>(index % lowercaseStart);

        if (index >= uppercaseStart)
            return 'A' + static_cast<char>(index % uppercaseStart);

        return '0' + static_cast<char>(index);
    }

    static size_t size() { return total; }

private:
    static const size_t lowercaseStart = static_cast<size_t>('Z' - 'A' + 11);
    static const size_t uppercaseStart = 10;
    static const size_t total = static_cast<size_t>('Z' - 'A' + 'z' - 'a' + 12);
};

// TODO: replace this old C based implementation with
// std(::experimental)::filesystem as soon as we upgrade to a MinGW version
// supporting it.
class TempFile {
public:
    TempFile() : _name{createUniqueFilename()} {}
    ~TempFile() { std::remove(name().c_str()); }  // Ignore non-existing

    const string &name() const { return _name; }

private:
    string createRandomFilename() const {
        hrc::time_point tp = hrc::now();
        // std::random_device is not really random in MinGW -> use clock
        std::mt19937 rand_func(static_cast<int>(
            duration_cast<milliseconds>(tp.time_since_epoch()).count() %
            INT_MAX));
        const auto randomAlphaNum = [&rand_func] {
            return AlphaNum::get(
                static_cast<size_t>(rand_func() % AlphaNum::size()));
        };
        vector<char> filename(12, '\0');
        generate(filename.begin(), filename.end(), randomAlphaNum);

        return {filename.cbegin(), filename.cend()};
    }

    // Create a unique filename in current working directory. A replacement for
    // std::tmpnam that just does not work in cross-platform environment.
    string createUniqueFilename() const {
        FileRotationApi fileapi;
        string filename;
        // The chances that this loop ever gets executed twice count at most as
        // 1 : 1034716802229536025600. Before that happens, you should have won
        // a million-euro prize at a national lottery quite many times and not
        // be running this... no, wait... You'd love to write and run unit tests
        // even as a millionaire, wouldn't you?
        do {
            filename = createRandomFilename();
        } while (fileapi.fileExists(filename));
        return filename;
    }

    const string _name;
};

class wa_RotatingFileHandlerTest : public Test {
public:
    wa_RotatingFileHandlerTest() : formatter(make_unique<SimpleFormatter>()) {}

protected:
    string readLogfile() const {
        ifstream logfile{testFile.name()};
        return {istreambuf_iterator<char>{logfile},
                istreambuf_iterator<char>{}};
    }

    const TempFile testFile;
    const unique_ptr<Formatter> formatter;
    const string timestampPattern =
        "\\d\\d\\d\\d-\\d\\d-\\d\\d \\d\\d:\\d\\d:\\d\\d";
};

TEST_F(wa_RotatingFileHandlerTest, publish_maxBytes_0) {
    const string testMessage{"This is a test message."};
    const LogRecord testRecord{LogLevel::notice, testMessage};
    unique_ptr<Handler> testHandler = make_unique<RotatingFileHandler>(
        testFile.name(), make_unique<StrictMock<MockFileApi>>());

    testHandler->publish(testRecord);

    ostringstream expectedLogContent;
    formatter->format(expectedLogContent, testRecord);
    expectedLogContent << std::endl;
    const string actualLogContent{readLogfile()};

    ASSERT_EQ(expectedLogContent.str(), actualLogContent);
}

TEST_F(wa_RotatingFileHandlerTest, publish_maxBytes_8_backupCount_0) {
    const string testMessage{"This is a test message."};
    const LogRecord testRecord{LogLevel::notice, testMessage};
    auto *fileapimock = new StrictMock<MockFileApi>();
    unique_ptr<Handler> testHandler = make_unique<RotatingFileHandler>(
        testFile.name(), unique_ptr<FileRotationApi>(fileapimock), 8, 0);

    EXPECT_CALL(*fileapimock, remove(testFile.name()))
        .WillOnce(Return(true));

    testHandler->publish(testRecord);

    ostringstream expectedLogContent;
    formatter->format(expectedLogContent, testRecord);
    expectedLogContent << std::endl;
    const string actualLogContent{readLogfile()};

    ASSERT_EQ(expectedLogContent.str(), actualLogContent);
}

TEST_F(wa_RotatingFileHandlerTest,
       publish_maxBytes_8_backupCount_0_remove_error) {
    const string testMessage{"This is a test message."};
    const LogRecord testRecord{LogLevel::notice, testMessage};
    auto *fileapimock = new StrictMock<MockFileApi>();
    unique_ptr<Handler> testHandler = make_unique<RotatingFileHandler>(
        testFile.name(), unique_ptr<FileRotationApi>(fileapimock), 8, 0);

    EXPECT_CALL(*fileapimock, remove(testFile.name()))
        .WillOnce(SetErrnoAndReturn(ENOENT, false));

    ::testing::internal::CaptureStderr();
    testHandler->publish(testRecord);

    ostringstream expectedLogContent;
    formatter->format(expectedLogContent, testRecord);
    expectedLogContent << std::endl;
    const string actualLogContent{readLogfile()};

    ASSERT_EQ(expectedLogContent.str(), actualLogContent);

    const auto expectedRegex =
        timestampPattern + " .3. Could not remove logfile " + testFile.name() +
        ": No such file or directory\n";
    ASSERT_THAT(::testing::internal::GetCapturedStderr(),
                MatchesRegex(expectedRegex));
}

TEST_F(wa_RotatingFileHandlerTest, publish_maxBytes_8_backupCount_2) {
    const string testMessage{"This is a test message."};
    const LogRecord testRecord{LogLevel::notice, testMessage};
    auto *fileapimock = new StrictMock<MockFileApi>();
    unique_ptr<Handler> testHandler = make_unique<RotatingFileHandler>(
        testFile.name(), unique_ptr<FileRotationApi>(fileapimock), 8, 2);
    const auto firstBackup = testFile.name() + ".1";
    const auto secondBackup = testFile.name() + ".2";

    EXPECT_CALL(*fileapimock, fileExists(secondBackup))
        .WillOnce(Return(true));
    EXPECT_CALL(*fileapimock, fileExists(firstBackup))
        .Times(2)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*fileapimock, fileExists(testFile.name()))
        .WillOnce(Return(true));
    EXPECT_CALL(*fileapimock, remove(secondBackup))
        .WillOnce(Return(true));
    EXPECT_CALL(*fileapimock, remove(firstBackup))
        .WillOnce(Return(true));
    EXPECT_CALL(*fileapimock, rename(firstBackup, secondBackup))
        .WillOnce(Return(true));
    EXPECT_CALL(*fileapimock, rename(testFile.name(), firstBackup))
        .WillOnce(Return(true));

    testHandler->publish(testRecord);

    ostringstream expectedLogContent;
    formatter->format(expectedLogContent, testRecord);
    expectedLogContent << std::endl;
    const string actualLogContent{readLogfile()};

    ASSERT_EQ(expectedLogContent.str(), actualLogContent);
}

TEST_F(wa_RotatingFileHandlerTest,
       publish_maxBytes_8_backupCount_1_remove_rename_error) {
    const string testMessage{"This is a test message."};
    const LogRecord testRecord{LogLevel::notice, testMessage};
    auto *fileapimock = new StrictMock<MockFileApi>();
    unique_ptr<Handler> testHandler = make_unique<RotatingFileHandler>(
        testFile.name(), unique_ptr<FileRotationApi>(fileapimock), 8, 1);

    const auto backup = testFile.name() + ".1";
    EXPECT_CALL(*fileapimock, fileExists(backup))
        .WillOnce(Return(true));
    EXPECT_CALL(*fileapimock, fileExists(testFile.name()))
        .WillOnce(Return(true));
    EXPECT_CALL(*fileapimock, remove(backup))
        .WillOnce(SetErrnoAndReturn(ENOENT, false));
    EXPECT_CALL(*fileapimock, rename(testFile.name(), backup))
        .WillOnce(SetErrnoAndReturn(ENOENT, false));

    ::testing::internal::CaptureStderr();
    testHandler->publish(testRecord);

    ostringstream expectedLogContent;
    formatter->format(expectedLogContent, testRecord);
    expectedLogContent << std::endl;
    const string actualLogContent{readLogfile()};

    ASSERT_EQ(expectedLogContent.str(), actualLogContent);

    const auto expectedRegex =
        timestampPattern + " .3. Could not remove logfile " + backup +
        ": No such file or directory\n" + timestampPattern +
        " .3. Could not rename " + testFile.name() + " to " + backup +
        ": No such file or directory\n";
    ASSERT_THAT(::testing::internal::GetCapturedStderr(),
                MatchesRegex(expectedRegex));
}
