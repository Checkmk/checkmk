#include <unordered_map>
#include <unordered_set>
#include "CustomActions.h"
#include "MockEnvironment.h"
#include "MockLogger.h"
#include "MockWinApi.h"
#include "WritableFile.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

using namespace ::testing;

class wa_WritableFileTest : public Test {
protected:
    StrictMock<MockWinApi> _mockwinapi;
};

TEST_F(wa_WritableFileTest, constructor_success) {
    const std::string testPath{"foo"};
    DWORD shareMode = 0x1;
    DWORD disposition = 0x2;
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x3);

    EXPECT_CALL(_mockwinapi,
                CreateFile(StrEq(testPath), _, shareMode, _, disposition, _, _))
        .WillOnce(Return(rawHandle));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    { WritableFile testFile{testPath, shareMode, disposition, _mockwinapi}; }
}

TEST_F(wa_WritableFileTest, constructor_failure) {
    const std::string testPath{"foo"};
    DWORD shareMode = 0x1;
    DWORD disposition = 0x2;
    DWORD errorCode = ERROR_ACCESS_DENIED;
    const std::string buf = "Access denied";
    std::vector<char> errorStr(buf.cbegin(), buf.cend());
    errorStr.push_back('\0');

    EXPECT_CALL(_mockwinapi,
                CreateFile(StrEq(testPath), _, shareMode, _, disposition, _, _))
        .WillOnce(Return(INVALID_HANDLE_VALUE));
    EXPECT_CALL(_mockwinapi, GetLastError()).WillOnce(Return(errorCode));
    EXPECT_CALL(_mockwinapi, FormatMessageA(_, _, errorCode, _, _, _, _))
        .WillOnce(DoAll(SetCharBuffer<4>(errorStr.data()),
                        Return(errorStr.size() - 1)));
    EXPECT_CALL(_mockwinapi, LocalFree(errorStr.data()));
    ASSERT_THROW(
        {
            try {
                WritableFile testFile(testPath, shareMode, disposition,
                                      _mockwinapi);
            } catch (const FileError &e) {
                EXPECT_STREQ("File 'foo': error: Access denied (5)", e.what());
                throw;
            }
        },
        FileError);
}

TEST_F(wa_WritableFileTest, stream_operator_string_success) {
    const std::string testPath{"foo"};
    DWORD shareMode = 0x1;
    DWORD disposition = 0x2;
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x3);
    const std::array<std::string, 2> testStrings = {
        "Test string to be written to file.", "Something even more fancy."};

    EXPECT_CALL(_mockwinapi,
                CreateFile(StrEq(testPath), _, shareMode, _, disposition, _, _))
        .WillOnce(Return(rawHandle));
    for (const auto &testString : testStrings) {
        EXPECT_CALL(_mockwinapi, WriteFile(rawHandle, testString.c_str(),
                                           testString.size(), _, _))
            .WillOnce(Return(1));
    }
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    {
        WritableFile testFile{testPath, shareMode, disposition, _mockwinapi};
        testFile << testStrings[0] << testStrings[1];
    }
}

TEST_F(wa_WritableFileTest, stream_operator_string_failure) {
    const std::string testPath{"foo"};
    DWORD shareMode = 0x1;
    DWORD disposition = 0x2;
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x3);
    const std::string testString{"Test string to be written to file."};
    DWORD errorCode = ERROR_ACCESS_DENIED;
    const std::string buf = "Access denied";
    std::vector<char> errorStr(buf.cbegin(), buf.cend());
    errorStr.push_back('\0');

    EXPECT_CALL(_mockwinapi,
                CreateFile(StrEq(testPath), _, shareMode, _, disposition, _, _))
        .WillOnce(Return(rawHandle));
    EXPECT_CALL(_mockwinapi, WriteFile(rawHandle, testString.c_str(),
                                       testString.size(), _, _))
        .WillOnce(Return(0));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    EXPECT_CALL(_mockwinapi, GetLastError()).WillOnce(Return(errorCode));
    EXPECT_CALL(_mockwinapi, FormatMessageA(_, _, errorCode, _, _, _, _))
        .WillOnce(DoAll(SetCharBuffer<4>(errorStr.data()),
                        Return(errorStr.size() - 1)));
    EXPECT_CALL(_mockwinapi, LocalFree(errorStr.data()));
    {
        WritableFile testFile{testPath, shareMode, disposition, _mockwinapi};
        ASSERT_THROW(
            {
                try {
                    testFile << testString;
                } catch (const FileError &e) {
                    EXPECT_STREQ("File 'foo': error: Access denied (5)",
                                 e.what());
                    throw;
                }
            },
            FileError);
    }
}

