#include "Crypto.h"
#include <stdexcept>
#include "Environment.h"
#include "WinApiAdaptor.h"
#include "types.h"
#include "win_error.h"

Crypto::Crypto(const WinApiAdaptor &winapi)
    : _algorithm(DEFAULT_ALGORITHM), _winapi(winapi) {
    _provider = initContext();
    _key = genKey(KEY_LEN_DEFAULT);
    configureKey();
}

Crypto::Crypto(const std::string &password, const WinApiAdaptor &winapi,
               KeyLength key_length)
    : _algorithm(DEFAULT_ALGORITHM), _winapi(winapi) {
    _provider = initContext();
    deriveOpenSSLKey(password, key_length, 1);
    configureKey();
}

Crypto::Crypto(const BYTE *key, DWORD key_size, const WinApiAdaptor &winapi)
    : _algorithm(DEFAULT_ALGORITHM), _winapi(winapi) {
    _provider = initContext();
    _key = importKey(key, key_size);
    configureKey();
}

Crypto::~Crypto() {
    releaseKey(_key);
    releaseContext();
}

void Crypto::checked(BOOL result, const char *failMessage) const {
    if (!result) {
        throw win_exception(_winapi, failMessage);
    }
}

DWORD Crypto::encrypt(BYTE *input, DWORD input_size, DWORD buffer_size,
                      BOOL fin) {
    if (!_winapi.CryptEncrypt(_key, 0, fin, 0, input, &input_size,
                              buffer_size)) {
        throw win_exception(_winapi, "failed to encrypt data");
    }
    return input_size;
}

DWORD Crypto::decrypt(BYTE *input, DWORD input_size, BOOL fin) {
    if (!_winapi.CryptDecrypt(_key, 0, fin, 0, input, &input_size)) {
        throw win_exception(_winapi, "failed to decrypt data");
    }
    return input_size;
}

HCRYPTPROV Crypto::initContext() {
    HCRYPTPROV result;

    // this actually matches all versions before vista but since we can't
    // support aes
    // on win2k anyway, xp and 2003 are the only relevant versions from the
    // pre-Vista era

    //    bool win_xp = Environment::winVersion() < 0x0600;

    BOOL res;

    if ((_algorithm == CALG_AES_128) || (_algorithm == CALG_AES_192) ||
        (_algorithm == CALG_AES_256)) {
        res = _winapi.CryptAcquireContext(&result, NULL, MS_ENH_RSA_AES_PROV,
                                          PROV_RSA_AES, CRYPT_VERIFYCONTEXT);
    } else {
        res = _winapi.CryptAcquireContext(&result, NULL, MS_DEF_PROV,
                                          PROV_RSA_FULL, CRYPT_VERIFYCONTEXT);
    }
    /*
        if (!res && (_winapi.GetLastError() ==
       static_cast<DWORD>(NTE_BAD_KEYSET))) {
            res = _winapi.CryptAcquireContext(&result, NULL, MS_DEF_PROV,
       PROV_RSA_FULL, CRYPT_NEWKEYSET);
        }
    */
    if (!res) {
        throw win_exception(_winapi, "failed to acquire context");
    }

    return result;
}

void Crypto::configureKey() {
    DWORD mode = CRYPT_MODE_CBC;
    if (!_winapi.CryptSetKeyParam(_key, KP_MODE, (BYTE *)&mode, 0)) {
        throw win_exception(_winapi, "failed to set cbc mode");
    }

    // in fact, pkcs5 seems to be the only padding supported by MS bundled CSPs?
    mode = PKCS5_PADDING;
    if (!_winapi.CryptSetKeyParam(_key, KP_PADDING, (BYTE *)&mode, 0)) {
        throw win_exception(_winapi, "failed to set padding");
    }
}

void Crypto::releaseContext() { _winapi.CryptReleaseContext(_provider, 0); }

HCRYPTKEY Crypto::genKey(KeyLength key_length) const {
    HCRYPTKEY result;
    if (!_winapi.CryptGenKey(_provider, _algorithm,
                             key_length | CRYPT_EXPORTABLE, &result)) {
        throw std::runtime_error(get_win_error_as_string(_winapi));
    }

    return result;
}

HCRYPTKEY Crypto::importKey(const BYTE *key, DWORD key_size) const {
    // the key structure we pass to the api needs to be "decorated"
    std::vector<BYTE> key_blob;

    // insert header
    BLOBHEADER hdr;
    hdr.bType = PLAINTEXTKEYBLOB;
    hdr.bVersion = CUR_BLOB_VERSION;
    hdr.reserved = 0;
    hdr.aiKeyAlg = _algorithm;

    BYTE *insert_ptr = reinterpret_cast<BYTE *>(&hdr);
    key_blob.insert(key_blob.end(), insert_ptr,
                    insert_ptr + sizeof(BLOBHEADER));

    // insert size field
    insert_ptr = reinterpret_cast<BYTE *>(&key_size);
    key_blob.insert(key_blob.end(), insert_ptr, insert_ptr + sizeof(DWORD));

    // insert the actual key
    key_blob.insert(key_blob.end(), key, key + key_size);

    HCRYPTKEY result;
    if (!_winapi.CryptImportKey(_provider, &key_blob[0], key_blob.size(), 0, 0,
                                &result)) {
        throw win_exception(_winapi, "failed to import key");
    }
    return result;
}

