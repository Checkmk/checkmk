use check_cert::check;
use check_cert::checker::certificate::{self, Config as CertConfig};

// Taken from `x509-parser`.
static DER: &[u8] = include_bytes!("../assets/IGC_A.der");

static SERIAL: &str = "39:11:45:10:94";
static PUBKEY_ALG: &str = "RSA";
static PUBKEY_SZ: usize = 2048;

fn s(s: &str) -> Option<String> {
    Some(String::from(s))
}

#[test]
fn test_cert_ok() {
    let coll = certificate::check(
        DER,
        CertConfig::builder()
            .serial(s(SERIAL))
            .subject_cn(s("IGC/A"))
            .subject_o(s("PM/SGDN"))
            .subject_ou(s("DCSSI"))
            .issuer_cn(s("IGC/A"))
            .issuer_o(s("PM/SGDN"))
            .issuer_ou(s("DCSSI"))
            .issuer_st(s("France"))
            .issuer_c(s("FR"))
            .signature_algorithm(s("1.2.840.113549.1.1.5"))
            .pubkey_algorithm(s(PUBKEY_ALG))
            .pubkey_size(Some(PUBKEY_SZ))
            .build(),
    );
    assert_eq!(check::exit_code(&coll), 2);
    assert_eq!(
        coll.to_string(),
        format!(
            "Subject CN: IGC/A, Certificate expired (Oct 17 14:29:22 2020 +00:00) (!!)\n\
            Subject CN: IGC/A\n\
            Subject O: PM/SGDN\n\
            Subject OU: DCSSI\n\
            Serial number: {SERIAL}\n\
            Issuer CN: IGC/A\n\
            Issuer O: PM/SGDN\n\
            Issuer OU: DCSSI\n\
            Issuer ST: France\n\
            Issuer C: FR\n\
            Certificate signature algorithm: sha1WithRSAEncryption\n\
            Public key algorithm: {PUBKEY_ALG}\n\
            Public key size: {PUBKEY_SZ}\n\
            Certificate expired (Oct 17 14:29:22 2020 +00:00) (!!)"
        )
    );
}

#[test]
fn test_cert_wrong_serial() {
    let serial = "01:02:03:04:05";
    let coll = certificate::check(
        DER,
        CertConfig::builder()
            .serial(s(serial))
            .subject_cn(s("IGC/A"))
            .subject_o(s("PM/SGDN"))
            .subject_ou(s("DCSSI"))
            .issuer_cn(s("IGC/A"))
            .issuer_o(s("PM/SGDN"))
            .issuer_ou(s("DCSSI"))
            .issuer_st(s("France"))
            .issuer_c(s("FR"))
            .build(),
    );
    assert_eq!(check::exit_code(&coll), 2);
    assert_eq!(
        coll.to_string(),
        format!(
            "Subject CN: IGC/A, Serial number: {SERIAL} but expected {serial} (!), Certificate expired (Oct 17 14:29:22 2020 +00:00) (!!)\n\
            Subject CN: IGC/A\n\
            Subject O: PM/SGDN\n\
            Subject OU: DCSSI\n\
            Serial number: {SERIAL} but expected {serial} (!)\n\
            Issuer CN: IGC/A\n\
            Issuer O: PM/SGDN\n\
            Issuer OU: DCSSI\n\
            Issuer ST: France\n\
            Issuer C: FR\n\
            Certificate expired (Oct 17 14:29:22 2020 +00:00) (!!)"
        )
    );
}
