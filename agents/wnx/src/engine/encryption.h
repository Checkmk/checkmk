// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef encryption_h__
#define encryption_h__

#include <wincrypt.h>

#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "tools/_misc.h"

namespace cma::encrypt {
// algorithm can't currently be changed
enum Algorithm {
    kDefault = CALG_AES_256,
    kHash = CALG_MD5

};

enum class Length {
    kDefault = 0,
    k128 = 128,
    k192 = 192,
    k256 = 256,
    k512 = 512,
    k1024 = 1024,
    k2048 = 2048
};

class Commander {
public:
    Commander();

    Commander(const std::string &key, Length length);
    explicit Commander(const std::string &key)
        : Commander(key, Length::kDefault) {}

    Commander(const BYTE *key, DWORD length);

    ~Commander();

    // in-place encrypt buffer
    std::tuple<bool, size_t> encode(void *in_out, size_t size,
                                    size_t buffer_size, bool last_block) const;
    std::tuple<bool, size_t> encode(void *in_out, size_t size,
                                    size_t buffer_size) const {
        return encode(in_out, size, buffer_size, true);
    }
    std::tuple<bool, size_t> decode(void *in_out, size_t size,
                                    bool last_block) const;
    std::tuple<bool, size_t> decode(void *in_out, size_t size) const {
        return decode(in_out, size, true);
    }

    [[nodiscard]] std::optional<cma::ByteVector> getKey() const;

    bool randomizeBuffer(void *buffer, size_t buffer_size) const;

    [[nodiscard]] bool available() const { return key_ != 0; }

    [[nodiscard]] std::optional<uint32_t> blockSize() const;

    [[nodiscard]] std::optional<size_t> CalcBufferOverhead(
        size_t data_size) const;

private:
    void cleanup();
    [[nodiscard]] HCRYPTPROV obtainContext() const;
    void releaseContext();

    void checkAndConfigure();

    static size_t keySize(ALG_ID algorithm);

    [[nodiscard]] HCRYPTKEY generateKey(Length key_length) const;
    HCRYPTKEY importKey(const BYTE *key, DWORD key_size) const;
    // derive key and iv from the password in the same manner as openssl does
    [[nodiscard]] HCRYPTKEY deriveOpenSSLKey(const std::string &password,
                                             Length key_length,
                                             int iterations) const;
    void releaseKey();

    HCRYPTPROV crypt_provider_;
    HCRYPTKEY key_;
    Algorithm algorithm_;
};

std::unique_ptr<Commander> MakeCrypt();

std::tuple<HCRYPTHASH, size_t> GetHash(HCRYPTPROV crypt_provider);
}  // namespace cma::encrypt
#endif  // encryption_h__
