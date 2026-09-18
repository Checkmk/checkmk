// Copyright (C) 2026 Checkmk GmbH
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

use crate::platform::registry::get_instances;
use crate::types::{AliasInfo, HostName, InstanceAlias, LocalInstance, Port, ServiceName, Sid};
use anyhow::{Context, Result};
use regex::Regex;
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::LazyLock;

/// Regex pattern to match Oracle PMON processes and capture the SID.
///
/// Group 1: the prefix (e.g. `ora_pmon_`)
/// Group 2: the SID name (e.g. `TEST19`)
const SID_MASK: &str = r"^(asm_pmon_|ora_pmon_|xe_pmon_|db_pmon_)(.+)";

/// Retrieves local Oracle SIDs, sorted in ascending order.
/// On Windows: the instance registry (SOFTWARE\Oracle), which lists installed
/// instances rather than running ones.
/// On Unix: only SIDs with a running PMON process.
/// Note: oratab plays no part in discovery. Two other places do read it on
/// Unix: `setup::detect_host_runtime`, to search for a host Oracle client, and
/// `dump_detected_sids` below, which therefore names other instances than this
/// function returns.
pub fn get_local_sid_names() -> Vec<String> {
    let mut names: Vec<String> = if cfg!(windows) {
        get_instances(None)
            .unwrap_or_default()
            .into_iter()
            .map(|i| i.name.to_string().to_uppercase())
            .collect()
    } else {
        find_sids_by_processes(Some(SID_MASK))
            .unwrap_or_default()
            .into_iter()
            .map(|i| i.to_uppercase())
            .collect()
    };

    names.sort();
    names
}

/// Extracts the SID (regex group 2) from a single process parameter.
///
/// The captured SID is upper-cased because Oracle SIDs are case-insensitive while the
/// Linux process name carries a lower-case variant (e.g. `ora_pmon_test23` -> `TEST23`).
/// Returns `None` when `param` does not match a known PMON pattern.
fn capture_sid(re: &Regex, param: &str) -> Option<String> {
    re.captures(param)
        .and_then(|c| c.get(2))
        .map(|m| m.as_str().to_uppercase())
}

/// Method is similar to `ps -ef | grep <match_string>`.
/// Empty on Windows, which has no per-SID processes.
/// Linux is scanned differently from the other Unixes. The process table of a
/// Linux host also contains the processes of every container on that host.
pub fn find_sids_by_processes(match_string: Option<&str>) -> Result<HashSet<String>> {
    if cfg!(windows) {
        return Ok(HashSet::new());
    }
    let re = Regex::new(match_string.unwrap_or(SID_MASK))?;
    if cfg!(target_os = "linux") {
        sids_outside_containers(&re)
    } else {
        sids_from_process_table(&re)
    }
}

