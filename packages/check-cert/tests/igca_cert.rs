use check_cert::check::Writer;
use check_cert::checker::{self, Config as CheckCertConfig};

// Taken from `x509-parser`.
static DER: &[u8] = include_bytes!("../assets/IGC_A.der");

static SERIAL: &str = "39:11:45:10:94";
static SUBJECT: &str =
    "C=FR, ST=France, L=Paris, O=PM/SGDN, OU=DCSSI, CN=IGC/A, Email=igca@sgdn.pm.gouv.fr";
static ISSUER: &str = SUBJECT;

fn s(s: &str) -> Option<String> {
    Some(String::from(s))
}

#[test]
fn test_cert_ok() {
    let out = Writer::from(&checker::check_cert(
        DER,
        CheckCertConfig::builder()
            .serial(s(SERIAL))
            .subject(s(SUBJECT))
            .issuer(s(ISSUER))
            .build(),
    ));
    assert_eq!(
        format!("{}", out),
        format!("OK - Serial {SERIAL}, {SUBJECT}, Issuer {ISSUER}")
    );
}

#[test]
fn test_cert_wrong_serial() {
    let serial = "01:02:03:04:05";

    let out = Writer::from(&checker::check_cert(
        DER,
        CheckCertConfig::builder()
            .serial(s(serial))
            .subject(s(SUBJECT))
            .issuer(s(ISSUER))
            .build(),
    ));
    assert_eq!(
        format!("{}", out),
        format!(
            "WARNING - Serial is {SERIAL} but expected {serial} (!), {SUBJECT}, Issuer {ISSUER}"
        )
    );
}
