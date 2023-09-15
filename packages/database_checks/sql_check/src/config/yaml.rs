// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::fs::File;
use std::io::Read;
use std::path::Path;
use yaml_rust::yaml::Yaml;
use yaml_rust::YamlLoader;

pub fn load_from_file(file_name: &Path) -> anyhow::Result<Vec<Yaml>> {
    let content = read_file(file_name)?;
    load_from_str(&content)
}

fn read_file(file_name: &Path) -> anyhow::Result<String> {
    let mut file = File::open(file_name)?;
    let mut content = String::new();
    file.read_to_string(&mut content)?;
    Ok(content)
}

fn load_from_str(content: &str) -> anyhow::Result<Vec<Yaml>> {
    YamlLoader::load_from_str(content).map_err(|e| {
        eprintln!("can't load {}, error {}", content, e);
        anyhow::Error::new(e)
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use lazy_static::lazy_static;
    use std::path::PathBuf;
    lazy_static! {
        static ref TEST_LOG_FILE_META: PathBuf = PathBuf::new()
            .join("tests")
            .join("files")
            .join("test-config.yml");
    }

    #[test]
    fn test_yaml_file() {
        assert!(load_from_file(&TEST_LOG_FILE_META).is_ok());
    }
}
