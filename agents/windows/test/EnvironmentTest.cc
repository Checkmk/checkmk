#include <array>
#include <functional>
#include <string>
#include <tuple>
#include "Environment.h"
#include "MockLogger.h"
#include "MockWinApi.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

using namespace std;
using namespace testing;

class wa_EnvironmentTest : public Test {
protected:
    NiceMock<MockLogger> _mocklogger;
    const NiceMock<MockWinApi> _mockwinapi;

public:
    virtual ~wa_EnvironmentTest() = default;
};

TEST_F(wa_EnvironmentTest, constructor_CurrentDirectory) {
    const string testCurrDir("C:\\Foo\\Bar");
    EXPECT_CALL(_mockwinapi, GetCurrentDirectoryA(32767, _))
        .WillOnce(
            DoAll(SetArrayArgument<1>(testCurrDir.cbegin(), testCurrDir.cend()),
                  Return(testCurrDir.length())));
    const ::Environment testEnvironment(false, &_mocklogger, _mockwinapi);
    EXPECT_EQ(testCurrDir, testEnvironment.currentDirectory());
}

TEST_F(wa_EnvironmentTest, constructor_AgentDirectory_use_cwd) {
    EXPECT_CALL(_mockwinapi, RegOpenKeyEx(_, _, _, _, _)).Times(0);
    EXPECT_CALL(_mockwinapi, RegQueryValueEx(_, _, _, _, _, _)).Times(0);
    EXPECT_CALL(_mockwinapi, RegCloseKey(_)).Times(1);
    const ::Environment testEnvironment(true, &_mocklogger, _mockwinapi);
    EXPECT_EQ(testEnvironment.currentDirectory(),
              testEnvironment.agentDirectory());
}

TEST_F(wa_EnvironmentTest, constructor_AgentDirectory) {
    HKEY testKey = reinterpret_cast<HKEY>(0x0123);
    const string testImagePath("C:\\Baz\\Qux\\check_mk_agent.exe");
    EXPECT_CALL(
        _mockwinapi,
        RegOpenKeyEx(
            HKEY_LOCAL_MACHINE,
            StrEq("SYSTEM\\CurrentControlSet\\Services\\check_mk_agent"), 0,
            KEY_READ, _))
        .WillOnce(DoAll(SetArgPointee<4>(testKey), Return(ERROR_SUCCESS)));
    EXPECT_CALL(_mockwinapi, RegQueryValueEx(testKey, StrEq("ImagePath"),
                                             nullptr, nullptr, _, _))
        .WillOnce(DoAll(
            SetArrayArgument<4>(testImagePath.cbegin(), testImagePath.cend()),
            SetArgPointee<5>(testImagePath.length()), Return(ERROR_SUCCESS)));
    EXPECT_CALL(_mockwinapi, RegCloseKey(testKey));
    const ::Environment testEnvironment(false, &_mocklogger, _mockwinapi);
    const string expectedAgentDir = "C:\\Baz\\Qux";
    EXPECT_EQ(expectedAgentDir, testEnvironment.agentDirectory());
}

TEST_F(wa_EnvironmentTest, constructor_AgentDirectory_ImagePathQuoted) {
    HKEY testKey = reinterpret_cast<HKEY>(0x0123);
    const string testImagePath("\"C:\\Baz\\Qux\\check_mk_agent.exe\"");
    EXPECT_CALL(
        _mockwinapi,
        RegOpenKeyEx(
            HKEY_LOCAL_MACHINE,
            StrEq("SYSTEM\\CurrentControlSet\\Services\\check_mk_agent"), 0,
            KEY_READ, _))
        .WillOnce(DoAll(SetArgPointee<4>(testKey), Return(ERROR_SUCCESS)));
    EXPECT_CALL(_mockwinapi, RegQueryValueEx(testKey, StrEq("ImagePath"),
                                             nullptr, nullptr, _, _))
        .WillOnce(DoAll(
            SetArrayArgument<4>(testImagePath.cbegin(), testImagePath.cend()),
            SetArgPointee<5>(testImagePath.length()), Return(ERROR_SUCCESS)));
    EXPECT_CALL(_mockwinapi, RegCloseKey(testKey));
    const ::Environment testEnvironment(false, &_mocklogger, _mockwinapi);
    const string expectedAgentDir = "C:\\Baz\\Qux";
    EXPECT_EQ(expectedAgentDir, testEnvironment.agentDirectory());
}

