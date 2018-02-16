#include "Configurable.h"
#include "Configuration.h"
#include "MockWinApi.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

using namespace ::testing;

class MockConfigurable : public ConfigurableBase {
public:
    MockConfigurable() : ConfigurableBase(MockWinApi()) {}
    MOCK_METHOD2(feed, void(const std::string &key, const std::string &value));
    MOCK_CONST_METHOD2(output, void(const std::string &key, std::ostream &out));
    MOCK_METHOD0(startFile, void());
    MOCK_METHOD0(startBlock, void());
};

class wa_ConfigurationTest : public Test {
protected:
    void reg(const std::string &section, const std::string &key,
             ConfigurableBase *cfg) {
        const ConfigKey testKey(section, key);
        _configurables[testKey].push_back(
            std::unique_ptr<ConfigurableBase>(cfg));
    }

    ConfigurableMap _configurables;
};

TEST_F(wa_ConfigurationTest, readConfigFile_global_only_from) {
    const std::string testConfig =
        "[global]\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_global_only_from_hash_comment) {
    const std::string testConfig =
        "# This is a comment line\r\n"
        "[global]\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_global_only_from_semicolon_comment) {
    const std::string testConfig =
        "; This is a comment line\r\n"
        "[global]\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_global_only_from_indented_hash_comment) {
    const std::string testConfig =
        "[global]\r\n"
        "    # This is an indented comment line\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_global_only_from_indented_semicolon_comment) {
    const std::string testConfig =
        "[global]\r\n"
        "    ; This is a comment line\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_global_only_from_lf) {
    const std::string testConfig =
        "[global]\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_global_only_from_no_indent) {
    const std::string testConfig =
        "[global]\r\n"
        "only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_global_only_from_tab_indent) {
    const std::string testConfig =
        "[global]\r\n"
        "\tonly_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest,
       readConfigFile_global_only_from_no_newline_at_end) {
    const std::string testConfig =
        "[global]\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_host_restriction_match) {
    const std::string testConfig =
        "[global]\r\n"
        "    host = foo ba*\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    const std::string testHost = "baz";
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("only_from"), StrEq("127.0.0.1 192.168.56.0/24 ::1")));
    readConfigFile(iss, testHost, _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_host_restriction_no_match) {
    const std::string testConfig =
        "[global]\r\n"
        "    host = foo bar\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n";
    std::istringstream iss(testConfig);
    const std::string testHost = "baz";
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable);
    readConfigFile(iss, testHost, _configurables);
}

