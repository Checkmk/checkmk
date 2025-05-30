// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::utils::read_file;
use anyhow::{anyhow, Result};
use std::path::{Path, PathBuf};
use yaml_rust2::YamlLoader;
pub type Yaml = yaml_rust2::yaml::Yaml;

pub mod trace_tools {
    use std::io::{self, Write};
    use yaml_rust2::{Yaml, YamlEmitter};
    #[allow(dead_code)]
    pub fn dump_yaml(yaml: &Yaml) -> String {
        let mut writer = String::new();

        let mut emitter = YamlEmitter::new(&mut writer);
        emitter.dump(yaml).unwrap();
        writer
    }

    #[allow(dead_code)]
    pub fn write_stdout(s: &impl ToString) {
        #[allow(clippy::explicit_write)]
        write!(io::stdout(), "{}", s.to_string()).unwrap();
    }
    #[allow(dead_code)]
    pub fn write_stderr(s: &impl ToString) {
        #[allow(clippy::explicit_write)]
        write!(io::stderr(), "{}", s.to_string()).unwrap();
    }
}

pub trait Get {
    fn get(&self, key: &str) -> &Self
    where
        Self: Sized;
    fn get_string(&self, key: &str) -> Option<String>
    where
        Self: Sized;
    fn get_int<T>(&self, key: &str) -> Option<T>
    where
        Self: Sized,
        T: std::convert::TryFrom<i64>;
    fn get_pathbuf(&self, key: &str) -> Option<PathBuf>;
    fn get_string_vector(&self, key: &str, default: &[&str]) -> Vec<String>;

    fn get_yaml_vector(&self, key: &str) -> Vec<Yaml>;

    fn get_bool(&self, key: &str, default: bool) -> bool {
        self.get_optional_bool(key).unwrap_or(default)
    }

    fn get_optional_bool(&self, key: &str) -> Option<bool>;
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

    fn get_int<T>(&self, key: &str) -> Option<T>
    where
        T: std::convert::TryFrom<i64>,
    {
        if let Some(value) = self[key].as_i64() {
            TryInto::try_into(value).ok()
        } else {
            log::debug!("{key} not found");
            None
        }
    }

    fn get_string_vector(&self, key: &str, default: &[&str]) -> Vec<String> {
        let map_str = |a: &&str| {
            if a.is_empty() {
                log::error!("Empty default value in key {key}");
                None
            } else {
                Some(str::to_string(a))
            }
        };

        let value = &self[key];
        if value.is_badvalue() {
            log::debug!("{key} no vector, using default {default:?}");
            return default.iter().filter_map(map_str).collect();
        }
        if let Some(v) = value.as_vec() {
            v.iter()
                .filter_map(|v| match v.as_str() {
                    Some(v) => map_str(&v),
                    None => {
                        log::error!("Bad value in {key} (expected string)");
                        None
                    }
                })
                .collect()
        } else {
            log::error!("Bad value in {key} {:?} (expected vector)", value);
            vec![]
        }
    }

    fn get_yaml_vector(&self, key: &str) -> Vec<Yaml> {
        self[key].as_vec().unwrap_or(&vec![]).to_vec()
    }

    fn get_optional_bool(&self, key: &str) -> Option<bool> {
        let result = &self[key];
        if result.is_badvalue() {
            return None;
        }

        let ret = result.as_bool();
        if ret.is_some() {
            return ret;
        }

        // for some reason yaml rust doesn't accept yes/no either True/False as bool
        let ret = result.as_str().map(to_bool).transpose().ok().flatten();
        if ret.is_none() {
            log::warn!("{key} is not bool like");
        }
        ret
    }
}

pub fn load_from_file(file_name: &Path) -> Result<Vec<Yaml>> {
    match read_file(file_name) {
        Ok(content) => load_from_str(&content),
        Err(e) => anyhow::bail!(
            "Can't read config file: {}, {e} ",
            // Use relatively complicated  method to print name of the file
            // as it is not possible to use "{file_name:?}": produces to many backslashes
            // in Windows. Probability to NOT decode filename as UTF-8 is nil.
            file_name.as_os_str().to_str().unwrap_or("")
        ),
    }
}

pub(super) fn load_from_str(content: &str) -> Result<Vec<Yaml>> {
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
pub mod test_tools {
    use yaml_rust2::{Yaml, YamlLoader};
    pub fn create_yaml(source: &str) -> Yaml {
        YamlLoader::load_from_str(source).expect("fix test string!")[0].clone()
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    static TEST_LOG_FILE_META: &str = include_str!("../../tests/files/test-config.yml");
    const YAML_VECTOR: &str = r#"
vector:
  - yaml1:
    a: x
  - yaml2:
    a: x
"#;

    #[test]
    fn test_yaml_file() {
        assert!(load_from_str(TEST_LOG_FILE_META).is_ok());
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

    #[test]
    fn test_get_string_vector() {
        let yaml = load_from_str("some: 1").unwrap();
        let z = yaml[0].get_string_vector("bad", &["1", "", "2"]);
        assert_eq!(z, ["1", "2"]);
        let yaml = load_from_str("bad: 1").unwrap();
        let z = yaml[0].get_string_vector("bad", &["1", "", "2"]);
        assert!(z.is_empty());
        let yaml = load_from_str("bad: [a, '3']").unwrap();
        let z = yaml[0].get_string_vector("bad", &["1", "", "2"]);
        assert_eq!(z, ["a", "3"]);
        let yaml = load_from_str(
            r#"
---
  bad:
    - aa
    - bb
"#,
        )
        .unwrap();
        let z = yaml[0].get_string_vector("bad", &["1", "", "2"]);
        assert_eq!(z, ["aa", "bb"]);
    }
}
