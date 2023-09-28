// test-onlyfrom.cpp
// also tested ipv6
// and ends there.
//
#include "pch.h"

#include "common/cfg_info.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"
#include "wnx/external_port.h"
#include "wnx/onlyfrom.h"
using namespace std::chrono_literals;

namespace {
std::string g_network_list[] = {
    "2001:db8:abcd:0012::0/112",  // mask
                                  // 2001:0DB8:ABCD:0012:0000:0000:0000:0000
                                  // 2001:0DB8:ABCD:0012:0000:0000:0000:FFFF
    "192.168.1.1/24"              // mask
                                  // 192.168.1.0
                                  // 192.168.1.255
};
const std::string g_loopback_list[] = {
    "::1",        // loopback ipv6
    "127.0.0.1",  // loopback ipv4
};
const std::string g_address_list[] = {
    "2001:0DB8:ABCD:0012::AAAA",  // address ipv6
    "192.168.1.13"};              // addressipv4

const std::string g_address_out_list[] = {
    "2001:0DB8:ABCD:0012:0001:0001:0002:AAAA",  // address ipv6
    "192.168.2.13"};                            // addressipv4}
}  // namespace

namespace cma::cfg {
TEST(OnlyFromTest, Convert) {
    using namespace asio;
    {
        auto n_v6 = of::MapToV6Address(g_network_list[0]);
        EXPECT_TRUE(n_v6.empty());
    }
    {
        auto n_v4 = of::MapToV6Address(g_network_list[1]);
        EXPECT_TRUE(n_v4.empty());
    }
    {
        auto l_v6 = of::MapToV6Address(g_loopback_list[0]);
        EXPECT_TRUE(l_v6.empty());
    }
    {
        auto l_v4 = of::MapToV6Address(g_loopback_list[1]);
        EXPECT_FALSE(l_v4.empty());
        EXPECT_TRUE(of::IsAddressV6(l_v4));
        auto table = cma::tools::SplitString(l_v4, ":");
        EXPECT_TRUE(table.size() == 4);
        EXPECT_EQ(table.back(), g_loopback_list[1]);
    }

    {
        auto a_v6 = of::MapToV6Address(g_address_list[0]);
        EXPECT_TRUE(a_v6.empty());
    }
    {
        auto a_v4 = of::MapToV6Address(g_address_list[1]);
        EXPECT_FALSE(a_v4.empty());
        EXPECT_TRUE(of::IsAddressV6(a_v4));
        auto table = cma::tools::SplitString(a_v4, ":");
        EXPECT_TRUE(table.size() == 4);
        EXPECT_EQ(table.back(), g_address_list[1]);
    }

    {
        auto mapped_v6 = of::MapToV6Network(g_network_list[0]);
        EXPECT_TRUE(mapped_v6.empty());
    }
    {
        auto mapped_v4 = of::MapToV6Network(g_network_list[1]);
        EXPECT_FALSE(mapped_v4.empty());
        EXPECT_TRUE(of::IsNetworkV6(mapped_v4));
        auto table = cma::tools::SplitString(mapped_v4, ":");
        EXPECT_TRUE(table.size() == 4);
        EXPECT_EQ(table.back(), "192.168.1.0/120");
    }
}

TEST(OnlyFromTest, Validness) {
    for (const auto &l : g_loopback_list) {
        EXPECT_TRUE(of::IsAddress(l));
        EXPECT_FALSE(of::IsNetwork(l));
    }
    for (const auto &a : g_address_list) {
        EXPECT_TRUE(of::IsAddress(a));
        EXPECT_FALSE(of::IsNetwork(a));
    }
    for (const auto &n : g_network_list) {
        EXPECT_TRUE(of::IsNetwork(n));
        EXPECT_FALSE(of::IsAddress(n));
    }

    EXPECT_TRUE(of::IsNetworkV6(g_network_list[0]));
    EXPECT_TRUE(of::IsAddressV6(g_address_list[0]));
    EXPECT_TRUE(of::IsAddressV6(g_loopback_list[0]));

    EXPECT_TRUE(of::IsNetworkV4(g_network_list[1]));
    EXPECT_TRUE(of::IsAddressV4(g_address_list[1]));
    EXPECT_TRUE(of::IsAddressV4(g_loopback_list[1]));

    EXPECT_TRUE(of::IsValid(g_address_list[0], g_address_list[0]));
    EXPECT_TRUE(of::IsValid(g_address_list[1], g_address_list[1]));

    EXPECT_TRUE(of::IsValid(g_loopback_list[0], g_loopback_list[0]));
    EXPECT_TRUE(of::IsValid(g_loopback_list[1], g_loopback_list[1]));

    EXPECT_TRUE(of::IsValid(g_address_out_list[0], g_address_out_list[0]));
    EXPECT_TRUE(of::IsValid(g_address_out_list[1], g_address_out_list[1]));

    EXPECT_FALSE(of::IsValid(g_address_list[0], g_address_list[1]));
    EXPECT_FALSE(of::IsValid(g_address_list[1], g_address_list[0]));
    EXPECT_FALSE(of::IsValid(g_loopback_list[0], g_loopback_list[1]));
    EXPECT_FALSE(of::IsValid(g_loopback_list[1], g_loopback_list[0]));
    EXPECT_FALSE(of::IsValid(g_address_out_list[0], g_address_out_list[1]));
    EXPECT_FALSE(of::IsValid(g_address_out_list[1], g_address_out_list[0]));

    EXPECT_FALSE(of::IsValid(g_address_list[0], g_address_out_list[0]));
    EXPECT_FALSE(of::IsValid(g_address_list[1], g_address_out_list[1]));

    EXPECT_TRUE(of::IsValid(g_network_list[0], g_address_list[0]));
    EXPECT_TRUE(of::IsValid(g_network_list[1], g_address_list[1]));

    EXPECT_FALSE(of::IsValid(g_network_list[0], g_address_out_list[0]));
    EXPECT_FALSE(of::IsValid(g_network_list[1], g_address_out_list[1]));

    EXPECT_FALSE(of::IsValid(g_loopback_list[0], g_loopback_list[1]))
        << "ipv4 loopback is good for ::1";
    EXPECT_FALSE(of::IsValid(g_loopback_list[1], g_loopback_list[0]));
}

TEST(OnlyFromTest, ConfigCheck) {
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));

    auto yaml = GetLoadedConfig();
    yaml[groups::kGlobal][vars::kOnlyFrom] =
        YAML::Load("192.168.1.14/24 ::1 127.0.0.1");

    yaml[groups::kGlobal][vars::kIpv6] = YAML::Load("on\n");

    groups::g_global.loadFromMainConfig();
    auto only_froms = groups::g_global.getOnlyFrom();
    EXPECT_TRUE(only_froms.size() == 5);
    EXPECT_TRUE(of::IsNetworkV4(only_froms[0]));
    EXPECT_TRUE(of::IsNetworkV6(only_froms[1]));
    EXPECT_TRUE(of::IsAddressV6(only_froms[2]));
    EXPECT_TRUE(of::IsAddressV4(only_froms[3]));
    EXPECT_TRUE(of::IsAddressV6(only_froms[4]));

    EXPECT_TRUE(groups::g_global.isIpAddressAllowed("192.168.1.13"));
    EXPECT_TRUE(groups::g_global.isIpAddressAllowed("::FFFF:192.168.1.2"));
    EXPECT_FALSE(groups::g_global.isIpAddressAllowed("192.168.2.13"));
    EXPECT_FALSE(groups::g_global.isIpAddressAllowed("::FFFF:192.168.2.2"));
    EXPECT_TRUE(groups::g_global.isIpAddressAllowed("::1"));
    EXPECT_TRUE(groups::g_global.isIpAddressAllowed("127.0.0.1"));
    EXPECT_TRUE(groups::g_global.isIpAddressAllowed("::FFFF:127.0.0.1"));
}

