// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The registration of the Python agent updater, which the migration to the
//! integrated updater proves to the site.
//!
//! The Python updater keeps it in its state file, `cmk-update-agent.state`, a
//! Python literal.
//!
//! The `host_secret` never leaves the host. The site gets the proof instead,
//! which covers the site and the UUID of one connection, so that no other site
//! and no other registration can use it.

use super::python_literal;
use crate::site_spec::SiteID;
use anyhow::{bail, Context, Result as AnyhowResult};
use hmac::{Hmac, Mac};
use serde::Deserialize;
use sha2::Sha256;
use std::path::Path;
use std::{fmt, fs, io};

pub struct LegacyRegistration {
    pub host_name: String,
    pub server: String,
    pub site: String,
    host_secret: String,
}

/// The keys of the state file that the migration reads. The Python updater
/// writes the others for itself.
#[derive(Deserialize)]
struct StateFile {
    host_name: Option<String>,
    server: Option<String>,
    site: Option<String>,
    host_secret: Option<String>,
}

impl LegacyRegistration {
    /// # Returns
    ///
    /// `None` if there is no state file, or if it holds no `host_secret`: the
    /// Python updater of this host was never registered.
    ///
    /// # Errors
    ///
    /// If the state file cannot be read or parsed, or if it holds a
    /// `host_secret` without the host name, the server or the site.
    pub fn load(path: &Path) -> AnyhowResult<Option<Self>> {
        let bytes = match fs::read(path) {
            Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(None),
            read => read.context(format!(
                "Failed to read the state of the Python agent updater {path:?}"
            ))?,
        };
        // Only last_error, a localized OS message on Windows, may not be UTF-8.
        // It is not read here, so a lossy decode keeps the file loadable.
        let text = String::from_utf8_lossy(&bytes);
        let context = || format!("Failed to load the state of the Python agent updater {path:?}");
        let value = python_literal::parse(&text).with_context(context)?;
        if !value.is_object() {
            bail!("{}: not a dict", context());
        }
        let state: StateFile = serde_json::from_value(value).with_context(context)?;
        let Some(host_secret) = state.host_secret.filter(|secret| !secret.is_empty()) else {
            return Ok(None);
        };
        let missing = |key| {
            format!("The state of the Python agent updater {path:?} has a host_secret but no {key}")
        };
        Ok(Some(Self {
            host_name: state.host_name.with_context(|| missing("host_name"))?,
            server: state.server.with_context(|| missing("server"))?,
            site: state.site.with_context(|| missing("site"))?,
            host_secret,
        }))
    }

    /// The site computes the same HMAC from its copy of the `host_secret`, with
    /// its site ID, which equals the site name in a distributed setup.
    pub fn migration_proof(&self, site_id: &SiteID, uuid: &uuid::Uuid) -> String {
        let mut mac = Hmac::<Sha256>::new_from_slice(self.host_secret.as_bytes())
            .expect("HMAC takes a key of any length");
        mac.update(format!("cmk-agent-update-migration:{}:{uuid}", site_id.site).as_bytes());
        mac.finalize()
            .into_bytes()
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect()
    }
}

impl fmt::Display for LegacyRegistration {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "the registration of the Python agent updater, host {} at {}/{}",
            self.host_name, self.server, self.site
        )
    }
}

impl fmt::Debug for LegacyRegistration {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("LegacyRegistration")
            .field("host_name", &self.host_name)
            .field("server", &self.server)
            .field("site", &self.site)
            .finish_non_exhaustive()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    /// `LEGACY_HOST_SECRET` of the site's tests, in
    /// `tests/unit/cmk/gui/nonfree/pro/agent_bakery/testlib.py`.
    const SECRET: &str = "the-host-secret-of-the-legacy-registration";
    const UUID: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a01";

    fn registration() -> LegacyRegistration {
        LegacyRegistration {
            host_name: String::from("myhost"),
            server: String::from("checkmk.example.com"),
            site: String::from("mysite"),
            host_secret: String::from(SECRET),
        }
    }

    fn uuid() -> uuid::Uuid {
        uuid::Uuid::from_str(UUID).unwrap()
    }

    fn load_state(content: impl AsRef<[u8]>) -> AnyhowResult<Option<LegacyRegistration>> {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("cmk-update-agent.state");
        fs::write(&path, content).unwrap();
        LegacyRegistration::load(&path)
    }