fn run_ps(args: &[&str]) -> Result<String> {
    let output = std::process::Command::new("ps").args(args).output()?;
    anyhow::ensure!(
        output.status.success(),
        "ps failed with {}: {}",
        output.status,
        String::from_utf8_lossy(&output.stderr)
    );
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

/// Solaris and AIX. A PMON process renames argv[0] and takes no arguments, so
/// only the first word of a command line can be a SID.
fn sids_from_process_table(re: &Regex) -> Result<HashSet<String>> {
    let process_table = run_ps(&["-A", "-o", "args="])?;
    Ok(process_table
        .lines()
        .filter_map(|line| line.split_whitespace().next())
        .filter_map(|command| capture_sid(re, command))
        .collect())
}

/// Linux. A PMON process that runs in a container is not an instance of the
/// host, so the SID of that process is dropped. The `pid=` column supplies the
/// PID that the cgroup lookup needs.
fn sids_outside_containers(re: &Regex) -> Result<HashSet<String>> {
    let process_table = run_ps(&["-A", "-o", "pid=", "-o", "args="])?;
    let own = cgroup_paths("self");
    Ok(process_table
        .lines()
        .filter_map(|line| {
            let mut fields = line.split_whitespace();
            let pid = fields.next()?;
            let sid = capture_sid(re, fields.next()?)?;
            if is_foreign(&own, &cgroup_paths(pid)) {
                log::info!("skipping SID {sid}: PMON process {pid} belongs to a foreign container");
                None
            } else {
                Some(sid)
            }
        })
        .collect())
}

fn cgroup_paths(pid: &str) -> Vec<String> {
    std::fs::read_to_string(format!("/proc/{pid}/cgroup"))
        .map(|content| {
            content
                .lines()
                .filter_map(|line| line.splitn(3, ':').nth(2).map(str::to_owned))
                .collect()
        })
        .unwrap_or_default()
}

fn names_container(path: &str) -> bool {
    const MARKERS: &[&str] = &[
        "docker-",
        "/docker/",
        "crio-",
        "cri-containerd-",
        "kubepods",
        "libpod-",
        "/lxc/",
        "lxc.payload",
    ];
    MARKERS.iter().any(|marker| path.contains(marker))
}

fn is_foreign(own: &[String], candidate: &[String]) -> bool {
    let containerized = own.is_empty() || own.iter().any(|p| p == "/" || p.contains("/.."));
    !containerized && candidate.iter().any(|p| names_container(p))
}

fn format_instance_info(
    local_instance: &LocalInstance,
    known_processes: Option<&HashSet<String>>,
) -> String {
    format!(
        "{:16} {:5} {:60} {}",
        local_instance.name,
        local_instance.state(known_processes),
        local_instance.home.display(),
        local_instance
            .base
            .as_ref()
            .map(|p| p.display().to_string())
            .unwrap_or_else(|| "N/A".to_string()),
    )
}

fn instance_info_header() -> String {
    format!(
        "{:16} {:5} {:60} {}",
        "SID", "STATE", "ORACLE_HOME", "ORACLE_BASE"
    )
}

/// The SIDs of the running Oracle processes, as far as they can be determined.
///
/// `None` means the question cannot be answered, so an instance's state is
/// unknown rather than stopped: on Windows the process list is not scanned at
/// all, and a failed scan is reported the same way as an empty one is not - an
/// empty set would claim every instance is stopped.
pub fn find_running_oracle_processes() -> Option<HashSet<String>> {
    if cfg!(windows) {
        return None;
    }
    Some(
        find_sids_by_processes(None)
            .map_err(|e| {
                log::info!("Error while detecting Oracle processes: {:?}", e);
            })
            .unwrap_or_default(),
    )
}

pub fn dump_detected_sids() -> String {
    print_detected_sids(
        &get_instances(None).unwrap_or_default(),
        find_running_oracle_processes(),
    )
}

fn print_detected_sids(
    locals: &[LocalInstance],
    oracle_processes: Option<HashSet<String>>,
) -> String {
    let rows = locals
        .iter()
        .map(|local| format_instance_info(local, oracle_processes.as_ref()))
        .collect::<Vec<String>>()
        .join("\n");
    if rows.is_empty() {
        "No local instances found.\n".to_string()
    } else {
        instance_info_header() + "\n" + &rows + "\n"
    }
}

/// `<name> =` at the start of a line: the only place an alias may appear, so a
/// `(SID = ...)` inside a descriptor is never mistaken for one.
static TNS_ENTRY_NAME: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^([A-Za-z0-9][\w.$-]*)\s*=").expect("hardcoded pattern must compile")
});

/// `(KEY = VALUE)` with a single-token value: enough for HOST, PORT, SID and
/// SERVICE_NAME, and it never matches a nested group such as `(DESCRIPTION = (`.
static TNS_PARAMETER: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\(\s*(HOST|PORT|SID|SERVICE_NAME)\s*=\s*([^\s()]+)\s*\)")
        .expect("hardcoded pattern must compile")
});

/// `IFILE = <path>`: an include directive, not an alias. Oracle allows several,
/// and the path may be quoted.
static TNS_IFILE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?im)^\s*IFILE\s*=\s*"?([^"\r\n]+?)"?\s*$"#)
        .expect("hardcoded pattern must compile")
});

/// How deep `IFILE` may nest. A cycle would otherwise recurse until the stack
/// runs out; the depth also bounds the work a hostile file can cause.
const TNS_MAX_IFILE_DEPTH: usize = 8;

