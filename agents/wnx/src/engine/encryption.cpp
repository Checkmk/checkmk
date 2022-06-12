// Windows Tools
#include "stdafx.h"

#include "encryption.h"

#include <string>
#include <string_view>
#include <tuple>

#include "cfg.h"
#include "logger.h"
#include "tools/_raii.h"

namespace cma::encrypt {
Commander::Commander() : algorithm_(Algorithm::kDefault) {
    crypt_provider_ = obtainContext();
    key_ = generateKey(Length::kDefault);

    checkAndConfigure();
}

Commander::Commander(const std::string &key, Length length)
    : algorithm_(Algorithm::kDefault) {
    crypt_provider_ = obtainContext();
    key_ = deriveOpenSSLKey(key, length, 1);

    checkAndConfigure();
}

Commander::Commander(const BYTE *key, DWORD length)
    : algorithm_(Algorithm::kDefault) {
    crypt_provider_ = obtainContext();
    key_ = importKey(key, length);

    checkAndConfigure();
}

Commander::~Commander() { cleanup(); }

void Commander::cleanup() {
    releaseKey();
    releaseContext();
}

std::tuple<bool, size_t> Commander::encode(void *in_out, size_t size,
                                           size_t buffer_size,
                                           bool last_block) const {
    if (!available()) {
        return {false, 0};
    }

    auto input_size = static_cast<DWORD>(size);
    if (input_size == 0) return {true, 0};
    if (nullptr == in_out) {
        XLOG::l.crit(XLOG_FLINE + " nullptr in param");
        return {false, 0};
    }

    if (FALSE == ::CryptEncrypt(key_, 0, last_block ? TRUE : FALSE, 0,
                                static_cast<BYTE *>(in_out), &input_size,
                                static_cast<DWORD>(buffer_size))) {
        // special case, when error is recoverable
        if (GetLastError() == ERROR_MORE_DATA) {
            return {false, input_size};
        }

        XLOG::l.crit("Cannot encode buffer {}", GetLastError());
        return {false, 0};
    }

    return {true, input_size};
}

std::tuple<bool, size_t> Commander::decode(void *in_out, size_t size,
                                           bool last_block) const {
    if (!available()) {
        return {false, 0};
    }

    auto input_size = static_cast<DWORD>(size);
    if (input_size == 0) return {true, 0};

    if (nullptr == in_out) {
        XLOG::l.crit(XLOG_FLINE + " nullptr in param");
        return {false, 0};
    }

    if (FALSE == ::CryptDecrypt(key_, 0, last_block ? TRUE : FALSE, 0,
                                static_cast<BYTE *>(in_out), &input_size)) {
        // special case, when error is recoverable
        if (GetLastError() == ERROR_MORE_DATA) {
            return {false, input_size};
        }

        XLOG::l.crit("Cannot decode buffer [{}]", GetLastError());
        return {false, 0};
    }

    return {true, input_size};
}

static bool IsAesAlgorithm(Algorithm algorithm) {
    return (algorithm == CALG_AES_128) || (algorithm == CALG_AES_192) ||
           (algorithm == CALG_AES_256);
}

// called from ctor
HCRYPTPROV Commander::obtainContext() const {
    HCRYPTPROV handle = 0;

    const auto *provider =
        IsAesAlgorithm(algorithm_) ? MS_ENH_RSA_AES_PROV : MS_DEF_PROV;

    auto provider_type =
        IsAesAlgorithm(algorithm_) ? PROV_RSA_AES : PROV_RSA_FULL;

    if (::CryptAcquireContext(&handle, nullptr, provider, provider_type,
                              CRYPT_VERIFYCONTEXT) == FALSE) {
        XLOG::l.crit("Cannot obtain crypto context error is [{}]",
                     GetLastError());
        return 0;
    }

    return handle;
}

// called from destructor
void Commander::releaseContext() {
    //
    if (0 != crypt_provider_) {
        ::CryptReleaseContext(crypt_provider_, 0);
        crypt_provider_ = 0;
    }
}

// called only from constructor
void Commander::checkAndConfigure() {
    if (0 == key_) {
        cleanup();
        return;
    }

    DWORD mode = CRYPT_MODE_CBC;
    auto *pmode = reinterpret_cast<BYTE *>(&mode);
    if (FALSE == ::CryptSetKeyParam(key_, KP_MODE, pmode, 0)) {
        XLOG::l.crit("Cannot set crypto mode error is [{}]", GetLastError());
        return;
    }

    // in fact, pkcs5 seems to be the only padding supported by MS bundled CSPs?
    mode = PKCS5_PADDING;
    if (FALSE == ::CryptSetKeyParam(key_, KP_PADDING, pmode, 0)) {
        XLOG::l.crit("Cannot set pad mode error is [{}]", GetLastError());
        return;
    }

    XLOG::t.i("Modes for a key set correctly");
}

HCRYPTKEY Commander::generateKey(Length key_length) const {
    HCRYPTKEY hkey = 0;
    if (crypt_provider_ == 0) return 0;
    if (FALSE ==
        ::CryptGenKey(crypt_provider_, algorithm_,
                      static_cast<unsigned>(key_length) | CRYPT_EXPORTABLE,
                      &hkey)) {
        XLOG::l.crit(XLOG_FLINE + "Cannot generate key, error is [{}]",
                     GetLastError());
        return 0;
    }

    return hkey;
}

// #TODO revamp
HCRYPTKEY Commander::importKey(const BYTE *key, DWORD key_size) const {
    if (crypt_provider_ == 0) return 0;

    // the key structure we pass to the api needs to be "decorated"
    std::vector<BYTE> key_blob;

    // insert header
    BLOBHEADER hdr;
    hdr.bType = PLAINTEXTKEYBLOB;
    hdr.bVersion = CUR_BLOB_VERSION;
    hdr.reserved = 0;
    hdr.aiKeyAlg = algorithm_;

    auto *insert_ptr = reinterpret_cast<BYTE *>(&hdr);
    key_blob.insert(key_blob.end(), insert_ptr,
                    insert_ptr + sizeof(BLOBHEADER));

    // insert size field
    insert_ptr = reinterpret_cast<BYTE *>(&key_size);
    key_blob.insert(key_blob.end(), insert_ptr, insert_ptr + sizeof(DWORD));

    // insert the actual key
    key_blob.insert(key_blob.end(), key, key + key_size);

    HCRYPTKEY crypt_key = 0;
    if (FALSE == ::CryptImportKey(crypt_provider_, &key_blob[0],
                                  static_cast<DWORD>(key_blob.size()), 0, 0,
                                  &crypt_key)) {
        XLOG::l.crit(XLOG_FLINE + " Cannot import key, error is [{}]",
                     GetLastError());
        return 0;
    }
    return crypt_key;
}

size_t Commander::keySize(ALG_ID algorithm) {
    switch (algorithm) {
        case CALG_AES_128:
            return 128;  // NOLINT
        case CALG_AES_192:
            return 192;  // NOLINT
        default:
            return 256;  // NOLINT
    }
}

std::tuple<HCRYPTHASH, size_t> GetHash(HCRYPTPROV crypt_provider) {
    HCRYPTHASH hash = 0;

    if (::CryptCreateHash(crypt_provider, Algorithm::kHash, 0, 0, &hash) ==
        FALSE) {
        XLOG::l("Can't create hash [{}]", GetLastError());
        return {};
    }
    DWORD hash_size = 0;

    if (DWORD sizeof_hashsize = sizeof(DWORD);
        ::CryptGetHashParam(hash, HP_HASHSIZE,
                            reinterpret_cast<BYTE *>(&hash_size),
                            &sizeof_hashsize, 0) == FALSE) {
        XLOG::l("Can't get hash size [{}]", GetLastError());
        return {hash, 0};
    }

    return {hash, hash_size};
}

template <typename T>
auto HashData(HCRYPTHASH Hash, T &Value) {
    return ::CryptHashData(Hash, reinterpret_cast<const BYTE *>(&Value[0]),
                           static_cast<DWORD>(Value.size()), 0);
}

template <typename T>
auto GetHashData(HCRYPTHASH Hash, T &Value) {
    auto buffer_size = static_cast<DWORD>(Value.size());
    return ::CryptGetHashParam(Hash, HP_HASHVAL, &Value[0], &buffer_size, 0);
}

HCRYPTHASH DuplicateHash(HCRYPTHASH hash) {
    HCRYPTHASH hash_out = 0;
    if (::CryptDuplicateHash(hash, nullptr, 0, &hash_out) == 0) {
        return 0;
    }
    return hash_out;
}

std::optional<uint32_t> BlockSize(HCRYPTKEY key) {
    DWORD block_length = 0;

    if (DWORD param_length = sizeof(block_length);
        ::CryptGetKeyParam(key, KP_BLOCKLEN,
                           reinterpret_cast<BYTE *>(&block_length),
                           &param_length, 0) == FALSE) {
        XLOG::l("Failure getting block len [{}]", GetLastError());
        return {};
    }
    return block_length;
}

std::optional<uint32_t> Commander::blockSize() const {
    if (0 == key_) return {};

    return BlockSize(key_);
}

// Stupid function from the LWA
HCRYPTKEY Commander::deriveOpenSSLKey(const std::string &password,
                                      Length key_length, int iterations) const {
    constexpr uint32_t kBlockALign = 8;
    if (crypt_provider_ == 0) return 0;

    auto [base_hash, hash_size] = GetHash(crypt_provider_);

    auto to_kill_base_hash = base_hash;
    ON_OUT_OF_SCOPE(
        if (to_kill_base_hash)::CryptDestroyHash(to_kill_base_hash););
    if (hash_size == 0) return 0;

    cma::ByteVector buffer;
    buffer.resize(hash_size);

    HCRYPTKEY hkey = 0;
    bool first_iteration = true;
    size_t key_offset = 0;
    size_t iv_offset = 0;

    auto key_size = (key_length == Length::kDefault)
                        ? keySize(algorithm_) / kBlockALign
                        : static_cast<size_t>(key_length);

    std::vector<BYTE> key(key_size);
    std::vector<BYTE> iv;

    while ((key_offset < key.size()) || (iv_offset < iv.size())) {
        HCRYPTHASH hash = DuplicateHash(base_hash);
        if (0 == hash) return 0;

        ON_OUT_OF_SCOPE(::CryptDestroyHash(hash));

        // after the first iteration, include the hash from the previous
        // iteration
        if (first_iteration) {
            first_iteration = false;
        } else {
            if (FALSE == HashData(hash, buffer)) return 0;
        }
        // include password in hash (duh!)
        if (FALSE == HashData(hash, password)) return 0;

        // #TODO: include salt
        if (FALSE == GetHashData(hash, buffer)) return 0;

        for (int i = 1; i < iterations; ++i) {
            auto hash_inner = DuplicateHash(base_hash);
            if (FALSE == hash_inner) return 0;

            ON_OUT_OF_SCOPE(::CryptDestroyHash(hash_inner));

            if (FALSE == HashData(hash_inner, buffer)) return 0;
            if (FALSE == GetHashData(hash_inner, buffer)) return 0;
        }

        size_t usable_bytes = buffer.size();
        size_t key_bytes =
            std::min<size_t>(usable_bytes, key.size() - key_offset);

        if (key_bytes > 0) {
            memcpy(&key[key_offset], &buffer[0], key_bytes);
            key_offset += key_bytes;
            if (key_offset == key.size()) {
                // apply key. we do this right away so that we can query the
                // necessary
                // size for the iv and don't need own logic to deduce it.
                hkey = importKey(&key[0], static_cast<DWORD>(key.size()));
                auto block_size = BlockSize(hkey);
                if (!block_size) {
                    ::CryptDestroyKey(hkey);
                    return 0;
                }
                iv.resize(*block_size / kBlockALign);
            }
        }

        if (usable_bytes > key_bytes) {
            auto iv_bytes = std::min<size_t>(usable_bytes - key_bytes,
                                             iv.size() - iv_offset);
            memcpy(&iv[iv_offset], &buffer[key_bytes], iv_bytes);
            iv_offset += iv_bytes;
        }
    }

    // apply iv
    if (hkey != 0 && FALSE == ::CryptSetKeyParam(hkey, KP_IV, &iv[0], 0)) {
        ::CryptDestroyKey(hkey);
        XLOG::l("Failure applying key [{}]", GetLastError());
        return 0;
    }

    return hkey;
}

void Commander::releaseKey() {
    if (0 != key_) {
        ::CryptDestroyKey(key_);
        key_ = 0;
    }
}

std::optional<cma::ByteVector> Commander::getKey() const {
    if (!available()) return {};

    DWORD key_size = 0;
    if (FALSE ==
        ::CryptExportKey(key_, 0, PLAINTEXTKEYBLOB, 0, nullptr, &key_size)) {
        XLOG::l("Failed to get key size, error [{}]", GetLastError());
        return {};
    }

    std::vector<BYTE> result;
    result.resize(key_size);
    if (FALSE ==
        ::CryptExportKey(key_, 0, PLAINTEXTKEYBLOB, 0, &result[0], &key_size)) {
        XLOG::l("Failed to export key, error [{}]", GetLastError());
        return {};
    }

    // return only the key, not the meta info
    return std::vector<BYTE>(result.begin() + sizeof(BLOBHEADER), result.end());
}

bool Commander::randomizeBuffer(void *buffer, size_t buffer_size) const {
    if (!available()) return false;

    if (FALSE == ::CryptGenRandom(crypt_provider_,
                                  static_cast<DWORD>(buffer_size),
                                  static_cast<BYTE *>(buffer))) {
        XLOG::l("Failed generate random data, error [{}]", GetLastError());
        return false;
    }

    return true;
}

std::unique_ptr<Commander> MakeCrypt() {
    auto pass = cma::cfg::groups::global.getPasword();
    if (!pass) {
        XLOG::t.t("Nothing.. ..");
        return {};
    }

    return std::make_unique<Commander>(pass.value());
}

// calculate additional size of buffer in bytes to compress DataSize
std::optional<size_t> Commander::CalcBufferOverhead(size_t data_size) const {
    if (!blockSize().has_value()) {
        XLOG::l("Impossible situation, crypt engine is absent");
        return {};
    }

    if (0 == blockSize().value()) {
        XLOG::l("Impossible situation, block is too short");
        return {};
    }

    auto block_size = blockSize().value();

    return block_size - (data_size % block_size);
}

}  // namespace cma::encrypt
