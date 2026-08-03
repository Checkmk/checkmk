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

//! Permission validation of the Oracle client runtime on Unix.
//!
//! Loading a shared library as root means executing whoever can write it with
//! root privileges, so before the client library is loaded the paths leading to
//! it are checked: nothing on the way may be writable by an untrusted user.
//!
//! Trusted means root, plus exactly one well-known exception - the conventional
//! Oracle software owner `oracle` and inventory group `oinstall`, which is how a
//! standard installation owns its binaries and libraries. That ownership must
//! not by itself make an Oracle home unusable. Any *other* non-root owner has to
//! be named in `permissions_safe_entries`, or the check has to be turned off with
//! `permissions_check: no`. The exception is deliberately a fixed pair of names
//! and not derived from the path being validated: deriving it would mean that
//! owning the path is all it takes to be trusted.
//!
//! The legacy shell plugin checked a single binary (`$ORACLE_HOME/bin/sqlplus`)
//! and switched to its owner via `su` instead of refusing. We cannot switch user
//! for an in-process library load, so we refuse instead - but we check the same
//! narrow scope plus the directories that would allow swapping the library:
//! the runtime path, its direct entries and its parent directories. The full
//! subtree is deliberately *not* walked.

use std::collections::HashSet;
use std::ffi::CString;
use std::fs::Metadata;
use std::os::unix::fs::MetadataExt;
use std::path::Path;

const ROOT_UID: u32 = 0;
const ROOT_GID: u32 = 0;
const WORLD_WRITE: u32 = 0o002;
const GROUP_WRITE: u32 = 0o020;
/// POSIX file type mask and the two file types treated specially below.
const S_IFMT: u32 = 0o170000;
const S_IFLNK: u32 = 0o120000;
const S_IFDIR: u32 = 0o040000;
/// Sticky bit. On a directory it prevents users from removing or replacing
/// entries they do not own, which is what makes a mode 1777 `/tmp` acceptable
/// as a path component.
const STICKY: u32 = 0o1000;

/// The conventional Oracle software owner and inventory group, trusted in
/// addition to root. A standard installation owns its Oracle home as
/// `oracle:oinstall`, and leaves `$ORACLE_BASE` group writable for `oinstall`.
const ORACLE_USER: &str = "oracle";
const ORACLE_GROUP: &str = "oinstall";

/// Returns true if the effective uid of the current process is 0 (root).
pub fn is_running_as_root() -> bool {
    // SAFETY: `geteuid` is a POSIX call with no preconditions and cannot fail.
    unsafe { libc::geteuid() == 0 }
}

/// Resolves a user name to its uid, `None` if there is no such user.
///
/// The plain, non-reentrant call is enough: the id is copied out before anything
/// else can touch libc's static storage, and both callers of [`SafeIds::new`] run
/// single-threaded - runtime detection before the monitoring process is spawned,
/// SQL file resolution while the query blocks are assembled, ahead of the worker
/// pool. It also has no caller-supplied buffer, so unlike `getpwnam_r` it cannot
/// fail with `ERANGE` on an entry that happens to be large.
fn uid_of_user(name: &str) -> Option<u32> {
    let c_name = CString::new(name).ok()?;
    // SAFETY: `c_name` is a valid NUL-terminated string. The call returns either
    // NULL or a pointer to a `passwd` in storage owned by libc.
    let pwd = unsafe { libc::getpwnam(c_name.as_ptr()) };
    if pwd.is_null() {
        return None;
    }
    // SAFETY: non-NULL, so `pwd` points to an initialised `passwd`.
    Some(unsafe { (*pwd).pw_uid })
}

/// Resolves a group name to its gid, `None` if there is no such group.
/// See [`uid_of_user`] on the choice of call.
fn gid_of_group(name: &str) -> Option<u32> {
    let c_name = CString::new(name).ok()?;
    // SAFETY: `c_name` is a valid NUL-terminated string. The call returns either
    // NULL or a pointer to a `group` in storage owned by libc.
    let grp = unsafe { libc::getgrnam(c_name.as_ptr()) };
    if grp.is_null() {
        return None;
    }
    // SAFETY: non-NULL, so `grp` points to an initialised `group`.
    Some(unsafe { (*grp).gr_gid })
}

