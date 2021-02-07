// carrier test
//

#include "pch.h"

#include "carrier.h"
#include "commander.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "logger.h"
#include "read_file.h"
#include "service_processor.h"
#include "tools/_misc.h"
#include "tools/_process.h"

using namespace std::chrono_literals;

namespace cma::carrier {
class CarrierTestFixture : public ::testing::Test {
protected:
    struct TestStorage {
        std::vector<uint8_t> buffer_;
        bool delivered_;
        uint64_t answer_id_;
        std::string peer_name_;
    };

    static inline TestStorage g_mailslot_storage;

    static bool MailboxCallbackCarrier(const MailSlot* Slot, const void* Data,
                                       int Len, void* Context) {
        using namespace std::chrono;
        auto storage = (TestStorage*)Context;
        if (!storage) {
            return false;
        }

        // your code is here
        auto fname = cfg::GetCurrentLogFileName();

        auto dt = static_cast<const CarrierDataHeader*>(Data);
        switch (dt->type()) {
            case DataType::kLog:
                break;

            case DataType::kSegment: {
                nanoseconds duration_since_epoch(dt->answerId());
                time_point<steady_clock> tp(duration_since_epoch);
                auto data_source = static_cast<const uint8_t*>(dt->data());
                auto data_end = data_source + dt->length();
                std::vector<uint8_t> vectorized_data(data_source, data_end);
                g_mailslot_storage.buffer_ = vectorized_data;
                g_mailslot_storage.answer_id_ = dt->answerId();
                g_mailslot_storage.peer_name_ = dt->providerId();
                g_mailslot_storage.delivered_ = true;
                break;
            }

            case DataType::kYaml:
                break;
        }

        return true;
    }

    void SetUp() override {
        internal_port_ = BuildPortName(kCarrierMailslotName,
                                       mailbox_.GetName());  // port here
        g_mailslot_storage.buffer_.resize(0);
        g_mailslot_storage.delivered_ = false;

        mailbox_.ConstructThread(&CarrierTestFixture::MailboxCallbackCarrier,
                                 20, &g_mailslot_storage,
                                 wtools::SecurityLevel::admin);
    }
    void TearDown() override {
        mailbox_.DismantleThread();  //
    }
    MailSlot mailbox_{"WinAgentTest", 0};
    std::string internal_port_;
    CoreCarrier cc_;
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

TEST_F(CarrierTestFixture, MailSlotIntegration) {
    auto summary_output = tools::ReadFileInVector(
        (tst::G_TestPath / L"summary.output").wstring().c_str());

    ASSERT_TRUE(cc_.establishCommunication(internal_port_));

    // send data to mailslot
    cc_.sendData("a", 11, summary_output->data(), summary_output->size());
    cc_.shutdownCommunication();

    int count = 1000;
    while (count--) {
        if (g_mailslot_storage.delivered_) {
            break;
        }

        cma::tools::sleep(10ms);
    }

    ASSERT_TRUE(g_mailslot_storage.delivered_);
    EXPECT_EQ(g_mailslot_storage.answer_id_, 11);
    EXPECT_EQ(g_mailslot_storage.peer_name_, "a");
    EXPECT_EQ(g_mailslot_storage.buffer_, summary_output);
}

namespace {
std::string g_last_command;

bool TestRunCommand(std::string_view peer, std::string_view cmd) {
    g_last_command = cmd;
    return true;
}
}  // namespace

// check that inform port works ok
TEST(CarrierTest, InformByMailSlot) {
    auto name_used = "WinAgentTestLocal";
    MailSlot mailbox_client(name_used, 0);
    MailSlot mailbox_server(name_used, 0);

    auto internal_port = BuildPortName(kCarrierMailslotName,
                                       mailbox_server.GetName());  // port here
    srv::ServiceProcessor processor;
    mailbox_server.ConstructThread(
        srv::SystemMailboxCallback, 20, &processor,
        wtools::SecurityLevel::standard);  // standard may be ok
    ON_OUT_OF_SCOPE(mailbox_server.DismantleThread());
    tools::sleep(100ms);

    {
        carrier::CoreCarrier cc;
        // "mail"
        auto ret = cc.establishCommunication(internal_port);
        ASSERT_TRUE(ret);
        ON_OUT_OF_SCOPE(cc.shutdownCommunication());

        tools::sleep(100ms);

        auto save_rcp = commander::ObtainRunCommandProcessor();
        ON_OUT_OF_SCOPE(commander::ChangeRunCommandProcessor(save_rcp));
        commander::ChangeRunCommandProcessor(TestRunCommand);

        InformByMailSlot(mailbox_client.GetName(), "xxx");
        tools::sleep(100ms);
        EXPECT_EQ(g_last_command, "xxx");

        InformByMailSlot(mailbox_client.GetName(), "zzz");
        tools::sleep(100ms);
        EXPECT_EQ(g_last_command, "zzz");
    }
}

}  // namespace cma::carrier
