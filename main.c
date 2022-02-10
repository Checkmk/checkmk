#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <unistd.h>
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <openssl/aes.h>
#include <openssl/bio.h>

/* Keep these constants in sync with `cmk/utils/encryption.py`. */
#define cmk_scrypt_N 16384
#define cmk_scrypt_r 8
#define cmk_scrypt_p 1
#define cmk_scrypt_keylen 32

typedef struct cmk_header_ctx {
  uint16_t version;
  unsigned char salt[AES_BLOCK_SIZE];
  unsigned char nonce[AES_BLOCK_SIZE];
  unsigned char tag[AES_BLOCK_SIZE];
} cmk_header_ctx;

#define cmk_header_length 50

cmk_header_ctx* cmk_header_new(void) {
  return (cmk_header_ctx*)calloc(1, sizeof(cmk_header_ctx));
}

void cmk_header_free(cmk_header_ctx *ctx) {
  free(ctx);
}

ssize_t cmk_header_parse(cmk_header_ctx *ctx,
                         const unsigned char *buffer, size_t buflen) {
  if (buflen < cmk_header_length) {
    return -1;
  }
  // Code uses big endian on the Python side so we cannot simply memcpy.
  ctx->version += buffer[0] << 8 * 1;
  ctx->version += buffer[1] << 8 * 0;
  memcpy(ctx->salt, &buffer[2], AES_BLOCK_SIZE);
  memcpy(ctx->nonce, &buffer[18], AES_BLOCK_SIZE);
  memcpy(ctx->tag, &buffer[34], AES_BLOCK_SIZE);
  return 0;
}

/* outbuf is allocated on success */
ssize_t cmk_read_file(const char *pathname, unsigned char *outbuf) {
  struct stat statbuf;
  if (stat(pathname, &statbuf) != 0) {
    goto err;
  }
  size_t outlen = statbuf.st_size;

  if ((outbuf = (unsigned char *)malloc(sizeof(unsigned char) * outlen)) == NULL) {
    goto err_buf;
  }

  FILE *stream = NULL;
  if ((stream = fopen(pathname, "rb")) == NULL) {
    goto err_buf;
  }

  size_t len = fread(outbuf, sizeof(unsigned char), outlen, stream);
  if (ferror(stream) != 0) {
    goto err_file;
  }

  fclose(stream);
  return outlen;

err_file:
  fclose(stream);

err_buf:
  free(outbuf);
  outbuf = NULL;

err:
  errno = 0;
  return -1;
}

ssize_t cmk_aes_gcm_decrypt(
    const unsigned char *key,
    const unsigned char *iv,
    const unsigned char *tag,
    const unsigned char *in, size_t inlen,
    unsigned char *outbuf) {
  /* See also `openssl/demos/cipher/aesgcm.c`. */
  int outlen = -1;
  EVP_CIPHER_CTX *ctx = NULL;
  if ((ctx = EVP_CIPHER_CTX_new()) == NULL) {
    puts("failed to create cipher context");
    goto err;
  }
  /* Select cipher */
  if (!EVP_DecryptInit(ctx, EVP_aes_256_gcm(), NULL, NULL)) {
    puts("failed to select the cipher");
    goto err_ciph;
  }
  /* Set IV length to 16 bytes (but we want nonce?) */
  if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_SET_IVLEN, sizeof iv, NULL)) {
    puts("failed to set the IV length");
    goto err_ciph;
  }
  /* Set key and IV */
  if (!EVP_DecryptInit_ex(ctx, NULL, NULL, key, iv)) {
    puts("failed to set the key and IV");
    goto err_ciph;
  }
  /* Decrypt input */
  if (!EVP_DecryptUpdate(ctx, outbuf, &outlen, in, inlen)) {
    puts("failed to decrypt the ciphertext");
    goto err_ciph;
  }
  BIO_dump_fp(stdout, (char*)outbuf, outlen);
  /* Set tag */
  if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_SET_TAG, sizeof tag, (void *)tag)) {
    puts("failed to set the tag");
    goto err_ciph;
  }
  /* Verify tag */
  int rv = -1;
  if ((rv = EVP_DecryptFinal_ex(ctx, outbuf, &outlen)) <= 0) {
    puts("failed tag validation");
    goto err_ciph;
  }

  EVP_CIPHER_CTX_free(ctx);
  return outlen;

