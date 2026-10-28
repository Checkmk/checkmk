// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The `agent_updates` entry of `cmk-agent-ctl status --json`.
//!
//! Every agent sends `status --json --no-query-remote` as the section
//! `cmk_agent_ctl_status`, so this entry is the whole path from the integrated
//! updater to the _Check_MK Agent_ service. Nothing is collected here, which is
//! what lets the entry survive a call that may not reach the site.
//!
//! The field names are those of `CMKAgentUpdateSection` in
//! `cmk/plugins/checkmk/agent_based/lib.py`, which carries the Python updater's
//! section too, so they are binding. `host_name` has no counterpart here: the
//! site resolves it from the UUID and the controller never learns it, TD(4.2).
//!
//! TD is `docs/non-free/tech_design/updater_in_controller.md`. It fixes the
//! field list and its sources, TD(4.2), and how the entry reaches the check,
//! TD(4.6). It settles no format and no wording, so every such choice below
//! says that it is ours and what it follows instead.

use super::{AgentInfo, UpdateState};
use crate::certs;
use serde::Serialize;
use std::collections::BTreeMap;
use x509_parser::certificate::X509Certificate;
use x509_parser::oid_registry::OidRegistry;
use x509_parser::time::ASN1Time;

/// The update state of this host, as the check plugin reads it.
#[derive(Serialize, Debug, PartialEq, Eq)]
pub struct AgentUpdates {
    last_check: Option<u64>,
    last_update: Option<u64>,
    aghash: Option<String>,
    pending_hash: Option<String>,
    update_url: Option<String>,
    trusted_certs: BTreeMap<usize, Cert>,
    error: Option<String>,
}

/// One configured signature key.
///
/// The site asserts that a key which is not corrupt reports an expiry, so the
/// two cases carry different data and are two variants rather than one struct
/// with four optional fields. `common_name` stays optional inside [`Trusted`]:
/// a readable certificate may still have no single common name.
///
/// [`Trusted`]: Cert::Trusted
#[derive(Debug, PartialEq, Eq)]
pub enum Cert {
    /// A key that could not be read far enough to report anything about it.
    Corrupt,
    Trusted {
        not_after: String,
        signature_algorithm: String,
        common_name: Option<String>,
    },
}

/// The four fields of `CertInfo` on the site, which [`Cert`] serializes as.
///
/// The site keeps `corrupt` next to three optional fields, so the wire format
/// cannot express the two cases as variants. This struct is that format, and
/// nothing else constructs it.
#[derive(Serialize)]
struct CertInfo<'a> {
    corrupt: bool,
    not_after: Option<&'a str>,
    signature_algorithm: Option<&'a str>,
    common_name: Option<&'a str>,
}

impl Serialize for Cert {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        CertInfo::from(self).serialize(serializer)
    }
}

impl<'a> From<&'a Cert> for CertInfo<'a> {
    fn from(cert: &'a Cert) -> Self {
        match cert {
            Cert::Corrupt => Self {
                corrupt: true,
                not_after: None,
                signature_algorithm: None,
                common_name: None,
            },
            Cert::Trusted {
                not_after,
                signature_algorithm,
                common_name,
            } => Self {
                corrupt: false,
                not_after: Some(not_after),
                signature_algorithm: Some(signature_algorithm),
                common_name: common_name.as_deref(),
            },
        }
    }
}

impl AgentUpdates {
    /// Assemble the entry from the artifacts the updater holds.
    ///
    /// # Arguments
    ///
    /// * `state` - the update state of this host
    /// * `agent_info` - the installed agent package, `None` when its file is
    ///   missing or unreadable
    /// * `signature_keys` - the trust anchors of the updater configuration,
    ///   empty when no configuration could be read
    /// * `update_url` - the receiver URL of the recorded update source
    /// * `config_error` - why the updater configuration could not be read
    ///
    /// # Returns
    ///
    /// An entry whose `error` carries `config_error` ahead of the error of the
    /// last update cycle. Both are reported, because they fail independently:
    /// a configuration that stopped parsing after the last cycle would
    /// otherwise hide the cycle's own error, and the other way round.
    pub(super) fn new(
        state: &UpdateState,
        agent_info: Option<&AgentInfo>,
        signature_keys: &[String],
        update_url: Option<String>,
        config_error: Option<&str>,
    ) -> Self {
        Self {
            last_check: state.last_check,
            last_update: state.last_update,
            aghash: agent_info.map(|info| String::from(info.hash.as_str())),
            pending_hash: state.pending_hash.clone(),
            update_url,
            trusted_certs: cert_index(signature_keys),
            error: merge_errors(config_error, state.last_error.as_deref()),
        }
    }
}