TEST_F(wa_WritableFileTest, stream_operator_bytes_success) {
    const std::string testPath{"foo"};
    DWORD shareMode = 0x1;
    DWORD disposition = 0x2;
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x3);
    const std::array<std::vector<BYTE>, 2> testArrays = {
        std::vector<BYTE>{6, 1}, std::vector<BYTE>{6, 2}};

    EXPECT_CALL(_mockwinapi,
                CreateFile(StrEq(testPath), _, shareMode, _, disposition, _, _))
        .WillOnce(Return(rawHandle));
    for (const auto &testBytes : testArrays) {
        EXPECT_CALL(_mockwinapi, WriteFile(rawHandle, testBytes.data(),
                                           testBytes.size(), _, _))
            .WillOnce(Return(1));
    }
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    {
        WritableFile testFile{testPath, shareMode, disposition, _mockwinapi};
        testFile << testArrays[0] << testArrays[1];
    }
}

TEST_F(wa_WritableFileTest, stream_operator_bytes_failure) {
    const std::string testPath{"foo"};
    DWORD shareMode = 0x1;
    DWORD disposition = 0x2;
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x3);
    const std::vector<BYTE> testBytes = {0, 1, 2, 3, 4, 5};
    DWORD errorCode = ERROR_ACCESS_DENIED;
    const std::string buf = "Access denied";
    std::vector<char> errorStr(buf.cbegin(), buf.cend());
    errorStr.push_back('\0');

    EXPECT_CALL(_mockwinapi,
                CreateFile(StrEq(testPath), _, shareMode, _, disposition, _, _))
        .WillOnce(Return(rawHandle));
    EXPECT_CALL(_mockwinapi,
                WriteFile(rawHandle, testBytes.data(), testBytes.size(), _, _))
        .WillOnce(Return(0));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    EXPECT_CALL(_mockwinapi, GetLastError()).WillOnce(Return(errorCode));
    EXPECT_CALL(_mockwinapi, FormatMessageA(_, _, errorCode, _, _, _, _))
        .WillOnce(DoAll(SetCharBuffer<4>(errorStr.data()),
                        Return(errorStr.size() - 1)));
    EXPECT_CALL(_mockwinapi, LocalFree(errorStr.data()));
    {
        WritableFile testFile{testPath, shareMode, disposition, _mockwinapi};
        ASSERT_THROW(
            {
                try {
                    testFile << testBytes;
                } catch (const FileError &e) {
                    EXPECT_STREQ("File 'foo': error: Access denied (5)",
                                 e.what());
                    throw;
                }
            },
            FileError);
    }
}

TEST_F(wa_WritableFileTest, getDefaultWhitelist_success) {
    NiceMock<MockLogger> mocklogger;
    NiceMock<MockWinApi> mockwinapi;
    StrictMock<MockEnvironment> mockenv{&mocklogger, mockwinapi};
    const std::string testDir{"foo\\bar"};
    const std::string testPath{"bazqux.exe"};
    EXPECT_CALL(mockenv, agentDirectory()).WillOnce(Return(testDir));
    EXPECT_CALL(mockwinapi, GetModuleFileName(nullptr, _, _MAX_PATH))
        .WillOnce(DoAll(SetArrayArgument<1>(testPath.cbegin(), testPath.cend()),
                        Return(10)));
    const std::unordered_set<std::string> expected{
        "foo\\bar\\bin\\OpenHardwareMonitorLib.sys", "bazqux.exe"};
    const auto actual = getDefaultWhitelist(mockenv, mockwinapi);
    ASSERT_EQ(expected, actual);
}

TEST_F(wa_WritableFileTest, getDefaultWhitelist_GetModuleFileName_failure) {
    NiceMock<MockLogger> mocklogger;
    NiceMock<MockWinApi> mockwinapi;
    StrictMock<MockEnvironment> mockenv{&mocklogger, mockwinapi};
    const std::string testDir{"foo\\bar"};
    EXPECT_CALL(mockenv, agentDirectory()).WillOnce(Return(testDir));
    EXPECT_CALL(mockwinapi, GetModuleFileName(nullptr, _, _MAX_PATH))
        .WillOnce(Return(0));
    const std::unordered_set<std::string> expected{
        "foo\\bar\\bin\\OpenHardwareMonitorLib.sys"};
    const auto actual = getDefaultWhitelist(mockenv, mockwinapi);
    ASSERT_EQ(expected, actual);
}

using CallTuple = std::tuple<BOOL, std::string, DWORD>;
template <size_t U>
using CallArray = std::array<CallTuple, U>;

