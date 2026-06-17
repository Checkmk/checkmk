// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(not(feature = "build_system_bazel"))]
mod common;

#[cfg(feature = "build_system_bazel")]
extern crate common;

use common::tools;

/// Returns instance names found in the Windows registry, or `None` when no
/// SQL Server installation is detected on this machine (e.g. a clean CI agent).
/// Prints a skip notice to stdout so the reason is visible in test output.
#[cfg(windows)]
fn registry_instances() -> Option<Vec<String>> {
    use mk_sql::platform::registry::get_instances;
    let instances = get_instances(None);
    if instances.is_empty() {
        println!("SKIPPING: no MSSQL instances found in registry — SQL Server not installed");
        return None;
    }
    Some(
        instances
            .into_iter()
            .map(|i| i.name.to_string().to_uppercase())
            .collect(),
    )
}

/// Library-level sanity check: the SCM enumeration returns well-formed names.
#[cfg(windows)]
#[test]
fn test_running_instances_if_installed() {
    use mk_sql::platform::processes::find_running_instances;

    let Some(_registered) = registry_instances() else {
        return;
    };

    let instances = find_running_instances();
    assert!(
        instances.len() >= 2,
        "Expected at least 2 running MSSQL instances, found: {:?}",
        instances
    );

    for name in &instances {
        assert!(!name.is_empty(), "Instance name must not be empty");
        assert_eq!(
            name.as_str(),
            name.to_uppercase(),
            "Instance name must be upper-case, got: {name}"
        );
    }
}

/// Verifies that `get_active_local_instances` returns a set whose size matches
/// the count reported by `find_running_instances` when the flag is enabled.
#[cfg(windows)]
#[test]
fn test_get_active_local_instances_count() {
    use mk_sql::config::ms_sql::Config;
    use mk_sql::ms_sql::instance::get_active_local_instances;
    use mk_sql::platform::processes::find_running_instances;

    let Some(_) = registry_instances() else {
        return;
    };

    let config = Config::from_string(
        r#"
---
mssql:
  main:
    options:
      ignore_inactive_local_instances: true
    authentication:
      username: ""
      type: "integrated"
    connection:
      hostname: "localhost"
"#,
    )
    .unwrap()
    .unwrap();

    let active = get_active_local_instances(&config);
    assert!(
        active.is_some(),
        "Expected Some on Windows localhost with flag enabled"
    );
    let active_count = active.unwrap().len();
    let running_count = find_running_instances().len();
    assert_eq!(
        active_count, running_count,
        "get_active_local_instances returned {active_count} but find_running_instances returned {running_count}"
    );
    assert!(active_count >= 1, "Expected at least 1 active instance");
}

/// Binary-level test for `--active-instances`.
///
/// Guards with a registry check: if SQL Server is not installed on this
/// machine the test returns immediately.  Otherwise verifies that:
///   - the binary exits with code 0
///   - stdout contains at least one line
///   - each output line is a non-empty string (a valid instance name)
#[cfg(windows)]
#[test]
fn test_active_instances_flag() {
    let Some(registered) = registry_instances() else {
        return;
    };

    let output = tools::run_bin().arg("--active-instances").unwrap();
    let (stdout, code) = tools::get_good_results(&output).unwrap();

    assert_eq!(code, 0, "Expected exit code 0, got {code}");

    let lines: Vec<&str> = stdout.lines().collect();
    assert!(
        !lines.is_empty(),
        "Expected at least one instance in stdout, registered={registered:?}"
    );

    for line in &lines {
        assert!(
            !line.is_empty(),
            "Output must not contain empty lines; got stdout:\n{stdout}"
        );
    }
}