namespace {
std::string ip_received;
void WriteToSocket(const std::string &ip) {
    asio::io_context ios;
    asio::ip::tcp::endpoint endpoint(asio::ip::make_address(ip),
                                     tst::TestPort());
    asio::ip::tcp::socket socket(ios);
    std::error_code ec;
    socket.connect(endpoint, ec);
    // just to skip 1 sec waiting
    asio::error_code error;
    char text[] = "a";
    socket.write_some(asio::buffer(text, 1), error);
    socket.close();
    tst::WaitForSuccessSilent(100ms, [] { return !ip_received.empty(); });
}

auto RegisterIp(const std::string &ip) -> std::vector<uint8_t> {
    if (groups::g_global.isIpAddressAllowed(ip)) {
        ip_received = ip;
    } else {
        XLOG::d("Invalid IP {}", ip);
        ip_received = "Forbidden";
    }
    return {};
}

}  // namespace

TEST(OnlyFromTest, LocalAllowedIpv6) {
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));
    auto yaml = GetLoadedConfig();
    yaml[groups::kGlobal][vars::kOnlyFrom] =
        YAML::Load("192.168.1.14/24 ::1 127.0.0.1");
    yaml[groups::kGlobal][vars::kIpv6] = YAML::Load("on\n");
    groups::g_global.loadFromMainConfig();

    ip_received.clear();
    world::ExternalPort test_port(nullptr);

    ASSERT_TRUE(
        test_port.startIo(RegisterIp, {.port = tst::TestPort(),
                                       .local_only = world::LocalOnly::no,
                                       .pid = std::nullopt}));
    WriteToSocket("::1");
    EXPECT_EQ(ip_received, "::1");
    test_port.shutdownIo();
}

