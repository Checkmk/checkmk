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

use std::ffi::{OsStr, OsString};
use std::fs::Metadata;
use std::os::windows::ffi::{OsStrExt, OsStringExt};
use std::os::windows::fs::MetadataExt;
use std::path::Path;
use std::ptr;

use winapi::ctypes::c_void;
use winapi::shared::minwindef::DWORD;
use winapi::shared::sddl::ConvertSidToStringSidW;
use winapi::shared::winerror::ERROR_SUCCESS;
use winapi::um::accctrl::SE_FILE_OBJECT;
use winapi::um::aclapi::{GetNamedSecurityInfoW, GetSecurityInfo};
use winapi::um::fileapi::{CreateFileW, OPEN_EXISTING};
use winapi::um::handleapi::{CloseHandle, INVALID_HANDLE_VALUE};
use winapi::um::securitybaseapi::{GetAce, IsValidSid};
use winapi::um::winbase::{LocalFree, FILE_FLAG_BACKUP_SEMANTICS, FILE_FLAG_OPEN_REPARSE_POINT};
use winapi::um::winnt::{
    ACCESS_ALLOWED_ACE, ACCESS_ALLOWED_ACE_TYPE, ACE_HEADER, DACL_SECURITY_INFORMATION, DELETE,
    FILE_APPEND_DATA, FILE_ATTRIBUTE_REPARSE_POINT, FILE_SHARE_DELETE, FILE_SHARE_READ,
    FILE_SHARE_WRITE, FILE_WRITE_ATTRIBUTES, FILE_WRITE_DATA, FILE_WRITE_EA, GENERIC_ALL,
    GENERIC_WRITE, PACL, PSID, READ_CONTROL, WRITE_DAC, WRITE_OWNER,
};

// Bounds tree recursion so admin-made junction cycles still terminate.
const MAX_DEPTH: usize = 64;

// Access bits corresponding to the legacy `Write`/`Modify`/`FullControl`.
const WRITE_MASK: DWORD = FILE_WRITE_DATA
    | FILE_APPEND_DATA
    | FILE_WRITE_ATTRIBUTES
    | FILE_WRITE_EA
    | DELETE
    | WRITE_DAC
    | WRITE_OWNER
    | GENERIC_WRITE
    | GENERIC_ALL;

/// Returns true iff the current process is running elevated (administrator).
pub fn is_running_as_admin() -> bool {
    is_elevated::is_elevated()
}

/// Well-known SIDs that the legacy plugin trusts unconditionally:
///   * `S-1-5-18`      — NT AUTHORITY\SYSTEM
///   * `S-1-5-32-544`  — BUILTIN\Administrators
///   * `S-1-5-21-*-512` — {domain}\Domain Admins
///   * `S-1-5-21-*-519` — {domain}\Enterprise Admins
fn is_privileged_sid(sid_str: &str) -> bool {
    if sid_str == "S-1-5-18" || sid_str == "S-1-5-32-544" {
        return true;
    }
    if let Some(rest) = sid_str.strip_prefix("S-1-5-21-") {
        return rest.ends_with("-512") || rest.ends_with("-519");
    }
    false
}

fn sid_to_string(sid: PSID) -> Option<String> {
    if sid.is_null() || unsafe { IsValidSid(sid) } == 0 {
        return None;
    }
    let mut raw: *mut u16 = ptr::null_mut();
    if unsafe { ConvertSidToStringSidW(sid, &mut raw) } == 0 || raw.is_null() {
        return None;
    }
    let mut len = 0usize;
    // SAFETY: ConvertSidToStringSidW returns a NUL-terminated wide string.
    unsafe {
        while *raw.add(len) != 0 {
            len += 1;
        }
    }
    let slice = unsafe { std::slice::from_raw_parts(raw, len) };
    let s = OsString::from_wide(slice).to_string_lossy().into_owned();
    unsafe {
        LocalFree(raw as *mut c_void);
    }
    Some(s)
}

fn to_wide(path: &Path) -> Vec<u16> {
    OsStr::new(path).encode_wide().chain(Some(0)).collect()
}

fn walk_dacl(pdacl: PACL, path: &Path) -> bool {
    if pdacl.is_null() {
        // A NULL DACL grants every principal full access — unsafe by
        // definition.
        log::warn!("Path {:?} has a NULL DACL", path);
        return false;
    }
    let ace_count = DWORD::from(unsafe { (*pdacl).AceCount });
    for i in 0..ace_count {
        let mut pace: *mut c_void = ptr::null_mut();
        if unsafe { GetAce(pdacl, i, &mut pace) } == 0 || pace.is_null() {
            log::warn!("Failed to read ACE #{} of {:?}", i, path);
            return false;
        }
        // SAFETY: GetAce returns a pointer to an ACE whose first field is
        // always an ACE_HEADER.
        let header_ptr = pace as *const ACE_HEADER;
        let ace_type = unsafe { (*header_ptr).AceType };
        // We only care about ACCESS_ALLOWED; deny/audit ACEs cannot grant
        // write access.
        if ace_type != ACCESS_ALLOWED_ACE_TYPE {
            continue;
        }
        let ace = pace as *const ACCESS_ALLOWED_ACE;
        let mask = unsafe { (*ace).Mask };
        if mask & WRITE_MASK == 0 {
            continue;
        }
        // SidStart is a variable-length trailing field; casting its address
        // yields a valid PSID.
        let psid: PSID = unsafe { &(*ace).SidStart as *const _ as PSID };
        let Some(sid_str) = sid_to_string(psid) else {
            log::warn!("ACE #{} of {:?} has an invalid SID", i, path);
            return false;
        };
        if !is_privileged_sid(&sid_str) {
            log::warn!(
                "Path {:?} grants write access to non-privileged SID {}",
                path,
                sid_str
            );
            return false;
        }
    }
    true
}

