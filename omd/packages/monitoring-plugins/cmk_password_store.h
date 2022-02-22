/* Replace passwords in command line from Check_MK password store */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <openssl/ossl_typ.h>
#include <openssl/evp.h>
#include <openssl/aes.h>
#include <openssl/bio.h>

/* Keep these constants in sync with `cmk/utils/encryption.py`. */
#define cmk_scrypt_N (1 << 14)
#define cmk_scrypt_r 8
#define cmk_scrypt_p 1
#define cmk_scrypt_keylen 32

void cmk_bail_out(const char *reason)
{
    fprintf(stderr, "Invalid --pwstore= option: %s\n", reason);
    exit(3);
}


typedef struct cmk_header_ctx
{
    uint16_t version;
    unsigned char salt[AES_BLOCK_SIZE];
    unsigned char iv[AES_BLOCK_SIZE];
    unsigned char tag[AES_BLOCK_SIZE];
} cmk_header_ctx;

#define cmk_header_length 50


cmk_header_ctx *cmk_header_new(void)
{
    return (cmk_header_ctx *)calloc(1, sizeof(cmk_header_ctx));
}


void cmk_header_free(cmk_header_ctx *ctx)
{
    free(ctx);
}


ssize_t cmk_header_parse(
        cmk_header_ctx *ctx,
        const unsigned char *buffer, size_t buflen)
{
    if (buflen < cmk_header_length) {
        return -1;
    }
    // Code uses big endian on the Python side so we cannot simply memcpy.
    ctx->version += buffer[0] << 8 * 1;
    ctx->version += buffer[1] << 8 * 0;
    memcpy(ctx->salt, &buffer[2], AES_BLOCK_SIZE);
    memcpy(ctx->iv, &buffer[18], AES_BLOCK_SIZE);
    memcpy(ctx->tag, &buffer[34], AES_BLOCK_SIZE);
    return 0;
}


/* outbuf is allocated on success */
ssize_t cmk_read_file(const char *pathname, unsigned char **outbuf)
{
    struct stat statbuf;
    if (stat(pathname, &statbuf) != 0) {
        goto err;
    }
    size_t outlen = statbuf.st_size;

    unsigned char *buf = malloc(outlen);
    if (buf == NULL) {
        goto err;
    }

    FILE *stream = fopen(pathname, "rb");
    if (stream == NULL) {
        goto err_buf;
    }

    outlen = fread(buf, sizeof(unsigned char), outlen, stream);
    if (ferror(stream) != 0) {
        goto err_file;
    }

    fclose(stream);
    *outbuf = buf;
    return outlen;

err_file:
    fclose(stream);

err_buf:
    free(buf);

err:
    errno = 0;
    return -1;
}


ssize_t cmk_aes_gcm_decrypt(
        const unsigned char *key,
        const unsigned char *iv, size_t ivlen,
        const unsigned char *tag, size_t taglen,
        const unsigned char *inbuf, size_t inlen,
        unsigned char *outbuf)
{
    /* See also `openssl/demos/cipher/aesgcm.c`. */
    int outlen = -1;
    EVP_CIPHER_CTX *ctx = NULL;
    if ((ctx = EVP_CIPHER_CTX_new()) == NULL) {
        puts("failed to create cipher context");
        goto err;
    }
    /* Select cipher */
    if (!EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL)) {
        puts("failed to select the cipher");
        goto err_ciph;
    }
    /* Set key and IV */
    if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, ivlen, NULL)) {
        puts("failed to set the IV length");
        goto err_ciph;
    }
    /* Set tag */
    if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, taglen, (void *)tag)) {
        puts("failed to set the tag");
        goto err_ciph;
    }
    if (!EVP_DecryptInit_ex(ctx, NULL, NULL, key, iv)) {
        puts("failed to set the key and IV");
        goto err_ciph;
    }
    /* Decrypt input */
    if (!EVP_DecryptUpdate(ctx, outbuf, &outlen, inbuf, inlen)) {
        puts("failed to decrypt the ciphertext");
        goto err_ciph;
    }
    /* Verify tag */
    int finlen = 0;
    int rv = -1;
    if ((rv = EVP_DecryptFinal_ex(ctx, NULL, &finlen)) <= 0) {
        puts("failed tag validation");
        goto err_ciph;
    }

    EVP_CIPHER_CTX_free(ctx);
    return outlen + finlen;

err_ciph:
    EVP_CIPHER_CTX_free(ctx);

err:
    return -1;
}


/* outbuf is allocated on success */
ssize_t cmk_decrypt(
    /* etc/password_store.secret */
    const char *pass, size_t passlen,
    /* var/check_mk/stored_passwords */
    const unsigned char *pwfile, size_t pwfilelen,
    unsigned char **outbuf)
{
    ssize_t outlen = -1;
    cmk_header_ctx *header = cmk_header_new();
    if (header == NULL) {
        puts("failed to allocate header context");
        goto err;
    }
    cmk_header_parse(header, pwfile, pwfilelen);

    unsigned char key[cmk_scrypt_keylen] = {0};
    EVP_PBE_scrypt(
            pass, passlen,
            header->salt, sizeof header->salt,
            cmk_scrypt_N, cmk_scrypt_r, cmk_scrypt_p, 0,
            key, sizeof key);

    unsigned char *buf = malloc(pwfilelen);
    if (buf == NULL) {
        goto err_header;
    }
    outlen = cmk_aes_gcm_decrypt(
            key, header->iv, sizeof header->iv, header->tag, sizeof header->tag,
            &pwfile[cmk_header_length], pwfilelen - cmk_header_length, buf);
    if (outlen <= 0) {
        goto err_buf;
    }

    cmk_header_free(header);
    *outbuf = buf;
    return outlen;

err_buf:
    free(buf);

err_header:
    cmk_header_free(header);

err:
    return -1;
}


