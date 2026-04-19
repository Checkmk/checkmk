// Copyright (C) 2025 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

use std::fs::Metadata;
use std::os::unix::fs::MetadataExt;
use std::path::Path;

const ROOT_UID: u32 = 0;
const ROOT_GID: u32 = 0;
const WORLD_WRITE: u32 = 0o002;
const GROUP_WRITE: u32 = 0o020;

/// Returns true if the effective uid of the current process is 0 (root).
pub fn is_running_as_root() -> bool {
    nix::unistd::geteuid().is_root()
}

/// Owner must be root, no world-write bit,
/// and either group is root or the group-write bit is unset.
fn check_uid_gid_mode(uid: u32, gid: u32, mode: u32) -> bool {
    if uid != ROOT_UID {
        return false;
    }
    if mode & WORLD_WRITE != 0 {
        return false;
    }
    gid == ROOT_GID || mode & GROUP_WRITE == 0
}

fn is_metadata_only_root_modifiable(md: &Metadata) -> bool {
    check_uid_gid_mode(md.uid(), md.gid(), md.mode())
}

pub fn only_root_can_modify(path: &Path) -> bool {
    match std::fs::symlink_metadata(path) {
        Ok(md) => is_metadata_only_root_modifiable(&md),
        Err(e) => {
            log::warn!("Cannot stat {:?}: {}", path, e);
            false
        }
    }
}

/// Recursively verify that every entry reachable from `path` is
/// only-root-modifiable. Symlinks are not followed but their own metadata is
/// checked.
pub fn is_tree_only_root_modifiable(path: &Path) -> bool {
    if !only_root_can_modify(path) {
        log::warn!("Path {:?} is writable by non-root", path);
        return false;
    }
    let entries = match std::fs::read_dir(path) {
        Ok(e) => e,
        Err(e) => {
            log::warn!("Cannot read dir {:?}: {}", path, e);
            return false;
        }
    };
    for entry in entries {
        let entry = match entry {
            Ok(e) => e,
            Err(e) => {
                log::warn!("Invalid entry under {:?}: {}", path, e);
                return false;
            }
        };
        let sub = entry.path();
        let md = match std::fs::symlink_metadata(&sub) {
            Ok(m) => m,
            Err(e) => {
                log::warn!("Cannot stat {:?}: {}", sub, e);
                return false;
            }
        };
        if !is_metadata_only_root_modifiable(&md) {
            log::warn!("Path {:?} is writable by non-root", sub);
            return false;
        }
        // Follow real directories only; skip symlinks to avoid cycles and to
        // match the legacy plugin which never dereferenced symlinks.
        if md.file_type().is_dir() && !is_tree_only_root_modifiable(&sub) {
            return false;
        }
    }
    true
}

/// Entry point for `setup::validate_permissions` on Linux.
///
/// Non-root callers always pass: the loaded library runs with the same
/// privileges as the user and no privilege escalation is possible. When
/// running as root, the path itself and, if it is a directory, its whole
/// subtree must be only-root-modifiable so that no unprivileged user could
/// have tampered with the client library we are about to load.
pub fn validate(path: &Path) -> bool {
    if !is_running_as_root() {
        log::info!(
            "Not running as root; skipping permission validation for {:?}",
            path
        );
        return true;
    }
    let md = match std::fs::symlink_metadata(path) {
        Ok(m) => m,
        Err(e) => {
            log::warn!("Cannot stat {:?}: {}", path, e);
            return false;
        }
    };
    if md.file_type().is_dir() {
        is_tree_only_root_modifiable(path)
    } else {
        is_metadata_only_root_modifiable(&md)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_check_uid_gid_mode_root_owned_safe() {
        assert!(check_uid_gid_mode(0, 0, 0o644));
        assert!(check_uid_gid_mode(0, 0, 0o755));
        assert!(check_uid_gid_mode(0, 0, 0o600));
    }

    #[test]
    fn test_check_uid_gid_mode_rejects_world_write() {
        assert!(!check_uid_gid_mode(0, 0, 0o646));
        assert!(!check_uid_gid_mode(0, 0, 0o666));
        assert!(!check_uid_gid_mode(0, 0, 0o777));
    }

    #[test]
    fn test_check_uid_gid_mode_rejects_non_root_owner() {
        assert!(!check_uid_gid_mode(1000, 0, 0o644));
        assert!(!check_uid_gid_mode(1000, 1000, 0o600));
    }

    #[test]
    fn test_check_uid_gid_mode_non_root_group_without_group_write_is_safe() {
        assert!(check_uid_gid_mode(0, 1000, 0o644));
        assert!(check_uid_gid_mode(0, 1000, 0o755));
    }

    #[test]
    fn test_check_uid_gid_mode_non_root_group_with_group_write_is_rejected() {
        assert!(!check_uid_gid_mode(0, 1000, 0o664));
        assert!(!check_uid_gid_mode(0, 1000, 0o775));
    }
}