err_ciph:
  EVP_CIPHER_CTX_free(ctx);

err:
  return -1;
}

int test_parser(void) {
  int result = 0;

  cmk_header_ctx *ctx = cmk_header_new();
  if (ctx == NULL) {
    return -1;
  }

  const unsigned char buf[] = {
    0x01, 0x02,
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
    0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
    0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
    0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f
  };
  cmk_header_parse(ctx, buf, sizeof buf);

  if (ctx->version != 258) {
    result |= (1 << 0);
  }
  if (memcmp(ctx->salt,
             "\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f",
             AES_BLOCK_SIZE) != 0) {
    result |= 1 << 1;
  }
  if (memcmp(ctx->nonce,
             "\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f",
             AES_BLOCK_SIZE) != 0) {
    result |= 1 << 2;
  }
  if (memcmp(ctx->tag,
             "\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f",
             AES_BLOCK_SIZE) != 0) {
    result |= 1 << 3;
  }

  cmk_header_free(ctx);
  return result;
}

int test_cipher(void) {
  int result = 0;
  const char passphrase[] =
    /* etc/password_store.secret */
    "JBLVRU76MFHTCXNXXV7NY6F36GL81QMA"
    "Z1U0G5ZFQTKRPIU9ILJSKDEYAOY202B7"
    "JOGQ8YW2S6J4122VVL35OULW03KMFA8Z"
    "U00CJQKHPZVW4Q13X4ANICFN29GN1G37"
    "ANXVJA77VZ2OI5RZ8KJVDEUVBUKKZJZ1"
    "71LCM31SK25VRV7T31C4YANR0MN6G37J"
    "GP7RFWZ1H7HWFVKPJ7N20UCW03KX857N"
    "IWFJRTG8EEKY95DBD7VZ3MLSX85X62ZV";
  const unsigned char pw_file[] = {
    /* var/check_mk/stored_passwords */
    0x00, 0x00, 0xbc, 0xc5, 0x9f, 0x94, 0x31, 0xe3,
    0x0e, 0x51, 0x71, 0xa4, 0xd8, 0xcb, 0xf7, 0x24,
    0x88, 0xa6, 0x26, 0x60, 0xc4, 0xde, 0xa7, 0x63,
    0x8b, 0xe5, 0x54, 0x97, 0xb5, 0x1b, 0x74, 0xa0,
    0xf5, 0xb2, 0xc1, 0x04, 0x01, 0xb4, 0x2f, 0x6a,
    0x39, 0xf1, 0x36, 0x53, 0x5f, 0xb3, 0x48, 0xb3,
    0xae, 0x38, 0x27, 0x51, 0xb7, 0xc2, 0xbe, 0x6e,
    0x0c, 0x2c, 0x7d, 0xda, 0x7d, 0x8c, 0x08, 0xf9,
    0x66, 0xf9};
  cmk_header_ctx *header = cmk_header_new();
  if (header == NULL) {
    return -1;
  }
  cmk_header_parse(header, pw_file, sizeof pw_file);

  unsigned char key[cmk_scrypt_keylen] = {0};
  EVP_PBE_scrypt(
      passphrase, 256,
      header->salt, sizeof header->salt,
      cmk_scrypt_N, cmk_scrypt_r, cmk_scrypt_p, 0,
      key, sizeof key);

  unsigned char text[sizeof pw_file] = {0};

  ssize_t textlen = cmk_aes_gcm_decrypt(
      key, header->nonce, header->tag,
      &pw_file[cmk_header_length], (sizeof pw_file) - cmk_header_length,
      text);
  if (textlen <= 0) {
    result |= 1 << 0;
  } else {
    printf("deciphered: %s\n", text);
  }

  cmk_header_free(header);
  return result;
}

void test(void) {
  printf("parser: %d\n", test_parser());
  printf("cipher: %d\n", test_cipher());
}

int main() {
  // Compile with `gcc main.c -lssl -lcrypto`.
  test();
  return 0;
}