/// Read the aliases of a `tnsnames.ora`.
///
/// Deliberately not a parser for the full Oracle grammar: it extracts only what
/// the plugin can act on - the alias, its first address and its first target -
/// and reports anything it cannot read as absent rather than failing. The file
/// belongs to the Oracle client, and a shape this reader does not understand
/// must never stop the monitoring.
///
/// Names come back upper-cased and hosts lower-cased: Oracle compares aliases,
/// SIDs and service names case-insensitively, while a host is a DNS name.
///
/// Only the first `ADDRESS` and the first `SID`/`SERVICE_NAME` of an entry are
/// taken - the plugin connects to one address, later ones are failover targets
/// it does not use.
///
/// `IFILE = <path>` directives are followed, as the Oracle client does, and
/// their aliases are appended after the ones of the including file. A relative
/// path is resolved against the directory of the file holding the directive. An
/// include that cannot be read is logged and skipped: it costs its aliases, not
/// the whole file.
///
/// # Errors
///
/// Returns an error only if `file` itself cannot be read.
pub fn parse_tns_names_ora(file: &Path) -> Result<Vec<AliasInfo>> {
    let content = fs::read_to_string(file)
        .with_context(|| format!("Failed to read tnsnames.ora at '{}'", file.display()))?;
    Ok(parse_tns_names_file_content(
        &content,
        file,
        TNS_MAX_IFILE_DEPTH,
    ))
}

/// The aliases of one file: its own, then those of every file it includes.
///
/// `depth` is the remaining `IFILE` budget; at zero the includes are reported and
/// skipped, which is what stops a cycle (`a.ora` including `b.ora` including
/// `a.ora`) from recursing forever.
fn parse_tns_names_file_content(content: &str, file: &Path, depth: usize) -> Vec<AliasInfo> {
    let cleaned = strip_tns_comments(content);

    let mut result = parse_tns_names_content(&cleaned);
    for include in tns_include_paths(&cleaned, file) {
        if depth == 0 {
            log::warn!(
                "tnsnames.ora at '{}': IFILE nesting deeper than {TNS_MAX_IFILE_DEPTH}, \
                 skipping '{}'",
                file.display(),
                include.display()
            );
            continue;
        }
        match fs::read_to_string(&include) {
            Ok(included) => {
                log::info!("tnsnames.ora: following IFILE '{}'", include.display());
                result.extend(parse_tns_names_file_content(&included, &include, depth - 1));
            }
            // The include belongs to the Oracle client; a missing or unreadable
            // one costs its aliases, not the aliases already read.
            Err(e) => log::warn!(
                "tnsnames.ora at '{}': cannot read IFILE '{}': {e}",
                file.display(),
                include.display()
            ),
        }
    }
    result
}

/// The `IFILE` paths of an already-cleaned content, each resolved against the
/// directory of the file it was found in - that is how the Oracle client reads a
/// relative include.
fn tns_include_paths(cleaned: &str, file: &Path) -> Vec<PathBuf> {
    let base = file.parent().unwrap_or_else(|| Path::new("."));
    TNS_IFILE
        .captures_iter(cleaned)
        .map(|c| {
            let path = c.get(1).expect("group 1 is not optional").as_str().trim();
            base.join(path)
        })
        .collect()
}

/// [`parse_tns_names_ora`] on already-read content.
pub fn parse_tns_names_content(content: &str) -> Vec<AliasInfo> {
    let cleaned = strip_tns_comments(content);

    // Every match opens an entry; its body reaches to the next match, or to the
    // end of the file for the last one.
    let starts: Vec<(usize, String)> = TNS_ENTRY_NAME
        .captures_iter(&cleaned)
        .map(|c| {
            let whole = c.get(0).expect("group 0 always exists");
            let name = c.get(1).expect("group 1 is not optional").as_str();
            (whole.end(), name.to_uppercase())
        })
        .collect();

    starts
        .iter()
        .enumerate()
        // `IFILE` is an include directive, not an alias: it is followed by
        // `parse_tns_names_file_content`, and reporting it here would put a
        // target-less entry into the result.
        .filter(|(_, (_, name))| name != "IFILE")
        .map(|(index, (body_start, name))| {
            let body_end =
                starts
                    .get(index + 1)
                    .map_or(cleaned.len(), |(next_start, next_name)| {
                        // The next body starts after its `<name> =`, so step back over
                        // the name and the `=` to end this body before it.
                        next_start - next_name.len()
                    });
            parse_tns_entry(name, &cleaned[*body_start..body_end])
        })
        .collect()
}

/// Drop `#` comments and blank lines, keeping the line structure so that the
/// `<name> =` anchor still works.
fn strip_tns_comments(content: &str) -> String {
    content
        .lines()
        .map(|line| line.split('#').next().unwrap_or(""))
        .filter(|line| !line.trim().is_empty())
        .collect::<Vec<_>>()
        .join("\n")
}