impl std::fmt::Display for AgentUpdates {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{}", self.lines().join("\n\t"))
    }
}

impl AgentUpdates {
    /// The human-readable block, one line per value an operator can act on.
    fn lines(&self) -> Vec<String> {
        let mut lines = vec![
            format!(
                "Update source: {}",
                self.update_url.as_deref().unwrap_or("none recorded yet")
            ),
            format!(
                "Installed agent: {}",
                self.aghash.as_deref().unwrap_or("unknown")
            ),
            format!("Last check: {}", render_optional_timestamp(self.last_check)),
            format!(
                "Last update: {}",
                render_optional_timestamp(self.last_update)
            ),
        ];
        if let Some(pending_hash) = &self.pending_hash {
            lines.push(format!("Installation pending: {pending_hash}"));
        }
        for (index, certificate) in &self.trusted_certs {
            lines.push(format!("Agent signature key #{index}: {certificate}"));
        }
        if let Some(error) = &self.error {
            lines.push(crate::modes::status::mark_problematic(&format!(
                "Error: {}",
                error.replace('\n', "\n\t")
            )));
        }
        lines
    }
}

impl std::fmt::Display for Cert {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::Corrupt => f.write_str("unreadable"),
            Self::Trusted {
                not_after,
                signature_algorithm,
                common_name,
            } => write!(
                f,
                "{} (valid until {not_after}, {signature_algorithm})",
                common_name.as_deref().unwrap_or("no common name"),
            ),
        }
    }
}

impl Cert {
    /// Read one configured signature key.
    fn from_pem(key: &str) -> Self {
        let Ok(pem) = certs::parse_pem(key) else {
            return Self::Corrupt;
        };
        let Ok(certificate) = pem.parse_x509() else {
            return Self::Corrupt;
        };
        Self::Trusted {
            not_after: render_not_after(&certificate.validity().not_after),
            signature_algorithm: signature_algorithm(&certificate),
            common_name: common_name(&certificate),
        }
    }
}

/// The configured signature keys, keyed by their position in the configuration.
///
/// That position is the key of the map on the site, so every entry has to keep
/// its index and a key that cannot be read is reported as corrupt in place.
/// [`super::verification::pem_blocks`] drops such a key instead, which is right
/// for verifying a package and wrong here: dropping it would shift every later
/// index and relabel the healthy keys without saying so.
///
/// A [`BTreeMap`] rather than a `HashMap`, because `serde_json` writes the keys
/// in iteration order. A `HashMap` randomizes that order per process, so two
/// runs on one host would emit the keys differently and [`AgentUpdates::lines`]
/// would number the keys out of order in the same output.
fn cert_index(signature_keys: &[String]) -> BTreeMap<usize, Cert> {
    signature_keys
        .iter()
        .enumerate()
        .map(|(index, key)| (index, Cert::from_pem(key)))
        .collect()
}

/// The errors of the configuration and of the last cycle, as one text.
///
/// Configuration error first, cycle error second, either one alone on its own.
///
/// TD(4.2) gives `error` as `last_error` alone. Merging is ours: the site model
/// has no second field for a configuration error.
fn merge_errors(config_error: Option<&str>, last_error: Option<&str>) -> Option<String> {
    match (config_error, last_error) {
        (None, last_error) => last_error.map(String::from),
        (Some(config_error), None) => Some(String::from(config_error)),
        (Some(config_error), Some(last_error)) => Some(format!("{config_error}\n{last_error}")),
    }
}

