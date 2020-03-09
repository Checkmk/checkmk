// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef Crypto_h
#define Crypto_h

#include <winsock2.h>
#include <windows.h>
#include <string>
#include <vector>
#include "WinApiInterface.h"

class WinApiInterface;

class Crypto {
    // algorithm can't currently be changed
    static const ALG_ID DEFAULT_ALGORITHM = CALG_AES_256;
    static const ALG_ID HASH_ALGORITHM = CALG_MD5;

    enum class KeyLength {
        KEY_LEN_DEFAULT = 0,
        KEY_LEN_128 = 128,
        KEY_LEN_192 = 192,
        KEY_LEN_256 = 256,
        KEY_LEN_512 = 512,
        KEY_LEN_1024 = 1024,
        KEY_LEN_2048 = 2048
    };

public:
    explicit Crypto(const WinApiInterface &winapi);

    Crypto(const std::string &password, const WinApiInterface &winapi,
           KeyLength key_length = KeyLength::KEY_LEN_DEFAULT);

    Crypto(const BYTE *key, DWORD key_size, const WinApiInterface &winapi);

    ~Crypto();

    // in-place encrypt buffer
    DWORD encrypt(BYTE *input, DWORD input_size, DWORD buffer_size,
                  BOOL fin = TRUE);
    DWORD decrypt(BYTE *input, DWORD input_size, BOOL fin = TRUE);

    std::vector<BYTE> getKey() const;

    DWORD blockSize() const;

    void random(BYTE *buffer, size_t buffer_size);

private:
    void checked(BOOL result, const char *failMessage) const;
    HCRYPTPROV initContext();
    void releaseContext();

    void configureKey();
    size_t keySize();

    static size_t keySize(ALG_ID algorithm);

    HCRYPTKEY genKey(KeyLength key_length) const;
    HCRYPTKEY importKey(const BYTE *key, DWORD key_size) const;
    // derive key and iv from the password in the same manner as openssl does
    void deriveOpenSSLKey(const std::string &password, KeyLength key_length,
                          int iterations);
    void releaseKey(HCRYPTKEY key);

    HCRYPTPROV _provider;
    HCRYPTKEY _key;
    ALG_ID _algorithm;
    const WinApiInterface &_winapi;
};

#endif  // Crypto_h