TEST(OnlyFromTest, LocalAllowed) {
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));
    auto yaml = GetLoadedConfig();
    yaml[groups::kGlobal][vars::kOnlyFrom] =
        YAML::Load("192.168.1.14/24 ::1 127.0.0.1");
    groups::g_global.loadFromMainConfig();

    ip_received.clear();
    world::ExternalPort test_port(nullptr);
    ASSERT_TRUE(test_port.startIoTcpPort(RegisterIp, tst::TestPort()));
    WriteToSocket("127.0.0.1");
    EXPECT_EQ(ip_received, "127.0.0.1");
    test_port.shutdownIo();
}

TEST(OnlyFromTest, LocalForbidden) {
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));
    auto yaml = GetLoadedConfig();
    yaml[groups::kGlobal][vars::kIpv6] = YAML::Load("on\n");
    yaml[groups::kGlobal][vars::kOnlyFrom] = YAML::Load("192.168.1.14/24");
    groups::g_global.loadFromMainConfig();
    auto only_froms = groups::g_global.getOnlyFrom();
    EXPECT_TRUE(only_froms.size() == 2);

    ip_received.clear();
    cma::world::ExternalPort test_port(nullptr);
    ASSERT_TRUE(test_port.startIoTcpPort(RegisterIp, tst::TestPort()));
    WriteToSocket("::1");  // forbidden address
    EXPECT_EQ(ip_received, "Forbidden");
    test_port.shutdownIo();
}

TEST(OnlyFromTest, AllowedIpv6) {
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));
    auto yaml = GetLoadedConfig();
    yaml[groups::kGlobal][vars::kOnlyFrom] =
        YAML::Load("127.0.0.1/32 0:0:0:0:0:0:0:1/128");
    yaml[groups::kGlobal][vars::kIpv6] = YAML::Load("on\n");

    groups::g_global.loadFromMainConfig();
    auto only_froms = groups::g_global.getOnlyFrom();

    ip_received.clear();
    cma::world::ExternalPort test_port(nullptr);
    ASSERT_TRUE(test_port.startIoTcpPort(RegisterIp, tst::TestPort()));
    WriteToSocket("::1");

    EXPECT_EQ(ip_received, "::1");
    test_port.shutdownIo();
}

namespace {
auto ReplyFunc(const std::string &ip) -> std::vector<uint8_t> {
    if (!groups::g_global.isIpAddressAllowed(ip)) {
        XLOG::d("Invalid IP {}", ip);
        return {};
    }

    const auto data = reinterpret_cast<const uint8_t *>(ip.data());
    std::vector v(data, data + ip.size());
    return v;
}
}  // namespace