/// The users and groups that may write to a path besides root: the conventional
/// Oracle account and inventory group, plus whatever `permissions_safe_entries`
/// adds.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct SafeIds {
    uids: HashSet<u32>,
    gids: HashSet<u32>,
}

impl SafeIds {
    /// Seeds the well-known Oracle account and group - absent on a host without
    /// an Oracle installation, in which case nothing beyond root is trusted -
    /// and adds the configured entries.
    pub fn new(entries: &[String]) -> Self {
        let mut ids = Self::default();
        if let Some(uid) = uid_of_user(ORACLE_USER) {
            ids.uids.insert(uid);
        }
        if let Some(gid) = gid_of_group(ORACLE_GROUP) {
            ids.gids.insert(gid);
        }
        ids.add_configured(entries);
        ids
    }

    /// Resolves each entry against both the passwd and the group database - the
    /// option is documented as "safe groups and/or users" and an entry such as
    /// `dba` may name either. A purely numeric entry is taken as a uid and a
    /// gid. Entries that resolve to nothing are reported so typos surface.
    fn add_configured(&mut self, entries: &[String]) {
        for entry in entries {
            let mut resolved = false;
            if let Some(uid) = uid_of_user(entry) {
                self.uids.insert(uid);
                resolved = true;
            }
            if let Some(gid) = gid_of_group(entry) {
                self.gids.insert(gid);
                resolved = true;
            }
            if let Ok(numeric) = entry.parse::<u32>() {
                self.uids.insert(numeric);
                self.gids.insert(numeric);
                resolved = true;
            }
            if !resolved {
                log::warn!(
                    "permissions_safe_entries: {:?} is neither a known user nor a known group, ignoring it",
                    entry
                );
            }
        }
    }
}

/// Whether one filesystem entry can only be modified by root or a safe user.
/// `mode` is a raw `st_mode`, so the file type is taken from it.
fn is_entry_safe(uid: u32, gid: u32, mode: u32, safe: &SafeIds) -> bool {
    if uid != ROOT_UID && !safe.uids.contains(&uid) {
        return false;
    }
    if mode & S_IFMT == S_IFLNK {
        // A symlink's own mode bits are meaningless: they are 0777 on Linux.
        // Repointing the link needs write access to the directory holding it,
        // and that directory is checked in its own right.
        return true;
    }
    if mode & S_IFMT == S_IFDIR && mode & STICKY != 0 {
        return true;
    }
    if mode & WORLD_WRITE != 0 {
        return false;
    }
    mode & GROUP_WRITE == 0 || gid == ROOT_GID || safe.gids.contains(&gid)
}

fn check_entry(path: &Path, md: &Metadata, safe: &SafeIds) -> bool {
    if is_entry_safe(md.uid(), md.gid(), md.mode(), safe) {
        return true;
    }
    log::warn!(
        "Path {:?} (uid {}, gid {}, mode {:o}) is writable by someone other than root or \
         {ORACLE_USER}:{ORACLE_GROUP}. List the owning user or group in \
         `permissions_safe_entries`, or set `permissions_check: no`, to accept it anyway.",
        path,
        md.uid(),
        md.gid(),
        md.mode() & 0o7777
    );
    false
}

fn symlink_metadata_of(path: &Path) -> Option<Metadata> {
    std::fs::symlink_metadata(path)
        .inspect_err(|e| log::warn!("Cannot stat {:?}: {}", path, e))
        .ok()
}

/// Checks `target` and every directory above it. `target` must be canonical, so
/// that no component is a symlink.
fn validate_ancestry(target: &Path, safe: &SafeIds) -> bool {
    target.ancestors().all(|ancestor| {
        symlink_metadata_of(ancestor).is_some_and(|md| check_entry(ancestor, &md, safe))
    })
}

/// Resolves a symlink and checks where it actually points. A link that does not
/// resolve cannot be loaded and is therefore harmless rather than a failure.
fn validate_symlink_target(link: &Path, safe: &SafeIds) -> bool {
    match std::fs::canonicalize(link) {
        Ok(target) => validate_ancestry(&target, safe),
        Err(e) => {
            log::debug!("Symlink {:?} does not resolve ({}), ignoring it", link, e);
            true
        }
    }
}

