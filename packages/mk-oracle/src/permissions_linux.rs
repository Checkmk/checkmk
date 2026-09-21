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
//! root privileges. A runtime that only root controls is therefore loaded as
//! root, a runtime whose directory belongs to another user is loaded as that
//! user - the process gives up root and becomes the owner first, as the legacy
//! shell plugin did with `su` before running `sqlplus` - and anything else is
//! refused. Whoever can already write the library gains nothing from it being
//! loaded under their own account.
//!
//! Above a runtime loaded as root every directory has to be root-controlled,
//! since a writable parent allows swapping the whole tree. Above a runtime
//! loaded as its owner the directories only have to be safe from everyone:
//! Oracle's own installation layout has the Grid user own the directories
//! above a database home, and once the plugin runs as the owner that is the
//! installation's trust model, not root's. The subtree below the runtime is
//! never walked.

use crate::setup::{RunAsUser, RuntimeVerdict};
use std::collections::HashSet;
use std::ffi::{CStr, CString};
use std::fs::Metadata;
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::MetadataExt;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

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

/// Returns true if the effective uid of the current process is 0 (root).
pub fn is_running_as_root() -> bool {
    // SAFETY: `geteuid` is a POSIX call with no preconditions and cannot fail.
    unsafe { libc::geteuid() == 0 }
}

/// The plain, non-reentrant calls of this module are enough: the result is
/// copied out before anything else can touch libc's static storage, and every
/// caller runs single-threaded - the runtime is assessed before the connection
/// pool starts, and SQL files are resolved while the query blocks are
/// assembled, ahead of the worker pool. They also have no caller-supplied
/// buffer, so unlike the `_r` variants they cannot fail with `ERANGE` on an
/// entry that happens to be large.
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

/// See [`uid_of_user`] on the choice of call.
fn user_of_uid(uid: u32) -> Option<RunAsUser> {
    // SAFETY: `getpwuid` has no preconditions. The call returns either NULL or a
    // pointer to a `passwd` in storage owned by libc.
    let pwd = unsafe { libc::getpwuid(uid) };
    if pwd.is_null() {
        return None;
    }
    // SAFETY: non-NULL, so `pwd` points to an initialised `passwd` whose string
    // fields are NUL-terminated and owned by libc; they are copied out here.
    let (name, gid, home) = unsafe {
        let name = CStr::from_ptr((*pwd).pw_name)
            .to_string_lossy()
            .into_owned();
        let home = if (*pwd).pw_dir.is_null() {
            PathBuf::from("/")
        } else {
            PathBuf::from(std::ffi::OsStr::from_bytes(
                CStr::from_ptr((*pwd).pw_dir).to_bytes(),
            ))
        };
        (name, (*pwd).pw_gid, home)
    };
    let groups = groups_of_user(&name, gid);
    Some(RunAsUser {
        uid,
        gid,
        groups,
        name,
        home,
    })
}

#[cfg(not(target_os = "aix"))]
fn groups_of_user(name: &str, primary_gid: u32) -> Vec<u32> {
    let Ok(c_name) = CString::new(name) else {
        return vec![primary_gid];
    };
    let mut capacity: libc::c_int = 16;
    loop {
        let mut groups = vec![0 as libc::gid_t; capacity as usize];
        let mut count = capacity;
        // SAFETY: `groups` has room for `count` entries, and `count` is passed by
        // pointer as the call requires; on a short buffer it is set to the
        // number of entries needed.
        let rc = unsafe {
            libc::getgrouplist(
                c_name.as_ptr(),
                primary_gid,
                groups.as_mut_ptr(),
                &mut count,
            )
        };
        if rc != -1 {
            groups.truncate(count as usize);
            return groups;
        }
        capacity = if count > capacity {
            count
        } else {
            capacity * 2
        };
        if capacity > 65536 {
            log::warn!("Cannot read the groups of {name}, using the primary group only");
            return vec![primary_gid];
        }
    }
}