/// Check the DACL of `path`. Follows reparse points to their target.
fn only_admins_can_modify(path: &Path) -> bool {
    let wide = to_wide(path);
    let mut pdacl: PACL = ptr::null_mut();
    let mut sd: *mut c_void = ptr::null_mut();
    let status = unsafe {
        GetNamedSecurityInfoW(
            wide.as_ptr() as *mut u16,
            SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION,
            ptr::null_mut(),
            ptr::null_mut(),
            &mut pdacl,
            ptr::null_mut(),
            &mut sd,
        )
    };
    if status != ERROR_SUCCESS {
        log::warn!(
            "GetNamedSecurityInfoW failed for {:?} (status {})",
            path,
            status
        );
        return false;
    }
    let ok = walk_dacl(pdacl, path);
    if !sd.is_null() {
        unsafe {
            LocalFree(sd);
        }
    }
    ok
}

/// Check the DACL of the reparse point itself, without following it.
/// `FILE_FLAG_OPEN_REPARSE_POINT` stops the resolve; `FILE_FLAG_BACKUP_SEMANTICS`
/// lets us open a directory handle.
fn only_admins_can_modify_no_follow(path: &Path) -> bool {
    let wide = to_wide(path);
    let handle = unsafe {
        CreateFileW(
            wide.as_ptr(),
            READ_CONTROL,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            ptr::null_mut(),
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
            ptr::null_mut(),
        )
    };
    if handle == INVALID_HANDLE_VALUE || handle.is_null() {
        log::warn!("CreateFileW (no-follow) failed for {:?}", path);
        return false;
    }
    let mut pdacl: PACL = ptr::null_mut();
    let mut sd: *mut c_void = ptr::null_mut();
    let status = unsafe {
        GetSecurityInfo(
            handle,
            SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION,
            ptr::null_mut(),
            ptr::null_mut(),
            &mut pdacl,
            ptr::null_mut(),
            &mut sd,
        )
    };
    unsafe {
        CloseHandle(handle);
    }
    if status != ERROR_SUCCESS {
        log::warn!(
            "GetSecurityInfo (no-follow) failed for {:?} (status {})",
            path,
            status
        );
        return false;
    }
    let ok = walk_dacl(pdacl, path);
    if !sd.is_null() {
        unsafe {
            LocalFree(sd);
        }
    }
    ok
}

fn is_reparse_point(md: &Metadata) -> bool {
    md.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0
}

/// For a reparse point, check its own DACL so a non-admin cannot redirect the walk.
fn check_reparse_point(path: &Path, md: &Metadata) -> bool {
    if is_reparse_point(md) && !only_admins_can_modify_no_follow(path) {
        log::warn!("Reparse point {:?} is writable by non-privileged SID", path);
        return false;
    }
    true
}

/// Check every entry reachable from `path` is only modifiable by privileged
/// principals. Reparse points are checked in place and then followed.
fn only_admins_can_modify_tree(path: &Path, depth: usize) -> bool {
    if depth == 0 {
        log::warn!(
            "Permission check aborted at {:?}: reparse recursion limit hit",
            path
        );
        return false;
    }
    if !only_admins_can_modify(path) {
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
        if !check_reparse_point(&sub, &md) {
            return false;
        }
        // Follow reparse points to find out whether to recurse.
        let follow_md = match std::fs::metadata(&sub) {
            Ok(m) => m,
            Err(e) => {
                log::warn!("Cannot follow {:?}: {}", sub, e);
                return false;
            }
        };
        if follow_md.is_dir() {
            if !only_admins_can_modify_tree(&sub, depth - 1) {
                return false;
            }
        } else if !only_admins_can_modify(&sub) {
            return false;
        }
    }
    true
}

/// Entry point for `setup::validate_permissions` on Windows. Non-admin
/// callers always pass; admins require the path (and subtree for directories)
/// to be only modifiable by privileged principals.
pub fn validate(path: &Path) -> bool {
    if !is_running_as_admin() {
        log::info!(
            "Not running as admin; skipping permission validation for {:?}",
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
    if !check_reparse_point(path, &md) {
        return false;
    }
    let follow_md = match std::fs::metadata(path) {
        Ok(m) => m,
        Err(e) => {
            log::warn!("Cannot follow {:?}: {}", path, e);
            return false;
        }
    };
    if follow_md.is_dir() {
        only_admins_can_modify_tree(path, MAX_DEPTH)
    } else {
        only_admins_can_modify(path)
    }
}

#[cfg(test)]
mod tests {
    use super::is_privileged_sid;

    #[test]
    fn test_is_privileged_sid_system_and_builtin_admins() {
        assert!(is_privileged_sid("S-1-5-18"));
        assert!(is_privileged_sid("S-1-5-32-544"));
    }

    #[test]
    fn test_is_privileged_sid_domain_and_enterprise_admins() {
        assert!(is_privileged_sid("S-1-5-21-1111-2222-3333-512"));
        assert!(is_privileged_sid("S-1-5-21-1111-2222-3333-519"));
    }

    #[test]
    fn test_is_privileged_sid_rejects_users_and_random_rids() {
        assert!(!is_privileged_sid("S-1-5-32-545")); // BUILTIN\Users
        assert!(!is_privileged_sid("S-1-5-21-1111-2222-3333-1001")); // random user
        assert!(!is_privileged_sid("S-1-5-21-1111-2222-3333-513")); // Domain Users
        assert!(!is_privileged_sid(""));
    }
}
