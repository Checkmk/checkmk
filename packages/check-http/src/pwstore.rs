use aes_gcm::{
    aead::{Aead, KeyInit, Result as AeadResult},
    aes::{cipher::consts::U16, Aes256},
    AesGcm, Nonce,
};
use anyhow::{anyhow, Result as AnyhowResult};
use scrypt::{scrypt, Params};
use std::{collections::HashMap, env, fs, path::PathBuf};

const PW_STORE_FILE: &str = "var/check_mk/stored_passwords";
const PW_STORE_SECRET_FILE: &str = "etc/password_store.secret";
const OMD_ROOT: &str = "OMD_ROOT";
const PW_STORE_ARG: &str = "--pwstore=";

const VERSION_LENGTH: usize = 2;
const SALT_LENGTH: usize = 16;
const NONCE_LENGTH: usize = 16;
const TAG_LENGTH: usize = 16;

const SCRYPT_LOG_N: u8 = 14;
const SCRYPT_R: u32 = 8;
const SCRYPT_P: u32 = 1;
const KEY_SIZE: usize = 32;

type AesGcmCustom = AesGcm<Aes256, U16>;

pub fn patch_args(args: env::Args) -> Vec<String> {
    let mut args_vec: Vec<_> = args.collect();

    let first_arg = &args_vec[1];
    if !first_arg.starts_with(PW_STORE_ARG) {
        return args_vec;
    };

    let parts: Vec<_> = first_arg[PW_STORE_ARG.len()..].splitn(3, '@').collect();

    if parts.len() != 3 {
        println!("pwstore: Invalid --pwstore entry: {}", first_arg);
        std::process::exit(3);
    }

    let target_arg_num: usize = parts[0].parse().unwrap();
    let insert_pos: usize = parts[1].parse().unwrap();
    let pw_id = parts[2];

    let (pw_store_bytes, secret) = load_pw_store_bytes().unwrap();
    let pw_store = unpack_pw_store(&pw_store_bytes, &secret).unwrap();
    let pw = lookup_pw(&pw_store, pw_id).unwrap();

    let target_arg = &args_vec[target_arg_num];
    args_vec[target_arg_num] = format!(
        "{}{}{}",
        &target_arg[..insert_pos],
        &pw,
        &target_arg[insert_pos + pw.len()..]
    );

    args_vec.remove(1);

    args_vec
}

fn load_pw_store_bytes() -> AnyhowResult<(Vec<u8>, Vec<u8>)> {
    let omd_root = env::var(OMD_ROOT)?;
    if omd_root.is_empty() {
        return Err(anyhow!("Environment variable {} is empty", OMD_ROOT));
    }
    let omd_path = PathBuf::from(omd_root);

    Ok((
        fs::read(omd_path.join(PW_STORE_FILE))?,
        fs::read(omd_path.join(PW_STORE_SECRET_FILE))?,
    ))
}

fn unpack_pw_store(pw_store_bytes: &[u8], secret: &[u8]) -> AnyhowResult<String> {
    let (salt, nonce, tag, ciphertext) = unpack_cipher_contents(pw_store_bytes);
    let key = derive_key(secret, salt)?;
    let plaintext = decrypt(ciphertext, &key, nonce, tag)?;

    Ok(String::from_utf8(plaintext)?)
}

fn unpack_cipher_contents(pw_store_bytes: &[u8]) -> (&[u8], &[u8], &[u8], &[u8]) {
    let salt_start = VERSION_LENGTH;
    let nonce_start = VERSION_LENGTH + SALT_LENGTH;
    let tag_start = nonce_start + NONCE_LENGTH;
    let ciphertext_start = tag_start + TAG_LENGTH;

    (
        &pw_store_bytes[salt_start..nonce_start],
        &pw_store_bytes[nonce_start..tag_start],
        &pw_store_bytes[tag_start..ciphertext_start],
        &pw_store_bytes[ciphertext_start..],
    )
}

fn derive_key(secret: &[u8], salt: &[u8]) -> AnyhowResult<[u8; 32]> {
    let params = Params::new(SCRYPT_LOG_N, SCRYPT_R, SCRYPT_P, KEY_SIZE)?;
    let mut key: [u8; KEY_SIZE] = [0; KEY_SIZE];
    scrypt(secret, salt, &params, &mut key)?;
    Ok(key)
}

fn decrypt(ciphertext: &[u8], key: &[u8], nonce: &[u8], tag: &[u8]) -> AeadResult<Vec<u8>> {
    let cipher = AesGcmCustom::new(key.into());
    let tagged_ciphertext: Vec<u8> = [ciphertext, tag].concat();
    cipher.decrypt(Nonce::from_slice(nonce), tagged_ciphertext.as_slice())
}

fn lookup_pw<'store>(pw_store: &'store str, pw_id: &'store str) -> AnyhowResult<&'store str> {
    let p: Option<HashMap<&str, &str>> = pw_store
        .split_whitespace()
        .map(|entry| entry.split_once(':'))
        .collect();
    let Some(parsed_store) = p else {
        return Err(anyhow!("Can't parse password store: Unexpected format."));
    };

    parsed_store
        .get(pw_id)
        .ok_or(anyhow!("Couldn't find requested ID in password store"))
        .map(|&pw| pw)
}
