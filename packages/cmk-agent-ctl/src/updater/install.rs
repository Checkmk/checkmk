// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The interface between the controller and the privileged install step.
//!
//! The controller writes an [`InstallRequest`] to the installer socket and
//! shuts down its write side; `cmk-agent-ctl install-agent`, which the socket
//! unit runs as root, reads it from its standard input. Both ends speak these
//! models, so they live with the other models of the updater.

use crate::agent_receiver_api::AgentSignature;
use anyhow::{bail, Context, Result as AnyhowResult};
use serde::Deserialize;
use std::io::Read;
use std::path::PathBuf;

/// Upper bound of one request, in bytes.
///
/// A request is a path and a handful of certificates, which is a few
/// kilobytes. The bound exists because the sender runs as the agent user: a
/// reader that holds root must not let it fill root's memory.
const MAX_REQUEST_BYTES: u64 = 64 * 1024;

/// What the controller asks the installer unit to install.
///
/// Everything in it comes from the agent user and is therefore untrusted.
#[derive(Deserialize, Debug, PartialEq, Eq)]
pub struct InstallRequest {
    /// Absolute path of the package in the controller's download directory.
    pub package: PathBuf,

    /// The signatures the site delivered with the package, which is
    /// `target_agent.signatures` of the update status it answered.
    pub signatures: Vec<AgentSignature>,
}

impl InstallRequest {
    /// Read one request from the connection of the installer socket.
    ///
    /// Reads to the end of the input, because the protocol has the controller
    /// shut down its write side once the request is out.
    ///
    /// # Arguments
    ///
    /// * `source` - the connection, which is standard input under the socket
    ///   unit
    ///
    /// # Errors
    ///
    /// If the input cannot be read, exceeds [`MAX_REQUEST_BYTES`], or is not a
    /// request.
    pub fn read(source: impl Read) -> AnyhowResult<InstallRequest> {
        let mut raw = Vec::new();
        // One byte over the bound, so that a request of exactly the bound is
        // still told apart from a stream that does not stop.
        source
            .take(MAX_REQUEST_BYTES + 1)
            .read_to_end(&mut raw)
            .context("Failed to read the install request")?;
        if raw.len() as u64 > MAX_REQUEST_BYTES {
            bail!("The install request exceeds {MAX_REQUEST_BYTES} bytes");
        }
        serde_json::from_slice(&raw).context("Failed to parse the install request")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const PACKAGE: &str = "/opt/checkmk/agent/runtime/controller/update/0123456789abcdef.deb";

    fn request(body: &str) -> AnyhowResult<InstallRequest> {
        InstallRequest::read(body.as_bytes())
    }

    #[test]
    fn test_read_a_request() {
        assert_eq!(
            request(&format!(
                r#"{{"package": "{PACKAGE}", "signatures": [{{"certificate": "cert", "signature": "sig"}}]}}"#
            ))
            .unwrap(),
            InstallRequest {
                package: PathBuf::from(PACKAGE),
                signatures: vec![AgentSignature {
                    certificate: String::from("cert"),
                    signature: String::from("sig"),
                }],
            }
        );
    }

    #[test]
    fn test_read_something_that_is_not_a_request() {
        assert!(request("/tmp/0123456789abcdef.deb\n").is_err());
    }

    /// The sender is the agent user, so the reader stops instead of growing
    /// with whatever arrives.
    #[test]
    fn test_read_refuses_an_oversized_request() {
        let padding = "x".repeat(MAX_REQUEST_BYTES as usize);
        assert!(request(&format!(
            r#"{{"package": "{PACKAGE}{padding}", "signatures": []}}"#
        ))
        .is_err());
    }
}