size_t Crypto::keySize(ALG_ID algorithm) {
    switch (algorithm) {
        case CALG_AES_128:
            return 128;
        case CALG_AES_192:
            return 192;
        case CALG_AES_256:
            return 256;
        default:
            throw std::runtime_error(
                "can't derive key size for that algorithm");
    }
}

void Crypto::deriveOpenSSLKey(const std::string &password, KeyLength key_length,
                              int iterations) {
    HCRYPTHASH hash_template;

    checked(_winapi.CryptCreateHash(_provider, HASH_ALGORITHM, 0, 0,
                                    &hash_template),
            "failed to create hash");

    OnScopeExit hashDeleter(
        [this, hash_template]() { _winapi.CryptDestroyHash(hash_template); });

    std::vector<BYTE> buffer;

    {  // limit scope fo hash_size_size
        DWORD hash_size;
        DWORD hash_size_size = sizeof(DWORD);
        checked(
            _winapi.CryptGetHashParam(hash_template, HP_HASHSIZE,
                                      (BYTE *)&hash_size, &hash_size_size, 0),
            "failed to retrieve hash size");
        buffer.resize(hash_size);
    }

    bool first_iteration = true;
    size_t key_offset = 0;
    size_t iv_offset = 0;

    int key_size = key_length;
    if (key_size == 0) {
        key_size = keySize(_algorithm) / 8;
    }

    std::vector<BYTE> key(key_size);
    std::vector<BYTE> iv;

    while ((key_offset < key.size()) || (iv_offset < iv.size())) {
        HCRYPTHASH hash;
        checked(_winapi.CryptDuplicateHash(hash_template, 0, 0, &hash),
                "failed to duplicate hash");

        // after the first iteration, include the hash from the previous
        // iteration
        if (first_iteration) {
            first_iteration = false;
        } else {
            checked(_winapi.CryptHashData(hash, &buffer[0], buffer.size(), 0),
                    "failed to hash data");
        }
        // include password in hash (duh!)
        checked(_winapi.CryptHashData(hash, (BYTE *)&password[0],
                                      password.size(), 0),
                "failed to hash data");

        // TODO include salt

        DWORD buffer_size = buffer.size();
        checked(_winapi.CryptGetHashParam(hash, HP_HASHVAL, &buffer[0],
                                          &buffer_size, 0),
                "failed to retrieve hash");

        for (int i = 1; i < iterations; ++i) {
            HCRYPTHASH hash_inner;
            checked(
                _winapi.CryptDuplicateHash(hash_template, 0, 0, &hash_inner),
                "failed to duplicate hash");
            checked(
                _winapi.CryptHashData(hash_inner, &buffer[0], buffer.size(), 0),
                "failed to hash data");
            buffer_size = buffer.size();
            checked(_winapi.CryptGetHashParam(hash_inner, HP_HASHVAL,
                                              &buffer[0], &buffer_size, 0),
                    "failed to retrieve hash");
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
                _key = importKey(&key[0], key.size());
                iv.resize(blockSize() / 8);
            }
        }
        if (usable_bytes > key_bytes) {
            size_t iv_bytes = std::min<size_t>(usable_bytes - key_bytes,
                                               iv.size() - iv_offset);
            memcpy(&iv[iv_offset], &buffer[key_bytes], iv_bytes);
            iv_offset += iv_bytes;
        }
    }

    // apply iv
    checked(_winapi.CryptSetKeyParam(_key, KP_IV, &iv[0], 0),
            "failed to set IV");
}

void Crypto::releaseKey(HCRYPTKEY key) { _winapi.CryptDestroyKey(key); }

std::vector<BYTE> Crypto::getKey() const {
    std::vector<BYTE> result;

    DWORD key_size = 0;
    if (!_winapi.CryptExportKey(_key, 0, PLAINTEXTKEYBLOB, 0, NULL,
                                &key_size)) {
        throw win_exception(_winapi, "failed to export key");
    }

    result.resize(key_size);
    if (!_winapi.CryptExportKey(_key, 0, PLAINTEXTKEYBLOB, 0, &result[0],
                                &key_size)) {
        throw win_exception(_winapi, "failed to export key");
    }

    // return only the key, not the meta info
    return std::vector<BYTE>(result.begin() + sizeof(BLOBHEADER), result.end());
}

DWORD Crypto::blockSize() const {
    DWORD block_length;
    DWORD param_length = sizeof(block_length);
    if (!_winapi.CryptGetKeyParam(_key, KP_BLOCKLEN, (BYTE *)&block_length,
                                  &param_length, 0)) {
        throw win_exception(_winapi, "failed to query block length");
    }
    return block_length;
}

void Crypto::random(BYTE *buffer, size_t buffer_size) {
    if (!_winapi.CryptGenRandom(_provider, static_cast<DWORD>(buffer_size),
                                static_cast<BYTE *>(buffer))) {
        throw win_exception(_winapi, "failed to generate random data");
    }
}