TEST_F(wa_EnvironmentTest, constructor_AgentDirectory_RegOpenKeyEx_failure) {
    HKEY testKey = reinterpret_cast<HKEY>(0x0123);
    const string testImagePath("C:\\Baz\\Qux\\check_mk_agent.exe");
    EXPECT_CALL(
        _mockwinapi,
        RegOpenKeyEx(
            HKEY_LOCAL_MACHINE,
            StrEq("SYSTEM\\CurrentControlSet\\Services\\check_mk_agent"), 0,
            KEY_READ, _))
        .WillOnce(DoAll(SetArgPointee<4>(testKey), Return(1)));  // return error
    EXPECT_CALL(_mockwinapi, RegQueryValueEx(_, _, _, _, _, _)).Times(0);
    EXPECT_CALL(_mockwinapi, RegCloseKey(testKey));
    const ::Environment testEnvironment(false, &_mocklogger, _mockwinapi);
    EXPECT_EQ(testEnvironment.currentDirectory(),
              testEnvironment.agentDirectory());
}

TEST_F(wa_EnvironmentTest, constructor_OtherDirectories) {
    const string testImagePath("C:\\Baz\\Qux\\check_mk_agent.exe");
    EXPECT_CALL(_mockwinapi, RegOpenKeyEx(_, _, _, _, _))
        .WillOnce(Return(ERROR_SUCCESS));
    EXPECT_CALL(_mockwinapi,
                RegQueryValueEx(_, StrEq("ImagePath"), nullptr, nullptr, _, _))
        .WillOnce(DoAll(
            SetArrayArgument<4>(testImagePath.cbegin(), testImagePath.cend()),
            SetArgPointee<5>(testImagePath.length()), Return(ERROR_SUCCESS)));
    const array<tuple<string, string, const_mem_fun_t<string, ::Environment>>,
                10>
        testEntries = {
            make_tuple(string("C:\\Baz\\Qux\\plugins"), string("MK_PLUGINSDIR"),
                       mem_fun(&::Environment::pluginsDirectory)),
            make_tuple(string("C:\\Baz\\Qux\\config"), string("MK_CONFDIR"),
                       mem_fun(&::Environment::configDirectory)),
            make_tuple(string("C:\\Baz\\Qux\\local"), string("MK_LOCALDIR"),
                       mem_fun(&::Environment::localDirectory)),
            make_tuple(string("C:\\Baz\\Qux\\spool"), string("MK_SPOOLDIR"),
                       mem_fun(&::Environment::spoolDirectory)),
            make_tuple(string("C:\\Baz\\Qux\\state"), string("MK_STATEDIR"),
                       mem_fun(&::Environment::stateDirectory)),
            make_tuple(string("C:\\Baz\\Qux\\temp"), string("MK_TEMPDIR"),
                       mem_fun(&::Environment::tempDirectory)),
            make_tuple(string("C:\\Baz\\Qux\\log"), string("MK_LOGDIR"),
                       mem_fun(&::Environment::logDirectory)),
            make_tuple(string("C:\\Baz\\Qux\\bin"), "",
                       mem_fun(&::Environment::binDirectory)),
            make_tuple(string("C:\\Baz\\Qux\\state\\logstate.txt"), "",
                       mem_fun(&::Environment::logwatchStatefile)),
            make_tuple(string("C:\\Baz\\Qux\\state\\eventstate.txt"), "",
                       mem_fun(&::Environment::eventlogStatefile))};

    for (const auto &entry : testEntries) {
        const auto &varname = get<1>(entry);
        if (!varname.empty()) {
            const auto &dirname = get<0>(entry);
            EXPECT_CALL(_mockwinapi, CreateDirectoryA(StrEq(dirname), nullptr))
                .WillOnce(Return(1));  // return success
            EXPECT_CALL(_mockwinapi,
                        SetEnvironmentVariable(StrEq(varname), StrEq(dirname)));
        }
    }

    const ::Environment testEnvironment(false, &_mocklogger, _mockwinapi);

    for (const auto &entry : testEntries) {
        EXPECT_EQ(get<0>(entry), get<2>(entry)(&testEnvironment));
    }
}

