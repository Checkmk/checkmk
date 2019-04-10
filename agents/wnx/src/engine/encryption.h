#ifndef encryption_h__
#define encryption_h__

#include <wincrypt.h>

#include <string>
#include <string_view>
#include <vector>

#include "common/wtools.h"
#include "tools/_misc.h"

#include "cfg.h"
#include "logger.h"

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
    explicit Commander();

    Commander(const std::string &Password, Length KeyLength = Length::kDefault);

    Commander(const BYTE *Key, DWORD KeyLength);

    ~Commander();

    // in-place encrypt buffer
    std::tuple<bool, size_t> encode(void *InOut, size_t InputSize,
                                    size_t BufferSize,
                                    bool LastBlock = true) const;
    std::tuple<bool, size_t> decode(void *InOut, size_t input_size,
                                    bool LastBlock = true);

    std::optional<cma::ByteVector> getKey() const;

    bool randomizeBuffer(void *Buffer, size_t BufferSize) const;

    const bool available() const { return key_ != 0; }

    std::optional<uint32_t> blockSize() const;

    std::optional<size_t> CalcBufferOverhead(size_t DataSize) const noexcept;

private:
    void cleanup();
    HCRYPTPROV obtainContext();
    void releaseContext();

    void checkAndConfigure();

    static size_t keySize(ALG_ID algorithm);

    HCRYPTKEY generateKey(Length KeyLength) const;
    HCRYPTKEY importKey(const BYTE *key, DWORD key_size) const;
    // derive key and iv from the password in the same manner as openssl does
    HCRYPTKEY deriveOpenSSLKey(const std::string &Password, Length KeyLength,
                               int Iterations);
    void releaseKey();

    HCRYPTPROV crypt_provider_;
    HCRYPTKEY key_;
    Algorithm algorithm_;
};

std::unique_ptr<Commander> MakeCrypt();

std::tuple<HCRYPTHASH, size_t> GetHash(HCRYPTPROV Provider);
}  // namespace cma::encrypt
#endif  // encryption_h__
