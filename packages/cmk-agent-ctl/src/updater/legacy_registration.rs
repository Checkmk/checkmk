// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The registration of the Python agent updater, which the migration to the
//! integrated updater proves to the site.
//!
//! The `host_secret` never leaves the host. The site gets the proof instead,
//! which covers the site and the UUID of one connection, so that no other site
//! and no other registration can use it.

use crate::site_spec::SiteID;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use std::fmt;

pub struct LegacyRegistration {
    pub host_name: String,
    pub server: String,
    pub site: String,
    host_secret: String,
}

impl LegacyRegistration {
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
