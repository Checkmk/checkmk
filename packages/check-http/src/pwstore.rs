// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use aes_gcm::{
    aead::{Aead, KeyInit, Result as AeadResult},
    aes::{cipher::consts::U16, Aes256},
    AesGcm, Nonce,
};
use anyhow::{anyhow, Result as AnyhowResult};
use scrypt::{scrypt, Params};
use std::{collections::HashMap, env, fs, path::PathBuf};

const PW_STORE_SECRET_FILE: &str = "etc/password_store.secret";
const OMD_ROOT: &str = "OMD_ROOT";

const VERSION_LENGTH: usize = 2;
const SALT_LENGTH: usize = 16;
const NONCE_LENGTH: usize = 16;
const TAG_LENGTH: usize = 16;

const SCRYPT_LOG_N: u8 = 14;
const SCRYPT_R: u32 = 8;
const SCRYPT_P: u32 = 1;
const KEY_SIZE: usize = 32;

type AesGcmCustom = AesGcm<Aes256, U16>;

pub fn password_from_store(pw_spec: &str) -> AnyhowResult<String> {
    let (pw_id, pwstore_path) = pw_spec
        .split_once(':')
        .ok_or_else(|| anyhow!("Invalid pwstore argument, expected <PW_ID>:<PWSTORE_FILE>"))?;
    let (pw_store_bytes, secret) = load_pw_store_bytes(pwstore_path)?;
    let pw_store = unpack_pw_store(&pw_store_bytes, &secret)?;

    lookup_pw(&pw_store, pw_id)
}

fn load_pw_store_bytes(pwstore_path: &str) -> AnyhowResult<(Vec<u8>, Vec<u8>)> {
    let omd_root = env::var(OMD_ROOT)?;
    if omd_root.is_empty() {
        return Err(anyhow!("Environment variable {} is empty", OMD_ROOT));
    }
    let omd_path = PathBuf::from(omd_root);

    Ok((
        fs::read(omd_path.join(pwstore_path))?,
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

fn lookup_pw(pw_store: &str, pw_id: &str) -> AnyhowResult<String> {
    let p: Option<HashMap<&str, &str>> = pw_store
        .lines()
        .map(|entry| entry.split_once(':'))
        .collect();
    let Some(parsed_store) = p else {
        return Err(anyhow!("Can't parse password store: Unexpected format."));
    };

    parsed_store
        .get(pw_id)
        .ok_or(anyhow!("Couldn't find requested ID in password store"))
        .map(|&pw| pw.to_owned())
}

#[cfg(test)]
mod test_pw_store {
    use crate::pwstore::{lookup_pw, unpack_pw_store};
    use std::num::ParseIntError;

    fn decode_hex(s: &str) -> Result<Vec<u8>, ParseIntError> {
        // https://stackoverflow.com/questions/52987181
        (0..s.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i + 2], 16))
            .collect()
    }

    #[test]
    fn test_decode_hex() {
        assert_eq!(decode_hex("00090a0b0cff").unwrap(), [0, 9, 10, 11, 12, 255]);
    }

    #[test]
    fn test_unpack_pw_store_with_test_vector() {
        // test vector from test_password_store.py
        let input = decode_hex(
            "\
        00003b1cedb92526621483f9ba140fbe\
        55f49916ae77a11a2ac93b4db0758061\
        71a62a8aedd3d1edd67e558385a98efe\
        be3c4c0ca364e54ff6ad2fa7ef48a0e8\
        8ed989283e9604e07da89301658f0370\
        d35bba1a8abf74bc971975\
        ",
        )
        .unwrap();
        let secret = b"password-secret";
        let output = String::from("Time is an illusion. Lunchtime doubly so.");

        assert_eq!(unpack_pw_store(&input, secret).unwrap(), output);
    }

    #[test]
    fn test_lookup_pw() {
        let pwstore = "my:password\nfoo:bar:baz\nbar: foo bar\nbaz:föö";
        assert_eq!(lookup_pw(pwstore, "my").unwrap(), "password".to_string());
        assert_eq!(lookup_pw(pwstore, "foo").unwrap(), "bar:baz".to_string());
        assert_eq!(lookup_pw(pwstore, "bar").unwrap(), " foo bar".to_string());
        assert_eq!(lookup_pw(pwstore, "baz").unwrap(), "föö".to_string());
    }

    #[test]
    fn test_lookup_pw_unexpected_format() {
        let pwstore = "foo:bar\nbarbaz";
        assert!(lookup_pw(pwstore, "foo").is_err());
    }

    #[test]
    fn test_lookup_pw_wrong_id() {
        let pwstore = "foo:bar\nbar:baz";
        assert!(lookup_pw(pwstore, "baz").is_err());
    }
}
