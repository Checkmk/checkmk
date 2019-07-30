//
// test-tools.cpp :

#include "pch.h"

#include "cfg.h"
#include "providers/check_mk.h"

namespace cma::provider {
TEST(CheckMkHeader, Convert) {
    using namespace cma::provider;
    auto local_host = cma::provider::AddressToCheckMkString("127.0.0.1");
    EXPECT_EQ(local_host, "127.0.0.1/32 0:0:0:0:0:ffff:7f00:1/128");

    auto usual_addr = AddressToCheckMkString("10.1.2.3");
    EXPECT_EQ(usual_addr, "10.1.2.3/32 0:0:0:0:0:ffff:a01:203/128");

    auto ipv6_addr =
        AddressToCheckMkString("2001:0db8:85a3:0000:0000:8a2e:0370:7334");
    EXPECT_EQ(ipv6_addr, "2001:db8:85a3:0:0:8a2e:370:7334/128");

    auto a3 = AddressToCheckMkString("10.1.2.3/4");
    EXPECT_EQ(a3, "10.1.2.3/4");
}

}  // namespace cma::provider
