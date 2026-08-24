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
use crate::types::LocalInstance;
use anyhow::Result;
use regex::Regex;
use std::collections::HashSet;

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
    let state = if let Some(processes) = known_processes {
        if processes.contains(&local_instance.name.to_string()) {
            "Run"
        } else {
            "Stop"
        }
    } else {
        "N/A"
    };
    format!(
        "{:16} {:5} {:60} {}",
        local_instance.name,
        state,
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

pub fn dump_detected_sids() -> String {
    let oracle_processes = if cfg!(windows) {
        None
    } else {
        Some(
            find_sids_by_processes(None)
                .map_err(|e| {
                    log::info!("Error while detecting Oracle processes: {:?}", e);
                })
                .unwrap_or_default(),
        )
    };

    print_detected_sids(&get_instances(None).unwrap_or_default(), oracle_processes)
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{InstanceName, LocalInstance};
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
}