TEST_F(wa_ConfigurationTest,
       readConfigFile_host_restriction_match_winperf_unaffected) {
    const std::string testConfig =
        "[global]\r\n"
        "    host = foo bar\r\n"
        "    only_from = 127.0.0.1 192.168.56.0/24 ::1\r\n"
        "\r\n"
        "[winperf]\r\n"
        "    counters = 10332:msx_queues\r\n";
    std::istringstream iss(testConfig);
    const std::string testHost = "baz";
    auto *testConfigurable1 = new StrictMock<MockConfigurable>();
    auto *testConfigurable2 = new StrictMock<MockConfigurable>();
    reg("global", "only_from", testConfigurable1);
    reg("winperf", "counters", testConfigurable2);
    EXPECT_CALL(*testConfigurable2,
                feed(StrEq("counters"), StrEq("10332:msx_queues")));
    readConfigFile(iss, testHost, _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_logfiles_several_files) {
    const std::string testConfig =
        "[logfiles]\r\n"
        "    textfile = C:\\tmp logfiles\\message_*.log|D:\\log\\sample.txt";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("logfiles", "textfile", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("textfile"),
             StrEq("C:\\tmp logfiles\\message_*.log|D:\\log\\sample.txt")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_logfiles_several_tags) {
    const std::string testConfig =
        "[logfiles]\r\n"
        "    textfile =  nocontext rotated d:\\log\\sample_*.txt";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("logfiles", "textfile", testConfigurable);
    EXPECT_CALL(*testConfigurable,
                feed(StrEq("textfile"),
                     StrEq("nocontext rotated d:\\log\\sample_*.txt")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_logwatch_logfile_mixed_case) {
    const std::string testConfig =
        "[logwatch]\r\n"
        "    logfile Application = crit\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("logwatch", "logfile", testConfigurable);
    EXPECT_CALL(*testConfigurable,
                feed(StrEq("logfile application"), StrEq("crit")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_logwatch_logfile_glob) {
    const std::string testConfig =
        "[logwatch]\r\n"
        "    logfile * = off\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("logwatch", "logfile", testConfigurable);
    EXPECT_CALL(*testConfigurable, feed(StrEq("logfile *"), StrEq("off")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_logwatch_logname) {
    const std::string testConfig =
        "[logwatch]\r\n"
        "    logname Microsoft-Windows-GroupPolicy/Operational = warn\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("logwatch", "logname", testConfigurable);
    EXPECT_CALL(*testConfigurable,
                feed(StrEq("logname microsoft-windows-grouppolicy/operational"),
                     StrEq("warn")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_mrpe_check) {
    const std::string testConfig =
        "[mrpe]\r\n"
        "    check = Whatever c:\\myplugins\\check_whatever -w 10 -c 20\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("mrpe", "check", testConfigurable);
    EXPECT_CALL(
        *testConfigurable,
        feed(StrEq("check"),
             StrEq("Whatever c:\\myplugins\\check_whatever -w 10 -c 20")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_mrpe_include) {
    const std::string testConfig =
        "[mrpe]\r\n"
        "    include \\exampleuser = C:\\includes\\exampleuser_mrpe.cfg\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("mrpe", "include", testConfigurable);
    EXPECT_CALL(*testConfigurable,
                feed(StrEq("include \\exampleuser"),
                     StrEq("C:\\includes\\exampleuser_mrpe.cfg")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, fileinfo_multiple_paths) {
    const std::string testConfig =
        "[fileinfo]\r\n"
        "    path = C:\\Programs\\Foo\\*.log\r\n"
        "    path = M:\\Bar Test\\*.*\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable = new StrictMock<MockConfigurable>();
    reg("fileinfo", "path", testConfigurable);
    EXPECT_CALL(*testConfigurable,
                feed(StrEq("path"),
                     StrEq("C:\\Programs\\Foo\\*.log")));
    EXPECT_CALL(*testConfigurable,
                feed(StrEq("path"),
                     StrEq("M:\\Bar Test\\*.*")));
    readConfigFile(iss, "", _configurables);
}

TEST_F(wa_ConfigurationTest, readConfigFile_plugins) {
    const std::string testConfig =
        "[plugins]\r\n"
        "    execution windows_updates.vbs = async\r\n"
        "    timeout windows_updates.vbs = 120\r\n"
        "    cache_age windows_updates.vbs = 3600\r\n"
        "    retry_count windows_updates.vbs = 3\r\n";
    std::istringstream iss(testConfig);
    auto *testConfigurable1 = new StrictMock<MockConfigurable>();
    auto *testConfigurable2 = new StrictMock<MockConfigurable>();
    auto *testConfigurable3 = new StrictMock<MockConfigurable>();
    auto *testConfigurable4 = new StrictMock<MockConfigurable>();
    reg("plugins", "execution", testConfigurable1);
    reg("plugins", "timeout", testConfigurable2);
    reg("plugins", "cache_age", testConfigurable3);
    reg("plugins", "retry_count", testConfigurable4);
    EXPECT_CALL(*testConfigurable1,
                feed(StrEq("execution windows_updates.vbs"), StrEq("async")));
    EXPECT_CALL(*testConfigurable2,
                feed(StrEq("timeout windows_updates.vbs"), StrEq("120")));
    EXPECT_CALL(*testConfigurable3,
                feed(StrEq("cache_age windows_updates.vbs"), StrEq("3600")));
    EXPECT_CALL(*testConfigurable4,
                feed(StrEq("retry_count windows_updates.vbs"), StrEq("3")));
    readConfigFile(iss, "", _configurables);
}