/// The expiry of a certificate, as ASN.1 GENERALIZEDTIME.
///
/// TD(4.2) names no format; `CertInfo` on the site parses this one first. The
/// RFC 2822 of [`certs::render_asn1_time`] is neither that nor its
/// `fromisoformat` fallback, and fails the whole section. `x509-parser` parses
/// certificate times into UTC, so the `Z` holds.
///
/// Written out by hand to keep `time` transitive. Replace with
/// `format_description!("[year][month][day][hour][minute][second]Z")` once
/// something here needs its `formatting` and `macros` features.
fn render_not_after(not_after: &ASN1Time) -> String {
    let expiry = not_after.to_datetime();
    format!(
        "{:04}{:02}{:02}{:02}{:02}{:02}Z",
        expiry.year(),
        u8::from(expiry.month()),
        expiry.day(),
        expiry.hour(),
        expiry.minute(),
        expiry.second(),
    )
}

/// A Unix timestamp in the format the rest of `status` uses for dates.
fn render_optional_timestamp(timestamp: Option<u64>) -> String {
    let Some(timestamp) = timestamp else {
        return String::from("never");
    };
    i64::try_from(timestamp)
        .ok()
        .and_then(|timestamp| ASN1Time::from_timestamp(timestamp).ok())
        .map_or_else(
            || timestamp.to_string(),
            |time| certs::render_asn1_time(&time),
        )
}

/// The signature algorithm of a certificate, by the short name of its OID.
///
/// TD(4.2) names no format. The short name is ours: it stays accurate for more
/// than a hash, `ecdsa-with-SHA256` where the Python updater writes `sha256`.
/// The check reads neither, so do not align the two without a reason.
fn signature_algorithm(certificate: &X509Certificate) -> String {
    let oid = &certificate.signature_algorithm.algorithm;
    OidRegistry::default()
        .with_crypto()
        .get(oid)
        .map_or_else(|| oid.to_id_string(), |entry| String::from(entry.sn()))
}