char *cmk_lookup_password(const char *pw_id)
{
    const char *omd_root = getenv("OMD_ROOT");
    if (!omd_root) {
        cmk_bail_out("Environment variable OMD_ROOT is missing.");
    }

    char pwfilepath[4096];  /* PATH_MAX from <linux/limits.h> */
    int ok = snprintf(
        pwfilepath, sizeof pwfilepath,
        "%s/var/check_mk/stored_passwords", omd_root);
    if (ok < 0 || ok >= sizeof pwfilepath) {
        cmk_bail_out("stored_passwords path too long");
    }
    unsigned char *pwfile = NULL;
    ssize_t pwfilelen = cmk_read_file(pwfilepath, &pwfile);
    if (pwfilelen == -1) {
        cmk_bail_out("Cannot open stored_passwords file");
    }

    char pwsecretpath[4096];  /* PATH_MAX from <linux/limits.h> */
    ok = snprintf(
        pwsecretpath, sizeof pwsecretpath,
        "%s/etc/password_store.secret", omd_root);
    if (ok < 0 || ok >= sizeof pwsecretpath) {
        cmk_bail_out("passwort_store.secret path too long");
    }
    unsigned char *pwsecret = NULL;
    ssize_t pwsecretlen = cmk_read_file(pwsecretpath, &pwsecret);
    if (pwsecretlen == -1) {
        cmk_bail_out("Cannot open password_store.secret file.");
    }

    unsigned char *text = NULL;
    ssize_t textlen = -1;
    if ((textlen = cmk_decrypt(
            pwsecret, pwsecretlen, pwfile, pwfilelen, &text)) == -1) {
       cmk_bail_out("Could not decrypt password store");
    }
    free(pwfile);
    free(pwsecret);
    if (text == NULL) {
        cmk_bail_out("Could not decrypt password store");
    }

    // The strict aliasing rule has an exception for signed/unsigned types
    // so the cast on the next line is OK.
    char *line = strtok(strndup((const char *)text, textlen), "\n");
    while (line) {
        if (strlen(line) == 0)
            continue;
        if (strncmp(line, pw_id, strlen(pw_id)) == 0 && line[strlen(pw_id)] == ':') {
            free(text);
            return line + strlen(pw_id) + 1;
        }
        line = strtok(NULL, "\n");
    }
    free(text);
    return NULL;
}


char **cmk_replace_passwords(int *argc, char **argv)
{
    if (*argc < 2)
        return argv; /* command line too short */
    else if (strncmp(argv[1], "--pwstore=", 10))
        return argv; /* no password store in use */

    /* --pwstore=4@4@web,6@0@foo
      In the 4th argument at char 4 replace the following bytes
      with the passwords stored under the ID 'web'
      In the 6th argument at char 0 insert the password with the ID 'foo'
    */

    /* Create copy of arguments and drop first argument */
    char **new_argv = (char **)malloc(sizeof(char *) * (*argc + 1));
    new_argv[0] = argv[0];
    unsigned i;
    for (i=2; i<*argc; i++)
        new_argv[i-1] = argv[i]; /* drop first option */
    new_argv[*argc] = NULL;
    *argc = (*argc) - 1; /* first option was dropped */

    /* Create copy of stuff after --pwstore=... so that we can strtok around there */
    char *info = strdup(argv[1] + 10);
    char *p = info;
    char *saveptr;
    while (true) {
        char *tok = strtok_r(p, "@", &saveptr);
        if (tok == NULL)
            break; // finished
        p = NULL; /* subsequent calls to strtok with NULL pointer */
        int argv_index = atoi(tok);
        if (argv_index >= *argc) {
            cmk_bail_out("Invalid argument index");
        }

        tok = strtok_r(NULL, "@", &saveptr);
        if (tok == NULL)
            cmk_bail_out("Missing second @");
        int char_index = atoi(tok);
        if (0 && char_index > strlen(argv[argv_index]))
            cmk_bail_out("Invalid character index");

        char *pw_id = strtok_r(NULL, ",", &saveptr);
        if (pw_id == NULL)
            cmk_bail_out("Missing password ID");

        char *new_arg = strdup(new_argv[argv_index]);
        char *password = cmk_lookup_password(pw_id);
        if (!password)
            cmk_bail_out("No password with that ID found.");
        if (strlen(password) + char_index > strlen(new_arg))
            cmk_bail_out("Password is too long for argument.");
        memcpy(new_arg + char_index, password, strlen(password));
        new_argv[argv_index] = new_arg;
    }
    free(info);
    return new_argv;
}


#define CMK_REPLACE_PASSWORDS do { argv = cmk_replace_passwords(&argc, argv); } while (false)
