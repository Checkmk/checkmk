use check_cert::checker::certificate::{self, Config as CertConfig};

// Taken from `x509-parser`.
static DER: &[u8] = include_bytes!("../assets/IGC_A.der");

static SERIAL: &str = "39:11:45:10:94";
static SIG_ALG: &str = "RSA";
static PUBKEY_ALG: &str = "RSA";
static PUBKEY_SZ: usize = 2048;

fn s(s: &str) -> Option<String> {
    Some(String::from(s))
}

#[test]
fn test_cert_ok() {
    let out = certificate::check(
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
            .signature_algorithm(s(SIG_ALG))
            .pubkey_algorithm(s(PUBKEY_ALG))
            .pubkey_size(Some(PUBKEY_SZ))
            .build(),
    );
    assert_eq!(
        out.to_string(),
        format!(
            "OK - CN=IGC/A\n\
            Subject CN: IGC/A\n\
            Subject O: PM/SGDN\n\
            Subject OU: DCSSI\n\
            Serial: {SERIAL}\n\
            Issuer CN: IGC/A\n\
            Issuer O: PM/SGDN\n\
            Issuer OU: DCSSI\n\
            Issuer ST: France\n\
            Issuer C: FR\n\
            Signature algorithm: {SIG_ALG}\n\
            Public key algorithm: {PUBKEY_ALG}\n\
            Public key size: {PUBKEY_SZ}"
        )
    );
}

#[test]
fn test_cert_wrong_serial() {
    let serial = "01:02:03:04:05";
    let out = certificate::check(
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
    assert_eq!(
        out.to_string(),
        format!(
            "WARNING - \
            CN=IGC/A, \
            Serial is {SERIAL} but expected {serial} (!)\n\
            Subject CN: IGC/A\n\
            Subject O: PM/SGDN\n\
            Subject OU: DCSSI\n\
            Issuer CN: IGC/A\n\
            Issuer O: PM/SGDN\n\
            Issuer OU: DCSSI\n\
            Issuer ST: France\n\
            Issuer C: FR"
        )
    );
}
