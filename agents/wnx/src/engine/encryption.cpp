// Windows Tools
#include "stdafx.h"

#include "encryption.h"

#include <string>
#include <string_view>

#include "cfg.h"
#include "logger.h"
#include "tools/_raii.h"

namespace cma::encrypt {
Commander::Commander() : algorithm_(Algorithm::kDefault) {
    crypt_provider_ = obtainContext();
    key_ = generateKey(Length::kDefault);

    checkAndConfigure();
}

Commander::Commander(const std::string &Password, Length KeyLength)
    : algorithm_(Algorithm::kDefault) {
    crypt_provider_ = obtainContext();
    key_ = deriveOpenSSLKey(Password, KeyLength, 1);

    checkAndConfigure();
}

Commander::Commander(const BYTE *key, DWORD KeySize)
    : algorithm_(Algorithm::kDefault) {
    crypt_provider_ = obtainContext();
    key_ = importKey(key, KeySize);

    checkAndConfigure();
}

Commander::~Commander() { cleanup(); }

void Commander::cleanup() {
    releaseKey();
    releaseContext();
}

std::tuple<bool, size_t> Commander::encode(void *InOut, size_t InputSize,
                                           size_t BufferSize,
                                           bool LastBlock) const {
    if (!available()) return {false, 0};

    auto input_size = static_cast<DWORD>(InputSize);
    if (input_size == 0) return {true, 0};
    if (nullptr == InOut) {
        XLOG::l.crit(XLOG_FLINE + " nullptr in param");
        return {false, 0};
    }

    if (!::CryptEncrypt(key_, 0, LastBlock, 0, static_cast<BYTE *>(InOut),
                        &input_size, static_cast<DWORD>(BufferSize))) {
        // special case, when error is recoverable
        if (GetLastError() == ERROR_MORE_DATA) return {false, input_size};

        XLOG::l.crit("Cannot encode buffer {}", GetLastError());
        return {false, 0};
    }

    return {true, input_size};
}

std::tuple<bool, size_t> Commander::decode(void *InOut, size_t InputSize,
                                           bool LastBlock) {
    if (!available()) return {false, 0};

    auto input_size = static_cast<DWORD>(InputSize);
    if (input_size == 0) return {true, 0};

    if (nullptr == InOut) {
        XLOG::l.crit(XLOG_FLINE + " nullptr in param");
        return {false, 0};
    }

    if (!::CryptDecrypt(key_, 0, LastBlock, 0, static_cast<BYTE *>(InOut),
                        &input_size)) {
        // special case, when error is recoverable
        if (GetLastError() == ERROR_MORE_DATA) return {false, input_size};

        XLOG::l.crit("Cannot decode buffer [{}]", GetLastError());
        return {false, 0};
    }

    return {true, input_size};
}

// called from ctor
HCRYPTPROV Commander::obtainContext() {
    HCRYPTPROV handle = 0;

    BOOL res = FALSE;

    if ((algorithm_ == CALG_AES_128) || (algorithm_ == CALG_AES_192) ||
        (algorithm_ == CALG_AES_256)) {
        res = ::CryptAcquireContext(&handle, nullptr, MS_ENH_RSA_AES_PROV,
                                    PROV_RSA_AES, CRYPT_VERIFYCONTEXT);
    } else {
        res = ::CryptAcquireContext(&handle, nullptr, MS_DEF_PROV,
                                    PROV_RSA_FULL, CRYPT_VERIFYCONTEXT);
    }
    if (!res) {
        XLOG::l.crit("Cannot obtain crypto context error is [{}]",
                     GetLastError());
        return 0;
    }

    return handle;
}

// called from destructor
void Commander::releaseContext() {
    //
    if (crypt_provider_) {
        ::CryptReleaseContext(crypt_provider_, 0);
        crypt_provider_ = 0;
    }
}

// called only from constructor
void Commander::checkAndConfigure() {
    if (!key_) {
        cleanup();
        return;
    }

    DWORD mode = CRYPT_MODE_CBC;
    auto pmode = reinterpret_cast<BYTE *>(&mode);
    if (!::CryptSetKeyParam(key_, KP_MODE, pmode, 0)) {
        XLOG::l.crit("Cannot set crypto mode error is [{}]", GetLastError());
        return;
    }

    // in fact, pkcs5 seems to be the only padding supported by MS bundled CSPs?
    mode = PKCS5_PADDING;
    if (!::CryptSetKeyParam(key_, KP_PADDING, pmode, 0)) {
        XLOG::l.crit("Cannot set pad mode error is [{}]", GetLastError());
        return;
    }

    XLOG::t.i("Modes for a key set correctly");
}

HCRYPTKEY Commander::generateKey(Length key_length) const {
    HCRYPTKEY hkey = 0;
    if (crypt_provider_ == 0) return 0;
    if (!::CryptGenKey(crypt_provider_, algorithm_,
                       static_cast<unsigned>(key_length) | CRYPT_EXPORTABLE,
                       &hkey)) {
        XLOG::l.crit(XLOG_FLINE + "Cannot generate key, error is [{}]",
                     GetLastError());
        return 0;
    }

    return hkey;
}

// #TODO revamp
HCRYPTKEY Commander::importKey(const BYTE *Key, DWORD KeySize) const {
    if (crypt_provider_ == 0) return 0;

    // the key structure we pass to the api needs to be "decorated"
    std::vector<BYTE> key_blob;

    // insert header
    BLOBHEADER hdr;
    hdr.bType = PLAINTEXTKEYBLOB;
    hdr.bVersion = CUR_BLOB_VERSION;
    hdr.reserved = 0;
    hdr.aiKeyAlg = algorithm_;

    auto insert_ptr = reinterpret_cast<BYTE *>(&hdr);
    key_blob.insert(key_blob.end(), insert_ptr,
                    insert_ptr + sizeof(BLOBHEADER));

    // insert size field
    insert_ptr = reinterpret_cast<BYTE *>(&KeySize);
    key_blob.insert(key_blob.end(), insert_ptr, insert_ptr + sizeof(DWORD));

    // insert the actual key
    key_blob.insert(key_blob.end(), Key, Key + KeySize);

    HCRYPTKEY hkey = 0;
    if (!::CryptImportKey(crypt_provider_, &key_blob[0],
                          static_cast<DWORD>(key_blob.size()), 0, 0, &hkey)) {
        XLOG::l.crit(XLOG_FLINE + " Cannot import key, error is [{}]",
                     GetLastError());
        return 0;
    }
    return hkey;
}

size_t Commander::keySize(ALG_ID AlgorithmId) {
    switch (AlgorithmId) {
        case CALG_AES_128:
            return 128;
        case CALG_AES_192:
            return 192;
        case CALG_AES_256:
        default:
            return 256;
    }
}

std::tuple<HCRYPTHASH, size_t> GetHash(HCRYPTPROV Provider) {
    HCRYPTHASH hash = 0;
    if (!::CryptCreateHash(Provider, Algorithm::kHash, 0, 0, &hash)) {
        XLOG::l("Can't create hash [{}]", GetLastError());
        return {};
    }
    DWORD hash_size = 0;
    DWORD sizeof_hashsize = sizeof(DWORD);

    if (!::CryptGetHashParam(hash, HP_HASHSIZE,
                             reinterpret_cast<BYTE *>(&hash_size),
                             &sizeof_hashsize, 0)) {
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

HCRYPTHASH DuplicateHash(HCRYPTHASH Hash) {
    HCRYPTHASH hash = 0;
    auto result = ::CryptDuplicateHash(Hash, 0, 0, &hash);
    if (!result) return 0;
    return hash;
}

std::optional<uint32_t> BlockSize(HCRYPTKEY Key) {
    DWORD block_length = 0;
    DWORD param_length = sizeof(block_length);
    if (!::CryptGetKeyParam(Key, KP_BLOCKLEN, (BYTE *)&block_length,
                            &param_length, 0)) {
        XLOG::l("Failure getting block len [{}]", GetLastError());
        return {};
    }
    return block_length;
}

std::optional<uint32_t> Commander::blockSize() const {
    if (!key_) return {};

    return BlockSize(key_);
}

// Stupid function from the LWA
HCRYPTKEY Commander::deriveOpenSSLKey(const std::string &Password,
                                      Length KeyLength, int iterations) {
    if (crypt_provider_ == 0) return 0;

    auto [base_hash, hash_size] = GetHash(crypt_provider_);

    ON_OUT_OF_SCOPE(if (base_hash)::CryptDestroyHash(base_hash));
    if (hash_size == 0) return 0;

    cma::ByteVector buffer;
    buffer.resize(hash_size);

    HCRYPTKEY hkey = 0;
    bool first_iteration = true;
    size_t key_offset = 0;
    size_t iv_offset = 0;

    auto key_size = (KeyLength == Length::kDefault)
                        ? keySize(algorithm_) / 8
                        : static_cast<size_t>(KeyLength);

    std::vector<BYTE> key(key_size);
    std::vector<BYTE> iv;

    while ((key_offset < key.size()) || (iv_offset < iv.size())) {
        HCRYPTHASH hash = DuplicateHash(base_hash);
        if (!hash) return 0;

        ON_OUT_OF_SCOPE(::CryptDestroyHash(hash));

        // after the first iteration, include the hash from the previous
        // iteration
        if (first_iteration) {
            first_iteration = false;
        } else {
            if (!HashData(hash, buffer)) return 0;
        }
        // include password in hash (duh!)
        if (!HashData(hash, Password)) return 0;

        // TODO include salt

        if (!GetHashData(hash, buffer)) return 0;

        for (int i = 1; i < iterations; ++i) {
            auto hash_inner = DuplicateHash(base_hash);
            if (hash_inner) return 0;

            ON_OUT_OF_SCOPE(::CryptDestroyHash(hash_inner));

            if (!HashData(hash_inner, buffer)) return 0;
            if (!GetHashData(hash_inner, buffer)) return 0;
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
                iv.resize(*block_size / 8);
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
    if (hkey && !::CryptSetKeyParam(hkey, KP_IV, &iv[0], 0)) {
        ::CryptDestroyKey(hkey);
        XLOG::l("Failure applying key [{}]", GetLastError());
        return 0;
    }

    return hkey;
}

void Commander::releaseKey() {
    if (key_) {
        ::CryptDestroyKey(key_);
        key_ = 0;
    }
}

std::optional<cma::ByteVector> Commander::getKey() const {
    if (!available()) return {};

    DWORD key_size = 0;
    if (!::CryptExportKey(key_, 0, PLAINTEXTKEYBLOB, 0, NULL, &key_size)) {
        XLOG::l("Failed to get key size, error [{}]", GetLastError());
        return {};
    }

    std::vector<BYTE> result;
    result.resize(key_size);
    if (!::CryptExportKey(key_, 0, PLAINTEXTKEYBLOB, 0, &result[0],
                          &key_size)) {
        XLOG::l("Failed to export key, error [{}]", GetLastError());
        return {};
    }

    // return only the key, not the meta info
    return std::vector<BYTE>(result.begin() + sizeof(BLOBHEADER), result.end());
}

bool Commander::randomizeBuffer(void *Buffer, size_t BufferSize) const {
    if (!available()) return false;

    if (!::CryptGenRandom(crypt_provider_, static_cast<DWORD>(BufferSize),
                          static_cast<BYTE *>(Buffer))) {
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

    auto p = pass.value();
    return std::make_unique<Commander>(p);
}

// calculate additional size of buffer in bytes to compress DataSize
std::optional<size_t> Commander::CalcBufferOverhead(size_t DataSize) const
    noexcept {
    if (!blockSize().has_value()) {
        XLOG::l("Impossible situation, crypt engine is absent");
        return {};
    }

    if (0 == blockSize().value()) {
        XLOG::l("Impossible situation, block is too short");
        return {};
    }

    auto block_size = blockSize().value();

    return block_size - (DataSize % block_size);
}

}  // namespace cma::encrypt
