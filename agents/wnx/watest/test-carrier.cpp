// carrier test
//

#include "pch.h"

#include "wnx/carrier.h"
#include "wnx/commander.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "wnx/service_processor.h"
#include "watest/test_tools.h"
#include "tools/_misc.h"

using namespace std::chrono_literals;
using namespace std::string_literals;

namespace cma::carrier {

TEST(CarrierTest, NoMaiSlotTracing) { EXPECT_FALSE(mailslot::IsApiLogged()); }

TEST(CarrierTest, DataHeaderConversion) {
    EXPECT_EQ(AsString(nullptr), ""s);
    EXPECT_EQ(AsDataBlock(nullptr), std::vector<unsigned char>{});
    const std::vector<unsigned char> buf{'a', 'b', 'c', 'd', 'e'};
    auto c1 =
        CarrierDataHeader::createPtr("1", 1, DataType::kLog, buf.data(), 5U);
    EXPECT_EQ(AsString(c1.get()), "abcde"s);
    EXPECT_EQ(AsDataBlock(c1.get()), buf);
}

class CarrierTestFixture : public ::testing::Test {
protected:
    const uint32_t cmd_count{3U};
    const uint32_t log_count{2U};
    const uint32_t yaml_count{2U};
    struct TestStorage {
        std::vector<uint8_t> buffer_;
        bool delivered_{false};
        uint64_t answer_id_{0U};
        std::string peer_name_;
        size_t correct_yamls_{0};
        size_t correct_logs_{0};
        size_t correct_commands_{0};
        void reset() {
            buffer_.resize(0);
            delivered_ = false;
            correct_logs_ = 0U;
            correct_yamls_ = 0U;
            correct_commands_ = 0U;
        }
    };

    TestStorage mailslot_storage;

    static bool MailboxCallbackCarrier(const mailslot::Slot *slot,
                                       const void *data, int len,
                                       void *context) {
        using namespace std::chrono;
        auto storage = static_cast<TestStorage *>(context);
        if (!storage) {
            return false;
        }

        // your code is here
        auto fname = cfg::GetCurrentLogFileName();

        auto dt = static_cast<const CarrierDataHeader *>(data);
        switch (dt->type()) {
            case DataType::kLog:
                try {
                    auto s = AsString(dt);
                    if (s == "aaa") {
                        ++storage->correct_logs_;
                    }
                } catch (const std::exception & /*e*/) {
                }
                break;

            case DataType::kSegment: {
                auto data_source = static_cast<const uint8_t *>(dt->data());
                auto data_end = data_source + dt->length();
                std::vector vectorized_data(data_source, data_end);
                storage->buffer_ = vectorized_data;
                storage->answer_id_ = dt->answerId();
                storage->peer_name_ = dt->providerId();
                break;
            }
            case DataType::kYaml:
                try {
                    auto s = AsString(dt);
                    if (s == "aaa") {
                        ++storage->correct_yamls_;
                    }
                } catch (const std::exception & /*e*/) {
                }
                break;
            case DataType::kCommand:
                try {
                    auto s = AsString(dt);
                    if (s == "aaa") {
                        ++storage->correct_commands_;
                    }
                } catch (const std::exception & /*e*/) {
                }
                storage->delivered_ = true;
                break;
        }

        return true;
    }