    /// CMK-39502: the migration reads the host name, the server, the site and
    /// the secret of the Python updater's registration.
    #[test]
    fn test_load_a_registered_python_updater() {
        let registration = load_state(format!(
            "{{'protocol': 'https', 'last_error': None, 'site': 'mysite', \
             'host_name': 'myhost', 'server': 'checkmk.example.com', \
             'last_check': 1563801836.6, 'host_secret': '{SECRET}', 'user': 'cmkadmin'}}\n"
        ))
        .unwrap()
        .unwrap();

        assert_eq!(registration.host_name, "myhost");
        assert_eq!(registration.server, "checkmk.example.com");
        assert_eq!(registration.site, "mysite");
        assert_eq!(registration.host_secret, SECRET);
    }

    /// CMK-39502: on Windows, the Python updater writes its state in the code
    /// page, here cp1252, which is no UTF-8.
    #[test]
    fn test_load_a_state_file_in_a_windows_code_page() {
        let registration = load_state(
            [
                b"{'last_error': 'Acc\xe8s refus\xe9', 'user': 'J\xf6rg', ".as_slice(),
                format!(
                    "'host_name': 'myhost', 'server': 'srv', 'site': 'mysite', \
                     'host_secret': '{SECRET}'}}\n"
                )
                .as_bytes(),
            ]
            .concat(),
        )
        .unwrap()
        .unwrap();

        assert_eq!(registration.host_name, "myhost");
        assert_eq!(registration.host_secret, SECRET);
    }

    /// CMK-39502: without a state file there is nothing to migrate.
    #[test]
    fn test_load_without_a_state_file() {
        let dir = tempfile::TempDir::new().unwrap();

        assert!(
            LegacyRegistration::load(&dir.path().join("cmk-update-agent.state"))
                .unwrap()
                .is_none()
        );
    }

    /// CMK-39502: a Python updater that was never registered has nothing to
    /// migrate.
    #[test]
    fn test_load_without_a_host_secret() {
        for secret in ["None", "''"] {
            assert!(load_state(format!(
                "{{'host_name': 'myhost', 'server': 'srv', 'site': 'mysite', \
                 'host_secret': {secret}}}"
            ))
            .unwrap()
            .is_none());
        }
        assert!(load_state("{'last_check': 1563801836.6}")
            .unwrap()
            .is_none());
    }

    #[test]
    fn test_load_a_secret_without_its_site() {
        let error = load_state(format!(
            "{{'host_name': 'myhost', 'server': 'srv', 'host_secret': '{SECRET}'}}"
        ))
        .unwrap_err();

        assert!(format!("{error:#}").contains("no site"));
    }

    /// CMK-39502: an error about the state file never shows the secret.
    #[test]
    fn test_load_a_malformed_state_file() {
        for content in [
            format!("{{'host_secret': '{SECRET}' 'site': 'mysite'}}"),
            format!("{{'host_secret': ['{SECRET}']}}"),
            format!("['myhost', 'srv', 'mysite', '{SECRET}']"),
        ] {
            let error = load_state(&content).unwrap_err();

            assert!(!format!("{error:#}").contains(SECRET), "{error:#}");
        }
    }

    /// CMK-39502: the proof is the HMAC that the site computes, as Python's
    /// `hmac.new(secret, f"cmk-agent-update-migration:{site}:{uuid}", sha256).hexdigest()`.
    #[test]
    fn test_proof_matches_the_site() {
        assert_eq!(
            registration().migration_proof(
                &SiteID::from_str("checkmk.example.com/mysite").unwrap(),
                &uuid()
            ),
            "3646567c79cf813effaf47ffe59e9987ee92a34c2e61ce57dea9e817b0c3d78d"
        );
    }

    /// CMK-39502: the proof covers the site and the UUID of the connection, not
    /// the server.
    #[test]
    fn test_proof_covers_the_site_and_the_uuid() {
        let proof = |site_id: &str, uuid: &uuid::Uuid| {
            registration().migration_proof(&SiteID::from_str(site_id).unwrap(), uuid)
        };
        let reference = proof("server/mysite", &uuid());

        assert_eq!(proof("other-server/mysite", &uuid()), reference);
        assert_ne!(proof("server/othersite", &uuid()), reference);
        assert_ne!(proof("server/mysite", &uuid::Uuid::new_v4()), reference);
    }

    /// CMK-39502: the secret stays out of the logs.
    #[test]
    fn test_debug_hides_the_secret() {
        let debug = format!("{:?}", registration());

        assert!(debug.contains("myhost"));
        assert!(!debug.contains(SECRET));
    }
}
