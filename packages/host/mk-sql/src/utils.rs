// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result;
/// Platform independent file and time routines
use std::fs;
use std::fs::File;
use std::io::Read;

use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

pub fn prepare_error(e: &anyhow::Error) -> String {
    let msg = e.to_string();
    format!("ERROR: {}", &msg.replace('\n', " "))
}

pub fn read_file(file_name: &Path) -> Result<String> {
    let mut file = File::open(file_name)?;
    let mut content = String::new();
    file.read_to_string(&mut content)?;
    Ok(content)
}

pub fn touch_dir<P: AsRef<Path>>(path: P) -> Result<PathBuf> {
    fs::File::create(path.as_ref().join(".touch"))?;
    fs::remove_file(path.as_ref().join(".touch"))?;
    Ok(path.as_ref().to_path_buf())
}

fn get_modified_utc_time<P: AsRef<Path>>(path: P) -> Result<u64> {
    Ok(fs::metadata(path)?
        .modified()?
        .duration_since(UNIX_EPOCH)?
        .as_secs())
}

pub fn get_utc_now() -> Result<u64> {
    Ok(std::time::SystemTime::now()
        .duration_since(UNIX_EPOCH)?
        .as_secs())
}

pub fn get_modified_age<P: AsRef<Path>>(path: P) -> Result<u64> {
    let modified = get_modified_utc_time(path)?;
    let now = get_utc_now()?;
    Ok(now.saturating_sub(modified))
}

#[cfg(test)]
mod tests {
    use super::get_modified_utc_time;

    #[test]
    fn test_get_utc_modified_time() {
        let e = get_modified_utc_time(".").unwrap();
        assert!(e > 1700000000);
    }
}