    void SetUp() override {
        internal_port_ = BuildPortName(kCarrierMailslotName,
                                       mailbox_.GetName());  // port here
        mailslot_storage.reset();

        mailbox_.ConstructThread(&CarrierTestFixture::MailboxCallbackCarrier,
                                 20, &mailslot_storage,
                                 wtools::SecurityLevel::admin);
    }
    void TearDown() override {
        mailbox_.DismantleThread();  //
    }
    mailslot::Slot mailbox_{"WinAgentTest", 0};
    std::string internal_port_;
    CoreCarrier cc_;
    void sendSetOfCommands(const std::optional<ByteVector> &summary_output) {
        // send data to mailslot
        cc_.sendData("a", 11, summary_output->data(), summary_output->size());

        for (size_t _ = 0; _ < log_count; ++_) {
            cc_.sendLog("x", "aaa", 3);
        }
        for (size_t _ = 0; _ < yaml_count; ++_) {
            cc_.sendYaml("x", "aaa");
        }
        for (size_t _ = 0; _ < cmd_count; ++_) {
            cc_.sendCommand("x", "aaa");
        }
    }
};

TEST_F(CarrierTestFixture, EstablishShutdown) {
    // "mail"
    EXPECT_TRUE(cc_.establishCommunication(internal_port_));
    EXPECT_EQ(cc_.getName(), kCarrierMailslotName);
    EXPECT_EQ(cc_.getAddress(), mailbox_.GetName());
    cc_.shutdownCommunication();

    // "asio"
    auto internal_port = BuildPortName(kCarrierAsioName, "127.0.0.1");
    EXPECT_FALSE(cc_.establishCommunication(internal_port));
    constexpr std::string_view s1 = "Output from the asio";
    EXPECT_FALSE(cc_.sendData("a", 11, s1.data(), s1.length()));

    // bad port
    internal_port = BuildPortName("<GTEST>", "127.0.0.1");
    EXPECT_FALSE(cc_.establishCommunication(internal_port));

    // "null"
    internal_port = BuildPortName(kCarrierNullName, "???");
    EXPECT_TRUE(cc_.establishCommunication(internal_port));
    constexpr std::string_view s2 = "Output from the null";
    EXPECT_TRUE(cc_.sendData("a", 11, s2.data(), s2.length()));
    cc_.shutdownCommunication();

    // "dump"
    internal_port = BuildPortName(kCarrierDumpName, "???");
    EXPECT_TRUE(cc_.establishCommunication(internal_port));
    constexpr std::string_view s3 = "Output from the dump";
    EXPECT_TRUE(cc_.sendData("a", 11, s3.data(), s3.length()));
    cc_.shutdownCommunication();

    // "file"
    internal_port = BuildPortName(kCarrierFileName, "fileout.dat.tmp");
    std::error_code ec;
    ON_OUT_OF_SCOPE(std::filesystem::remove("fileout.dat.tmp", ec));
    EXPECT_TRUE(cc_.establishCommunication(internal_port));
    EXPECT_TRUE(cc_.sendData("a", 11, "aaa", 3));
    cc_.shutdownCommunication();
}

TEST_F(CarrierTestFixture, MailSlotComponent) {
    auto summary_output = tools::ReadFileInVector(
        (tst::GetUnitTestFilesRoot() / L"summary.output").wstring().c_str());

    ASSERT_TRUE(cc_.establishCommunication(internal_port_));
    sendSetOfCommands(summary_output);
    cc_.shutdownCommunication();

    tst::WaitForSuccessSilent(
        10'000ms, [this] { return mailslot_storage.correct_commands_ == 3U; });

    ASSERT_TRUE(mailslot_storage.delivered_);
    EXPECT_EQ(mailslot_storage.answer_id_, 11);
    EXPECT_EQ(mailslot_storage.peer_name_, "a");
    EXPECT_EQ(mailslot_storage.buffer_, summary_output);
    EXPECT_EQ(mailslot_storage.correct_logs_, log_count);
    EXPECT_EQ(mailslot_storage.correct_yamls_, yaml_count);
    EXPECT_EQ(mailslot_storage.correct_commands_, cmd_count);
}

namespace {
// Simple callback for the mailslot. Must be thread safe.
std::mutex g_lock_command;
std::string g_last_command;
std::string GetRunCommand() {
    std::scoped_lock l(g_lock_command);
    return g_last_command;
}
bool TestRunCommand(std::string_view /*peer*/, std::string_view cmd) {
    std::scoped_lock l(g_lock_command);
    g_last_command = cmd;
    return true;
}
}  // namespace

class CarrierTestInformFixture : public ::testing::Test {
public:
    void SetUp() override {
        mailbox_server.ConstructThread(
            srv::SystemMailboxCallback, 20, &processor,
            wtools::SecurityLevel::standard);  // standard may be ok
        ASSERT_TRUE(cc.establishCommunication(internal_port));
        save_rcp = commander::ObtainRunCommandProcessor();

        commander::ChangeRunCommandProcessor(TestRunCommand);
    }
    void TearDown() override {
        commander::ChangeRunCommandProcessor(save_rcp);
        cc.shutdownCommunication();

        mailbox_server.DismantleThread();
    }
    const char *name_used{"WinAgentTestLocal"};
    mailslot::Slot mailbox_client{name_used, 0};

private:
    mailslot::Slot mailbox_server{name_used, 0};

    std::string internal_port{BuildPortName(
        kCarrierMailslotName, mailbox_server.GetName())};  // port here
    srv::ServiceProcessor processor;
    CoreCarrier cc;
    commander::RunCommandProcessor save_rcp{nullptr};
};

TEST_F(CarrierTestInformFixture, InformByMailSlot) {
    using namespace std::string_literals;
    for (const auto &cmd : {"xxx"s, "zzz"s}) {
        InformByMailSlot(mailbox_client.GetName(), cmd);
        EXPECT_TRUE(tst::WaitForSuccessSilent(
            100ms, [cmd] { return GetRunCommand() == cmd; }))
            << "FAILED= " << cmd;
    }
}

}  // namespace cma::carrier