/// Checks the entries directly inside `dir`, without descending into
/// subdirectories.
fn validate_dir_entries(dir: &Path, safe: &SafeIds) -> bool {
    let entries = match std::fs::read_dir(dir) {
        Ok(entries) => entries,
        Err(e) => {
            log::warn!("Cannot read dir {:?}: {}", dir, e);
            return false;
        }
    };
    for entry in entries {
        let entry = match entry {
            Ok(entry) => entry,
            Err(e) => {
                log::warn!("Invalid entry under {:?}: {}", dir, e);
                return false;
            }
        };
        let path = entry.path();
        let Some(md) = symlink_metadata_of(&path) else {
            return false;
        };
        if !check_entry(&path, &md, safe) {
            return false;
        }
        if md.file_type().is_symlink() && !validate_symlink_target(&path, safe) {
            return false;
        }
    }
    true
}

fn validate_tree(path: &Path, safe: &SafeIds) -> bool {
    // Canonicalize first so the ancestor walk sees real directories only. This
    // is also what makes the walk sound against a redirected symlink: whoever
    // repoints one has to point it somewhere, and that is what gets checked.
    let target = match std::fs::canonicalize(path) {
        Ok(target) => target,
        Err(e) => {
            log::warn!("Cannot resolve {:?}: {}", path, e);
            return false;
        }
    };
    let Some(md) = symlink_metadata_of(&target) else {
        return false;
    };
    if !validate_ancestry(&target, safe) {
        return false;
    }
    // A file is fully covered by the ancestry walk; a directory additionally
    // needs its entries checked, since the library we load is one of them.
    !md.file_type().is_dir() || validate_dir_entries(&target, safe)
}

/// Entry point for `setup::validate_permissions` on Unix.
///
/// A non-root caller always passes: the library is loaded with the same
/// privileges the user already has, so there is nothing to escalate. As root,
/// the path, its direct entries (for a directory) and its parent directories
/// must only be writable by root, by `oracle:oinstall`, or by a user or group
/// listed in `safe_entries`.
pub fn validate(path: &Path, check: bool, safe_entries: &[String]) -> bool {
    if !check {
        log::info!(
            "Permission check disabled; skipping validation for {:?}",
            path
        );
        return true;
    }
    if !is_running_as_root() {
        log::info!(
            "Not running as root; skipping permission validation for {:?}",
            path
        );
        return true;
    }
    validate_tree(path, &SafeIds::new(safe_entries))
}

#[cfg(test)]
mod tests {
    use super::*;

    const FILE: u32 = 0o100000;
    const DIR: u32 = S_IFDIR;
    const LINK: u32 = S_IFLNK;

    /// Stand-ins for the resolved `oracle` uid and `oinstall` gid: the real ones
    /// only exist on a host with an Oracle installation.
    const ORA_UID: u32 = 54321;
    const ORA_GID: u32 = 54321;
    const STRANGER: u32 = 4242;

    fn root_only() -> SafeIds {
        SafeIds::default()
    }

    fn oracle_safe() -> SafeIds {
        SafeIds {
            uids: HashSet::from([ORA_UID]),
            gids: HashSet::from([ORA_GID]),
        }
    }

    #[test]
    fn test_root_owned_entries_are_safe() {
        assert!(is_entry_safe(0, 0, FILE | 0o644, &root_only()));
        assert!(is_entry_safe(0, 0, FILE | 0o755, &root_only()));
        assert!(is_entry_safe(0, 0, DIR | 0o755, &root_only()));
    }

    #[test]
    fn test_world_writable_is_rejected() {
        assert!(!is_entry_safe(0, 0, FILE | 0o666, &root_only()));
        assert!(!is_entry_safe(0, 0, FILE | 0o777, &root_only()));
        assert!(!is_entry_safe(
            ORA_UID,
            ORA_GID,
            FILE | 0o646,
            &oracle_safe()
        ));
    }