TEST_F(wa_WritableFileTest, areAllFilesWritable_true) {
    // Mock directory layout (in order of traversal):
    // foo (base dir):
    // |_ bar (file)
    // |_ baz (subdir)
    //    |_ qux (file)
    //    |_ quux (file)

    const std::string testPath{"foo"};
    const DWORD expectedShareMode = FILE_SHARE_READ | FILE_SHARE_WRITE;
    const DWORD expectedDisposition = OPEN_EXISTING;
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    const std::unordered_map<std::string, std::string> globToFile{
        {"foo\\*", "bar"}, {"foo\\baz\\*", "qux"}};
    for (const auto &item : globToFile) {
        WIN32_FIND_DATA findData{0};
        std::copy(item.second.cbegin(), item.second.cend(), findData.cFileName);
        findData.cFileName[item.second.size()] = '\0';
        EXPECT_CALL(_mockwinapi, FindFirstFile(StrEq(item.first), _))
            .WillOnce(DoAll(SetArgPointee<1>(findData), Return(rawHandle)));
    }
    EXPECT_CALL(_mockwinapi, FindClose(rawHandle)).Times(globToFile.size());
    {
        const CallArray<4> findNextCalls = {
            std::make_tuple(1, "baz", FILE_ATTRIBUTE_DIRECTORY),  //
            std::make_tuple(0, "", 0),                            //
            std::make_tuple(1, "quux", 0),                        //
            std::make_tuple(0, "", 0)};
        InSequence dummy;
        for (const auto &call : findNextCalls) {
            WIN32_FIND_DATA findData{0};
            const auto &fileName = get<1>(call);
            std::copy(fileName.cbegin(), fileName.cend(), findData.cFileName);
            findData.cFileName[fileName.size()] = '\0';
            findData.dwFileAttributes = get<2>(call);
            EXPECT_CALL(_mockwinapi, FindNextFile(rawHandle, _))
                .WillOnce(
                    DoAll(SetArgPointee<1>(findData), Return(get<0>(call))));
        }
    }
    for (const auto path : {"foo\\bar", "foo\\baz\\qux", "foo\\baz\\quux"}) {
        EXPECT_CALL(_mockwinapi, CreateFile(StrEq(path), _, expectedShareMode,
                                            _, expectedDisposition, _, _))
            .WillOnce(Return(rawHandle));
    }
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle)).Times(3);
    ASSERT_TRUE(areAllFilesWritable(testPath, _mockwinapi));
}

TEST_F(wa_WritableFileTest, areAllFilesWritable_failure) {
    // Mock directory layout (in order of traversal):
    // foo (base dir):
    // |_ bar (file)
    // |_ baz (subdir)
    //    |_ qux (file) NOT WRITABLE
    //    |_ quux (file)

    const std::string testPath{"foo"};
    const DWORD expectedShareMode = FILE_SHARE_READ | FILE_SHARE_WRITE;
    const DWORD expectedDisposition = OPEN_EXISTING;
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    const std::unordered_map<std::string, std::string> globToFile{
        {"foo\\*", "bar"}, {"foo\\baz\\*", "qux"}};
    for (const auto &item : globToFile) {
        WIN32_FIND_DATA findData{0};
        std::copy(item.second.cbegin(), item.second.cend(), findData.cFileName);
        findData.cFileName[item.second.size()] = '\0';
        EXPECT_CALL(_mockwinapi, FindFirstFile(StrEq(item.first), _))
            .WillOnce(DoAll(SetArgPointee<1>(findData), Return(rawHandle)));
    }
    EXPECT_CALL(_mockwinapi, FindClose(rawHandle)).Times(globToFile.size());
    {
        const CallArray<2> findNextCalls = {
            std::make_tuple(1, "baz", FILE_ATTRIBUTE_DIRECTORY),
            std::make_tuple(0, "", 0)};
        InSequence dummy;
        for (const auto &call : findNextCalls) {
            WIN32_FIND_DATA findData{0};
            const auto &fileName = get<1>(call);
            std::copy(fileName.cbegin(), fileName.cend(), findData.cFileName);
            findData.cFileName[fileName.size()] = '\0';
            findData.dwFileAttributes = get<2>(call);
            EXPECT_CALL(_mockwinapi, FindNextFile(rawHandle, _))
                .WillOnce(
                    DoAll(SetArgPointee<1>(findData), Return(get<0>(call))));
        }
    }
    const std::unordered_map<std::string, HANDLE> pathToHandle{
        {"foo\\bar", rawHandle}, {"foo\\baz\\qux", INVALID_HANDLE_VALUE}};
    for (const auto &item : pathToHandle) {
        EXPECT_CALL(_mockwinapi,
                    CreateFile(StrEq(item.first), _, expectedShareMode, _,
                               expectedDisposition, _, _))
            .WillOnce(Return(item.second));
    }
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    DWORD errorCode = ERROR_ACCESS_DENIED;
    const std::string buf = "Access denied";
    std::vector<char> errorStr(buf.cbegin(), buf.cend());
    errorStr.push_back('\0');
    EXPECT_CALL(_mockwinapi, GetLastError()).WillOnce(Return(errorCode));
    EXPECT_CALL(_mockwinapi, FormatMessageA(_, _, errorCode, _, _, _, _))
        .WillOnce(DoAll(SetCharBuffer<4>(errorStr.data()),
                        Return(errorStr.size() - 1)));
    EXPECT_CALL(_mockwinapi, LocalFree(errorStr.data()));
    ASSERT_THROW(
        {
            try {
                areAllFilesWritable(testPath, _mockwinapi);
            } catch (const FileError &e) {
                EXPECT_STREQ("File 'foo\\baz\\qux': error: Access denied (5)",
                             e.what());
                throw;
            }
        },
        FileError);
}

