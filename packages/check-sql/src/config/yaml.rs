// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{anyhow, Context, Result};
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};
use yaml_rust::YamlLoader;
pub type Yaml = yaml_rust::yaml::Yaml;

pub trait Get {
    fn get(&self, key: &str) -> &Self
    where
        Self: Sized;
    fn get_string(&self, key: &str) -> Option<String>
    where
        Self: Sized;
    fn get_int<T>(&self, key: &str, default: T) -> T
    where
        Self: Sized,
        T: std::convert::TryFrom<i64>;
    fn get_pathbuf(&self, key: &str) -> Option<PathBuf>;
    fn get_string_vector(&self, key: &str, default: &[&str]) -> Result<Vec<String>>;

    fn get_yaml_vector(&self, key: &str) -> Vec<Yaml>;

    /// load a string from using key with default.
    /// If obtained string is not bool-like -> error
    fn get_bool(&self, key: &str, default: bool) -> Result<bool>;
}

impl Get for Yaml {
    fn get(&self, key: &str) -> &Self {
        &self[key]
    }

    fn get_string(&self, key: &str) -> Option<String> {
        self[key].as_str().map(str::to_string)
    }

    fn get_pathbuf(&self, key: &str) -> Option<PathBuf> {
        self[key].as_str().map(PathBuf::from)
    }

    /// always with default
    fn get_int<T>(&self, key: &str, default: T) -> T
    where
        T: std::convert::TryFrom<i64>,
    {
        if let Some(value) = self[key].as_i64() {
            TryInto::try_into(value).unwrap_or(default)
        } else {
            default
        }
    }

    fn get_string_vector(&self, key: &str, default: &[&str]) -> Result<Vec<String>> {
        if self[key].is_badvalue() {
            Ok(default.iter().map(|&a| str::to_string(a)).collect())
        } else {
            self[key]
                .as_vec()
                .unwrap_or(&vec![])
                .iter()
                .map(|v| v.as_str().map(str::to_string).context("Not string"))
                .collect()
        }
    }

    fn get_yaml_vector(&self, key: &str) -> Vec<Yaml> {
        self[key].as_vec().unwrap_or(&vec![]).to_vec()
    }

    fn get_bool(&self, key: &str, default: bool) -> Result<bool> {
        if let Some(v) = self[key].as_str() {
            to_bool(v)
        } else {
            Ok(default)
        }
    }
}

pub fn load_from_file(file_name: &Path) -> Result<Vec<Yaml>> {
    match read_file(file_name) {
        Ok(content) => load_from_str(&content),
        Err(e) => anyhow::bail!(
            "Can't read file: {}, {e} ",
            // Use relatively complicated  method to print name of the file
            // as it is not possible to use "{file_name:?}": produces to many backslashes
            // in Windows. Probability to NOT decode filename as UTF-8 is nil.
            file_name.as_os_str().to_str().unwrap_or("")
        ),
    }
}

fn read_file(file_name: &Path) -> Result<String> {
    let mut file = File::open(file_name)?;
    let mut content = String::new();
    file.read_to_string(&mut content)?;
    Ok(content)
}

fn load_from_str(content: &str) -> Result<Vec<Yaml>> {
    Ok(YamlLoader::load_from_str(content)?)
}

fn to_bool(value: &str) -> Result<bool> {
    match value.to_lowercase().as_ref() {
        "yes" | "true" => Ok(true),
        "no" | "false" => Ok(false),
        _ => Err(anyhow!("Invalid boolean value: {}", value)),
    }
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

    const YAML_VECTOR: &str = r#"
vector:
  - yaml1:
    a: x
  - yaml2:
    a: x
"#;

    #[test]
    fn test_yaml_file() {
        assert!(load_from_file(&TEST_LOG_FILE_META).is_ok());
    }
    #[test]
    fn test_to_bool() {
        assert!(to_bool("yEs").unwrap());
        assert!(!to_bool("nO").unwrap());
        assert!(to_bool("truE").unwrap());
        assert!(!to_bool("faLse").unwrap());
        assert!(to_bool("").is_err());
        assert!(to_bool("1").is_err());
    }
    #[test]
    fn test_yaml_vector() {
        assert!(load_from_str(YAML_VECTOR).unwrap()[0]
            .get_yaml_vector("bad")
            .is_empty());
        assert_eq!(
            load_from_str(YAML_VECTOR).unwrap()[0]
                .get_yaml_vector("vector")
                .len(),
            2
        );
    }
}
