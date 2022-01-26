// test-encryption.cpp

// Test encryption
//
#include "pch.h"

#include "cfg.h"
#include "common/cfg_info.h"
#include "encryption.h"

namespace cma::encrypt {

TEST(EncryptionTest, Base) {
    // stub
    {
        Commander c;
        EXPECT_TRUE(c.available());
    }

    {
        Commander enc("abc");
        EXPECT_TRUE(enc.available());
        char word[1024] = "0123456789ABCDE";
        constexpr int len = 16;
        size_t required_sz = 0;
        {
            auto [success, sz] = enc.encode(word, len, len);
            EXPECT_FALSE(success);
            EXPECT_TRUE(sz > len);
            required_sz = sz;
        }
        ASSERT_TRUE(required_sz != 0);
        size_t encrypted_sz = 0;
        {
            auto [success, sz] = enc.encode(word, 16, required_sz);
            EXPECT_TRUE(success);
            EXPECT_TRUE(sz != 0);
            encrypted_sz = sz;
        }
        ASSERT_TRUE(encrypted_sz != 0);

        Commander dec("abc");
        EXPECT_TRUE(dec.available());
        {
            auto [success, sz] = dec.decode(word, encrypted_sz);
            EXPECT_TRUE(success);
            EXPECT_TRUE(sz == len);
            auto b_size = dec.blockSize();
            EXPECT_TRUE(b_size.has_value() && *b_size > 100);
        }
    }
}

TEST(EncryptionTest, BigBlock) {
    // stub
    constexpr int sz = 32003;
    auto buf = std::make_unique<char[]>(sz);
    for (int i = 0; i < sz; i++) {
        buf[i] = i;
    }
    std::vector<char> out;

    uint32_t segment_size = 48 * 11;
    uint32_t length = sz;

    // encrypt with checking status
    Commander enc("abc");
    ASSERT_TRUE(enc.available());
    auto block_size = enc.blockSize();
    ASSERT_TRUE(block_size.has_value());

    // alignment
    segment_size /= *block_size;
    segment_size++;
    segment_size *= *block_size;

    auto data = buf.get();

    auto segment = std::make_unique<char[]>(segment_size);
    std::vector<char> to_send;

    while (length) {
        uint32_t to_encrypt = std::min(length, segment_size);

        memcpy(segment.get(), data, to_encrypt);
        auto [success, size] = enc.encode(segment.get(), to_encrypt,
                                          segment_size, length == to_encrypt);
        EXPECT_TRUE(success);
        EXPECT_TRUE(size > 0);
        EXPECT_TRUE(size >= to_encrypt);
        EXPECT_TRUE(size <= segment_size);
        // send;
        to_send.insert(to_send.end(), segment.get(), segment.get() + size);
        length -= to_encrypt;
        data += to_encrypt;
    }

    ASSERT_TRUE(to_send.size() >= sz);

    Commander dec("abc");
    {
        auto [success, dec_sz] = dec.decode(to_send.data(), to_send.size());
        ASSERT_EQ(dec_sz, sz);

        EXPECT_EQ(0, memcmp(buf.get(), to_send.data(), sz));
    }
}

}  // namespace cma::encrypt