/// The common name of the subject, `None` unless it has exactly one.
///
/// TD(4.2) says only that the entry carries a `common_name`. The rule is ours,
/// taken from the Python updater.
fn common_name(certificate: &X509Certificate) -> Option<String> {
    match certs::common_names(certificate.subject()).ok()?.as_slice() {
        [common_name] => Some(String::from(*common_name)),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Valid PEM whose content is the text "not a certificate".
    const CORRUPT_KEY: &str =
        "-----BEGIN CERTIFICATE-----\nbm90IGEgY2VydGlmaWNhdGU=\n-----END CERTIFICATE-----\n";

    /// The reason this map is built by hand: dropping an unreadable key would
    /// move every later key to another index, and the site reports its results
    /// by that index.
    #[test]
    fn test_a_corrupt_key_keeps_its_index() {
        let certificates = cert_index(&[
            String::from(CORRUPT_KEY),
            certificate_pem(Some("Second key"), 2031),
        ]);

        assert_eq!(certificates[&0], Cert::Corrupt);
        let Cert::Trusted { common_name, .. } = &certificates[&1] else {
            panic!("the second key should have been read");
        };
        assert_eq!(common_name.as_deref(), Some("Second key"));
    }

    /// A corrupt entry fills none of the other three fields, which is what the
    /// site asserts. The variant makes that true by construction, the wire
    /// format still has to show it.
    #[test]
    fn test_a_corrupt_key_reports_nothing_else() {
        assert_eq!(
            serde_json::to_value(cert_index(&[String::from(CORRUPT_KEY)])).unwrap(),
            serde_json::json!({
                "0": {
                    "corrupt": true,
                    "not_after": null,
                    "signature_algorithm": null,
                    "common_name": null,
                }
            })
        );
    }

    /// The other half of `CertInfo`: a key that was read reaches the site as
    /// `corrupt: false`.
    #[test]
    fn test_a_key_that_was_read_is_not_marked_corrupt() {
        let certificates = cert_index(&[certificate_pem(Some("Signing key"), 2031)]);

        assert_eq!(
            serde_json::to_value(&certificates[&0]).unwrap()["corrupt"],
            serde_json::json!(false)
        );
    }

    #[test]
    fn test_a_key_that_is_no_pem_block_is_corrupt() {
        assert_eq!(
            cert_index(&[String::from("not a PEM block")])[&0],
            Cert::Corrupt
        );
    }

    /// RFC 2822, which the connection block of the same output uses, would fail
    /// validation on the site.
    #[test]
    fn test_not_after_is_generalized_time() {
        let certificates = cert_index(&[certificate_pem(Some("Signing key"), 2031)]);

        let Cert::Trusted { not_after, .. } = &certificates[&0] else {
            panic!("the key should have been read");
        };
        assert_eq!(not_after, "20310101000000Z");
    }

    #[test]
    fn test_signature_algorithm_is_named_where_the_oid_is_known() {
        let certificates = cert_index(&[certificate_pem(Some("Signing key"), 2031)]);

        let Cert::Trusted {
            signature_algorithm,
            ..
        } = &certificates[&0]
        else {
            panic!("the key should have been read");
        };
        assert_eq!(signature_algorithm, "ecdsa-with-SHA256");
    }

    #[test]
    fn test_a_subject_without_a_common_name_reports_none() {
        let certificates = cert_index(&[certificate_pem(None, 2031)]);

        let Cert::Trusted { common_name, .. } = &certificates[&0] else {
            panic!("the key should have been read");
        };
        assert_eq!(common_name, &None);
    }

    /// An empty map, not an absent one: the check then says that the updater
    /// trusts no signature key, which is what such a host does.
    #[test]
    fn test_without_configured_keys_the_map_is_empty() {
        assert!(cert_index(&[]).is_empty());
    }

    #[test]
    fn test_the_configuration_error_comes_before_the_one_of_the_cycle() {
        assert_eq!(
            merge_errors(Some("configuration broken"), Some("receiver unreachable")).as_deref(),
            Some("configuration broken\nreceiver unreachable")
        );
    }

    #[test]
    fn test_second_error_stays_inside_the_indented_block() {
        let entry = AgentUpdates {
            last_check: None,
            last_update: None,
            aghash: None,
            pending_hash: None,
            update_url: None,
            trusted_certs: BTreeMap::new(),
            error: merge_errors(Some("configuration broken"), Some("receiver unreachable")),
        };

        assert!(entry
            .to_string()
            .ends_with("Error: configuration broken\n\treceiver unreachable (!!)"));
    }

    #[test]
    fn test_one_error_alone_stands_on_its_own() {
        assert_eq!(
            merge_errors(None, Some("receiver unreachable")).as_deref(),
            Some("receiver unreachable")
        );
        assert_eq!(
            merge_errors(Some("configuration broken"), None).as_deref(),
            Some("configuration broken")
        );
        assert_eq!(merge_errors(None, None), None);
    }

    #[test]
    fn test_a_timestamp_that_was_never_set() {
        assert_eq!(render_optional_timestamp(None), "never");
    }

    #[test]
    fn test_a_timestamp_in_the_format_of_the_rest_of_the_status() {
        assert_eq!(
            render_optional_timestamp(Some(1_759_276_800)),
            "Wed, 01 Oct 2025 00:00:00 +0000"
        );
    }

    /// A self-signed certificate as PEM, valid until the start of
    /// `until_year`. Elliptic curve, because key generation is slow in
    /// unoptimized builds.
    fn certificate_pem(common_name: Option<&str>, until_year: i32) -> String {
        let key_pair = rcgen::KeyPair::generate_for(&rcgen::PKCS_ECDSA_P256_SHA256).unwrap();
        let mut params = rcgen::CertificateParams::default();
        params.distinguished_name = rcgen::DistinguishedName::new();
        if let Some(common_name) = common_name {
            params
                .distinguished_name
                .push(rcgen::DnType::CommonName, common_name);
        }
        params.not_after = rcgen::date_time_ymd(until_year, 1, 1);
        pem_rfc7468::encode_string(
            "CERTIFICATE",
            pem_rfc7468::LineEnding::LF,
            params.self_signed(&key_pair).unwrap().der(),
        )
        .unwrap()
    }
}
