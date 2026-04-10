// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use std::path::PathBuf;

use package_validator::package::Package;
use package_validator::report::{IgnoredFiles, Report, SystemDependencies};

fn get_examples_dir() -> PathBuf {
    match runfiles::Runfiles::create() {
        Ok(r) => r
            .rlocation("_main/tests/packaging/package_validator/fixtures")
            .expect("fixtures not found in runfiles"),
        Err(_) => PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fixtures"),
    }
}

fn load_package(package_file: &str) -> Package {
    let package_path = get_examples_dir().join(package_file);
    assert!(
        package_path.exists(),
        "Fixture not found: {}. All package fixtures must be present for integration tests.",
        package_path.display()
    );
    Package::new(package_path).expect("Should extract package")
}

#[test]
fn test_package_integration_report() {
    for package_file in ["test.deb", "test.rpm", "test.cma"] {
        let package = load_package(package_file);

        assert!(
            !package.files().is_empty(),
            "{}: Should extract files from package",
            package_file
        );

        // Create a system dependencies resolver (empty is OK for testing)
        let system_deps = SystemDependencies::default();

        // Generate report
        let report = Report::new(&package, &system_deps, &IgnoredFiles::default())
            .expect("Should generate report");

        // Test JSON output
        let json_str = serde_json::to_string(&report).expect("Should serialize report to JSON");
        let json: serde_json::Value = serde_json::from_str(&json_str).expect("Should parse JSON");

        // Verify expected fields are present and have correct types
        assert!(
            json["package"].is_string(),
            "{}: 'package' field should be a string",
            package_file
        );
        let total_files = json["totals"]["files"]
            .as_u64()
            .expect("totals.files should be a number");
        assert!(
            total_files > 0,
            "{}: Should have at least one file, got {}",
            package_file,
            total_files
        );
    }
}

#[test]
fn test_package_discovers_dependencies() {
    for package_file in ["test.deb", "test.rpm", "test.cma"] {
        let package = load_package(package_file);

        assert!(
            !package.files().is_empty(),
            "{}: Package should have files",
            package_file
        );

        // Create a system dependencies resolver (empty is OK for testing)
        let system_deps = SystemDependencies::default();

        // Generate report and check ELF/dependency info via JSON
        let report = Report::new(&package, &system_deps, &IgnoredFiles::default())
            .expect("Should generate report");
        let json: serde_json::Value =
            serde_json::from_str(&serde_json::to_string(&report).unwrap()).unwrap();

        // Check that we found ELF files (binaries + shared libraries + others)
        let elfs = &json["totals"]["elfs"];
        let total_elfs = elfs["total"]
            .as_u64()
            .expect("totals.elfs.total should be a number");
        assert!(
            total_elfs > 0,
            "{}: Should find at least one ELF file, got {}",
            package_file,
            total_elfs
        );

        let binaries = elfs["binaries"].as_u64().unwrap_or(0);
        let shared_libs = elfs["shared_libraries"].as_u64().unwrap_or(0);
        assert!(
            binaries > 0 || shared_libs > 0,
            "{}: Should have at least one binary ({}) or shared library ({})",
            package_file,
            binaries,
            shared_libs
        );

        // Check that we discovered dependencies
        let deps = &json["totals"]["dependencies"];
        let total_deps = deps["total"]
            .as_u64()
            .expect("totals.dependencies.total should be a number");
        assert!(
            total_deps > 0,
            "{}: Should have discovered dependencies, got {}",
            package_file,
            total_deps
        );

        // Verify dependency counts are consistent
        let found = deps["found"].as_u64().unwrap_or(0);
        let missing = deps["missing"].as_u64().unwrap_or(0);
        let error = deps["error"].as_u64().unwrap_or(0);
        assert_eq!(
            found + missing + error,
            total_deps,
            "{}: Dependency counts should sum to total",
            package_file
        );
    }
}