/// The first host, port and target of one entry body.
fn parse_tns_entry(name: &str, body: &str) -> AliasInfo {
    let mut host_name = None;
    let mut port = None;
    let mut sid = None;
    let mut service_name = None;

    for parameter in TNS_PARAMETER.captures_iter(body) {
        let key = parameter
            .get(1)
            .expect("group 1 is not optional")
            .as_str()
            .to_uppercase();
        let value = parameter.get(2).expect("group 2 is not optional").as_str();
        match key.as_str() {
            "HOST" if host_name.is_none() => host_name = Some(HostName::from(value.to_lowercase())),
            "PORT" if port.is_none() => match value.parse::<u16>() {
                Ok(number) => port = Some(Port(number)),
                Err(e) => log::warn!("{name}: port {value:?} is not a port number: {e}"),
            },
            // A SID and a service name are alternatives; the first one wins, so
            // an entry naming both is read the way the client reads it.
            "SID" if sid.is_none() && service_name.is_none() => {
                sid = Some(Sid::from(value.to_uppercase().as_str()))
            }
            "SERVICE_NAME" if sid.is_none() && service_name.is_none() => {
                service_name = Some(ServiceName::from(value.to_uppercase().as_str()))
            }
            _ => log::debug!("{name}: ignoring repeated or unknown parameter {key}"),
        }
    }

    AliasInfo {
        alias: InstanceAlias::from(name.to_string()),
        host_name,
        port,
        sid,
        service_name,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{InstanceName, LocalInstance, LocalInstanceState};
    use std::path::PathBuf;

    fn make_instance(name: &str, home: &str, base: Option<&str>) -> LocalInstance {
        LocalInstance {
            name: InstanceName::from(name),
            home: PathBuf::from(home),
            base: base.map(PathBuf::from),
        }
    }

    #[test]
    fn test_capture_sid_uppercases_lowercase() {
        let re = Regex::new(SID_MASK).expect("Failed to compile regex");
        assert_eq!(
            capture_sid(&re, "ora_pmon_test23"),
            Some("TEST23".to_string())
        );
        assert_eq!(
            capture_sid(&re, "ora_pmon_Test23"),
            Some("TEST23".to_string())
        );
        assert_eq!(capture_sid(&re, "asm_pmon_+ASM"), Some("+ASM".to_string()));
    }

    #[test]
    fn test_names_container() {
        assert!(names_container(
            "/system.slice/docker-cfa02fe92a5ef6a7c2fed620578bed5760ec0aee9368e2e746a023215c972bca.scope"
        ));
        assert!(names_container(
            "/../docker-b397f6fed93bf2921326d2535ebf689e.scope"
        ));
        assert!(names_container("/docker/b397f6fed93bf2921326d2535ebf689e"));
        assert!(names_container(
            "/kubepods.slice/kubepods-besteffort.slice/kubepods-besteffort-pod1234.slice/cri-containerd-abc.scope"
        ));
        assert!(names_container("/machine.slice/libpod-abc.scope"));

        // A systemd unit is not a container, however deeply nested.
        assert!(!names_container(
            "/system.slice/check-mk-agent@1234-127.0.0.1:6556.service"
        ));
        assert!(!names_container("/system.slice/oracle.service"));
        assert!(!names_container(
            "/user.slice/user-54321.slice/session-3.scope"
        ));
        assert!(!names_container("/"));
    }

    #[test]
    fn test_is_foreign_per_deployment() {
        let agent_on_host = [String::from("/system.slice/check-mk-agent@1234.service")];
        let agent_in_container = [String::from("/")];
        let db_on_host = [String::from("/system.slice/oracle-XE.service")];
        let db_in_container_from_host = [String::from(
            "/system.slice/docker-cfa02fe92a5ef6a7c2fed620578bed57.scope",
        )];
        let db_in_sibling_container = [String::from("/../docker-b397f6fed93bf2921326d2535e.scope")];

        assert!(is_foreign(&agent_on_host, &db_in_container_from_host));

        assert!(!is_foreign(&agent_on_host, &db_on_host));

        assert!(!is_foreign(&agent_in_container, &db_in_sibling_container));
        assert!(!is_foreign(&agent_in_container, &db_on_host));

        assert!(!is_foreign(&agent_in_container, &agent_in_container));

        assert!(!is_foreign(&[], &db_in_container_from_host));
    }

    /// The last two are the first word of `vi ora_pmon_TYPO` and of a command
    /// line that starts with a path. Only the first word of a line reaches
    /// `capture_sid`, so neither of them may yield a SID.
    #[test]
    fn test_capture_sid_no_match() {
        let re = Regex::new(SID_MASK).expect("Failed to compile regex");
        assert_eq!(capture_sid(&re, "pmon_test"), None);
        assert_eq!(capture_sid(&re, "some_other_process"), None);
        assert_eq!(capture_sid(&re, "vi"), None);
        assert_eq!(capture_sid(&re, "/usr/sbin/cron"), None);
    }

    fn parts(inst: LocalInstance, processes: Option<&HashSet<String>>) -> Vec<String> {
        format_instance_info(&inst, processes)
            .split_whitespace()
            .map(str::to_string)
            .collect()
    }

    /// Both sides of the match are upper-cased - `InstanceName::from` and
    /// `capture_sid` - so a lower-cased SID from either side still matches. If
    /// one of them stops doing it, a running instance silently reports `Stop`.
    #[test]
    fn test_state_matches_regardless_of_the_written_case() {
        let procs = HashSet::from(["ORCL".to_string()]);

        assert_eq!(
            make_instance("orcl", "/home", None).state(Some(&procs)),
            LocalInstanceState::Run
        );
        assert_eq!(
            make_instance("other", "/home", None).state(Some(&procs)),
            LocalInstanceState::Stop
        );
        assert_eq!(
            make_instance("orcl", "/home", None).state(None),
            LocalInstanceState::NA
        );
    }

    #[test]
    fn test_format_instance_info_no_processes() {
        let result = parts(make_instance("orcl", "/path/to/ora/home", None), None);
        assert_eq!(result, vec!["ORCL", "N/A", "/path/to/ora/home", "N/A"]);
    }

    #[test]
    fn test_format_instance_info_running() {
        let procs = HashSet::from(["TEST19".to_string()]);
        let result = parts(
            make_instance("TEST19", "/path/to/ora/home", Some("/path/to/ora/base")),
            Some(&procs),
        );
        assert_eq!(
            result,
            vec!["TEST19", "Run", "/path/to/ora/home", "/path/to/ora/base"]
        );
    }

    #[test]
    fn test_format_instance_info_stopped() {
        let result = parts(
            make_instance("TEST19", "/path/to/ora/home", Some("/path/to/ora/base")),
            Some(&HashSet::new()),
        );
        assert_eq!(
            result,
            vec!["TEST19", "Stop", "/path/to/ora/home", "/path/to/ora/base"]
        );
    }

    #[test]
    fn test_format_instance_info_no_base() {
        let result = parts(make_instance("XE", "/path/to/ora/home", None), None);
        assert_eq!(result, vec!["XE", "N/A", "/path/to/ora/home", "N/A"]);
    }

    fn split_row(line: &str) -> Vec<&str> {
        line.split_whitespace().collect()
    }

    /// Empty instance list — even with known processes the output is the "not found" message.
    #[test]
    fn test_print_detected_sids_empty() {
        let procs = HashSet::from(["abc".to_string(), "xyz".to_string()]);
        let result = print_detected_sids(&[], Some(procs));
        assert_eq!(result, "No local instances found.\n");
    }

    /// Windows output: process state is always "N/A" because we don't check processes on Windows, only registry.
    #[test]
    fn test_print_detected_sids_windows() {
        let instances = vec![
            make_instance("TEST19", "/path/to/ora/home", None),
            make_instance("XE", "/path/to/ora/xe", Some("/path/to/ora/base")),
        ];
        let output = print_detected_sids(&instances, None);
        let lines: Vec<&str> = output.lines().collect();
        assert_eq!(
            split_row(lines[1]),
            vec!["TEST19", "N/A", "/path/to/ora/home", "N/A"]
        );
        assert_eq!(
            split_row(lines[2]),
            vec!["XE", "N/A", "/path/to/ora/xe", "/path/to/ora/base"]
        );
    }

    /// Linux output: process has info "Run" or "Stop".
    #[test]
    fn test_print_detected_sids_linux() {
        let instances = vec![
            make_instance("TEST19", "/path/to/ora/home", Some("/path/to/ora/base")),
            make_instance("XE", "/path/to/ora/xe", None),
        ];
        let procs = HashSet::from(["TEST19".to_string()]);
        let output = print_detected_sids(&instances, Some(procs));
        let lines: Vec<&str> = output.lines().collect();
        assert_eq!(
            split_row(lines[1]),
            vec!["TEST19", "Run", "/path/to/ora/home", "/path/to/ora/base"]
        );
        assert_eq!(
            split_row(lines[2]),
            vec!["XE", "Stop", "/path/to/ora/xe", "N/A"]
        );
    }

    /// The file shipped in `tests/files/tns`, the shape a real client uses.
    const TNS_REFERENCE: &str = include_str!("../../tests/files/tns/tnsnames.ora");

    fn tns_entry(content: &str) -> AliasInfo {
        let entries = parse_tns_names_content(content);
        assert_eq!(entries.len(), 1, "expected exactly one entry: {entries:?}");
        entries.into_iter().next().expect("checked above")
    }

    fn tns_parts(
        entry: &AliasInfo,
    ) -> (
        String,
        Option<String>,
        Option<u16>,
        Option<String>,
        Option<String>,
    ) {
        (
            entry.alias.to_string(),
            entry.host_name.as_ref().map(ToString::to_string),
            entry.port.as_ref().map(|p| p.value()),
            entry.sid.as_ref().map(ToString::to_string),
            entry.service_name.as_ref().map(ToString::to_string),
        )
    }

    #[test]
    fn test_parse_tns_names_reference_file() {
        let entries = parse_tns_names_content(TNS_REFERENCE);

        assert_eq!(
            entries.iter().map(tns_parts).collect::<Vec<_>>(),
            vec![
                (
                    "ORA_LOCAL".to_string(),
                    Some("localhost".to_string()),
                    Some(1521),
                    Some("FREE".to_string()),
                    None,
                ),
                (
                    "ORA_REMOTE".to_string(),
                    Some("oracle-rocky-ci.lan.checkmk.net".to_string()),
                    Some(1521),
                    Some("SID23".to_string()),
                    None,
                ),
            ]
        );
    }

    #[test]
    fn test_parse_tns_names_multi_line_entry_with_service_name() {
        let entry = tns_entry(
            r#"
LISTENER20 =
  (DESCRIPTION =
    (ADDRESS = ( protocol = TCP)(host = ORACLE-rocky-ci.lan.checkmk.net)(PORT = 1522))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = dbtest19)
    )
  )
"#,
        );

        assert_eq!(
            tns_parts(&entry),
            (
                "LISTENER20".to_string(),
                Some("oracle-rocky-ci.lan.checkmk.net".to_string()),
                Some(1522),
                None,
                Some("DBTEST19".to_string()),
            )
        );
    }

    /// Keys, alias and values are matched case-insensitively; names come back
    /// upper-cased and the host lower-cased.
    #[test]
    fn test_parse_tns_names_ignores_case() {
        let entry = tns_entry(
            "MiXeD = (description = (address = (protocol = tcp)(Host = Oracle-Host.Example.NET)\
             (pOrT = 1521))(connect_data = (service_Name = MyService)))",
        );

        assert_eq!(
            tns_parts(&entry),
            (
                "MIXED".to_string(),
                Some("oracle-host.example.net".to_string()),
                Some(1521),
                None,
                Some("MYSERVICE".to_string()),
            )
        );
    }

    #[test]
    fn test_parse_tns_names_tolerates_padded_values() {
        let entry = tns_entry("PADDED = (ADDRESS = (HOST =  host.example.net )(PORT =  1600 ))");

        assert_eq!(
            entry.host_name.map(|h| h.to_string()).as_deref(),
            Some("host.example.net")
        );
        assert_eq!(entry.port.map(|p| p.value()), Some(1600));
    }

    /// Only the first address and the first target are taken: the rest are
    /// failover targets the plugin does not use.
    #[test]
    fn test_parse_tns_names_takes_only_the_first_address_and_target() {
        let entry = tns_entry(
            "FAILOVER = (DESCRIPTION = (ADDRESS_LIST =
                 (ADDRESS = (PROTOCOL = TCP)(HOST = first.example.net)(PORT = 1521))
                 (ADDRESS = (PROTOCOL = TCP)(HOST = second.example.net)(PORT = 1522)))
               (CONNECT_DATA = (SID = FIRSTSID)(SERVICE_NAME = ignored)))",
        );

        assert_eq!(
            tns_parts(&entry),
            (
                "FAILOVER".to_string(),
                Some("first.example.net".to_string()),
                Some(1521),
                Some("FIRSTSID".to_string()),
                None,
            )
        );
    }

    #[test]
    fn test_parse_tns_names_drops_comments_and_blank_lines() {
        let entries = parse_tns_names_content(
            "# leading comment\n\
             \n\
             # ONLY_A_COMMENT = (HOST = commented.example.net)\n\
             REAL = (ADDRESS = (HOST = real.example.net)(PORT = 1521)) # trailing comment\n",
        );

        assert_eq!(entries.len(), 1, "{entries:?}");
        assert_eq!(entries[0].alias.to_string(), "REAL");
        assert_eq!(
            entries[0]
                .host_name
                .as_ref()
                .map(ToString::to_string)
                .as_deref(),
            Some("real.example.net")
        );
    }

    /// A missing key is reported as absent, not as an error: the file belongs to
    /// the Oracle client and may hold shapes this reader does not read.
    #[test]
    fn test_parse_tns_names_missing_parts_are_none() {
        let entry = tns_entry("BARE = (DESCRIPTION = (CONNECT_DATA = (SERVER = DEDICATED)))");

        assert_eq!(
            tns_parts(&entry),
            ("BARE".to_string(), None, None, None, None)
        );
    }

    #[test]
    fn test_parse_tns_names_non_numeric_port_is_none() {
        let entry =
            tns_entry("BADPORT = (ADDRESS = (HOST = host.example.net)(PORT = not_a_number))");

        assert_eq!(
            entry.host_name.map(|h| h.to_string()).as_deref(),
            Some("host.example.net")
        );
        assert!(entry.port.is_none(), "an unparsable port is absent");
    }

    #[test]
    fn test_parse_tns_names_empty_content_yields_nothing() {
        assert!(parse_tns_names_content("").is_empty());
        assert!(parse_tns_names_content("\n\n   \n").is_empty());
        assert!(parse_tns_names_content("# just a comment\n").is_empty());
    }

    /// An indented `(SID = ...)` must not open an entry: only a name at the
    /// start of a line does.
    #[test]
    fn test_parse_tns_names_nested_keys_do_not_open_an_entry() {
        let entries = parse_tns_names_content(
            "ONLY_ONE =\n  (DESCRIPTION =\n    (CONNECT_DATA =\n      (SID = FREE)))\n",
        );

        assert_eq!(entries.len(), 1, "{entries:?}");
        assert_eq!(entries[0].alias.to_string(), "ONLY_ONE");
        assert_eq!(
            entries[0].sid.as_ref().map(ToString::to_string).as_deref(),
            Some("FREE")
        );
    }

    /// Aliases may carry dots, dashes and underscores; the entry after them must
    /// still be found.
    #[test]
    fn test_parse_tns_names_dotted_and_dashed_alias_names() {
        let entries = parse_tns_names_content(
            "db-one.world = (ADDRESS = (HOST = a.example.net)(PORT = 1521))\n\
             DB_TWO = (ADDRESS = (HOST = b.example.net)(PORT = 1522))\n",
        );

        assert_eq!(
            entries
                .iter()
                .map(|e| e.alias.to_string())
                .collect::<Vec<_>>(),
            vec!["DB-ONE.WORLD", "DB_TWO"]
        );
        assert_eq!(entries[1].port.as_ref().map(|p| p.value()), Some(1522));
    }

    /// Reads from disk, not from `include_str!`: the file path is what the
    /// caller passes. Written to a temp dir so the test does not depend on the
    /// working directory, which differs between cargo and bazel.
    #[test]
    fn test_parse_tns_names_ora_reads_the_file() {
        let file = std::env::temp_dir().join(format!(
            "mk-oracle-test-{}-tnsnames.ora",
            std::process::id()
        ));
        fs::write(&file, TNS_REFERENCE).expect("write the reference file");

        let entries = parse_tns_names_ora(&file);
        let _ = fs::remove_file(&file);

        assert_eq!(
            entries
                .expect("the written file must be readable")
                .iter()
                .map(|e| e.alias.to_string())
                .collect::<Vec<_>>(),
            vec!["ORA_LOCAL", "ORA_REMOTE"]
        );
    }

    #[test]
    fn test_parse_tns_names_ora_reports_an_unreadable_file() {
        assert!(parse_tns_names_ora(Path::new("no/such/tnsnames.ora")).is_err());
    }
}