TEST(OnlyFromTest, Config) {
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));

    auto yaml = GetLoadedConfig();
    yaml[groups::kGlobal][vars::kOnlyFrom] = YAML::Load("::1 127.0.0.1");
    yaml[groups::kGlobal][vars::kIpv6] = YAML::Load("on\n");

    groups::g_global.loadFromMainConfig();
    auto only_froms = groups::g_global.getOnlyFrom();
}
TEST(OnlyFromTest, Ipv6AndIpv4Component) {
    tst::FirewallOpener fwo;

    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));

    auto yaml = GetLoadedConfig();
    yaml[groups::kGlobal][vars::kOnlyFrom] = YAML::Load("::1 127.0.0.1");
    yaml[groups::kGlobal][vars::kIpv6] = YAML::Load("on\n");
    groups::g_global.loadFromMainConfig();
    auto only_froms = groups::g_global.getOnlyFrom();
    EXPECT_TRUE(only_froms.size() == 3);
    EXPECT_TRUE(of::IsAddressV6(only_froms[0]));
    EXPECT_TRUE(of::IsAddressV4(only_froms[1]));
    EXPECT_TRUE(of::IsAddressV6(only_froms[2]));

    // ipv4
    {
        cma::world::ExternalPort test_port(nullptr);                      //
        auto ret = test_port.startIoTcpPort(ReplyFunc, tst::TestPort());  //
        ASSERT_TRUE(ret);

        try {
            asio::io_context ios;
            asio::ip::tcp::endpoint endpoint(
                asio::ip::make_address("127.0.0.1"), tst::TestPort());
            asio::ip::tcp::socket socket(ios);
            socket.connect(endpoint);
            asio::error_code error;
            char text[256];
            auto count = socket.read_some(asio::buffer(text), error);
            EXPECT_TRUE(count > 1);
            socket.close();
        } catch (const std::exception &e) {
            XLOG::l("Exception {} during connection to ", e.what());
        }
        test_port.shutdownIo();  //
    }

    // ipv6 connect
    {
        cma::world::ExternalPort test_port(nullptr);                      //
        auto ret = test_port.startIoTcpPort(ReplyFunc, tst::TestPort());  //
        ASSERT_TRUE(ret);
        asio::io_context ios;
        asio::ip::tcp::endpoint endpoint(asio::ip::make_address("::1"),
                                         tst::TestPort());

        asio::ip::tcp::socket socket(ios);

        socket.connect(endpoint);

        asio::error_code error;
        char text[256];
        auto count = socket.read_some(asio::buffer(text), error);
        socket.close();
        EXPECT_TRUE(count > 1);
        test_port.shutdownIo();  //
    }
}

TEST(OnlyFromTest, Ipv4OnlyComponent) {
    tst::FirewallOpener fwo;
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));

    auto yaml = GetLoadedConfig();
    yaml[groups::kGlobal][vars::kOnlyFrom] = YAML::Load("::1 127.0.0.1");
    yaml[groups::kGlobal][vars::kIpv6] = YAML::Load("off\n");
    groups::g_global.loadFromMainConfig();
    auto only_froms = groups::g_global.getOnlyFrom();
    EXPECT_TRUE(only_froms.size() == 1);
    EXPECT_TRUE(of::IsAddressV4(only_froms[0]));

    //  ipv6 no connect
    {
        cma::world::ExternalPort test_port(nullptr);                      //
        auto ret = test_port.startIoTcpPort(ReplyFunc, tst::TestPort());  //
        ASSERT_TRUE(ret);
        asio::io_context ios;
        asio::ip::tcp::endpoint endpoint(asio::ip::make_address("::1"),
                                         tst::TestPort());
        asio::ip::tcp::socket socket(ios);
        EXPECT_ANY_THROW(socket.connect(endpoint));
        asio::error_code error;
        char text[256];
        auto count = socket.read_some(asio::buffer(text), error);
        socket.close();
        EXPECT_TRUE(count == 0);
        test_port.shutdownIo();  //
    }

    //  ipv4 connected successfully
    {
        cma::world::ExternalPort test_port(nullptr);                      //
        auto ret = test_port.startIoTcpPort(ReplyFunc, tst::TestPort());  //
        ASSERT_TRUE(ret);
        asio::io_context ios;
        asio::ip::tcp::endpoint endpoint(asio::ip::make_address("127.0.0.1"),
                                         tst::TestPort());

        asio::ip::tcp::socket socket(ios);

        EXPECT_NO_THROW(socket.connect(endpoint));

        asio::error_code error;
        char text[256];
        auto count = socket.read_some(asio::buffer(text), error);
        socket.close();
        EXPECT_TRUE(count > 0);
        test_port.shutdownIo();  //
    }
}

}  // namespace cma::cfg