ACTION_TEMPLATE(SetCharBuffer, HAS_1_TEMPLATE_PARAMS(unsigned, uIndex),
                AND_1_VALUE_PARAMS(data)) {
    // Courtesy of Microsoft: A function takes a char** param
    // but is declared as taking char* (>sigh<)
    *reinterpret_cast<char **>(std::get<uIndex>(args)) = data;
}

TEST_F(wa_EnvironmentTest, constructor_OtherDirectories_creation_failed) {
    const string testImagePath("C:\\Baz\\Qux\\check_mk_agent.exe");
    EXPECT_CALL(_mockwinapi, RegOpenKeyEx(_, _, _, _, _))
        .WillOnce(Return(ERROR_SUCCESS));
    EXPECT_CALL(_mockwinapi,
                RegQueryValueEx(_, StrEq("ImagePath"), nullptr, nullptr, _, _))
        .WillOnce(DoAll(
            SetArrayArgument<4>(testImagePath.cbegin(), testImagePath.cend()),
            SetArgPointee<5>(testImagePath.length()), Return(ERROR_SUCCESS)));
    const string baseDir = "C:\\Baz\\Qux\\";
    const array<tuple<string, string, const_mem_fun_t<string, ::Environment>>,
                10>
        testEntries = {make_tuple(baseDir + "plugins", string("MK_PLUGINSDIR"),
                                  mem_fun(&::Environment::pluginsDirectory)),
                       make_tuple(baseDir + "config", string("MK_CONFDIR"),
                                  mem_fun(&::Environment::configDirectory)),
                       make_tuple(baseDir + "local", string("MK_LOCALDIR"),
                                  mem_fun(&::Environment::localDirectory)),
                       make_tuple(baseDir + "spool", string("MK_SPOOLDIR"),
                                  mem_fun(&::Environment::spoolDirectory)),
                       make_tuple(baseDir + "state", string("MK_STATEDIR"),
                                  mem_fun(&::Environment::stateDirectory)),
                       make_tuple(baseDir + "temp", string("MK_TEMPDIR"),
                                  mem_fun(&::Environment::tempDirectory)),
                       make_tuple(baseDir + "log", string("MK_LOGDIR"),
                                  mem_fun(&::Environment::logDirectory)),
                       make_tuple(baseDir + "bin", "",
                                  mem_fun(&::Environment::binDirectory)),
                       make_tuple(baseDir + "state\\logstate.txt", "",
                                  mem_fun(&::Environment::logwatchStatefile)),
                       make_tuple(baseDir + "state\\eventstate.txt", "",
                                  mem_fun(&::Environment::eventlogStatefile))};

    const string buf = "Bad pathname";
    vector<char> errorStr(buf.cbegin(), buf.cend());
    errorStr.push_back('\0');
    EXPECT_CALL(_mockwinapi, GetLastError())
        .Times(7)
        .WillRepeatedly(Return(ERROR_BAD_PATHNAME));
    EXPECT_CALL(_mockwinapi, FormatMessageA(_, nullptr, ERROR_BAD_PATHNAME, _,
                                            _, 0, nullptr))
        .Times(7)
        .WillRepeatedly(DoAll(
            SetCharBuffer<4>(errorStr.data()),
            Return(errorStr.size() - 1)));  // exclude terminating null char
    EXPECT_CALL(_mockwinapi, LocalFree(_)).Times(7);

    for (const auto &entry : testEntries) {
        const auto &varname = get<1>(entry);
        if (!varname.empty()) {
            const auto &dirname = get<0>(entry);
            EXPECT_CALL(_mockwinapi, CreateDirectoryA(StrEq(dirname), nullptr))
                .WillOnce(Return(0));  // return failure
            EXPECT_CALL(_mockwinapi,
                        SetEnvironmentVariable(StrEq(varname), StrEq(dirname)));
        }
    }

    const ::Environment testEnvironment(false, &_mocklogger, _mockwinapi);

    for (const auto &entry : testEntries) {
        EXPECT_EQ(get<0>(entry), get<2>(entry)(&testEnvironment));
    }
}