/// AIX has no `getgrouplist`. `getgrset` returns the user's group ids as a
/// comma-separated string that the caller has to free.
#[cfg(target_os = "aix")]
fn groups_of_user(name: &str, primary_gid: u32) -> Vec<u32> {
    let Ok(c_name) = CString::new(name) else {
        return vec![primary_gid];
    };
    // SAFETY: `c_name` is a valid NUL-terminated string. The call returns NULL
    // or a malloc'ed, NUL-terminated string that is ours to free.
    let list = unsafe { libc::getgrset(c_name.as_ptr()) };
    if list.is_null() {
        log::warn!("Cannot read the groups of {name}, using the primary group only");
        return vec![primary_gid];
    }
    // SAFETY: non-NULL and NUL-terminated, see above; copied out before the free.
    let text = unsafe { CStr::from_ptr(list) }
        .to_string_lossy()
        .into_owned();
    // SAFETY: `list` came from malloc inside libc and is not used afterwards.
    unsafe { libc::free(list as *mut libc::c_void) };
    let mut groups: Vec<u32> = text
        .split(',')
        .filter_map(|gid| gid.trim().parse().ok())
        .collect();
    if !groups.contains(&primary_gid) {
        groups.push(primary_gid);
    }
    groups
}

/// Besides root, the users and groups whose write access to a path is accepted.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct SafeIds {
    uids: HashSet<u32>,
    gids: HashSet<u32>,
}

impl SafeIds {
    pub fn configured(entries: &[String]) -> Self {
        let mut ids = Self::default();
        ids.add_configured(entries);
        ids
    }