    #[test]
    fn test_oracle_owner_is_safe() {
        assert!(is_entry_safe(
            ORA_UID,
            ORA_GID,
            FILE | 0o644,
            &oracle_safe()
        ));
        // The Oracle installer leaves $ORACLE_BASE group writable for oinstall.
        assert!(is_entry_safe(ORA_UID, ORA_GID, DIR | 0o775, &oracle_safe()));
    }

    /// The point of not deriving the trusted owner from the path: a directory
    /// owned by some unrelated account must not become trusted just because it
    /// is the one being validated.
    #[test]
    fn test_unrelated_owner_is_rejected() {
        assert!(!is_entry_safe(
            STRANGER,
            ORA_GID,
            FILE | 0o644,
            &oracle_safe()
        ));
        assert!(!is_entry_safe(
            STRANGER,
            STRANGER,
            DIR | 0o755,
            &oracle_safe()
        ));
        assert!(!is_entry_safe(
            STRANGER,
            STRANGER,
            FILE | 0o600,
            &root_only()
        ));
    }

    #[test]
    fn test_group_write_needs_a_safe_group() {
        assert!(!is_entry_safe(
            ORA_UID,
            STRANGER,
            FILE | 0o664,
            &oracle_safe()
        ));
        // ... unless the group is root, or explicitly marked safe.
        assert!(is_entry_safe(ORA_UID, 0, FILE | 0o664, &oracle_safe()));
        let mut safe = oracle_safe();
        safe.gids.insert(STRANGER);
        assert!(is_entry_safe(ORA_UID, STRANGER, FILE | 0o664, &safe));
        // A group without the write bit is irrelevant.
        assert!(is_entry_safe(
            ORA_UID,
            STRANGER,
            FILE | 0o644,
            &oracle_safe()
        ));
    }

    #[test]
    fn test_symlink_mode_bits_are_ignored() {
        // Symlinks are mode 0777 on Linux; judging them by their mode would
        // reject every real Oracle home, they all ship libclntsh.so as a link.
        assert!(is_entry_safe(0, 0, LINK | 0o777, &root_only()));
        assert!(is_entry_safe(
            ORA_UID,
            ORA_GID,
            LINK | 0o777,
            &oracle_safe()
        ));
        // The owner still has to be trusted.
        assert!(!is_entry_safe(STRANGER, 0, LINK | 0o777, &oracle_safe()));
    }

    #[test]
    fn test_sticky_directory_tolerates_world_write() {
        // /tmp is mode 1777: the sticky bit stops users replacing entries they
        // do not own, so it is acceptable as a path component.
        assert!(is_entry_safe(0, 0, DIR | STICKY | 0o777, &root_only()));
        // Only for directories, and only with the sticky bit.
        assert!(!is_entry_safe(0, 0, DIR | 0o777, &root_only()));
        assert!(!is_entry_safe(0, 0, FILE | STICKY | 0o777, &root_only()));
    }

    #[test]
    fn test_safe_ids_always_carries_root_nothing_else_by_default() {
        // `oracle`/`oinstall` are resolved from the host, so only their absence
        // can be asserted portably: on a host without them nothing but root is
        // trusted, and no configured entry appears.
        let ids = SafeIds::new(&[]);
        assert!(!ids.uids.contains(&STRANGER));
        assert!(!ids.gids.contains(&STRANGER));
    }

    #[test]
    fn test_configured_entries_are_added() {
        let mut ids = SafeIds::default();
        ids.add_configured(&["root".to_string()]);
        assert!(ids.uids.contains(&0));

        // Numeric entries count as both a uid and a gid. Group *names* are
        // deliberately not asserted on: root's group is `root` on some distros
        // and `wheel` on others.
        let mut ids = SafeIds::default();
        ids.add_configured(&["4242".to_string()]);
        assert!(ids.uids.contains(&4242));
        assert!(ids.gids.contains(&4242));

        let mut ids = SafeIds::default();
        ids.add_configured(&["_no_such_user_or_group_42_".to_string()]);
        assert_eq!(ids, SafeIds::default());
    }

    #[test]
    fn test_disabled_check_skips_validation() {
        // The `check` flag is honoured before the root check, so this holds
        // whether or not the test itself runs as root. The path does not even
        // have to exist: nothing is looked at once the check is off.
        assert!(validate(Path::new("/no/such/runtime"), false, &[]));
    }
}
