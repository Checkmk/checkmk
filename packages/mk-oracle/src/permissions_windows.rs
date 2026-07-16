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

use std::collections::HashSet;
use std::ffi::{OsStr, OsString};
use std::fs::Metadata;
use std::os::windows::ffi::{OsStrExt, OsStringExt};
use std::os::windows::fs::MetadataExt;
use std::path::Path;
use std::ptr;

use winapi::ctypes::c_void;
use winapi::shared::basetsd::DWORD_PTR;
use winapi::shared::lmcons::MAX_PREFERRED_LENGTH;
use winapi::shared::minwindef::{DWORD, LPBYTE};
use winapi::shared::sddl::{ConvertSidToStringSidW, ConvertStringSidToSidW};
use winapi::shared::winerror::ERROR_SUCCESS;
use winapi::um::accctrl::SE_FILE_OBJECT;
use winapi::um::aclapi::{GetNamedSecurityInfoW, GetSecurityInfo};
use winapi::um::fileapi::{CreateFileW, OPEN_EXISTING};
use winapi::um::handleapi::{CloseHandle, INVALID_HANDLE_VALUE};
use winapi::um::lmaccess::{NetLocalGroupGetMembers, LOCALGROUP_MEMBERS_INFO_0};
use winapi::um::lmapibuf::NetApiBufferFree;
use winapi::um::securitybaseapi::{GetAce, IsValidSid};
use winapi::um::winbase::{
    LocalFree, LookupAccountSidW, FILE_FLAG_BACKUP_SEMANTICS, FILE_FLAG_OPEN_REPARSE_POINT,
};
use winapi::um::winnt::{
    ACCESS_ALLOWED_ACE, ACCESS_ALLOWED_ACE_TYPE, ACE_HEADER, DACL_SECURITY_INFORMATION, DELETE,
    FILE_APPEND_DATA, FILE_ATTRIBUTE_REPARSE_POINT, FILE_SHARE_DELETE, FILE_SHARE_READ,
    FILE_SHARE_WRITE, FILE_WRITE_ATTRIBUTES, FILE_WRITE_DATA, FILE_WRITE_EA, GENERIC_ALL,
    GENERIC_WRITE, PACL, PSID, READ_CONTROL, SID_NAME_USE, WRITE_DAC, WRITE_OWNER,
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

/// Well-known SID for BUILTIN\Administrators.
const ADMINISTRATORS_SID: &str = "S-1-5-32-544";

/// `$admin_sids` from the legacy plugin — confirmed by Security team:
///   * `S-1-5-18`      — NT AUTHORITY\SYSTEM
///   * `S-1-5-32-544`  — BUILTIN\Administrators
const ADMIN_SIDS: &[&str] = &["S-1-5-18", ADMINISTRATORS_SID];

/// Port of the legacy `Test-DomainSid`: true for a Domain Admins (RID 512)
/// or Enterprise Admins (RID 519) SID, i.e. `S-1-5-21-<a>-<b>-<c>-51{2,9}`.
/// The RID (last component) must equal 512 or 519 exactly; matching a prefix
/// or an interior subauthority would wrongly trust ordinary users.
/// TODO(sk): check the captured domain id against the local domain instead
/// of trusting any domain's admin group; a mismatch is highly unlikely, but
/// worth hardening later.
fn is_domain_sid(sid_str: &str) -> bool {
    sid_str
        .strip_prefix("S-1-5-21-")
        .and_then(|rest| rest.rsplit_once('-'))
        .is_some_and(|(_, rid)| rid == "512" || rid == "519")
}

/// Well-known SIDs that the legacy plugin trusts unconditionally: any SID in
/// [`ADMIN_SIDS`], plus domain/enterprise admins ([`is_domain_sid`]).
fn is_privileged_sid(sid_str: &str) -> bool {
    ADMIN_SIDS.contains(&sid_str) || is_domain_sid(sid_str)
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

fn str_to_wide(s: &str) -> Vec<u16> {
    OsStr::new(s).encode_wide().chain(Some(0)).collect()
}

/// Resolve a SID to its `DOMAIN\name` account name, mirroring what the
/// legacy plugin gets from `NTAccount`/`Get-LocalGroupMember`.
fn resolve_account_name(sid: PSID) -> Option<String> {
    let mut name_buf = [0u16; 256];
    let mut domain_buf = [0u16; 256];
    let mut name_len = name_buf.len() as DWORD;
    let mut domain_len = domain_buf.len() as DWORD;
    let mut sid_use: SID_NAME_USE = 0;
    let ok = unsafe {
        LookupAccountSidW(
            ptr::null(),
            sid,
            name_buf.as_mut_ptr(),
            &mut name_len,
            domain_buf.as_mut_ptr(),
            &mut domain_len,
            &mut sid_use,
        )
    };
    if ok == 0 {
        return None;
    }
    let name = OsString::from_wide(&name_buf[..name_len as usize])
        .to_string_lossy()
        .into_owned();
    let domain = OsString::from_wide(&domain_buf[..domain_len as usize])
        .to_string_lossy()
        .into_owned();
    Some(if domain.is_empty() {
        name
    } else {
        format!("{}\\{}", domain, name)
    })
}

/// Members of the local Administrators group, as SID strings. Mirrors
/// `Get-LocalGroupMember -SID "S-1-5-32-544"` from the legacy plugin: a
/// principal added directly to that group is safe even though it isn't one
/// of the well-known SIDs `is_privileged_sid` recognizes.
fn local_administrators() -> HashSet<String> {
    let mut members = HashSet::new();
    let mut group_sid: PSID = ptr::null_mut();
    let sid_wide = str_to_wide(ADMINISTRATORS_SID);
    if unsafe { ConvertStringSidToSidW(sid_wide.as_ptr(), &mut group_sid) } == 0 {
        log::warn!("Failed to build SID for {}", ADMINISTRATORS_SID);
        return members;
    }
    // NetLocalGroupGetMembers wants the (localized) group name, not the SID.
    let group_name =
        resolve_account_name(group_sid).and_then(|full| full.rsplit('\\').next().map(str_to_wide));
    unsafe {
        LocalFree(group_sid);
    }
    let Some(group_name) = group_name else {
        log::warn!(
            "Failed to resolve local group name for {}",
            ADMINISTRATORS_SID
        );
        return members;
    };

    let mut buf: LPBYTE = ptr::null_mut();
    let mut entries_read: DWORD = 0;
    let mut total_entries: DWORD = 0;
    let mut resume_handle: DWORD_PTR = 0;
    let status = unsafe {
        NetLocalGroupGetMembers(
            ptr::null(),
            group_name.as_ptr(),
            0,
            &mut buf,
            MAX_PREFERRED_LENGTH,
            &mut entries_read,
            &mut total_entries,
            &mut resume_handle,
        )
    };
    if status != ERROR_SUCCESS || buf.is_null() {
        log::warn!("NetLocalGroupGetMembers failed with status {}", status);
        return members;
    }
    // SAFETY: NetLocalGroupGetMembers filled in `entries_read` contiguous
    // LOCALGROUP_MEMBERS_INFO_0 records at `buf`.
    let infos = buf as *const LOCALGROUP_MEMBERS_INFO_0;
    for i in 0..entries_read {
        let info = unsafe { &*infos.add(i as usize) };
        if let Some(sid_str) = sid_to_string(info.lgrmi0_sid) {
            members.insert(sid_str);
        }
    }
    unsafe {
        NetApiBufferFree(buf as *mut c_void);
    }
    members
}

/// Full-parity port of the legacy `Invoke-SafetyCheck`. An ACE granting
/// write access is safe only if its SID is a well-known admin group or
/// domain/enterprise admin ([`is_privileged_sid`]), or a member of
/// `local_admins` (see [`local_administrators`]).
fn walk_dacl_ex(pdacl: PACL, path: &Path, local_admins: &HashSet<String>) -> bool {
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
        let header_ptr = pace as *const ACE_HEADER;
        let ace_type = unsafe { (*header_ptr).AceType };
        // We only care about ACCESS_ALLOWED; deny/audit ACEs cannot grant write access.
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
        if is_privileged_sid(&sid_str) || local_admins.contains(&sid_str) {
            continue;
        }
        log::warn!(
            "Path {:?} grants write access to non-privileged SID {}",
            path,
            sid_str
        );
        return false;
    }
    true
}

/// Check the DACL of `path`. Follows reparse points to their target.
fn only_admins_can_modify(path: &Path, local_admins: &HashSet<String>) -> bool {
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
    let ok = walk_dacl_ex(pdacl, path, local_admins);
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
fn only_admins_can_modify_no_follow(path: &Path, local_admins: &HashSet<String>) -> bool {
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
    let ok = walk_dacl_ex(pdacl, path, local_admins);
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
fn check_reparse_point(path: &Path, md: &Metadata, local_admins: &HashSet<String>) -> bool {
    if is_reparse_point(md) && !only_admins_can_modify_no_follow(path, local_admins) {
        log::warn!("Reparse point {:?} is writable by non-privileged SID", path);
        return false;
    }
    true
}

/// Check every entry reachable from `path` is only modifiable by privileged
/// principals. Reparse points are checked in place and then followed.
fn only_admins_can_modify_tree(path: &Path, depth: usize, local_admins: &HashSet<String>) -> bool {
    if depth == 0 {
        log::warn!(
            "Permission check aborted at {:?}: reparse recursion limit hit",
            path
        );
        return false;
    }
    if !only_admins_can_modify(path, local_admins) {
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
        if !check_reparse_point(&sub, &md, local_admins) {
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
            if !only_admins_can_modify_tree(&sub, depth - 1, local_admins) {
                return false;
            }
        } else if !only_admins_can_modify(&sub, local_admins) {
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
    // Resolved once per validation run instead of per-ACL-walk: the tree walk
    // below can call only_admins_can_modify for every file under `path`.
    let local_admins = local_administrators();
    if !check_reparse_point(path, &md, &local_admins) {
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
        only_admins_can_modify_tree(path, MAX_DEPTH, &local_admins)
    } else {
        only_admins_can_modify(path, &local_admins)
    }
}

#[cfg(test)]
mod tests {
    use super::{is_privileged_sid, local_administrators, only_admins_can_modify};
    use std::path::PathBuf;

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

    // Regression: the RID (and any subauthority) must equal 512/519 exactly,
    // not merely start with those digits. A prefix/substring match wrongly
    // trusted ordinary users and whole domains.
    #[test]
    fn test_is_privileged_sid_rejects_512_519_prefixes() {
        assert!(!is_privileged_sid("S-1-5-21-1111-2222-3333-5120")); // RID starts 512
        assert!(!is_privileged_sid("S-1-5-21-1111-2222-3333-5129"));
        assert!(!is_privileged_sid("S-1-5-21-1111-2222-3333-5199")); // RID starts 519
        assert!(!is_privileged_sid("S-1-5-21-1111-2222-3333-51234"));
        // Subauthority starts with 512: every user of such a domain must NOT
        // be trusted just because the domain id begins with those digits.
        assert!(!is_privileged_sid("S-1-5-21-5123456789-1111-2222-1001"));
        assert!(!is_privileged_sid("S-1-5-21-5190000000-1111-2222-1001"));
    }

    #[test]
    fn test_only_admins_can_modify() {
        let protected_path = PathBuf::from("c:\\Windows\\Registration");
        assert!(
            only_admins_can_modify(protected_path.as_path(), &local_administrators()),
            "This is wrong: {protected_path:?} is protected"
        );
        let un_protected_path = PathBuf::from("c:\\Users\\Public\\Downloads");
        assert!(
            !only_admins_can_modify(un_protected_path.as_path(), &local_administrators()),
            "This is wrong: {un_protected_path:?} is not protected"
        );
    }
}