    pub fn for_owner(owner: &RunAsUser, entries: &[String]) -> Self {
        let mut ids = Self::configured(entries);
        ids.uids.insert(owner.uid);
        ids.gids.insert(owner.gid);
        ids.gids.extend(owner.groups.iter().copied());
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

/// Who is trusted with the directories above the validated path.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Ancestry {
    RootOnly,
    Shared,
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

fn is_shared_ancestor_safe(mode: u32) -> bool {
    mode & WORLD_WRITE == 0 || (mode & S_IFMT == S_IFDIR && mode & STICKY != 0)
}

fn check_entry(path: &Path, md: &Metadata, safe: &SafeIds) -> bool {
    if is_entry_safe(md.uid(), md.gid(), md.mode(), safe) {
        return true;
    }
    log::warn!(
        "Path {:?} (uid {}, gid {}, mode {:o}) is writable by someone other than root or \
         the owner of the runtime. List the owning user or group in \
         `permissions_safe_entries`, or set `permissions_check: no`, to accept it anyway.",
        path,
        md.uid(),
        md.gid(),
        md.mode() & 0o7777
    );
    false
}

fn check_ancestor(path: &Path, md: &Metadata, safe: &SafeIds, ancestry: Ancestry) -> bool {
    match ancestry {
        Ancestry::RootOnly => check_entry(path, md, safe),
        Ancestry::Shared => {
            if is_shared_ancestor_safe(md.mode()) {
                return true;
            }
            log::warn!(
                "Path {:?} (mode {:o}) is writable by everyone",
                path,
                md.mode() & 0o7777
            );
            false
        }
    }
}

fn symlink_metadata_of(path: &Path) -> Option<Metadata> {
    std::fs::symlink_metadata(path)
        .inspect_err(|e| log::warn!("Cannot stat {:?}: {}", path, e))
        .ok()
}

/// Symlinks in `path` are resolved before the walk, so that the real file and
/// the real directories above it are what gets checked: whoever repoints a link
/// has to point it somewhere.
fn resolve(path: &Path) -> std::io::Result<(PathBuf, Metadata)> {
    let target = std::fs::canonicalize(path)?;
    let md = std::fs::symlink_metadata(&target)?;
    Ok((target, md))
}

/// `target` has to come from `resolve`: a symlinked directory above it would be
/// judged by its owner alone, wherever it points.
fn validate_path(target: &Path, md: &Metadata, safe: &SafeIds, ancestry: Ancestry) -> bool {
    check_entry(target, md, safe)
        && target.ancestors().skip(1).all(|dir| {
            symlink_metadata_of(dir).is_some_and(|md| check_ancestor(dir, &md, safe, ancestry))
        })
}

/// Resolves a symlink and checks where it actually points. A link that does not
/// resolve cannot be loaded and is therefore harmless rather than a failure.
fn validate_symlink_target(link: &Path, safe: &SafeIds, ancestry: Ancestry) -> bool {
    match resolve(link) {
        Ok((target, md)) => validate_path(&target, &md, safe, ancestry),
        Err(e) => {
            log::debug!("Symlink {:?} does not resolve ({}), ignoring it", link, e);
            true
        }
    }
}

/// Checks the entries directly inside `dir`, without descending into
/// subdirectories.
fn validate_dir_entries(dir: &Path, safe: &SafeIds, ancestry: Ancestry) -> bool {
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
        if md.file_type().is_symlink() && !validate_symlink_target(&path, safe, ancestry) {
            return false;
        }
    }
    true
}

fn validate_tree(target: &Path, md: &Metadata, safe: &SafeIds, ancestry: Ancestry) -> bool {
    validate_path(target, md, safe, ancestry)
        && (!md.file_type().is_dir() || validate_dir_entries(target, safe, ancestry))
}

/// Public only for the component tests, which run without root: a directory
/// the test owns yields `SwitchTo` that very user.
#[doc(hidden)]
pub fn assess_tree(path: &Path, safe_entries: &[String]) -> RuntimeVerdict {
    let (target, md) = match resolve(path) {
        Ok(resolved) => resolved,
        Err(e) => return RuntimeVerdict::Reject(format!("Cannot resolve {path:?}: {e}")),
    };
    if md.uid() == ROOT_UID {
        let safe = SafeIds::configured(safe_entries);
        return if validate_tree(&target, &md, &safe, Ancestry::RootOnly) {
            RuntimeVerdict::Load
        } else {
            RuntimeVerdict::Reject(format!("{path:?} is writable by someone other than root"))
        };
    }
    let Some(owner) = user_of_uid(md.uid()) else {
        return RuntimeVerdict::Reject(format!(
            "{target:?} belongs to uid {}, which is not a known user: cannot run as its owner",
            md.uid()
        ));
    };
    let safe = SafeIds::for_owner(&owner, safe_entries);
    if !validate_tree(&target, &md, &safe, Ancestry::Shared) {
        return RuntimeVerdict::Reject(format!(
            "{path:?} is writable by someone other than root or its owner {}",
            owner.name
        ));
    }
    log::info!(
        "{:?} belongs to {} (uid {}): the client library will be loaded as that user",
        target,
        owner.name,
        owner.uid
    );
    RuntimeVerdict::SwitchTo(owner)
}

/// Without root there is nothing to escalate: the library runs with the
/// privileges the user already has, so the runtime is loaded unchecked.
pub fn assess(path: &Path, check: bool, safe_entries: &[String]) -> RuntimeVerdict {
    if !check {
        log::info!(
            "Permission check disabled; skipping validation for {:?}",
            path
        );
        return RuntimeVerdict::Load;
    }
    if !is_running_as_root() {
        log::info!(
            "Not running as root; skipping permission validation for {:?}",
            path
        );
        return RuntimeVerdict::Load;
    }
    assess_tree(path, safe_entries)
}

/// A caller that never had root passes, there is nothing to escalate. One that
/// gave up root for the owner of the runtime does not: it judges the file by
/// the owner's identity instead of skipping the check.
///
/// The `Err` names the checked path only; which entry of it is writable, and by
/// whom, stays in the log the walk writes.
pub fn validate_file(path: &Path, check: bool, safe_entries: &[String]) -> Result<(), String> {
    if !check {
        log::info!(
            "Permission check disabled; skipping validation for {:?}",
            path
        );
        return Ok(());
    }
    if is_running_as_root() {
        return validate_against(path, &SafeIds::configured(safe_entries), Ancestry::RootOnly);
    }
    match switched_to() {
        Some(owner) => validate_against(
            path,
            &SafeIds::for_owner(owner, safe_entries),
            Ancestry::Shared,
        ),
        None => {
            log::info!(
                "Not running as root; skipping permission validation for {:?}",
                path
            );
            Ok(())
        }
    }
}

fn validate_against(path: &Path, safe: &SafeIds, ancestry: Ancestry) -> Result<(), String> {
    let (target, md) = resolve(path).map_err(|e| format!("Cannot resolve {path:?}: {e}"))?;
    if validate_tree(&target, &md, safe, ancestry) {
        return Ok(());
    }
    Err(format!(
        "{path:?} is writable by someone other than root or the owner of the runtime"
    ))
}

static SWITCHED_TO: OnceLock<RunAsUser> = OnceLock::new();

pub fn switched_to() -> Option<&'static RunAsUser> {
    SWITCHED_TO.get()
}

fn last_os_error(what: &str) -> std::io::Error {
    let e = std::io::Error::last_os_error();
    std::io::Error::new(e.kind(), format!("{what} failed: {e}"))
}

