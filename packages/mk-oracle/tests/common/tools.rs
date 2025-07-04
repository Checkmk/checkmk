// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub const ORA_ENDPOINT_ENV_VAR_LOCAL: &str = "CI_ORA1_DB_TEST";
pub const ORA_ENDPOINT_ENV_VAR_EXT: &str = "CI_ORA2_DB_TEST";

#[cfg(windows)]
pub mod platform {
    use std::path::PathBuf;
    use std::sync::OnceLock;
    pub const RUNTIME_NAME: &str = "oci_light_win_x64.zip";

    #[cfg(windows)]
    static RUNTIME_PATH: OnceLock<PathBuf> = OnceLock::new();
    static PATCHED_PATH: OnceLock<()> = OnceLock::new();
    pub fn add_runtime_to_path() {
        PATCHED_PATH.get_or_init(_patch_path);
    }

    fn _init_runtime_path() -> PathBuf {
        if let Ok(path) = std::env::var("MK_LIBDIR") {
            return PathBuf::from(path);
        }
        let _this_file: PathBuf = PathBuf::from(file!());
        _this_file
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .join("runtimes")
            .join(RUNTIME_NAME)
    }

    fn _patch_path() {
        let cwd = RUNTIME_PATH.get_or_init(_init_runtime_path).clone();
        unsafe {
            std::env::set_var(
                "PATH",
                format!("{cwd:?};") + &std::env::var("PATH").unwrap(),
            );
        }
        std::env::set_current_dir(cwd).unwrap();
        eprintln!("PATH={}", std::env::var("PATH").unwrap());
    }
}

#[cfg(unix)]
pub mod platform {
    pub fn add_runtime_to_path() {
        // nothing to do
    }
}