TEST_F(wa_WritableFileTest, areAllFilesWritable_whitelist_failure) {
    // Mock directory layout (in order of traversal):
    // foo (base dir):
    // |_ bar (file)
    // |_ baz (subdir)
    //    |_ qux (file) NOT WRITABLE, WHITELISTED
    //    |_ quux (file) NOT WRITABLE

    const std::string testPath{"foo"};
    const DWORD expectedShareMode = FILE_SHARE_READ | FILE_SHARE_WRITE;
    const DWORD expectedDisposition = OPEN_EXISTING;
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    const std::unordered_map<std::string, std::string> globToFile{
        {"foo\\*", "bar"}, {"foo\\baz\\*", "qux"}};
    for (const auto &item : globToFile) {
        WIN32_FIND_DATA findData{0};
        std::copy(item.second.cbegin(), item.second.cend(), findData.cFileName);
        findData.cFileName[item.second.size()] = '\0';
        EXPECT_CALL(_mockwinapi, FindFirstFile(StrEq(item.first), _))
            .WillOnce(DoAll(SetArgPointee<1>(findData), Return(rawHandle)));
    }
    EXPECT_CALL(_mockwinapi, FindClose(rawHandle)).Times(globToFile.size());
    {
        const CallArray<3> findNextCalls = {
            std::make_tuple(1, "baz", FILE_ATTRIBUTE_DIRECTORY),  //
            std::make_tuple(0, "", 0),                            //
            std::make_tuple(1, "quux", 0)};
        InSequence dummy;
        for (const auto &call : findNextCalls) {
            WIN32_FIND_DATA findData{0};
            const auto &fileName = get<1>(call);
            std::copy(fileName.cbegin(), fileName.cend(), findData.cFileName);
            findData.cFileName[fileName.size()] = '\0';
            findData.dwFileAttributes = get<2>(call);
            EXPECT_CALL(_mockwinapi, FindNextFile(rawHandle, _))
                .WillOnce(
                    DoAll(SetArgPointee<1>(findData), Return(get<0>(call))));
        }
    }
    const std::unordered_map<std::string, HANDLE> pathToHandle{
        {"foo\\bar", rawHandle}, {"foo\\baz\\quux", INVALID_HANDLE_VALUE}};
    for (const auto &item : pathToHandle) {
        EXPECT_CALL(_mockwinapi,
                    CreateFile(StrEq(item.first), _, expectedShareMode, _,
                               expectedDisposition, _, _))
            .WillOnce(Return(item.second));
    }
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    DWORD errorCode = ERROR_ACCESS_DENIED;
    const std::string buf = "Access denied";
    std::vector<char> errorStr(buf.cbegin(), buf.cend());
    errorStr.push_back('\0');
    EXPECT_CALL(_mockwinapi, GetLastError()).WillOnce(Return(errorCode));
    EXPECT_CALL(_mockwinapi, FormatMessageA(_, _, errorCode, _, _, _, _))
        .WillOnce(DoAll(SetCharBuffer<4>(errorStr.data()),
                        Return(errorStr.size() - 1)));
    EXPECT_CALL(_mockwinapi, LocalFree(errorStr.data()));
    const std::unordered_set<std::string> whitelist = {"foo\\baz\\qux"};
    ASSERT_THROW(
        {
            try {
                areAllFilesWritable(testPath, _mockwinapi, whitelist);
            } catch (const FileError &e) {
                EXPECT_STREQ("File 'foo\\baz\\quux': error: Access denied (5)",
                             e.what());
                throw;
            }
        },
        FileError);
}
