//
// test-tools.cpp :

#include "pch.h"

#include "cfg.h"
#include "providers/check_mk.h"

namespace cma::provider {
TEST(CheckMkHeader, Convert) {
    auto local_host = AddressToCheckMkString("127.0.0.1");
    EXPECT_EQ(local_host, "127.0.0.1");

    auto usual_addr = AddressToCheckMkString("10.1.2.3");
    EXPECT_EQ(usual_addr, "10.1.2.3");

    auto ipv6_addr =
        AddressToCheckMkString("2001:0db8:85a3:0000:0000:8a2e:0370:7334");
    EXPECT_EQ(ipv6_addr, "2001:0db8:85a3:0000:0000:8a2e:0370:7334");

    auto a3 = AddressToCheckMkString("10.1.2.3/4");
    EXPECT_EQ(a3, "10.1.2.3/4");
}

}  // namespace cma::provider