pub fn drop_privileges(user: &RunAsUser) -> std::io::Result<()> {
    // SAFETY: `setgroups` reads `groups.len()` gids from `groups.as_ptr()`, the
    // buffer of a live `Vec<u32>`, and `gid_t` is `u32` on Linux. `setgid` and
    // `setuid` take plain integers and touch no memory of ours.
    unsafe {
        if libc::setgroups(user.groups.len() as _, user.groups.as_ptr()) != 0 {
            return Err(last_os_error("setgroups"));
        }
        if libc::setgid(user.gid) != 0 {
            return Err(last_os_error("setgid"));
        }
        if libc::setuid(user.uid) != 0 {
            return Err(last_os_error("setuid"));
        }
        // setuid(0) succeeding would mean the saved uid is still 0
        if user.uid != ROOT_UID && libc::setuid(ROOT_UID) == 0 {
            return Err(std::io::Error::other(
                "root privileges could be regained after dropping them",
            ));
        }
    }
    SWITCHED_TO
        .set(user.clone())
        .map_err(|_| std::io::Error::other("privileges were already dropped once"))?;
    // SAFETY: the switch runs from `main` before the tokio runtime is built, so
    // no other thread can read the environment while it is written.
    unsafe {
        std::env::set_var("HOME", &user.home);
        std::env::set_var("USER", &user.name);
        std::env::set_var("LOGNAME", &user.name);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const FILE: u32 = 0o100000;
    const DIR: u32 = S_IFDIR;
    const LINK: u32 = S_IFLNK;

    const ORA_UID: u32 = 54321;
    const ORA_GID: u32 = 54321;
    const DBA_GID: u32 = 54322;
    const STRANGER: u32 = 4242;

    fn root_only() -> SafeIds {
        SafeIds::default()
    }

    fn oracle() -> RunAsUser {
        RunAsUser {
            uid: ORA_UID,
            gid: ORA_GID,
            groups: vec![ORA_GID, DBA_GID],
            name: "oracle".to_string(),
            home: PathBuf::from("/home/oracle"),
        }
    }

    fn oracle_safe() -> SafeIds {
        SafeIds::for_owner(&oracle(), &[])
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
    fn test_owner_and_owner_groups_are_safe() {
        assert!(is_entry_safe(
            ORA_UID,
            ORA_GID,
            FILE | 0o644,
            &oracle_safe()
        ));
        // The Oracle installer leaves $ORACLE_BASE group writable for oinstall.
        assert!(is_entry_safe(ORA_UID, ORA_GID, DIR | 0o775, &oracle_safe()));
        assert!(is_entry_safe(ORA_UID, DBA_GID, DIR | 0o775, &oracle_safe()));
    }

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
        assert!(!is_entry_safe(ORA_UID, ORA_GID, FILE | 0o644, &root_only()));
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
    fn test_shared_ancestor_only_has_to_be_safe_from_everyone() {
        assert!(is_shared_ancestor_safe(DIR | 0o755));
        assert!(is_shared_ancestor_safe(DIR | 0o775));
        assert!(is_shared_ancestor_safe(DIR | STICKY | 0o777));
        assert!(!is_shared_ancestor_safe(DIR | 0o777));
        assert!(!is_shared_ancestor_safe(DIR | 0o757));
    }

    #[test]
    fn test_safe_ids_for_owner_carry_the_owner_and_all_owner_groups() {
        let ids = oracle_safe();
        assert_eq!(ids.uids, HashSet::from([ORA_UID]));
        assert_eq!(ids.gids, HashSet::from([ORA_GID, DBA_GID]));
        assert!(!ids.uids.contains(&STRANGER));
    }

    #[test]
    fn test_configured_entries_are_added() {
        let ids = SafeIds::configured(&["root".to_string()]);
        assert!(ids.uids.contains(&0));

        // Numeric entries count as both a uid and a gid. Group *names* are
        // deliberately not asserted on: root's group is `root` on some distros
        // and `wheel` on others.
        let ids = SafeIds::configured(&["4242".to_string()]);
        assert!(ids.uids.contains(&4242));
        assert!(ids.gids.contains(&4242));

        let ids = SafeIds::configured(&["_no_such_user_or_group_42_".to_string()]);
        assert_eq!(ids, SafeIds::default());

        let ids = SafeIds::for_owner(&oracle(), &["4242".to_string()]);
        assert!(ids.uids.contains(&ORA_UID));
        assert!(ids.uids.contains(&4242));
    }

    #[test]
    fn test_disabled_check_skips_validation() {
        // The `check` flag is honoured before the root check, so this holds
        // whether or not the test itself runs as root. The path does not even
        // have to exist: nothing is looked at once the check is off.
        assert_eq!(
            assess(Path::new("/no/such/runtime"), false, &[]),
            RuntimeVerdict::Load
        );
        assert!(validate_file(Path::new("/no/such/file.sql"), false, &[]).is_ok());
    }
}
