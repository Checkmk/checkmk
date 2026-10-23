// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(unix)]
use faccess::PathExt;
use std::fmt::Display;
#[cfg(unix)]
use std::path::{Path, PathBuf};

pub type AgentLabels = std::collections::HashMap<String, String>;

/// Number of characters of an agent hash, as the bakery and the site write it.
const AGENT_HASH_LEN: usize = 16;

/// The hash that identifies a baked agent package.
///
/// Exactly [`AGENT_HASH_LEN`] lowercase hexadecimal characters.
#[derive(serde::Serialize, serde::Deserialize, Clone, Debug, PartialEq, Eq)]
#[serde(try_from = "String")]
pub struct AgentHash(String);

impl AgentHash {
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::convert::TryFrom<String> for AgentHash {
    type Error = anyhow::Error;

    fn try_from(value: String) -> anyhow::Result<Self> {
        if value.len() != AGENT_HASH_LEN
            || !value
                .bytes()
                .all(|c| matches!(c, b'0'..=b'9' | b'a'..=b'f'))
        {
            anyhow::bail!(
                "Not an agent hash: {value:?} - expected {AGENT_HASH_LEN} \
                 lowercase hexadecimal characters"
            );
        }
        Ok(Self(value))
    }
}

impl std::str::FromStr for AgentHash {
    type Err = anyhow::Error;

    fn from_str(s: &str) -> anyhow::Result<Self> {
        Self::try_from(String::from(s))
    }
}

impl Display for AgentHash {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[cfg(unix)]
#[derive(Clone)]
pub struct AgentChannel(std::path::PathBuf);
#[cfg(windows)]
#[derive(Clone)]
pub struct AgentChannel(String);

#[cfg(unix)]
impl std::convert::From<PathBuf> for AgentChannel {
    fn from(p: PathBuf) -> Self {
        AgentChannel(p)
    }
}

#[cfg(unix)]
impl std::convert::From<&str> for AgentChannel {
    fn from(s: &str) -> Self {
        AgentChannel(PathBuf::from(s))
    }
}

#[cfg(unix)]
impl std::convert::AsRef<Path> for AgentChannel {
    fn as_ref(&self) -> &Path {
        &self.0
    }
}

#[cfg(windows)]
impl std::convert::From<&str> for AgentChannel {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}

#[cfg(windows)]
impl std::convert::AsRef<String> for AgentChannel {
    fn as_ref(&self) -> &String {
        &self.0
    }
}

impl Display for AgentChannel {
    #[cfg(unix)]
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        {
            write!(f, "{}", self.0.to_string_lossy())
        }
    }

    #[cfg(windows)]
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl AgentChannel {
    #[cfg(unix)]
    pub fn operational(&self) -> bool {
        // https://man7.org/linux/man-pages/man7/unix.7.html
        // On Linux, connecting to a stream socket object requires write permission on that socket;
        self.0.writable()
    }

    #[cfg(windows)]
    pub fn operational(&self) -> bool {
        // Todo (sk): anything to check here? Before we do anything here, we should however switch
        // to a toml config instead of command line options, st. this check can actually be done
        // for any mode
        true
    }
}

#[derive(serde::Deserialize, Clone, Debug, PartialEq, Eq)]
#[serde(untagged)]
pub enum Credentials {
    UsernamePassword { username: String, password: String },
    OneTimeToken { ott: String },
}

impl Credentials {
    pub fn username_password(username: impl Into<String>, password: impl Into<String>) -> Self {
        Self::UsernamePassword {
            username: username.into(),
            password: password.into(),
        }
    }

    pub fn one_time_token(token: impl Into<String>) -> Self {
        Self::OneTimeToken { ott: token.into() }
    }

    pub fn as_basic_auth(&self) -> Option<(&str, &str)> {
        match self {
            Self::UsernamePassword { username, password } => {
                Some((username.as_str(), password.as_str()))
            }
            Self::OneTimeToken { .. } => None,
        }
    }

    pub fn as_token(&self) -> Option<&str> {
        match self {
            Self::UsernamePassword { .. } => None,
            Self::OneTimeToken { ott } => Some(ott.as_str()),
        }
    }
}

#[cfg(test)]
mod test_agent_hash {
    use super::AgentHash;

    const HASH: &str = "0123456789abcdef";

    #[test]
    fn test_agent_hash_from_a_hexadecimal_string() {
        assert_eq!(HASH.parse::<AgentHash>().unwrap().as_str(), HASH);
    }

    #[test]
    fn test_agent_hash_displays_as_it_was_written() {
        assert_eq!(HASH.parse::<AgentHash>().unwrap().to_string(), HASH);
    }

    #[test]
    fn test_agent_hash_rejects_anything_else() {
        for candidate in [
            "",
            "0123456789abcde",   // one short
            "0123456789abcdef0", // one long
            "0123456789ABCDEF",  // uppercase
            "0123456789abcdeg",  // not hexadecimal
            "0123456789abcde/",  // a path separator
            "0123456789abcdeä",  // 16 characters, but 17 bytes
        ] {
            assert!(
                candidate.parse::<AgentHash>().is_err(),
                "accepted {candidate:?}"
            );
        }
    }
}
