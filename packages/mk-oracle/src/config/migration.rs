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

use crate::config::defines::{keys, values};
use anyhow::{bail, Context, Result};
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

/// True for entries the legacy plugin sources: `*.cfg` files that are not hidden.
/// The legacy plugin globs `mk_oracle.d/*.cfg`, and a shell glob never matches
/// names starting with a dot, so hidden files are skipped here as well.
fn is_legacy_config_fragment(path: &Path) -> bool {
    path.extension().is_some_and(|ext| ext == "cfg")
        && path
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| !name.starts_with('.'))
}

/// The legacy config files in the order the legacy plugin sources them: `input`
/// first, then every `*.cfg` file of `mk_oracle_d` (when given) sorted by name,
/// so the result is deterministic regardless of the `read_dir` order.
fn config_files(input: &Path, mk_oracle_d: Option<&Path>) -> Result<Vec<PathBuf>> {
    let mut files = vec![input.to_path_buf()];
    if let Some(dir) = mk_oracle_d {
        let mut cfg_files = Vec::new();
        let entries = std::fs::read_dir(dir)
            .with_context(|| format!("Cannot read the config directory {}", dir.display()))?;
        for entry in entries {
            let path = entry
                .with_context(|| format!("Cannot list the config directory {}", dir.display()))?
                .path();
            if is_legacy_config_fragment(&path) {
                cfg_files.push(path);
            }
        }
        cfg_files.sort();
        files.extend(cfg_files);
    }
    Ok(files)
}

/// The config files as a comma separated list, to name them in error messages.
fn format_paths(files: &[PathBuf]) -> String {
    files
        .iter()
        .map(|p| p.display().to_string())
        .collect::<Vec<_>>()
        .join(", ")
}

/// Concatenate the content of `files`, separated by a newline so that a file not
/// ending with one cannot glue its last line to the next file's first line.
fn merge_config_files(files: &[PathBuf]) -> Result<String> {
    let mut legacy = String::new();
    for (index, path) in files.iter().enumerate() {
        if index > 0 {
            legacy.push('\n');
        }
        legacy.push_str(
            &std::fs::read_to_string(path)
                .with_context(|| format!("Cannot read the legacy config {}", path.display()))?,
        );
    }
    Ok(legacy)
}

/// Read the legacy config from `input`, appending the content of every `*.cfg` file found in
/// `mk_oracle_d` (when given). Files are merged in sorted order so the result is deterministic.
pub fn read_legacy_config(input: &Path, mk_oracle_d: Option<&Path>) -> Result<String> {
    merge_config_files(&config_files(input, mk_oracle_d)?)
}

/// Full migration pipeline: read legacy config, execute it, convert to new format.
///
/// Returns the formatted output string. Caller decides whether to write to file or stdout.
pub fn migrate(input: &Path, mk_oracle_d: Option<&Path>) -> Result<String> {
    // Determine the file list once and reuse it: the textual merge and the variable
    // extraction must see the same set of files.
    let files = config_files(input, mk_oracle_d)?;
    let legacy = merge_config_files(&files)?;
    // Failing here must be reported as is: falling back to no variables at all would
    // hide the culprit behind a misleading "DBUSER not defined" from convert().
    let variables = convert_configs(&files).with_context(|| {
        format!(
            "Cannot execute the legacy config ({})",
            format_paths(&files)
        )
    })?;
    let timestamp = format_timestamp();
    convert(
        &legacy,
        &input.display().to_string(),
        &variables,
        &timestamp,
    )
}

/// Convert legacy Oracle plugin configuration to mk-oracle.yml content.
///
/// Output structure:
/// - Header with timestamp and source path
/// - Original config content as comments
/// - Extracted environment variables as comments
/// - Resulting YAML configuration
// DBUSER fields: USERNAME:PASSWORD:ROLE:HOST:PORT:TNSALIAS
#[derive(Debug)]
struct LegacyDbUser {
    sid: Option<String>, // None for DBUSER, Some(XE) for DBUSER_XE
    username: String,
    password: String,
    role: Option<String>,
    hostname: String,
    port: Option<String>,
    tns_alias: Option<String>,
    piggyback_host: Option<String>,
    /// True when the legacy username was "/", i.e. external/wallet authentication.
    wallet: bool,
}

/// Custom SQL section from legacy config: a function name listed in
/// SQLS_SECTIONS plus the SQLS_* variables set inside that function.
#[derive(Debug, PartialEq)]
struct LegacyCustomSql {
    name: String,
    dir: Option<String>,
    sql_file: String,
    sids: Vec<String>,
    /// True when `sids` comes from a shell expression instead of a literal list
    dynamic_sids: bool,
    tns_alias: Option<String>,
    header_name: Option<String>,
    header_sep: Option<char>,
    /// `SQLS_ITEM_SID`: the SID the legacy plugin puts into the output item.
    /// Not supported by the new plugin, only used to warn about it.
    item_sid: Option<String>,
}

impl LegacyCustomSql {
    /// Full path of the SQL file (SQLS_DIR + SQLS_SQL)
    fn path(&self) -> String {
        match &self.dir {
            Some(dir) => format!("{}/{}", dir.trim_end_matches('/'), self.sql_file),
            None => self.sql_file.clone(),
        }
    }

    /// The SID an aliased section can keep as the `sid:` of its instance entry:
    /// only a single, literal `SQLS_SIDS` value identifies one instance.
    fn reference_sid(&self) -> Option<String> {
        match self.sids.as_slice() {
            [sid] if !self.dynamic_sids => Some(sid.clone()),
            _ => None,
        }
    }
}

fn optional_value(s: &str) -> Option<String> {
    (!s.is_empty()).then(|| s.to_string())
}

// Escaping mirrors yaml_rust2::YamlEmitter (its private escape_str) for a
// double-quoted scalar.
fn yaml_quote(value: &str) -> String {
    let mut out = String::from("\"");
    for c in value.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            '\r' => out.push_str("\\r"),
            '\x08' => out.push_str("\\b"),
            '\x0c' => out.push_str("\\f"),
            c if (c as u32) < 0x20 || c as u32 == 0x7f => {
                out.push_str(&format!("\\u{:04x}", c as u32))
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn parse_sections(variables: &HashMap<String, String>, key: &str) -> HashSet<String> {
    variables
        .get(key)
        .map(|v| {
            v.split_whitespace()
                .filter(|s| !s.is_empty())
                .map(String::from)
                .collect()
        })
        .unwrap_or_default()
}

// TODO(sk): parse whole config and return Vec<LegacyDbUser> instead of just DBUSER
fn parse_asmuser(value: &str) -> Result<LegacyDbUser> {
    parse_dbuser_raw("ASMUSER", value)
}

fn parse_dbuser(name: &str, value: &str) -> Result<LegacyDbUser> {
    if name != "DBUSER" && !name.starts_with("DBUSER_") {
        bail!("invalid variable name: {name}, expected DBUSER or DBUSER_*");
    }
    parse_dbuser_raw(name, value)
}

fn parse_dbuser_raw(name: &str, value: &str) -> Result<LegacyDbUser> {
    let fields: Vec<&str> = value.splitn(6, ':').collect();
    if fields.len() < 2 {
        bail!("DBUSER must have at least username:password, got: {value}");
    }
    let field = |i: usize| fields.get(i).copied().unwrap_or("");
    // Upper-cased like every other SID in the config - `REMOTE_INSTANCE_*`, the
    // `sid:` key and the discovery lists - so entries naming one database in
    // different cases do not end up as two instances.
    let sid = name
        .strip_prefix("DBUSER_")
        .map(|suffix| suffix.to_uppercase());
    let raw_username = field(0);
    // Legacy "/" means external authentication: emit an empty username and flag
    // the entry so the migrated config declares `type: wallet`. We always map to
    // wallet and never to AuthType::Os: OS authentication is not a supported
    // migration target.
    let wallet = raw_username == "/";
    let username = if wallet {
        log::info!("{name}: replacing '/' username with empty string (wallet authentication)");
        String::new()
    } else {
        raw_username.to_string()
    };
    Ok(LegacyDbUser {
        sid,
        username,
        password: field(1).to_string(),
        role: optional_value(field(2)),
        hostname: field(3).to_string(),
        port: optional_value(field(4)),
        tns_alias: optional_value(field(5)),
        piggyback_host: None,
        wallet,
    })
}

/// Parse REMOTE_INSTANCE_XXX='user:pass:role:host:port:piggyback_host:SID:version'
/// Version (last field) is ignored — detected automatically.
/// Returns None with log warning on any invalid entry.
fn parse_remote_instance(name: &str, value: &str) -> Option<LegacyDbUser> {
    if !name.starts_with("REMOTE_INSTANCE_") {
        log::warn!("{name}: expected REMOTE_INSTANCE_* prefix");
        return None;
    }
    let fields: Vec<&str> = value.splitn(9, ':').collect();
    if fields.len() < 5 {
        log::warn!("{name}: need at least user:pass:role:host:port, got: {value}");
        return None;
    }
    let field = |i: usize| fields.get(i).copied().unwrap_or("");
    let username = field(0);
    if username.is_empty() || username == "/" {
        log::warn!("{name}: empty or OS username not supported for remote instances");
        return None;
    }
    let sid = match optional_value(field(6)) {
        Some(s) => s,
        None => {
            log::warn!("{name}: SID (field 7) is empty");
            return None;
        }
    };
    Some(LegacyDbUser {
        sid: Some(sid.to_uppercase()),
        username: username.to_string(),
        password: field(1).to_string(),
        role: optional_value(field(2)),
        hostname: field(3).to_string(),
        port: optional_value(field(4)),
        tns_alias: optional_value(field(8)),
        piggyback_host: optional_value(field(5)),
        // REMOTE_INSTANCE rejects "/" usernames above, so it is never wallet auth.
        wallet: false,
    })
}

/// Parse custom SQL sections from SQLS_SECTIONS and the per-section
/// `SQLS.<section>.<VAR>` entries extracted by the config shell script.
/// Top-level SQLS_DIR/SQLS_SQL act as defaults, as in the legacy plugin.
fn parse_custom_sqls(legacy: &str, variables: &HashMap<String, String>) -> Vec<LegacyCustomSql> {
    let Some(section_names) = variables.get("SQLS_SECTIONS") else {
        return Vec::new();
    };
    let raw_sids = collect_raw_sqls_sids(legacy);

    section_names
        .split(|c: char| c == ',' || c.is_whitespace())
        .filter(|s| !s.is_empty())
        .filter_map(|name| {
            let section_var = |var: &str| variables.get(&format!("SQLS.{name}.{var}"));
            let Some(sql_file) = section_var("SQLS_SQL").or_else(|| variables.get("SQLS_SQL"))
            else {
                log::warn!("{name}: SQLS_SQL not defined, skipping custom SQL section");
                return None;
            };
            Some(LegacyCustomSql {
                // SQLS_ITEM_NAME overrides the name used as [[[<sid>|<name>]]]
                // output item; can only be set within a section
                name: section_var("SQLS_ITEM_NAME")
                    .cloned()
                    .unwrap_or_else(|| name.to_string()),
                dir: section_var("SQLS_DIR")
                    .or_else(|| variables.get("SQLS_DIR"))
                    .cloned(),
                sql_file: sql_file.clone(),
                sids: parse_custom_sql_sids(name, variables),
                dynamic_sids: has_dynamic_sqls_sids(name, &raw_sids),
                // no global fallback: the legacy plugin unsets SQLS_TNSALIAS
                // before each section and never saves a global value
                tns_alias: section_var("SQLS_TNSALIAS").cloned(),
                // no global fallback either (hardcoded to "oracle_sql" in the
                // legacy plugin); the default value means default output
                // section, so only a custom name is kept
                header_name: section_var("SQLS_SECTION_NAME")
                    .filter(|v| v.as_str() != "oracle_sql")
                    .cloned(),
                header_sep: section_var("SQLS_SECTION_SEP")
                    .or_else(|| variables.get("SQLS_SECTION_SEP"))
                    .and_then(|v| parse_header_sep(name, v)),
                // no global fallback: the legacy plugin unsets SQLS_ITEM_SID
                // before each section
                item_sid: section_var("SQLS_ITEM_SID").cloned(),
            })
        })
        .collect()
}

/// Convert a legacy SQLS_SECTION_SEP (an ASCII code, e.g. "124") to the
/// separator character used by the `header_sep:` field.
fn parse_header_sep(section: &str, value: &str) -> Option<char> {
    let sep = value
        .parse::<u8>()
        .ok()
        .map(char::from)
        .filter(|c| (' '..='~').contains(c) && *c != '"' && *c != '\\');
    if sep.is_none() {
        log::warn!("{section}: SQLS_SECTION_SEP '{value}' is not a printable ASCII code, ignoring");
    }
    sep
}

/// Warnings for custom SQL files that need manual review after migration:
/// unreadable files and PL/SQL blocks, which the new plugin cannot execute.
/// The sections are migrated regardless.
fn custom_sql_warnings(custom_sqls: &[LegacyCustomSql]) -> Vec<String> {
    custom_sqls
        .iter()
        .filter_map(|custom| {
            let path = custom.path();
            match std::fs::read_to_string(&path) {
                Err(err) => Some(format!(
                    "{}: cannot read SQL file '{path}': {err}",
                    custom.name
                )),
                Ok(sql) if contains_plsql_block(&sql) => Some(format!(
                    "{}: SQL file '{path}' contains a PL/SQL block, which is not supported",
                    custom.name
                )),
                Ok(_) => None,
            }
        })
        .collect()
}

/// Keywords starting a PL/SQL block or a SQL*Plus command,
/// neither of which the new plugin can execute
const PLSQL_KEYWORDS: [&str; 10] = [
    "begin", "declare", "prompt", "exec", "var", "set", "column", "spool", "execute", "variable",
];

/// Detect a line starting with one of the PLSQL_KEYWORDS
fn contains_plsql_block(sql: &str) -> bool {
    sql.lines()
        .map(str::trim_start)
        .any(|line| PLSQL_KEYWORDS.iter().any(|kw| starts_with_word(line, kw)))
}

fn starts_with_word(line: &str, word: &str) -> bool {
    line.len() >= word.len()
        && line[..word.len()].eq_ignore_ascii_case(word)
        && !line[word.len()..].starts_with(|c: char| c.is_ascii_alphanumeric() || c == '_')
}

/// SIDs a custom SQL section is restricted to, empty means all instances.
///
/// The values come from sourcing the config, so a `SQLS_SIDS` built by a shell
/// expression contributes whatever it expanded to on the migration host. The
/// section value falls back to the global one, as in the legacy plugin
/// (`${SQLS_SIDS:-$custom_sqls_sids}`).
fn parse_custom_sql_sids(section: &str, variables: &HashMap<String, String>) -> Vec<String> {
    variables
        .get(&format!("SQLS.{section}.SQLS_SIDS"))
        .or_else(|| variables.get("SQLS_SIDS"))
        .map(|v| {
            v.split(|c: char| c == ',' || c.is_whitespace())
                .filter(|s| !s.is_empty())
                .map(String::from)
                .collect()
        })
        .unwrap_or_default()
}

/// True when the `SQLS_SIDS` a section uses is assigned from a shell expression
/// (`$...` or a command substitution) instead of a literal list.
///
/// `raw_sids` comes from parsing the config text, the only place where the
/// expression is still visible: after sourcing the config only its expansion
/// is left, and that depends on the migration host and on state the legacy
/// plugin sets up at runtime.
fn has_dynamic_sqls_sids(section: &str, raw_sids: &HashMap<Option<String>, String>) -> bool {
    raw_sids
        .get(&Some(section.to_string()))
        .or_else(|| raw_sids.get(&None))
        .is_some_and(|raw| raw.contains('$') || raw.contains('`'))
}

/// Rewrite the `SQLS_SIDS` entries that name a `REMOTE_INSTANCE_*` variable
/// instead of an Oracle SID.
///
/// A section that keeps no SID at all is dropped instead of migrated: an empty
/// SID list means "run everywhere" and would widen its scope silently. A section
/// with a `SQLS_TNSALIAS` is exempt, the alias already pins it to one instance.
///
/// Returns the warnings for the dropped references and sections.
fn resolve_remote_instance_sids(
    custom_sqls: &mut Vec<LegacyCustomSql>,
    variables: &HashMap<String, String>,
) -> Vec<String> {
    let mut warnings = Vec::new();
    custom_sqls.retain_mut(|custom| {
        let resolved: Vec<String> = custom
            .sids
            .iter()
            .filter_map(|sid| match resolve_remote_instance_sid(sid, variables) {
                Ok(sid) => Some(sid),
                Err(reason) => {
                    warnings.push(format!("{}: {reason}", custom.name));
                    None
                }
            })
            .collect();
        if custom.tns_alias.is_none() && !custom.sids.is_empty() && resolved.is_empty() {
            warnings.push(format!(
                "{}: no instance left to run on, skipping custom SQL section",
                custom.name
            ));
            return false;
        }
        custom.sids = resolved;
        true
    });
    warnings
}

/// Map a single `SQLS_SIDS` entry to the SID of the migrated instance.
/// Entries that are not a `REMOTE_INSTANCE_*` reference pass through unchanged.
fn resolve_remote_instance_sid(
    sid: &str,
    variables: &HashMap<String, String>,
) -> Result<String, String> {
    if !sid.starts_with("REMOTE_INSTANCE_") {
        return Ok(sid.to_string());
    }
    let Some(value) = variables.get(sid) else {
        return Err(format!(
            "SQLS_SIDS references '{sid}', but no such remote instance is defined, ignoring it"
        ));
    };
    parse_remote_instance(sid, value)
        .and_then(|remote| remote.sid)
        .ok_or_else(|| {
            format!("SQLS_SIDS references '{sid}', whose definition is invalid, ignoring it")
        })
}

/// Warn about the custom SQL sections whose `SQLS_SIDS` is built by a shell
/// expression: the migration can only keep the SIDs the expression expanded to
/// while the config was sourced, which is not necessarily the set the legacy
/// plugin selects at runtime.
///
/// A section whose expression expanded to nothing is dropped instead of
/// migrated: an empty SID list means "run on all instances" in the migrated
/// config, so it would silently widen the scope of the section.
///
/// Returns the warnings for the kept and the dropped sections.
fn warn_dynamic_sqls_sids(custom_sqls: &mut Vec<LegacyCustomSql>) -> Vec<String> {
    let mut warnings = Vec::new();
    custom_sqls.retain(|custom| {
        // the alias already pins the section to one instance, its SQLS_SIDS
        // never reach the migrated config
        if !custom.dynamic_sids || custom.tns_alias.is_some() {
            return true;
        }
        if custom.sids.is_empty() {
            warnings.push(format!(
                "{}: SQLS_SIDS is built by a shell expression that expanded to no SID, \
                 skipping custom SQL section; assign the intended instances manually",
                custom.name
            ));
            return false;
        }
        warnings.push(format!(
            "{}: SQLS_SIDS is built by a shell expression, which cannot be migrated reliably; \
             using the SIDs it expanded to: {}",
            custom.name,
            custom.sids.join(", ")
        ));
        true
    });
    warnings
}

/// Warn about the custom SQL sections that set `SQLS_SIDS` and `SQLS_TNSALIAS`
/// together.
///
/// The two restrict different things in the legacy plugin — the SID the section
/// runs on and the connect identifier it uses — while the migrated config
/// resolves an instance by its alias as soon as one is set. The SID is
/// therefore kept as the `sid:` of the aliased entry wherever
/// `custom_sql_alias_instances` can place it, but it never restricts the
/// section any more, so both outcomes are reported.
fn warn_custom_sql_alias_sids(
    custom_sqls: &[LegacyCustomSql],
    known_aliases: &[String],
) -> Vec<String> {
    let instances = custom_sql_alias_instances(custom_sqls, known_aliases);
    custom_sqls
        .iter()
        .filter(|c| !c.sids.is_empty())
        .filter_map(|custom| {
            let alias = custom.tns_alias.as_ref()?;
            let kept = custom.reference_sid().is_some_and(|sid| {
                instances
                    .iter()
                    .any(|(known, known_sid)| known == alias && known_sid.as_ref() == Some(&sid))
            });
            Some(if kept {
                format!(
                    "{}: SQLS_SIDS '{}' is migrated next to SQLS_TNSALIAS '{alias}', but the \
                     instance is resolved by its alias, so the SID no longer restricts the section",
                    custom.name,
                    custom.sids.join(", ")
                )
            } else {
                format!(
                    "{}: SQLS_SIDS '{}' cannot be kept next to SQLS_TNSALIAS '{alias}', the \
                     instance is resolved by its alias alone; verify that the alias connects to \
                     the intended database",
                    custom.name,
                    custom.sids.join(", ")
                )
            })
        })
        .collect()
}

/// Warn about the custom SQL sections that set `SQLS_ITEM_SID`.
fn warn_custom_sql_item_sid(custom_sqls: &[LegacyCustomSql]) -> Vec<String> {
    custom_sqls
        .iter()
        .filter(|custom| custom.header_name.is_none())
        .filter_map(|custom| {
            let item_sid = custom.item_sid.as_ref()?;
            // the item is unchanged when the section already runs on exactly
            // that instance
            if custom.tns_alias.is_none() && custom.reference_sid().as_ref() == Some(item_sid) {
                return None;
            }
            Some(format!(
                "{}: SQLS_ITEM_SID '{item_sid}' is not supported and is not migrated; the item of \
                 the oracle_sql section is built from the name of the instance the section runs \
                 on, so the name of the service changes and it is rediscovered",
                custom.name
            ))
        })
        .collect()
}

/// Collect raw `SQLS_SIDS=` assignments from the legacy config text, keyed by
/// the enclosing function name (None = top level).
fn collect_raw_sqls_sids(legacy: &str) -> HashMap<Option<String>, String> {
    let mut assignments = HashMap::new();
    let mut current_fn: Option<String> = None;
    for line in legacy.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('#') {
            // Commented line: neither a function scope nor an assignment.
            continue;
        }
        if let Some(value) = trimmed.strip_prefix("SQLS_SIDS=") {
            assignments.insert(current_fn.clone(), value.to_string());
        } else if current_fn.is_some() && trimmed.starts_with('}') {
            current_fn = None;
        } else if let Some(name) = parse_custom_sqls_function_def(trimmed) {
            current_fn = Some(name);
        }
    }
    assignments
}

fn parse_custom_sqls_function_def(line: &str) -> Option<String> {
    let (name, _) = line.split_once("()")?;
    let name = name.trim();
    (!name.is_empty() && name.chars().all(|c| c.is_ascii_alphanumeric() || c == '_'))
        .then(|| name.to_string())
}

pub fn convert(
    legacy: &str,
    source_path: &str,
    variables: &HashMap<String, String>,
    timestamp: &str,
) -> Result<String> {
    let dbuser_raw = variables
        .get("DBUSER")
        .ok_or_else(|| anyhow::anyhow!("DBUSER not defined in legacy config, cannot generate"))?;
    let dbuser = parse_dbuser("DBUSER", dbuser_raw)?;

    let mut dbuser_extras: Vec<LegacyDbUser> = Vec::new();
    let mut invalid_remotes: Vec<(&str, &str)> = Vec::new();
    for (name, value) in variables {
        if name.starts_with("DBUSER_") {
            dbuser_extras.push(parse_dbuser(name, value)?);
        } else if !cfg!(windows) && name.starts_with("REMOTE_INSTANCE_") {
            // Windows legacy plugin doesn't support REMOTE_INSTANCE
            match parse_remote_instance(name, value) {
                Some(ri) => dbuser_extras.push(ri),
                None => invalid_remotes.push((name, value)),
            }
        }
    }

    let mut out = String::new();

    out.push_str(&format!(
        "# --- Converted from {source_path} at {timestamp} ---\n"
    ));

    out.push_str("# --- Known environment variables defined in legacy config ---\n");
    for (name, value) in variables {
        if name == "DBUSER"
            || name == "ASMUSER"
            || name.starts_with("DBUSER_")
            || name.starts_with("REMOTE_INSTANCE_")
            || name.ends_with("SQLS_DBPASSWORD")
        {
            out.push_str(&format!("# {name} ***\n"));
        } else {
            out.push_str(&format!("# {name} {value}\n"));
        }
    }

    for (name, value) in &invalid_remotes {
        out.push_str(&format!("# INVALID {name}\n# {name} {value}\n"));
    }

    // Windows legacy plugin doesn't support custom SQL sections
    let mut custom_sqls = if cfg!(windows) {
        Vec::new()
    } else {
        parse_custom_sqls(legacy, variables)
    };

    let mut warnings = resolve_remote_instance_sids(&mut custom_sqls, variables);
    warnings.extend(warn_dynamic_sqls_sids(&mut custom_sqls));
    warnings.extend(warn_custom_sql_alias_sids(
        &custom_sqls,
        &known_aliases(&dbuser, &dbuser_extras),
    ));
    warnings.extend(warn_custom_sql_item_sid(&custom_sqls));
    warnings.extend(custom_sql_warnings(&custom_sqls));
    for warning in warnings {
        let warning = format!("# WARNING: {warning}\n");
        print!("{warning}");
        out.push_str(&warning);
    }

    out.push_str("# --- Unified Config ---\n---\noracle:\n  main:\n");

    // connection
    let host = if dbuser.hostname.is_empty() {
        "localhost"
    } else {
        &dbuser.hostname
    };
    out.push_str(&format!("    connection:\n      hostname: {host}\n"));
    if let Some(port) = &dbuser.port {
        out.push_str(&format!("      port: {port}\n"));
    }
    if let Some(tns_admin) = variables.get("TNS_ADMIN") {
        out.push_str(&format!("      tns_admin: {tns_admin}\n"));
    }
    if let Some(olrloc) = variables.get("OLRLOC") {
        out.push_str(&format!("      oracle_local_registry: {olrloc}\n"));
    }

    // authentication
    let auth_type = if dbuser.wallet {
        values::WALLET
    } else {
        values::STANDARD
    };
    out.push_str(&format!(
        "    authentication:\n      username: {}\n      password: {}\n      type: {auth_type}\n",
        yaml_quote(&dbuser.username),
        yaml_quote(&dbuser.password)
    ));
    if let Some(role) = &dbuser.role {
        out.push_str(&format!("      role: {}\n", role.to_lowercase()));
    }
    if let Some(asm_raw) = variables.get("ASMUSER") {
        if let Ok(asm) = parse_asmuser(asm_raw) {
            if !asm.username.is_empty() {
                out.push_str(&format!(
                    "      asm_username: {}\n",
                    yaml_quote(&asm.username)
                ));
            }
            if !asm.password.is_empty() {
                out.push_str(&format!(
                    "      asm_password: {}\n",
                    yaml_quote(&asm.password)
                ));
            }
            // Like DBUSER, a "/" ASMUSER is external auth. The username is erased
            // to empty, so declare `asm_type: wallet` explicitly; without it the
            // parser would fall back to the main auth type. OS auth is not a
            // supported migration target.
            if asm.wallet {
                out.push_str(&format!("      asm_type: {}\n", values::WALLET));
            }
            if let Some(role) = &asm.role {
                out.push_str(&format!("      asm_role: {}\n", role.to_lowercase()));
            }
        }
    }

    let sync_normal = parse_sections(variables, "SYNC_SECTIONS");
    let async_normal = parse_sections(variables, "ASYNC_SECTIONS");
    let sync_asm = parse_sections(variables, "SYNC_ASM_SECTIONS");
    let async_asm = parse_sections(variables, "ASYNC_ASM_SECTIONS");

    fn as_str(s: &HashSet<String>) -> HashSet<&str> {
        s.iter().map(|s| s.as_str()).collect()
    }
    let sync_n = as_str(&sync_normal);
    let async_n = as_str(&async_normal);
    let sync_a = as_str(&sync_asm);
    let async_a = as_str(&async_asm);

    let normals: HashSet<&str> = sync_n.union(&async_n).copied().collect();
    let asms: HashSet<&str> = sync_a.union(&async_a).copied().collect();
    let asyncs: HashSet<&str> = async_n.union(&async_a).copied().collect();
    let all: HashSet<&str> = normals.union(&asms).copied().collect();

    let cache_maxage = variables
        .get("CACHE_MAXAGE")
        .and_then(|v| v.parse::<u32>().ok());

    let sqls_max_cache_age = variables
        .get("SQLS_MAX_CACHE_AGE")
        .and_then(|v| v.parse::<u32>().ok());

    let max_tasks = variables
        .get("MAX_TASKS")
        .and_then(|v| v.parse::<u32>().ok());

    let excluded_sections = find_excluded_sections(variables);
    let only_sids = parse_sid_list(variables, "ONLY_SIDS");
    let skip_sids = parse_sid_list(variables, "SKIP_SIDS");

    out.extend(format_options(max_tasks));
    out.extend(format_instances(&dbuser, &dbuser_extras, &custom_sqls));
    out.extend(format_excluded_sections(&excluded_sections));
    out.extend(format_sections(&all, &asyncs, &normals, &asms));
    out.extend(format_custom_metrics(&custom_sqls));
    out.extend(format_cache_age(cache_maxage));
    out.extend(format_custom_metrics_cache_age(sqls_max_cache_age));
    out.extend(format_discovery(&only_sids, &skip_sids));

    Ok(out)
}

fn format_options(max_tasks: Option<u32>) -> Vec<String> {
    let threads = max_tasks.and_then(|v| (v >= 2).then(|| v.min(8)));

    if threads.is_none() {
        return Vec::new();
    }

    let mut lines = vec!["    options:\n".to_string()];
    if let Some(v) = threads {
        lines.push(format!("      threads: {v}\n"));
    }
    lines
}

/// TNS aliases that already have an instance entry of their own
fn known_aliases(dbuser: &LegacyDbUser, dbuser_extras: &[LegacyDbUser]) -> Vec<String> {
    std::iter::once(dbuser)
        .chain(dbuser_extras.iter())
        .filter_map(|entry| entry.tns_alias.clone())
        .collect()
}

fn format_instances(
    dbuser: &LegacyDbUser,
    dbuser_extras: &[LegacyDbUser],
    custom_sqls: &[LegacyCustomSql],
) -> Vec<String> {
    // Accumulate instance entries first; the `instances:` header is prepended
    // only when at least one entry exists, so a bare DBUSER yields no block.
    let mut lines: Vec<String> = Vec::new();
    let mut known_sids: Vec<String> = Vec::new();
    let known_aliases = known_aliases(dbuser, dbuser_extras);
    let all_dbusers = std::iter::once(dbuser).chain(dbuser_extras.iter());
    for entry in all_dbusers {
        let sid = &entry.sid;
        // Wallet auth connects via `/@<alias>`: the SEPS credential is keyed by
        // the alias, not by host/port. The legacy plugin uses the explicit
        // TNSALIAS and falls back to the SID as the alias
        // (`${CFGTNSALIAS:-${ORACLE_SID}}`); we reproduce that mapping so the
        // runtime resolves the instance through its alias. tnsping verification
        // of the alias is not migrated yet (may be added later). The SID-as-alias
        // fallback is a stopgap and will be revisited once ORACLE_HOME detection
        // is finally solved (enabling a proper local connection).
        let alias = entry.tns_alias.clone().or_else(|| {
            let sid = entry.sid.clone().filter(|_| entry.wallet)?;
            log::info!(
                "wallet authentication without TNSALIAS: assuming SID '{sid}' as the TNS alias"
            );
            Some(sid)
        });
        if sid.is_none() && alias.is_none() {
            log::info!("DBUSER has neither SID nor TNS alias, skipping instance entry");
            continue;
        }

        let sid_written = if let Some(sid) = &sid {
            known_sids.push(sid.clone());
            lines.push(format!("      - sid: {sid}\n"));
            true
        } else {
            false
        };
        if let Some(alias) = &alias {
            lines.push(format!(
                "      {} alias: {}\n",
                if sid_written { ' ' } else { '-' },
                alias
            ));
        };
        // The main DBUSER (sid == None) inherits connection and authentication
        // from `main:`; emitting them again here would duplicate the credentials
        // and pair a self-resolving TNS alias with an explicit host/port. Only
        // SID-bearing entries (DBUSER_*, REMOTE_INSTANCE_*) may override them.
        let has_connection =
            entry.sid.is_some() && (!entry.hostname.is_empty() || entry.port.is_some());
        if has_connection {
            lines.push("        connection:\n".to_string());
            let hostname = if entry.hostname.is_empty() {
                "localhost"
            } else {
                &entry.hostname
            };
            lines.push(format!("          hostname: {hostname}\n"));
            if let Some(port) = &entry.port {
                lines.push(format!("          port: {port}\n"));
            }
        }
        if let Some(piggyback) = &entry.piggyback_host {
            lines.push(format!("        piggyback_host: {piggyback}\n"));
        }
        // Only SID-bearing entries emit their own auth block; the main entry
        // (sid == None) inherits it from `main:`. Wallet entries emit despite
        // empty username/password, but stay behind the same SID guard.
        let has_auth = entry.sid.is_some()
            && (!entry.username.is_empty() || !entry.password.is_empty() || entry.wallet);
        if has_auth {
            let auth_type = if entry.wallet {
                values::WALLET
            } else {
                values::STANDARD
            };
            lines.push(format!(
                    "        authentication:\n          username: {}\n          password: {}\n          type: {auth_type}\n",
                    yaml_quote(&entry.username),
                    yaml_quote(&entry.password)
                ));
            if let Some(role) = &entry.role {
                lines.push(format!("          role: {}\n", role.to_lowercase()));
            }
        }
        lines.extend(instance_custom_metrics(
            custom_sqls,
            entry.sid.as_deref(),
            entry.tns_alias.as_deref(),
        ));
    }
    // SIDs and aliases only referenced by SQLS_SIDS/SQLS_TNSALIAS need an
    // own entry to carry the metrics
    for sid in custom_sql_only_sids(custom_sqls, &known_sids) {
        lines.push(format!("      - sid: {sid}\n"));
        lines.extend(instance_custom_metrics(custom_sqls, Some(&sid), None));
    }
    for (alias, sid) in custom_sql_alias_instances(custom_sqls, &known_aliases) {
        match sid {
            Some(sid) => {
                lines.push(format!("      - sid: {sid}\n"));
                lines.push(format!("        alias: {alias}\n"));
            }
            None => lines.push(format!("      - alias: {alias}\n")),
        }
        lines.extend(instance_custom_metrics(custom_sqls, None, Some(&alias)));
    }
    if lines.is_empty() {
        return Vec::new();
    }
    let mut out = vec!["    instances:\n".to_string()];
    out.extend(lines);
    out
}

fn instance_custom_metrics(
    custom_sqls: &[LegacyCustomSql],
    sid: Option<&str>,
    alias: Option<&str>,
) -> Vec<String> {
    let metrics: Vec<&LegacyCustomSql> = custom_sqls
        .iter()
        .filter(|c| match &c.tns_alias {
            // a TNS alias overrides the connect string in the legacy plugin,
            // so the metric belongs to exactly one instance: the aliased one
            Some(tns_alias) => alias == Some(tns_alias.as_str()),
            None => sid.is_some_and(|sid| c.sids.iter().any(|s| s == sid)),
        })
        .collect();
    format_custom_metric_entries(&metrics, "        ")
}

/// SIDs referenced by `SQLS_SIDS` without a matching instance entry; a section
/// with a TNS alias contributes its alias instead (see
/// `custom_sql_alias_instances`)
fn custom_sql_only_sids(custom_sqls: &[LegacyCustomSql], known_sids: &[String]) -> Vec<String> {
    let mut seen = HashSet::new();
    custom_sqls
        .iter()
        .filter(|c| c.tns_alias.is_none())
        .flat_map(|c| &c.sids)
        .filter(|sid| !known_sids.contains(sid))
        .filter(|sid| seen.insert(sid.as_str()))
        .cloned()
        .collect()
}

/// TNS aliases referenced by `SQLS_TNSALIAS` without a matching instance entry,
/// paired with the SID the aliased sections are restricted to.
///
/// The alias identifies the instance — that is what the plugin connects
/// through — so the SID of `SQLS_SIDS` can only be carried along as the `sid:`
/// of the same entry. That works as long as the sections sharing the alias
/// agree on exactly one SID; otherwise the entry keeps the alias alone and
/// `warn_custom_sql_alias_sids` reports the loss.
fn custom_sql_alias_instances(
    custom_sqls: &[LegacyCustomSql],
    known_aliases: &[String],
) -> Vec<(String, Option<String>)> {
    let mut instances: Vec<(String, Option<String>)> = Vec::new();
    for custom in custom_sqls {
        let Some(alias) = custom.tns_alias.clone() else {
            continue;
        };
        if known_aliases.contains(&alias) {
            continue;
        }
        let sid = custom.reference_sid();
        match instances.iter_mut().find(|(known, _)| *known == alias) {
            // sections sharing the alias but not the SID leave it undecided
            Some(instance) if instance.1 != sid => instance.1 = None,
            Some(_) => (),
            None => instances.push((alias, sid)),
        }
    }
    instances
}

fn format_sections(
    all_sections: &HashSet<&str>,
    all_async: &HashSet<&str>,
    all_normal: &HashSet<&str>,
    all_asm: &HashSet<&str>,
) -> Vec<String> {
    if all_sections.is_empty() {
        return Vec::new();
    }
    let mut sorted: Vec<&str> = all_sections.iter().copied().collect();
    sorted.sort();
    let mut lines = vec!["    sections:\n".to_string()];
    for name in sorted {
        let is_async = all_async.contains(name);
        let affinity = if all_normal.contains(name) && all_asm.contains(name) {
            Some("all")
        } else if all_asm.contains(name) {
            Some("asm")
        } else {
            None
        };
        lines.push(format!("      - {name}:\n"));
        lines.push(format!("          is_async: {is_async}\n"));
        if let Some(aff) = affinity {
            lines.push(format!("          affinity: \"{aff}\"\n"));
        }
    }
    lines
}

fn format_excluded_sections(excluded_sections: &HashMap<String, Vec<String>>) -> Vec<String> {
    if excluded_sections.is_empty() {
        return Vec::new();
    }
    let mut lines = vec![format!("    {}:\n", keys::EXCLUDED_SECTIONS)];
    // Sort by SID: `HashMap` iteration order is unspecified, but the generated
    // config must be stable across runs.
    let mut sids: Vec<&String> = excluded_sections.keys().collect();
    sids.sort();
    for sid in sids {
        lines.push(format!("      - {}:\n", keys::TARGET_ID));
        lines.push(format!("          sid: {sid}\n"));
        lines.push(format!(
            "        sections: [{}]\n",
            format_yaml_list(&excluded_sections[sid])
        ));
    }
    lines
}

/// Sections without a SID or TNS alias restriction apply to all instances → global level
fn format_custom_metrics(custom_sqls: &[LegacyCustomSql]) -> Vec<String> {
    let global: Vec<&LegacyCustomSql> = custom_sqls
        .iter()
        .filter(|c| c.sids.is_empty() && c.tns_alias.is_none())
        .collect();
    format_custom_metric_entries(&global, "    ")
}

fn format_custom_metric_entries(metrics: &[&LegacyCustomSql], indent: &str) -> Vec<String> {
    if metrics.is_empty() {
        return Vec::new();
    }
    let mut lines = vec![format!("{indent}custom_metrics:\n")];
    for custom in metrics {
        lines.push(format!("{indent}  - {}:\n", custom.name));
        lines.push(format!("{indent}      path: {}\n", custom.path()));
        if let Some(header_name) = &custom.header_name {
            lines.push(format!("{indent}      header_name: {header_name}\n"));
            // the legacy plugin uses the separator only together with a custom section name
            if let Some(sep) = custom.header_sep {
                lines.push(format!("{indent}      header_sep: \"{sep}\"\n"));
            }
        }
    }
    lines
}

fn format_cache_age(cache_maxage: Option<u32>) -> Vec<String> {
    let Some(age) = cache_maxage else {
        return Vec::new();
    };
    vec![format!("    cache_age: {age}\n")]
}

fn format_custom_metrics_cache_age(sqls_max_cache_age: Option<u32>) -> Vec<String> {
    let Some(age) = sqls_max_cache_age else {
        return Vec::new();
    };
    vec![format!("    custom_metrics_cache_age: {age}\n")]
}

/// Sections excluded per SID, as declared by the legacy `EXCLUDE_<SID>='<section> ...'`
/// variables: the key is the SID, the value that variable's section list.
///
/// The legacy plugin removes those sections only while processing that one SID;
/// every other discovered instance keeps running the globally configured
/// sections.
///
/// A variable with an empty SID or an empty section list is dropped, matching
/// the legacy plugin, which treats both as no exclusion at all. `EXCLUDE_<SID>=ALL`
/// is dropped too: it names no section but the whole instance, which is not
/// supported yet.
fn find_excluded_sections(variables: &HashMap<String, String>) -> HashMap<String, Vec<String>> {
    variables
        .iter()
        .filter_map(|(name, value)| {
            let sid = name
                .strip_prefix("EXCLUDE_")
                .filter(|sid| !sid.is_empty())?;
            let sections: Vec<String> = value.split_whitespace().map(String::from).collect();
            (!sections.is_empty() && sections != ["ALL"]).then(|| (sid.to_string(), sections))
        })
        .collect()
}

fn parse_sid_list(variables: &HashMap<String, String>, key: &str) -> Vec<String> {
    variables
        .get(key)
        .map(|v| v.split_whitespace().map(String::from).collect())
        .unwrap_or_default()
}

fn format_discovery(only_sids: &[String], skip_sids: &[String]) -> Vec<String> {
    if only_sids.is_empty() && skip_sids.is_empty() {
        return Vec::new();
    }
    let mut lines = vec![
        "    discovery:\n".to_string(),
        "      detect: true\n".to_string(),
    ];
    if !only_sids.is_empty() {
        lines.push(format!(
            "      include: [{}]\n",
            format_yaml_list(only_sids)
        ));
    }
    if !skip_sids.is_empty() {
        lines.push(format!(
            "      exclude: [{}]\n",
            format_yaml_list(skip_sids)
        ));
    }
    lines
}

fn format_yaml_list(items: &[String]) -> String {
    items
        .iter()
        .map(|s| s.as_str())
        .collect::<Vec<_>>()
        .join(", ")
}

fn format_timestamp() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let (year, month, day) = civil_from_days((secs / 86400) as i64);
    let t = (secs % 86400) as u32;
    format!(
        "{year:04}-{month:02}-{day:02} {:02}:{:02}:{:02} UTC",
        t / 3600,
        (t % 3600) / 60,
        t % 60
    )
}

/// Convert days since Unix epoch to (year, month, day).
fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let z = days + 719468;
    let era = (if z >= 0 { z } else { z - 146096 }) / 146097;
    let doe = (z - era * 146097) as u32;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y, m, d)
}

/// Variables to extract from legacy config files.
const KNOWN_VARIABLES: &[&str] = &[
    "DBUSER",
    "ASMUSER",
    "SYNC_SECTIONS",
    "ASYNC_SECTIONS",
    "SYNC_ASM_SECTIONS",
    "ASYNC_ASM_SECTIONS",
    "CACHE_MAXAGE",
    "REMOTE_ORACLE_HOME",
    "ONLY_SIDS",
    "SKIP_SIDS",
    "ORACLE_HOME",
    "TNS_ADMIN",
    "OLRLOC",
    "MAX_TASKS",
    "ID_BY",
    "SQLS_SECTIONS",
    "SQLS_DBUSER",
    "SQLS_DBPASSWORD",
    "SQLS_DBSYSCONNECT",
    "SQLS_TNSALIAS",
    "SQLS_SIDS",
    "SQLS_DIR",
    "SQLS_SQL",
    "SQLS_PARAMETERS",
    "SQLS_SECTION_NAME",
    "SQLS_SECTION_SEP",
    "SQLS_MAX_CACHE_AGE",
];

/// Variable name prefixes for dynamic matching (e.g. REMOTE_INSTANCE_XE).
const KNOWN_PREFIXES: &[&str] = &["DBUSER_", "REMOTE_INSTANCE_", "EXCLUDE_"];

/// Variables set inside custom SQL section functions.
#[cfg(unix)]
const CUSTOM_SQL_SECTION_VARIABLES: &[&str] = &[
    "SQLS_SECTION_NAME",
    "SQLS_SECTION_SEP",
    "SQLS_SIDS",
    "SQLS_DIR",
    "SQLS_SQL",
    "SQLS_PARAMETERS",
    "SQLS_ITEM_NAME",
    "SQLS_ITEM_SID",
    "SQLS_DBUSER",
    "SQLS_DBPASSWORD",
    "SQLS_DBSYSCONNECT",
    "SQLS_TNSALIAS",
];

/// Execute the legacy config files in their native shell and return extracted variables.
///
/// Sources them in the given order in the platform's shell (bash on Linux, ksh
/// on AIX, powershell on Windows) — one shell for all of them, as the legacy
/// plugin does for `mk_oracle.cfg` plus `mk_oracle.d` — and captures known
/// variable values.
///
/// Returns pairs of (name, value) for variables with non-empty values.
pub fn convert_configs(config_paths: &[PathBuf]) -> Result<HashMap<String, String>> {
    let output = run_config_shell(config_paths)?;
    parse_variable_output(&output)
}

#[cfg(target_os = "windows")]
fn run_config_shell(config_paths: &[PathBuf]) -> Result<String> {
    run_shell(
        "powershell",
        &["-NoProfile", "-NonInteractive", "-Command"],
        &build_powershell_script(config_paths),
    )
}

#[cfg(target_os = "aix")]
fn run_config_shell(config_paths: &[PathBuf]) -> Result<String> {
    run_shell("ksh", &["-c"], &build_posix_script(config_paths))
}

#[cfg(not(any(target_os = "windows", target_os = "aix")))]
fn run_config_shell(config_paths: &[PathBuf]) -> Result<String> {
    run_shell("bash", &["-c"], &build_posix_script(config_paths))
}

fn run_shell(shell: &str, args: &[&str], script: &str) -> Result<String> {
    let output = std::process::Command::new(shell)
        .args(args)
        .arg(script)
        .output()
        .with_context(|| format!("Cannot run {shell}"))?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    let stderr = stderr.trim_end();
    if !output.status.success() {
        anyhow::bail!("Config execution failed ({}): {stderr}", output.status);
    }
    // A config file that cannot be sourced (missing, syntax error, ...) does not fail
    // the script — the shell only complains about it on stderr, naming the file. Pass
    // that on instead of silently migrating from a partial set of variables.
    if !stderr.is_empty() {
        eprintln!("WARNING: {shell} reported while reading the legacy config:\n{stderr}");
    }
    Ok(String::from_utf8(output.stdout)?)
}

#[cfg(unix)]
fn build_posix_script(config_paths: &[PathBuf]) -> String {
    let source_configs = config_paths
        .iter()
        .map(|p| format!(". {}", posix_quote(&p.display().to_string())))
        .collect::<Vec<_>>()
        .join("\n");
    let vars = KNOWN_VARIABLES.join(" ");
    let prefixes = KNOWN_PREFIXES
        .iter()
        .map(|p| format!("{p}*"))
        .collect::<Vec<_>>()
        .join("|");
    let section_vars = CUSTOM_SQL_SECTION_VARIABLES.join(" ");
    format!(
        r#"{source_configs}
for __n in {vars}; do
  eval "__v=\$$__n"
  [ -n "$__v" ] && printf '%s %s\n' "$__n" "$__v"
done
set 2>/dev/null | while IFS='=' read -r __n __rest; do
  case "$__n" in {prefixes}) eval "__v=\$$__n"; [ -n "$__v" ] && printf '%s %s\n' "$__n" "$__v";; esac
done
for __sec in $(echo "$SQLS_SECTIONS" | tr ',' ' '); do
  type "$__sec" >/dev/null 2>&1 || continue
  unset {section_vars}
  "$__sec" >/dev/null 2>&1
  for __n in {section_vars}; do
    eval "__v=\$$__n"
    [ -n "$__v" ] && printf '%s %s\n' "SQLS.$__sec.$__n" "$__v"
  done
done
true"#
    )
}

#[cfg(windows)]
fn build_powershell_script(config_paths: &[PathBuf]) -> String {
    // Windows has no mk_oracle.d equivalent (`--migrate-subdir` is compiled out
    // there), so this is always the main config alone.
    let source_configs = config_paths
        .iter()
        .map(|p| format!(". {}", powershell_quote(&p.display().to_string())))
        .collect::<Vec<_>>()
        .join("\n");
    let var_list = KNOWN_VARIABLES
        .iter()
        .map(|v| format!("'{v}'"))
        .collect::<Vec<_>>()
        .join(",");
    let prefix_filter = KNOWN_PREFIXES
        .iter()
        .map(|p| format!("$_.Name -like '{p}*'"))
        .collect::<Vec<_>>()
        .join(" -or ");
    format!(
        r#"{source_configs}
foreach ($__n in @({var_list})) {{
  $__v = (Get-Variable -Name $__n -ValueOnly -ErrorAction SilentlyContinue)
  if ($__v -is [array]) {{
    if ($__n -like 'DBUSER*' -or $__n -like 'ASMUSER*') {{ $__v = ($__v -join ':') + ':' }}
    else {{ $__v = $__v -join ' ' }}
  }}
  if ($__v) {{ Write-Output "$__n $__v" }}
}}
Get-Variable | Where-Object {{ {prefix_filter} }} | ForEach-Object {{
  $__v = $_.Value
  if ($__v -is [array]) {{ $__v = ($__v -join ':') + ':' }}
  if ($__v) {{ Write-Output "$($_.Name) $__v" }}
}}"#
    )
}

#[cfg(unix)]
fn posix_quote(s: &str) -> String {
    format!("'{}'", s.replace('\'', "'\\''"))
}

#[cfg(windows)]
fn powershell_quote(s: &str) -> String {
    format!("'{}'", s.replace('\'', "''"))
}

fn parse_variable_output(output: &str) -> Result<HashMap<String, String>> {
    Ok(output
        .lines()
        .filter_map(|line| {
            let (name, value) = line.split_once(' ')?;
            if name.is_empty() || value.is_empty() {
                return None;
            }
            Some((name.to_string(), value.to_string()))
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    const TS: &str = "2026-06-15 12:00:00 UTC";

    #[test]
    fn test_convert_minimal() {
        let legacy = "DBUSER='checkmk:secret::localhost::XE'\n";
        let vars = HashMap::from([("DBUSER".into(), "checkmk:secret::localhost::XE".into())]);
        let result = convert(legacy, "/test/mk_oracle.cfg", &vars, TS).unwrap();
        assert!(result.starts_with(
            "# --- Converted from /test/mk_oracle.cfg at 2026-06-15 12:00:00 UTC ---\n"
        ));
        assert!(result.contains("# DBUSER ***"));
        assert!(result.contains("# --- Known environment variables defined in legacy config ---\n"));
        assert!(result.contains("# --- Unified Config ---\n"));
        assert!(result.contains("hostname: localhost"));
        assert!(result.contains("      - alias: XE"));
        assert!(result.contains("username: \"checkmk\""));
        assert!(result.contains("password: \"secret\""));
    }

    #[test]
    fn test_convert_masks_sqls_dbpassword() {
        let legacy = "DBUSER='checkmk:secret::localhost::XE'\n";
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::localhost::XE".into()),
            ("SQLS.mysec.SQLS_DBPASSWORD".into(), "topsecret".into()),
        ]);
        let result = convert(legacy, "/test/mk_oracle.cfg", &vars, TS).unwrap();
        assert!(result.contains("# SQLS.mysec.SQLS_DBPASSWORD ***"));
        assert!(!result.contains("topsecret"));
    }

    #[test]
    fn test_convert_escapes_special_chars_in_password() {
        let legacy = "DBUSER='checkmk:a\\b\"c\td::localhost::XE'\n";
        let vars = HashMap::from([("DBUSER".into(), "checkmk:a\\b\"c\td::localhost::XE".into())]);
        let result = convert(legacy, "/test/mk_oracle.cfg", &vars, TS).unwrap();
        assert!(result.contains(r#"password: "a\\b\"c\td""#));
    }

    #[test]
    fn test_convert_no_dbuser_fails() {
        let result = convert("", "/test/empty.cfg", &HashMap::new(), TS);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("DBUSER not defined"), "got: {err}");
    }

    #[test]
    fn test_convert_result_is_valid_yaml() {
        let legacy = "DBUSER='checkmk:secret::::'\n";
        let vars = HashMap::from([("DBUSER".into(), "checkmk:secret::::".into())]);
        let result = convert(legacy, "/test/mk_oracle.cfg", &vars, TS).unwrap();
        let config = super::super::OracleConfig::load_str(&result);
        assert!(config.is_ok(), "generated YAML must be loadable: {result}");
        assert!(config.unwrap().ora_sql().is_some());
    }

    #[test]
    fn test_convert_olrloc_sets_oracle_local_registry() {
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            ("OLRLOC".into(), "/etc/oracle/olr.loc".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let ms = config.ora_sql().expect("ora_sql must be present");
        assert_eq!(
            ms.conn().oracle_local_registry(),
            Some(&std::path::PathBuf::from("/etc/oracle/olr.loc"))
        );
    }

    #[cfg(not(windows))]
    #[test]
    fn test_convert_remote_instance_platform_behavior() {
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            (
                "REMOTE_INSTANCE_1".into(),
                "user:pass:sysdba:remotehost:1521:piggyhost:ORCL:11.2".into(),
            ),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let ms = config.ora_sql().expect("ora_sql must be present");
        if cfg!(windows) {
            // Windows legacy plugin doesn't support REMOTE_INSTANCE
            assert!(
                ms.instances().is_empty(),
                "REMOTE_INSTANCE must be ignored on Windows"
            );
        } else {
            assert_eq!(
                ms.instances().len(),
                1,
                "REMOTE_INSTANCE must produce one instance"
            );
            let inst = &ms.instances()[0];
            assert_eq!(inst.auth().username(), "user");
            assert_eq!(inst.conn().hostname().to_string(), "remotehost");
        }
    }

    #[cfg(not(windows))]
    #[test]
    fn test_convert_remote_instance_emits_field9_tnsalias() {
        // A 9-field REMOTE_INSTANCE must emit the explicit TNS alias (field 9),
        // kept distinct from the SID (field 7) rather than defaulted to it.
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            (
                "REMOTE_INSTANCE_1".into(),
                "user:pass::remotehost:1521:piggyhost:PRODSID:11.2:prod_alias".into(),
            ),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(
            result.contains("- sid: PRODSID\n"),
            "SID from field 7 must be emitted, got: {result}"
        );
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let inst = &config
            .ora_sql()
            .expect("ora_sql must be present")
            .instances()[0];
        assert_eq!(
            inst.alias().as_ref().map(|a| a.to_string()),
            Some("prod_alias".to_string()),
            "explicit field-9 TNS alias must reach the instance, distinct from the SID"
        );
    }

    #[test]
    fn test_find_excluded_sections_maps_sid_to_its_section_list() {
        let vars = HashMap::from([
            (
                "EXCLUDE_proddb".into(),
                "performance processes sessions".into(),
            ),
            ("EXCLUDE_AAA".into(), "jobs".into()),
        ]);

        assert_eq!(
            find_excluded_sections(&vars),
            HashMap::from([
                (
                    "proddb".to_string(),
                    vec![
                        "performance".to_string(),
                        "processes".to_string(),
                        "sessions".to_string()
                    ]
                ),
                ("AAA".to_string(), vec!["jobs".to_string()]),
            ])
        );
    }

    #[test]
    fn test_find_excluded_sections_drops_empty_sid_and_value() {
        let vars = HashMap::from([
            ("EXCLUDE_".into(), "sessions".into()),
            ("EXCLUDE_XE".into(), "   ".into()),
            ("EXCLUDE_PROD".into(), String::new()),
        ]);

        assert!(find_excluded_sections(&vars).is_empty());
    }

    /// `ALL` excludes the whole instance instead of naming sections, which is
    /// not supported yet, so the pair is not processed at all.
    #[test]
    fn test_find_excluded_sections_drops_a_bare_all() {
        let vars = HashMap::from([
            ("EXCLUDE_AAA".into(), "ALL".into()),
            ("EXCLUDE_BBB".into(), " ALL ".into()),
            // A list that merely mentions ALL is still a section list.
            ("EXCLUDE_CCC".into(), "ALL jobs".into()),
        ]);

        assert_eq!(
            find_excluded_sections(&vars),
            HashMap::from([(
                "CCC".to_string(),
                vec!["ALL".to_string(), "jobs".to_string()]
            )])
        );
    }

    #[test]
    fn test_format_excluded_sections_emits_target_block() {
        let excluded = HashMap::from([(
            "prodpdb".to_string(),
            vec!["performance".to_string(), "sessions".to_string()],
        )]);

        let out: String = format_excluded_sections(&excluded).join("");

        assert_eq!(
            out,
            concat!(
                "    excluded_sections:\n",
                "      - target_id:\n",
                "          sid: prodpdb\n",
                "        sections: [performance, sessions]\n",
            )
        );
    }

    #[test]
    fn test_format_excluded_sections_empty_map_emits_nothing() {
        assert!(format_excluded_sections(&HashMap::new()).is_empty());
    }

    /// Blocks are emitted one per SID, sorted by SID so the config is stable
    /// regardless of `HashMap` order (XE2 inserted first, XE1 must come first).
    #[test]
    fn test_format_excluded_sections_sorts_blocks_by_sid() {
        let excluded = HashMap::from([
            ("XE2".to_string(), vec!["jobs".to_string()]),
            ("XE1".to_string(), vec!["performance".to_string()]),
        ]);

        let out: String = format_excluded_sections(&excluded).join("");

        assert_eq!(
            out,
            concat!(
                "    excluded_sections:\n",
                "      - target_id:\n",
                "          sid: XE1\n",
                "        sections: [performance]\n",
                "      - target_id:\n",
                "          sid: XE2\n",
                "        sections: [jobs]\n",
            )
        );
    }

    #[test]
    fn test_parse_custom_sqls_per_section_vars() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "mycustomsection1".into()),
            ("SQLS.mycustomsection1.SQLS_SIDS".into(), "MYINST3".into()),
            (
                "SQLS.mycustomsection1.SQLS_DIR".into(),
                "/etc/check_mk".into(),
            ),
            (
                "SQLS.mycustomsection1.SQLS_SQL".into(),
                "MyCustomSQL.sql".into(),
            ),
        ]);
        let result = parse_custom_sqls("", &vars);
        assert_eq!(
            result,
            vec![LegacyCustomSql {
                name: "mycustomsection1".into(),
                dir: Some("/etc/check_mk".into()),
                sql_file: "MyCustomSQL.sql".into(),
                sids: vec!["MYINST3".into()],
                dynamic_sids: false,
                tns_alias: None,
                header_name: None,
                header_sep: None,
                item_sid: None,
            }]
        );
    }

    #[test]
    fn test_parse_custom_sqls_global_fallback() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS_DIR".into(), "/global/dir".into()),
            ("SQLS_SQL".into(), "global.sql".into()),
        ]);
        let result = parse_custom_sqls("", &vars);
        assert_eq!(
            result,
            vec![LegacyCustomSql {
                name: "sec1".into(),
                dir: Some("/global/dir".into()),
                sql_file: "global.sql".into(),
                sids: vec![],
                dynamic_sids: false,
                tns_alias: None,
                header_name: None,
                header_sep: None,
                item_sid: None,
            }]
        );
    }

    #[test]
    fn test_parse_custom_sqls_missing_sql_skipped() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "nosql withsql".into()),
            ("SQLS.nosql.SQLS_DIR".into(), "/etc/check_mk".into()),
            ("SQLS.withsql.SQLS_SQL".into(), "query.sql".into()),
        ]);
        let result = parse_custom_sqls("", &vars);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].name, "withsql");
    }

    #[test]
    fn test_parse_custom_sqls_no_sections() {
        assert!(parse_custom_sqls("", &HashMap::new()).is_empty());
    }

    /// A `SQLS_SIDS` built by a shell expression is migrated as the SIDs the
    /// expression expanded to while the config was sourced.
    #[test]
    fn test_parse_custom_sqls_dynamic_sids_use_expansion() {
        let legacy = r#"SQLS_SECTIONS="sec1 sec2"
sec1 () {
    SQLS_SIDS=${ORACLE_SID:-$SIDS}
    SQLS_SQL="a.sql"
}
sec2 () {
    SQLS_SIDS=$(ps -ef | grep pmon | cut -d"_" -f3-)
    SQLS_SQL="b.sql"
}
"#;

        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1 sec2".into()),
            ("SQLS.sec1.SQLS_SIDS".into(), "EXPANDED".into()),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
            ("SQLS.sec2.SQLS_SQL".into(), "b.sql".into()),
        ]);
        let result = parse_custom_sqls(legacy, &vars);
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].sids, vec!["EXPANDED"]);
        assert!(result[0].dynamic_sids);
        assert!(
            result[1].sids.is_empty(),
            "the command expanded to nothing, so no SID is left"
        );
        assert!(result[1].dynamic_sids);
    }

    /// A `SQLS_SIDS` assigned at the top level applies to every section that
    /// does not define one of its own, so its dynamic nature applies too.
    #[test]
    fn test_parse_custom_sqls_dynamic_sids_from_global_assignment() {
        let legacy = r#"SQLS_SIDS="$(echo "$SIDS" | paste -sd,)"
SQLS_SECTIONS="sec1 sec2"
sec1 () {
    SQLS_SQL="a.sql"
}
sec2 () {
    SQLS_SIDS="PLAIN"
    SQLS_SQL="b.sql"
}
"#;

        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1 sec2".into()),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
            ("SQLS.sec2.SQLS_SIDS".into(), "PLAIN".into()),
            ("SQLS.sec2.SQLS_SQL".into(), "b.sql".into()),
        ]);
        let result = parse_custom_sqls(legacy, &vars);
        assert!(
            result[0].dynamic_sids,
            "sec1 inherits the global expression"
        );
        assert!(
            !result[1].dynamic_sids,
            "sec2 overrides it with a literal list"
        );
    }

    #[test]
    fn test_warn_dynamic_sqls_sids_keeps_expanded_section() {
        let legacy = "sec1 () {\n    SQLS_SIDS=$SIDS\n    SQLS_SQL=\"a.sql\"\n}\n";
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS.sec1.SQLS_SIDS".into(), "XE,MYINST2".into()),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls(legacy, &vars);
        assert_eq!(custom_sqls.len(), 1);
        assert_eq!(custom_sqls[0].sids, vec!["XE", "MYINST2"]);
        assert_eq!(
            warnings,
            vec!["sec1: SQLS_SIDS is built by a shell expression, which cannot be migrated reliably; using the SIDs it expanded to: XE, MYINST2".to_string()]
        );
    }

    #[test]
    fn test_warn_dynamic_sqls_sids_drops_unexpanded_section() {
        let legacy = "sec1 () {\n    SQLS_SIDS=$SIDS\n    SQLS_SQL=\"a.sql\"\n}\n";
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls(legacy, &vars);
        assert!(
            custom_sqls.is_empty(),
            "an unresolved expression must not become a global metric"
        );
        assert_eq!(
            warnings,
            vec!["sec1: SQLS_SIDS is built by a shell expression that expanded to no SID, skipping custom SQL section; assign the intended instances manually".to_string()]
        );
    }

    #[test]
    fn test_warn_dynamic_sqls_sids_keeps_tnsalias_sections() {
        let legacy = "sec1 () {\n    SQLS_SIDS=$SIDS\n    SQLS_SQL=\"a.sql\"\n}\n";
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS.sec1.SQLS_TNSALIAS".into(), "TNS".into()),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls(legacy, &vars);
        assert_eq!(
            custom_sqls.len(),
            1,
            "SQLS_TNSALIAS pins the section, its SQLS_SIDS is irrelevant"
        );
        assert!(warnings.is_empty(), "got: {warnings:?}");
    }

    #[test]
    fn test_warn_custom_sql_alias_sids_kept() {
        let mut custom = make_custom_sql("sec1", None, "a.sql", &["XE"]);
        custom.tns_alias = Some("PROD".into());
        assert_eq!(
            warn_custom_sql_alias_sids(&[custom], &[]),
            ["sec1: SQLS_SIDS 'XE' is migrated next to SQLS_TNSALIAS 'PROD', but the instance is resolved by its alias, so the SID no longer restricts the section".to_string()]
        );
    }

    #[test]
    fn test_warn_custom_sql_alias_sids_lost() {
        let mut custom = make_custom_sql("sec1", None, "a.sql", &["XE", "XE2"]);
        custom.tns_alias = Some("PROD".into());
        assert_eq!(
            warn_custom_sql_alias_sids(&[custom], &[]),
            ["sec1: SQLS_SIDS 'XE, XE2' cannot be kept next to SQLS_TNSALIAS 'PROD', the instance is resolved by its alias alone; verify that the alias connects to the intended database".to_string()]
        );
    }

    #[test]
    fn test_warn_custom_sql_alias_sids_ignores_unaffected_sections() {
        let plain = make_custom_sql("plain", None, "a.sql", &["XE"]);
        let mut aliased = make_custom_sql("aliased", None, "b.sql", &[]);
        aliased.tns_alias = Some("PROD".into());
        assert!(
            warn_custom_sql_alias_sids(&[plain, aliased], &[]).is_empty(),
            "only sections setting both are reported"
        );
    }

    #[test]
    fn test_parse_custom_sqls_sids_comma_and_space_separated() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS.sec1.SQLS_SIDS".into(), "A,B C".into()),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
        ]);
        let result = parse_custom_sqls("", &vars);
        assert_eq!(result[0].sids, vec!["A", "B", "C"]);
    }

    /// Build the custom SQL sections the way `convert` does: parse, map the
    /// `REMOTE_INSTANCE_*` references onto the SIDs of the migrated instances,
    /// then handle the dynamic `SQLS_SIDS` values.
    /// Returns the sections and the warnings.
    fn parse_and_resolve_custom_sqls(
        legacy: &str,
        variables: &HashMap<String, String>,
    ) -> (Vec<LegacyCustomSql>, Vec<String>) {
        let mut custom_sqls = parse_custom_sqls(legacy, variables);
        let mut warnings = resolve_remote_instance_sids(&mut custom_sqls, variables);
        warnings.extend(warn_dynamic_sqls_sids(&mut custom_sqls));
        (custom_sqls, warnings)
    }

    #[test]
    fn test_resolve_remote_instance_sids() {
        // The legacy plugin sets MK_SID to the variable name of a remote
        // instance, so SQLS_SIDS addresses it that way; the migrated config
        // knows it by its SID (field 7).
        let vars = HashMap::from([
            (
                "REMOTE_INSTANCE_FOO".into(),
                "user:pass::remotehost:1521::prod_sid:11.2".into(),
            ),
            ("SQLS_SECTIONS".into(), "sec1".into()),
            (
                "SQLS.sec1.SQLS_SIDS".into(),
                "PLAIN,REMOTE_INSTANCE_FOO".into(),
            ),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls("", &vars);
        assert_eq!(custom_sqls[0].sids, vec!["PLAIN", "PROD_SID"]);
        assert!(warnings.is_empty(), "got: {warnings:?}");
    }

    #[test]
    fn test_resolve_remote_instance_sids_unknown_reference() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1 sec2".into()),
            ("SQLS.sec1.SQLS_SIDS".into(), "REMOTE_INSTANCE_GONE".into()),
            (
                "SQLS.sec2.SQLS_SIDS".into(),
                "REMOTE_INSTANCE_GONE PLAIN".into(),
            ),
            ("SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls("", &vars);
        assert_eq!(
            custom_sqls.len(),
            1,
            "a section without any resolvable SID must be dropped, not made global"
        );
        assert_eq!(custom_sqls[0].name, "sec2");
        assert_eq!(custom_sqls[0].sids, vec!["PLAIN"]);
        assert_eq!(
            warnings,
            vec![
                "sec1: SQLS_SIDS references 'REMOTE_INSTANCE_GONE', but no such remote instance is defined, ignoring it".to_string(),
                "sec1: no instance left to run on, skipping custom SQL section".to_string(),
                "sec2: SQLS_SIDS references 'REMOTE_INSTANCE_GONE', but no such remote instance is defined, ignoring it".to_string(),
            ]
        );
    }

    #[test]
    fn test_resolve_remote_instance_sids_invalid_definition() {
        let vars = HashMap::from([
            // no SID in field 7, so the definition yields no instance
            ("REMOTE_INSTANCE_FOO".into(), "user:pass::host:1521".into()),
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS.sec1.SQLS_SIDS".into(), "REMOTE_INSTANCE_FOO".into()),
            ("SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls("", &vars);
        assert!(custom_sqls.is_empty());
        assert_eq!(
            warnings[0],
            "sec1: SQLS_SIDS references 'REMOTE_INSTANCE_FOO', whose definition is invalid, ignoring it"
        );
    }

    #[test]
    fn test_resolve_remote_instance_sids_keeps_tnsalias_sections() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS.sec1.SQLS_SIDS".into(), "REMOTE_INSTANCE_GONE".into()),
            ("SQLS.sec1.SQLS_TNSALIAS".into(), "TNS".into()),
            ("SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls("", &vars);
        assert_eq!(
            custom_sqls.len(),
            1,
            "SQLS_TNSALIAS pins the section, its SQLS_SIDS must not drop it"
        );
        assert!(
            custom_sqls[0].sids.is_empty(),
            "the dangling reference must not be kept as a SID"
        );
        assert_eq!(
            warnings,
            ["sec1: SQLS_SIDS references 'REMOTE_INSTANCE_GONE', but no such remote instance is defined, ignoring it".to_string()]
        );
    }

    #[test]
    fn test_resolve_remote_instance_sids_of_tnsalias_section() {
        let vars = HashMap::from([
            (
                "REMOTE_INSTANCE_FOO".into(),
                "user:pass::remotehost:1521::PROD_SID:11.2".into(),
            ),
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS.sec1.SQLS_SIDS".into(), "REMOTE_INSTANCE_FOO".into()),
            ("SQLS.sec1.SQLS_TNSALIAS".into(), "TNS".into()),
            ("SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls("", &vars);
        assert_eq!(
            custom_sqls[0].sids,
            vec!["PROD_SID"],
            "an aliased section keeps its SID, so the reference must be resolved too"
        );
        assert!(warnings.is_empty(), "got: {warnings:?}");
    }

    #[test]
    fn test_resolve_remote_instance_sids_keeps_global_sections() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS_SQL".into(), "a.sql".into()),
        ]);
        let (custom_sqls, warnings) = parse_and_resolve_custom_sqls("", &vars);
        assert_eq!(custom_sqls.len(), 1, "no SQLS_SIDS means all instances");
        assert!(custom_sqls[0].sids.is_empty());
        assert!(warnings.is_empty());
    }

    #[cfg(not(windows))]
    #[test]
    fn test_convert_custom_sql_of_remote_instance() {
        // CMK-37343: a REMOTE_INSTANCE_* reference used to be migrated as a
        // literal SID, adding an instance that only carried the metric and fell
        // back to the main connection.
        let legacy =
            "sec1 () {\n    SQLS_SIDS=\"REMOTE_INSTANCE_FOO\"\n    SQLS_SQL=\"a.sql\"\n}\n";
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            (
                "REMOTE_INSTANCE_FOO".into(),
                "user:pass::remotehost:1521::PRODSID:11.2".into(),
            ),
            ("SQLS_SECTIONS".into(), "sec1".into()),
            ("SQLS.sec1.SQLS_SIDS".into(), "REMOTE_INSTANCE_FOO".into()),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
        ]);
        let result = convert(legacy, "/test/cfg", &vars, TS).unwrap();
        assert!(
            !result.contains("- sid: REMOTE_INSTANCE_FOO"),
            "the reference must not become an own instance, got: {result}"
        );
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let ora = config.ora_sql().expect("ora_sql must be present");
        let inst = ora
            .instances()
            .iter()
            .find(|i| i.standalone_sid().map(|s| s.to_string()).as_deref() == Some("PRODSID"))
            .expect("the remote instance must be migrated");
        assert_eq!(inst.conn().hostname().to_string(), "remotehost");
        assert_eq!(
            inst.custom_metrics()
                .iter()
                .map(|s| s.item_value().unwrap().as_str().to_string())
                .collect::<Vec<_>>(),
            ["sec1"],
            "the metric must be attached to the migrated remote instance"
        );
    }

    #[cfg(not(windows))]
    #[test]
    fn test_convert_warns_on_custom_sql_item_sid() {
        let legacy = "sec1 () {\n    SQLS_SIDS=\"REMOTE_INSTANCE_PRODPDB1\"\n    \
                      SQLS_SQL=\"a.sql\"\n    SQLS_ITEM_SID=\"PRODPDB1\"\n}\n";
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            (
                "REMOTE_INSTANCE_PRODPDB1".into(),
                "user:pass::remotehost:1521::PRODCDB:11.2".into(),
            ),
            ("SQLS_SECTIONS".into(), "sec1".into()),
            (
                "SQLS.sec1.SQLS_SIDS".into(),
                "REMOTE_INSTANCE_PRODPDB1".into(),
            ),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
            ("SQLS.sec1.SQLS_ITEM_SID".into(), "PRODPDB1".into()),
        ]);
        let result = convert(legacy, "/test/cfg", &vars, TS).unwrap();
        assert!(
            result.contains("# WARNING: sec1: SQLS_ITEM_SID 'PRODPDB1' is not supported"),
            "got: {result}"
        );
        assert!(
            !result.contains("item_sid"),
            "there is no field to migrate it to, got: {result}"
        );
    }

    #[test]
    fn test_parse_custom_sqls_header_name() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1 sec2".into()),
            ("SQLS_SQL".into(), "a.sql".into()),
            ("SQLS.sec1.SQLS_SECTION_NAME".into(), "my_section".into()),
            ("SQLS.sec2.SQLS_SECTION_NAME".into(), "oracle_sql".into()),
        ]);
        let result = parse_custom_sqls("", &vars);
        assert_eq!(result[0].header_name.as_deref(), Some("my_section"));
        assert!(
            result[1].header_name.is_none(),
            "default 'oracle_sql' must not produce a header_name field"
        );
    }

    #[test]
    fn test_parse_custom_sqls_item_name() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1 sec2".into()),
            ("SQLS_SQL".into(), "a.sql".into()),
            ("SQLS.sec1.SQLS_ITEM_NAME".into(), "my_item".into()),
        ]);
        let result = parse_custom_sqls("", &vars);
        assert_eq!(result[0].name, "my_item");
        assert_eq!(result[1].name, "sec2", "default is the section name");
    }

    #[test]
    fn test_parse_custom_sqls_item_sid() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1 sec2".into()),
            ("SQLS_SQL".into(), "a.sql".into()),
            ("SQLS_ITEM_SID".into(), "GLOBAL".into()),
            ("SQLS.sec1.SQLS_ITEM_SID".into(), "PRODPDB1".into()),
        ]);
        let result = parse_custom_sqls("", &vars);
        assert_eq!(result[0].item_sid.as_deref(), Some("PRODPDB1"));
        assert!(
            result[1].item_sid.is_none(),
            "SQLS_ITEM_SID has no global fallback"
        );
    }

    #[test]
    fn test_warn_custom_sql_item_sid() {
        let mut custom = make_custom_sql("sec1", None, "a.sql", &["REMOTE_PROD"]);
        custom.item_sid = Some("PRODPDB1".into());
        assert_eq!(
            warn_custom_sql_item_sid(&[custom]),
            vec![
                "sec1: SQLS_ITEM_SID 'PRODPDB1' is not supported and is not migrated; the item of \
                 the oracle_sql section is built from the name of the instance the section runs \
                 on, so the name of the service changes and it is rediscovered"
            ]
        );
    }

    #[test]
    fn test_warn_custom_sql_item_sid_same_as_only_sid() {
        let mut custom = make_custom_sql("sec1", None, "a.sql", &["PRODPDB1"]);
        custom.item_sid = Some("PRODPDB1".into());
        assert!(
            warn_custom_sql_item_sid(&[custom]).is_empty(),
            "item is unchanged when the section runs on that instance only"
        );
    }

    #[test]
    fn test_warn_custom_sql_item_sid_of_aliased_section() {
        let mut custom = make_custom_sql("sec1", None, "a.sql", &["PRODPDB1"]);
        custom.item_sid = Some("PRODPDB1".into());
        custom.tns_alias = Some("PROD_ALIAS".into());
        assert_eq!(
            warn_custom_sql_item_sid(&[custom]).len(),
            1,
            "an aliased section may connect to any instance"
        );
    }

    #[test]
    fn test_warn_custom_sql_item_sid_ignores_unaffected_sections() {
        let plain = make_custom_sql("plain", None, "a.sql", &["PRODPDB1"]);
        let mut custom_section = make_custom_sql("custom_section", None, "a.sql", &["PRODPDB1"]);
        custom_section.item_sid = Some("OTHER".into());
        custom_section.header_name = Some("my_section".into());
        assert!(
            warn_custom_sql_item_sid(&[plain, custom_section]).is_empty(),
            "no SQLS_ITEM_SID, or a section the legacy plugin emits no item for"
        );
    }

    #[test]
    fn test_parse_custom_sqls_section_sep() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1 sec2 sec3".into()),
            ("SQLS_SQL".into(), "a.sql".into()),
            ("SQLS_SECTION_SEP".into(), "59".into()),
            ("SQLS.sec1.SQLS_SECTION_SEP".into(), "124".into()),
            ("SQLS.sec3.SQLS_SECTION_SEP".into(), "not-a-number".into()),
        ]);
        let result = parse_custom_sqls("", &vars);
        assert_eq!(result[0].header_sep, Some('|'));
        assert_eq!(
            result[1].header_sep,
            Some(';'),
            "top-level SQLS_SECTION_SEP is a global fallback"
        );
        assert!(
            result[2].header_sep.is_none(),
            "invalid ASCII code must be ignored"
        );
    }

    #[test]
    fn test_contains_plsql_block() {
        assert!(contains_plsql_block("BEGIN\n  NULL;\nEND;\n"));
        assert!(contains_plsql_block(
            "SELECT 1 FROM dual;\n  declare\n    x NUMBER;\nbegin\n"
        ));
        assert!(contains_plsql_block("DECLARE x NUMBER;"));
        assert!(contains_plsql_block("EXEC something; SELECT * FROM dual;"));
        assert!(contains_plsql_block("VAR variable; SELECT * FROM dual;"));
        assert!(contains_plsql_block("SET variable; SELECT * FROM dual;"));
        assert!(contains_plsql_block("SELECT * FROM dual;\nspool something"));
        assert!(contains_plsql_block(
            "Execute variable; SELECT * FROM dual;"
        ));
        assert!(contains_plsql_block("SELECT * FROM dual;\n variable var"));
        assert!(contains_plsql_block("SELECT * FROM dual;\n column var"));
        assert!(!contains_plsql_block("SELECT * FROM dual;\n"));
        assert!(!contains_plsql_block("SELECT begin_date FROM t;\n"));
        assert!(
            !contains_plsql_block("BEGIN_DATE := 1;\n"),
            "keyword must match the whole word"
        );
    }

    // Run this test only on Linux since on Windows the legacy plugin
    // doesn't support custom SQL sections and the test would fail.
    #[cfg(unix)]
    #[test]
    fn test_convert_warns_on_unreadable_custom_sql() {
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            ("SQLS_SECTIONS".into(), "myscn".into()),
            (
                "SQLS.myscn.SQLS_SQL".into(),
                "/nonexistent/dir/c.sql".into(),
            ),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(
            result.contains("# WARNING: myscn: cannot read SQL file '/nonexistent/dir/c.sql'"),
            "got: {result}"
        );
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        assert!(config.ora_sql().is_some());
    }

    #[test]
    fn test_collect_raw_sqls_sids() {
        let legacy = r#"SQLS_SIDS='TOP1 TOP2'
sec1 () {
    SQLS_SIDS="MYINST3"
}
sec2() {
    SQLS_SIDS=$(ps -ef | awk '{print $NF}')
}
sec3 () {
    SQLS_SQL="x.sql"
}
"#;
        let raw = collect_raw_sqls_sids(legacy);
        assert_eq!(raw[&None], "'TOP1 TOP2'");
        assert_eq!(raw[&Some("sec1".to_string())], "\"MYINST3\"");
        assert!(raw[&Some("sec2".to_string())].starts_with("$("));
        assert!(!raw.contains_key(&Some("sec3".to_string())));
    }

    fn make_custom_sql(
        name: &str,
        dir: Option<&str>,
        sql_file: &str,
        sids: &[&str],
    ) -> LegacyCustomSql {
        LegacyCustomSql {
            name: name.into(),
            dir: dir.map(String::from),
            sql_file: sql_file.into(),
            sids: sids.iter().map(|s| s.to_string()).collect(),
            dynamic_sids: false,
            tns_alias: None,
            header_name: None,
            header_sep: None,
            item_sid: None,
        }
    }

    #[test]
    fn test_format_custom_metrics_dir_trailing_slash() {
        let custom = make_custom_sql("sec1", Some("/etc/check_mk/"), "query.sql", &[]);
        let out: String = format_custom_metrics(&[custom]).join("");
        assert!(out.contains("          path: /etc/check_mk/query.sql\n"));
    }

    #[test]
    fn test_format_custom_metrics_no_dir_relative_path() {
        let custom = make_custom_sql("sec1", None, "query.sql", &[]);
        let out: String = format_custom_metrics(&[custom]).join("");
        assert!(out.contains("          path: query.sql\n"));
    }

    #[test]
    fn test_format_custom_metrics_skips_sid_restricted() {
        let global = make_custom_sql("global_sec", None, "a.sql", &[]);
        let restricted = make_custom_sql("sid_sec", None, "b.sql", &["XE"]);
        let out: String = format_custom_metrics(&[global, restricted]).join("");
        assert!(out.contains("      - global_sec:\n"));
        assert!(
            !out.contains("sid_sec"),
            "restricted metric must not be global"
        );
    }

    #[test]
    fn test_format_custom_metrics_skips_tnsalias_restricted() {
        let mut restricted = make_custom_sql("alias_sec", None, "b.sql", &[]);
        restricted.tns_alias = Some("PROD".into());
        let out: String = format_custom_metrics(&[restricted]).join("");
        assert!(out.is_empty(), "alias-restricted metric must not be global");
    }

    #[test]
    fn test_format_custom_metrics_header_name() {
        let mut custom = make_custom_sql("sec1", None, "query.sql", &[]);
        custom.header_name = Some("my_section".into());
        let out: String = format_custom_metrics(&[custom]).join("");
        assert!(
            out.contains("          path: query.sql\n          header_name: my_section\n"),
            "got: {out}"
        );
    }

    #[test]
    fn test_format_custom_metrics_section_sep() {
        let mut custom = make_custom_sql("sec1", None, "query.sql", &[]);
        custom.header_name = Some("my_section".into());
        custom.header_sep = Some('|');
        let out: String = format_custom_metrics(&[custom]).join("");
        assert!(
            out.contains("          header_name: my_section\n          header_sep: \"|\"\n"),
            "got: {out}"
        );
    }

    #[test]
    fn test_format_custom_metrics_section_sep_needs_section_name() {
        let mut custom = make_custom_sql("sec1", None, "query.sql", &[]);
        custom.header_sep = Some('|');
        let out: String = format_custom_metrics(&[custom]).join("");
        assert!(
            !out.contains("header_sep:"),
            "sep has no effect on the default oracle_sql section, got: {out}"
        );
    }

    #[test]
    fn test_format_instances_empty_hostname_defaults_to_localhost() {
        let dbuser = make_dbuser(None, "user", "pass", "", None, None, None);
        // port without hostname: connection block must fall back to localhost
        let xe = make_dbuser(Some("XE"), "", "", "", Some("1522"), None, None);
        let out: String = format_instances(&dbuser, &[xe], &[]).join("");
        assert!(out.contains(
            "        connection:\n          hostname: localhost\n          port: 1522\n"
        ));
    }

    #[test]
    fn test_format_instances_tnsalias_attaches_to_existing_alias() {
        let dbuser = make_dbuser(None, "user", "pass", "", None, None, None);
        let xe = make_dbuser(Some("XE"), "", "", "", None, None, Some("PROD"));
        let mut custom = make_custom_sql("sec1", None, "a.sql", &[]);
        custom.tns_alias = Some("PROD".to_owned());
        let out: String = format_instances(&dbuser, &[xe], &[custom]).join("");
        assert!(out.contains(
            "      - sid: XE\n        alias: PROD\n        custom_metrics:\n          - sec1:\n              path: a.sql\n"
        ), "got: {out}");
        assert!(
            !out.contains("      - alias: PROD\n"),
            "no extra instance for an already known alias"
        );
    }

    #[test]
    fn test_format_instances_tnsalias_creates_shared_alias_entry() {
        let dbuser = make_dbuser(None, "user", "pass", "", None, None, None);
        let mut c1 = make_custom_sql("sec1", None, "a.sql", &[]);
        c1.tns_alias = Some("REPORTING".into());
        let mut c2 = make_custom_sql("sec2", None, "b.sql", &[]);
        c2.tns_alias = Some("REPORTING".into());
        let out: String = format_instances(&dbuser, &[], &[c1, c2]).join("");
        assert_eq!(
            out.matches("      - alias: REPORTING\n").count(),
            1,
            "shared alias entry must be created once, got: {out}"
        );
        assert!(out.contains(
            "      - alias: REPORTING\n        custom_metrics:\n          - sec1:\n              path: a.sql\n          - sec2:\n              path: b.sql\n"
        ), "got: {out}");
    }

    #[test]
    fn test_format_instances_tnsalias_keeps_single_sid() {
        let dbuser = make_dbuser(None, "user", "pass", "", None, None, None);
        let mut custom = make_custom_sql("sec1", None, "a.sql", &["XE"]);
        custom.tns_alias = Some("PROD".into());
        let out: String = format_instances(&dbuser, &[], &[custom]).join("");
        assert!(
            out.contains("      - sid: XE\n        alias: PROD\n        custom_metrics:\n"),
            "SQLS_SIDS and SQLS_TNSALIAS must both reach the entry, got: {out}"
        );
        assert_eq!(
            out.matches("- sid: XE").count(),
            1,
            "the aliased entry is the only one carrying the SID, got: {out}"
        );
    }

    #[test]
    fn test_format_instances_tnsalias_drops_ambiguous_sids() {
        let dbuser = make_dbuser(None, "user", "pass", "", None, None, None);
        let mut multi = make_custom_sql("multi", None, "a.sql", &["XE", "XE2"]);
        multi.tns_alias = Some("PROD".into());
        let mut shared = make_custom_sql("shared", None, "b.sql", &["OTHER"]);
        shared.tns_alias = Some("REPORTING".into());
        let mut rival = make_custom_sql("rival", None, "c.sql", &["RIVAL"]);
        rival.tns_alias = Some("REPORTING".into());
        let out: String = format_instances(&dbuser, &[], &[multi, shared, rival]).join("");
        assert!(
            out.contains("      - alias: PROD\n"),
            "several SIDs cannot identify one aliased entry, got: {out}"
        );
        assert!(
            out.contains("      - alias: REPORTING\n"),
            "sections disagreeing on the SID leave the alias alone, got: {out}"
        );
        assert!(!out.contains("- sid:"), "got: {out}");
    }

    #[test]
    fn test_format_instances_tnsalias_of_known_instance_keeps_its_sid() {
        let dbuser = make_dbuser(None, "user", "pass", "", None, None, None);
        let owner = make_dbuser(Some("XE1"), "user", "pass", "", None, None, Some("PROD"));
        let mut custom = make_custom_sql("sec1", None, "a.sql", &["OTHER"]);
        custom.tns_alias = Some("PROD".into());
        let out: String = format_instances(&dbuser, &[owner], &[custom]).join("");
        assert!(
            out.contains("      - sid: XE1\n        alias: PROD\n"),
            "the alias keeps the SID of the instance owning it, got: {out}"
        );
        assert!(
            !out.contains("OTHER"),
            "the section must not add a second entry for the same alias, got: {out}"
        );
    }

    // Run this test only on Linux since on Windows the legacy plugin
    // doesn't support custom SQL sections and the test would fail.
    #[cfg(unix)]
    #[test]
    fn test_convert_custom_metrics_static_sids_attach_to_instances() {
        let legacy = "myscn () {\n    SQLS_SIDS=\"XE MYINST2\"\n    SQLS_SQL=\"c.sql\"\n}\n";
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            ("DBUSER_XE".into(), "xe:xepwd::::".into()),
            ("SQLS_SECTIONS".into(), "myscn".into()),
            ("SQLS.myscn.SQLS_SIDS".into(), "XE MYINST2".into()),
            ("SQLS.myscn.SQLS_SQL".into(), "c.sql".into()),
        ]);
        let result = convert(legacy, "/test/cfg", &vars, TS).unwrap();
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let ms = config.ora_sql().expect("ora_sql must be present");
        // no global custom metric
        assert!(!ms.all_sections().iter().any(|s| s.is_custom_metric()));

        let instance_metric = |result: &str, sid: &str| {
            result.contains(&format!(
                "      - sid: {sid}\n        custom_metrics:\n          - myscn:\n              path: c.sql\n"
            ))
        };
        // MYINST2 has no DBUSER entry — created just for the custom metric
        assert!(instance_metric(&result, "MYINST2"), "got: {result}");
        // XE exists (DBUSER_XE) and carries the metric after its auth block
        assert!(
            result.contains(
                "          type: standard\n        custom_metrics:\n          - myscn:\n              path: c.sql\n"
            ),
            "got: {result}"
        );
        let metric_of = |sid: &str| {
            ms.instances()
                .iter()
                .find(|i| i.standalone_sid().map(|s| s.to_string()).as_deref() == Some(sid))
                .map(|i| i.custom_metrics().to_vec())
                .unwrap_or_else(|| panic!("instance {sid} not found"))
        };
        for sid in ["XE", "MYINST2"] {
            let metrics = metric_of(sid);
            assert_eq!(metrics.len(), 1, "{sid} must have one custom metric");
            assert_eq!(metrics[0].item_value().unwrap().as_str(), "myscn");
            assert_eq!(metrics[0].path(), Some(Path::new("c.sql")));
        }
    }

    // Run this test only on Linux since on Windows the legacy plugin
    // doesn't support custom SQL sections and the test would fail.
    #[cfg(unix)]
    #[test]
    fn test_convert_custom_metrics_tnsalias_attaches_to_alias_instance() {
        let legacy = "myscn () {\n    SQLS_TNSALIAS=\"PROD_ALIAS\"\n    SQLS_SQL=\"c.sql\"\n}\n";
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            ("SQLS_SECTIONS".into(), "myscn".into()),
            ("SQLS.myscn.SQLS_TNSALIAS".into(), "PROD_ALIAS".into()),
            ("SQLS.myscn.SQLS_SQL".into(), "c.sql".into()),
        ]);
        let result = convert(legacy, "/test/cfg", &vars, TS).unwrap();
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let ms = config.ora_sql().expect("ora_sql must be present");
        // no global custom metric
        assert!(!ms.all_sections().iter().any(|s| s.is_custom_metric()));

        let inst = ms
            .instances()
            .iter()
            .find(|i| i.alias() == &Some("PROD_ALIAS".to_string().into()))
            .expect("instance with TNS alias must exist");
        assert!(
            inst.standalone_sid().is_none(),
            "alias-only instance must have no sid"
        );
        let metrics = inst.custom_metrics();
        assert_eq!(metrics.len(), 1);
        assert_eq!(metrics[0].item_value().unwrap().as_str(), "myscn");
        assert_eq!(metrics[0].path(), Some(Path::new("c.sql")));
    }

    // Run this test only on Linux since on Windows the legacy plugin
    // doesn't support custom SQL sections and the test would fail.
    #[cfg(unix)]
    #[test]
    fn test_convert_custom_metrics_header_name_in_yaml() {
        let legacy =
            "myscn () {\n    SQLS_SECTION_NAME=\"my_section\"\n    SQLS_SECTION_SEP=124\n    SQLS_SQL=\"c.sql\"\n}\n";
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            ("SQLS_SECTIONS".into(), "myscn".into()),
            ("SQLS.myscn.SQLS_SECTION_NAME".into(), "my_section".into()),
            ("SQLS.myscn.SQLS_SECTION_SEP".into(), "124".into()),
            ("SQLS.myscn.SQLS_SQL".into(), "c.sql".into()),
        ]);
        let result = convert(legacy, "/test/cfg", &vars, TS).unwrap();
        assert!(
            result.contains(
                "    custom_metrics:\n      - myscn:\n          path: c.sql\n          header_name: my_section\n          header_sep: \"|\"\n"
            ),
            "got: {result}"
        );
        // the loader must tolerate the header_name/sep keys (support comes later)
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        assert!(config.ora_sql().is_some());
    }

    #[test]
    fn test_convert_asmuser_fields_in_yaml() {
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            ("ASMUSER".into(), "asm-user:asm-password:SYSASM:::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let ms = config.ora_sql().expect("ora_sql must be present");
        let auth = ms.auth();
        assert_eq!(auth.asm_username(), "asm-user");
        assert_eq!(auth.asm_password(), Some("asm-password"));
        assert_eq!(
            auth.asm_role(),
            Some(&crate::config::authentication::Role::SysASM)
        );
    }

    #[test]
    fn test_convert_asmuser_without_password() {
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::::".into()),
            ("ASMUSER".into(), "/::SYSASM:::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let ms = config.ora_sql().expect("ora_sql must be present");
        let auth = ms.auth();
        assert_eq!(auth.asm_username(), "checkmk");
        assert_eq!(auth.asm_password(), Some("secret"));
        assert_eq!(
            auth.asm_role(),
            Some(&crate::config::authentication::Role::SysASM)
        );
    }

    #[test]
    fn test_convert_tns_admin() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("TNS_ADMIN".into(), "/opt/oracle/tns".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains("tns_admin: /opt/oracle/tns"));
    }

    #[test]
    fn test_convert_dbuser_extra_omits_default_alias() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_XE2".into(), "xe2user:xe2pwd:::1521:".into()),
            ("DBUSER_XE1".into(), "/:::::oooo".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(!result.contains("      - sid: XE2\n        alias:"));
        assert!(result.contains("      - sid: XE1\n        alias: oooo\n"));
    }

    #[test]
    fn test_convert_dbuser_slash_username_is_wallet() {
        // A "/" username in DBUSER / DBUSER_ means external authentication: the
        // migrated config gets an empty username and `type: wallet`. A regular
        // instance user stays `type: standard`.
        let vars = HashMap::from([
            ("DBUSER".into(), "/:::::".into()),
            ("DBUSER_XE1".into(), "/:::::".into()),
            ("DBUSER_XE2".into(), "xe2user:xe2pwd:::1521:".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();

        // main authentication: empty username, wallet type
        assert!(
            result.contains(
                "    authentication:\n      username: \"\"\n      password: \"\"\n      type: wallet\n"
            ),
            "main auth not wallet: {result}"
        );
        // DBUSER_XE1 instance: wallet block emitted despite empty user and password
        assert!(
            result.contains(
                "        authentication:\n          username: \"\"\n          password: \"\"\n          type: wallet\n"
            ),
            "XE1 instance auth not wallet: {result}"
        );
        // DBUSER_XE2 instance: ordinary user keeps standard type
        assert!(
            result.contains(
                "        authentication:\n          username: \"xe2user\"\n          password: \"xe2pwd\"\n          type: standard\n"
            ),
            "XE2 instance auth not standard: {result}"
        );
    }

    #[test]
    fn test_convert_asmuser_slash_is_wallet() {
        // Like DBUSER, a "/" ASMUSER is external auth: the migrated config declares
        // `asm_type: wallet` (username erased) so ASM auth parses back as wallet
        // instead of inheriting the main auth type.
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("ASMUSER".into(), "/:::::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(
            result.contains("      asm_type: wallet\n"),
            "ASM '/' must map to wallet: {result}"
        );
        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        assert_eq!(
            config
                .ora_sql()
                .expect("ora_sql")
                .auth()
                .asm_auth_type()
                .to_string(),
            "wallet",
            "ASM auth type must parse back as wallet"
        );
    }

    #[test]
    fn test_convert_wallet_main_with_alias_has_no_instance_auth() {
        // A wallet main DBUSER with a TNS alias yields an alias instance, but its
        // auth stays under `main:`; the instance must not re-emit an auth block
        // (an 8-space `authentication:`), even though `wallet` is set.
        let vars = HashMap::from([("DBUSER".into(), "/:::::MYALIAS".into())]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(
            result.contains("      - alias: MYALIAS\n"),
            "alias instance expected: {result}"
        );
        assert!(
            result.contains(
                "    authentication:\n      username: \"\"\n      password: \"\"\n      type: wallet\n"
            ),
            "main must carry the wallet auth: {result}"
        );
        assert!(
            !result.contains("        authentication:"),
            "alias instance must inherit main auth, not emit its own: {result}"
        );
    }

    #[test]
    fn test_parse_sections() {
        let vars = HashMap::from([("SYNC_SECTIONS".into(), "instance performance locks".into())]);
        let result = parse_sections(&vars, "SYNC_SECTIONS");
        assert_eq!(
            result,
            HashSet::from(["instance".into(), "performance".into(), "locks".into()])
        );
        assert!(parse_sections(&vars, "MISSING").is_empty());
    }

    #[test]
    fn test_parse_sections_splits_on_tabs() {
        let vars = HashMap::from([("SYNC_SECTIONS".into(), "instance\tperformance".into())]);
        assert_eq!(
            parse_sections(&vars, "SYNC_SECTIONS"),
            HashSet::from(["instance".into(), "performance".into()])
        );
    }

    #[test]
    fn test_parse_custom_sqls_splits_on_comma_tab_and_space() {
        let vars = HashMap::from([
            ("SQLS_SECTIONS".into(), "sec1,sec2\tsec3 sec4".into()),
            ("SQLS.sec1.SQLS_SQL".into(), "a.sql".into()),
            ("SQLS.sec2.SQLS_SQL".into(), "b.sql".into()),
            ("SQLS.sec3.SQLS_SQL".into(), "c.sql".into()),
            ("SQLS.sec4.SQLS_SQL".into(), "d.sql".into()),
        ]);
        let names: Vec<String> = parse_custom_sqls("", &vars)
            .into_iter()
            .map(|s| s.name)
            .collect();
        assert_eq!(names, vec!["sec1", "sec2", "sec3", "sec4"]);
    }

    #[test]
    fn test_convert_sections_with_async_flag() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("SYNC_SECTIONS".into(), "instance locks".into()),
            ("ASYNC_SECTIONS".into(), "tablespaces rman".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains("      - instance:\n"));
        assert!(result.contains("      - locks:\n"));
        assert!(result.contains("      - rman:\n          is_async: true\n"));
        assert!(result.contains("      - tablespaces:\n          is_async: true\n"));
    }

    #[test]
    fn test_convert_sections_asm_affinity() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("SYNC_SECTIONS".into(), "instance locks".into()),
            ("ASYNC_SECTIONS".into(), "tablespaces".into()),
            ("SYNC_ASM_SECTIONS".into(), "instance processes".into()),
            ("ASYNC_ASM_SECTIONS".into(), "asm_diskgroup".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        // asm_diskgroup: async + asm-only
        assert!(result.contains(
            "      - asm_diskgroup:\n          is_async: true\n          affinity: \"asm\"\n"
        ));
        // instance: sync normal + sync asm → is_async: false, affinity: all
        assert!(result.contains(
            "      - instance:\n          is_async: false\n          affinity: \"all\"\n"
        ));
        // processes: asm-only (not in normal), sync
        assert!(result.contains(
            "      - processes:\n          is_async: false\n          affinity: \"asm\"\n"
        ));
        // locks: normal-only, sync → is_async: false, no affinity
        assert!(result.contains("      - locks:\n          is_async: false\n"));
        assert!(!result.contains("      - locks:\n          is_async: false\n          affinity:"));
        // tablespaces: normal-only, async
        assert!(result.contains("      - tablespaces:\n          is_async: true\n"));
        assert!(
            !result.contains("      - tablespaces:\n          is_async: true\n          affinity:")
        );
    }

    #[test]
    fn test_convert_dbuser_extra_has_connection_and_auth() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_ORCL".into(), "admin:secret::myhost:1522:".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains(
            r#"      - sid: ORCL
        connection:
          hostname: myhost
          port: 1522
        authentication:
          username: "admin"
          password: "secret"
          type: standard
"#
        ));
    }

    #[test]
    fn test_convert_dbuser_extra_no_connection_when_empty() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_XE".into(), "xe:xepwd::::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(!result.contains("      - sid: XE\n        connection:"));
    }

    #[test]
    fn test_convert_main_dbuser_alias_no_duplicate_connection_or_auth() {
        // The main DBUSER carries a TNS alias but no SID, so it becomes an
        // alias-only instance. Its connection and authentication belong to
        // `main:`; the instance entry must not duplicate them (8-space-indented
        // blocks are instance-level, 4-space ones are main-level).
        let vars = HashMap::from([("DBUSER".into(), "admin:secret::myhost:1522:ORCL".into())]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains("      - alias: ORCL\n"), "got: {result}");
        assert!(!result.contains("      - sid"), "got: {result}");
        assert!(
            !result.contains("        connection:\n"),
            "alias-only instance must inherit connection from main:, got: {result}"
        );
        assert!(
            !result.contains("        authentication:\n"),
            "alias-only instance must inherit auth from main:, got: {result}"
        );
    }

    #[test]
    fn test_convert_dbuser_role_in_auth() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_XE".into(), "admin:secret:SYSDBA:::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains("          role: sysdba\n"));
    }

    /// The SID-as-alias fallback must survive loading, not just appear in the
    /// yaml: `alias` outranks `sid` when the target is resolved, so such an
    /// instance is an alias target with no standalone sid. The Windows reference
    /// config takes this path (its `$DBUSER_*` arrays carry no TNSALIAS field),
    /// and only the Windows CI node runs it - hence this check here.
    #[test]
    fn test_wallet_without_alias_resolves_as_an_alias_target() {
        let vars = HashMap::from([
            ("DBUSER".into(), "checkmk:secret::localhost:1521:".into()),
            ("DBUSER_XE1".into(), "/:::::".into()),
        ]);

        let result = convert("", "/test/cfg", &vars, TS).unwrap();

        let config =
            super::super::OracleConfig::load_str(&result).expect("generated YAML must be loadable");
        let instance = &config
            .ora_sql()
            .expect("ora_sql must be present")
            .instances()[0];
        assert_eq!(
            instance
                .alias()
                .as_ref()
                .map(ToString::to_string)
                .as_deref(),
            Some("XE1"),
            "got: {result}"
        );
        assert!(
            instance.standalone_sid().is_none(),
            "the alias outranks the sid, so there is no standalone sid: {result}"
        );
    }

    #[test]
    fn test_convert_slash_username_emits_wallet_auth() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_XE3".into(), "/::SYSASM:::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(
            !result.contains("      - sid: XE3\n        connection:"),
            "XE3 must have no connection (empty hostname)"
        );
        // "/" username → wallet auth: empty username/password, type wallet, role kept.
        // No explicit TNSALIAS → the SID is assumed as the alias (wallet connects
        // via `/@<alias>`), so `alias: XE3` precedes the authentication block.
        assert!(
            result.contains(
                "      - sid: XE3\n        alias: XE3\n        authentication:\n          username: \"\"\n          password: \"\"\n          type: wallet\n          role: sysasm\n"
            ),
            "XE3 must have wallet authentication with SID-as-alias: {result}"
        );
    }

    #[test]
    fn test_parse_dbuser_slash_username_replaced() {
        let db = parse_dbuser("DBUSER", "/::SYSASM:::").unwrap();
        assert!(db.username.is_empty(), "'/' must be replaced with empty");
        assert!(db.wallet, "'/' username must flag wallet authentication");
        assert_eq!(db.role.as_deref(), Some("SYSASM"));
    }

    #[test]
    fn test_parse_dbuser() {
        let db = parse_dbuser("DBUSER", "checkmk:secret:SYSDBA:myhost:1522:ORCL").unwrap();
        assert!(db.sid.is_none(), "DBUSER has no SID suffix");
        assert_eq!(db.username, "checkmk");
        assert_eq!(db.password, "secret");
        assert_eq!(db.role.as_deref(), Some("SYSDBA"));
        assert_eq!(db.hostname, "myhost");
        assert_eq!(db.port.as_deref(), Some("1522"));
        assert_eq!(db.tns_alias, Some("ORCL".to_owned()));
    }

    #[test]
    fn test_parse_dbuser_with_sid_suffix() {
        let db = parse_dbuser("DBUSER_XE1", "/:::::oooo").unwrap();
        assert_eq!(db.sid.as_deref(), Some("XE1"));
        assert!(db.username.is_empty(), "'/' replaced with empty");
        assert_eq!(db.tns_alias, Some("oooo".to_owned()));
    }

    /// A `DBUSER_<sid>` SID is upper-cased, like the SID of a `REMOTE_INSTANCE_*`,
    /// so the two never name one database as two instances.
    #[test]
    fn test_parse_dbuser_sid_suffix_is_upper_cased() {
        assert_eq!(
            parse_dbuser("DBUSER_xe", "user:pass")
                .unwrap()
                .sid
                .as_deref(),
            Some("XE")
        );
        let remote = parse_remote_instance(
            "REMOTE_INSTANCE_1",
            "user:pass::remotehost:1521:piggyhost:xe:11.2",
        )
        .expect("valid remote instance");
        assert_eq!(remote.sid.as_deref(), Some("XE"));
    }

    #[test]
    fn test_parse_dbuser_empty_optionals() {
        let db = parse_dbuser("DBUSER", "user:pass::::").unwrap();
        assert!(db.sid.is_none());
        assert_eq!(db.username, "user");
        assert_eq!(db.password, "pass");
        assert!(db.role.is_none());
        assert!(db.hostname.is_empty());
        assert!(db.port.is_none());
        assert!(db.tns_alias.is_none());
    }

    #[test]
    fn test_parse_dbuser_minimal() {
        let db = parse_dbuser("DBUSER", "user:pass").unwrap();
        assert!(db.sid.is_none());
        assert_eq!(db.username, "user");
        assert_eq!(db.password, "pass");
        assert!(db.role.is_none());
        assert!(db.hostname.is_empty());
        assert!(db.port.is_none());
        assert!(db.tns_alias.is_none());
    }

    #[test]
    fn test_parse_dbuser_too_few_fields() {
        assert!(parse_dbuser("DBUSER", "onlyuser").is_err());
    }

    #[test]
    fn test_parse_dbuser_invalid_name() {
        let err = parse_dbuser("ASMUSER", "/:::::").unwrap_err();
        assert!(err.to_string().contains("invalid variable name"));
        assert!(parse_dbuser("DB_USER", "user:pass").is_err());
        assert!(parse_dbuser("DBUSER", "user:pass").is_ok());
        assert!(parse_dbuser("DBUSER_XE", "user:pass").is_ok());
    }

    #[test]
    fn test_parse_remote_instance_full() {
        let ri = parse_remote_instance(
            "REMOTE_INSTANCE_1",
            "check_mk:mypassword:sysdba:myRemoteHost:1521:myOracleHost:MYINST3:11.2",
        )
        .expect("valid remote instance must return Some");
        assert_eq!(ri.sid.as_deref(), Some("MYINST3"));
        assert_eq!(ri.username, "check_mk");
        assert_eq!(ri.password, "mypassword");
        assert_eq!(ri.role.as_deref(), Some("sysdba"));
        assert_eq!(ri.hostname, "myRemoteHost");
        assert_eq!(ri.port.as_deref(), Some("1521"));
        assert_eq!(ri.piggyback_host.as_deref(), Some("myOracleHost"));
        // 8-field value has no TNS alias (field 9); it is not defaulted to the SID
        assert_eq!(ri.tns_alias, None);
    }

    #[test]
    fn test_parse_remote_instance_full_2() {
        let ri = parse_remote_instance(
            "REMOTE_INSTANCE_piggy-hostname",
            "u:p::hostname:1521:piggy-hostname:OACL-hostname:9.2:tns-hostname",
        )
        .expect("valid remote instance must return Some");
        assert_eq!(ri.sid.as_deref(), Some("OACL-HOSTNAME"));
        assert_eq!(ri.username, "u");
        assert_eq!(ri.password, "p");
        assert!(ri.role.is_none());
        assert_eq!(ri.hostname, "hostname");
        assert_eq!(ri.port.as_deref(), Some("1521"));
        assert_eq!(ri.piggyback_host.as_deref(), Some("piggy-hostname"));
        assert_eq!(ri.tns_alias, Some("tns-hostname".to_string()));
    }

    #[test]
    fn test_parse_remote_instance_no_sid_returns_none() {
        assert!(parse_remote_instance("REMOTE_INSTANCE_XE", "user:pass::host:1521::").is_none());
    }

    #[test]
    fn test_parse_remote_instance_no_sid_field_returns_none() {
        assert!(parse_remote_instance("REMOTE_INSTANCE_DB1", "user:pass::host:1521").is_none());
    }

    #[test]
    fn test_parse_remote_instance_empty_username_returns_none() {
        assert!(parse_remote_instance("REMOTE_INSTANCE_1", ":pass::host:1521::MYINST3").is_none());
    }

    #[test]
    fn test_parse_remote_instance_slash_username_returns_none() {
        assert!(parse_remote_instance("REMOTE_INSTANCE_1", "/:pass::host:1521::MYINST3").is_none());
    }

    #[test]
    fn test_parse_remote_instance_too_few_fields() {
        assert!(parse_remote_instance("REMOTE_INSTANCE_1", "user:pass").is_none());
    }

    #[test]
    fn test_parse_remote_instance_invalid_prefix() {
        assert!(parse_remote_instance("DBUSER_XE", "user:pass::host:1521").is_none());
    }

    #[test]
    fn test_format_timestamp() {
        let ts = format_timestamp();
        assert!(ts.ends_with(" UTC"));
        assert!(ts.contains('-'));
        assert!(ts.contains(':'));
        assert_eq!(ts.len(), 23);
    }

    #[test]
    fn test_civil_from_days() {
        assert_eq!(civil_from_days(0), (1970, 1, 1));
        assert_eq!(civil_from_days(365), (1971, 1, 1));
        assert_eq!(civil_from_days(19889), (2024, 6, 15));
    }

    #[test]
    fn test_parse_variable_output() {
        let output = "DBUSER checkmk:secret\nCACHE_MAXAGE 600\nSYNC_SECTIONS instance sessions\n";
        let result = parse_variable_output(output).unwrap();
        assert_eq!(result.len(), 3);
        assert_eq!(result["DBUSER"], "checkmk:secret");
        assert_eq!(result["CACHE_MAXAGE"], "600");
        assert!(result["SYNC_SECTIONS"].contains("sessions"));
    }

    #[test]
    fn test_parse_variable_output_skips_malformed() {
        let output = "DBUSER checkmk\n\n BADNAME value\nNOSPACE\nVAR \n";
        let result = parse_variable_output(output).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result["DBUSER"], "checkmk");
    }

    #[cfg(unix)]
    #[test]
    fn test_build_posix_script() {
        let script = build_posix_script(&[PathBuf::from("/tmp/test.cfg")]);
        assert!(script.starts_with(". '/tmp/test.cfg'"));
        assert!(script.contains("DBUSER"));
        assert!(script.contains("CACHE_MAXAGE"));
        assert!(script.contains("REMOTE_INSTANCE_"));
        assert!(script.contains("EXCLUDE_"));
        assert!(script.contains("SQLS.$__sec.$__n"));
    }

    /// Several configs are sourced in the given order, like the legacy plugin
    /// sources mk_oracle.cfg and then the fragments of mk_oracle.d.
    #[cfg(unix)]
    #[test]
    fn test_build_posix_script_sources_all_configs() {
        let script = build_posix_script(&[
            PathBuf::from("/tmp/test.cfg"),
            PathBuf::from("/tmp/mk_oracle.d/01_a.cfg"),
            PathBuf::from("/tmp/mk_oracle.d/02_b.cfg"),
        ]);
        assert!(script.starts_with(
            ". '/tmp/test.cfg'\n. '/tmp/mk_oracle.d/01_a.cfg'\n. '/tmp/mk_oracle.d/02_b.cfg'\n"
        ));
    }

    #[cfg(unix)]
    #[test]
    fn test_execute_config_basic() {
        let config_path =
            std::env::temp_dir().join(format!("mk_oracle_test_exec_{}.cfg", std::process::id()));
        std::fs::write(
            &config_path,
            "DBUSER='checkmk:secret'\nCACHE_MAXAGE=600\nREMOTE_INSTANCE_XE='user:pass::host'\n",
        )
        .unwrap();
        let result = convert_configs(std::slice::from_ref(&config_path));
        let _ = std::fs::remove_file(&config_path);
        let vars = result.unwrap();
        assert_eq!(vars["DBUSER"], "checkmk:secret");
        assert_eq!(vars["CACHE_MAXAGE"], "600");
        assert_eq!(vars["REMOTE_INSTANCE_XE"], "user:pass::host");
    }

    fn make_dbuser(
        sid: Option<&str>,
        username: &str,
        password: &str,
        hostname: &str,
        port: Option<&str>,
        role: Option<&str>,
        tns_alias: Option<&str>,
    ) -> LegacyDbUser {
        LegacyDbUser {
            sid: sid.map(String::from),
            username: username.to_string(),
            password: password.to_string(),
            hostname: hostname.to_string(),
            port: port.map(String::from),
            role: role.map(String::from),
            tns_alias: tns_alias.map(|s| s.to_string()),
            piggyback_host: None,
            wallet: username == "/",
        }
    }

    /// Wallet auth without an explicit TNSALIAS connects via the SID used as the
    /// alias (legacy `${CFGTNSALIAS:-${ORACLE_SID}}`), so the entry carries both
    /// `sid:` and `alias:` (the runtime's alias path drives the connect).
    #[test]
    fn test_format_instances_wallet_falls_back_to_sid_alias() {
        let dbuser = make_dbuser(None, "checkmk", "secret", "localhost", None, None, None);
        let xe = make_dbuser(Some("XE"), "/", "", "", None, None, None);

        let out: String = format_instances(&dbuser, &[xe], &[]).join("");

        assert!(
            out.contains("      - sid: XE\n        alias: XE\n"),
            "wallet instance must use its SID as the TNS alias, got: {out}"
        );
    }

    /// An explicit TNSALIAS on a wallet entry takes precedence over the SID.
    #[test]
    fn test_format_instances_wallet_keeps_explicit_alias() {
        let dbuser = make_dbuser(None, "checkmk", "secret", "localhost", None, None, None);
        let xe = make_dbuser(Some("XE"), "/", "", "", None, None, Some("PRODALIAS"));

        let out: String = format_instances(&dbuser, &[xe], &[]).join("");

        assert!(
            out.contains("      - sid: XE\n        alias: PRODALIAS\n"),
            "explicit TNSALIAS must win over SID-as-alias, got: {out}"
        );
        assert!(
            !out.contains("alias: XE\n"),
            "SID must not be reused as alias when TNSALIAS is set, got: {out}"
        );
    }

    /// Standard (non-wallet) auth without an alias keeps a bare `sid:`; the
    /// SID-as-alias fallback is wallet-only.
    #[test]
    fn test_format_instances_standard_auth_has_no_alias() {
        let dbuser = make_dbuser(None, "checkmk", "secret", "localhost", None, None, None);
        let xe = make_dbuser(Some("XE"), "user", "pass", "", None, None, None);

        let out: String = format_instances(&dbuser, &[xe], &[]).join("");

        assert!(out.contains("      - sid: XE\n"), "got: {out}");
        assert!(
            !out.contains("alias:"),
            "standard auth must not synthesize an alias, got: {out}"
        );
    }

    #[test]
    fn test_format_instances() {
        let dbuser = make_dbuser(
            None,
            "checkmk",
            "secret",
            "localhost",
            Some("1521"),
            None,
            None,
        );
        // XE1: inherits main connection/auth, custom alias
        let xe1 = make_dbuser(Some("XE1"), "", "", "", None, None, Some("myalias"));
        // XE2: own connection + auth + role, alias=None
        let xe2 = make_dbuser(
            Some("XE2"),
            "xe2user",
            "xe2pwd",
            "dbhost",
            Some("1522"),
            Some("SYSDBA"),
            None,
        );

        let out: String = format_instances(&dbuser, &[xe1, xe2], &[]).join("");

        // DBUSER without sid/alias contributes no instance entry:
        // the first entry after the header is XE1
        assert!(out.starts_with("    instances:\n      - sid: XE1\n"));
        // XE1: sid=XE1, alias=myalias, no connection/auth block
        assert!(out.contains("      - sid: XE1\n"));
        assert!(out.contains("        alias: myalias\n"));
        assert!(!out.contains("      - sid: XE1\n        alias: myalias\n        connection:"));
        assert!(!out.contains("      - sid: XE1\n        alias: myalias\n        authentication:"));
        // XE2: sid=XE2, alias omitted, has connection + auth + role
        assert!(out.contains("      - sid: XE2\n"));
        assert!(!out.contains("      - sid: XE2\n        alias:"));
        assert!(out.contains("          hostname: dbhost\n"));
        assert!(out.contains("          port: 1522\n"));
        assert!(out.contains("          username: \"xe2user\"\n"));
        assert!(out.contains("          role: sysdba\n"));
    }

    #[test]
    fn test_format_options_none() {
        assert!(format_options(None).is_empty());
    }

    #[test]
    fn test_format_options_zero() {
        assert!(format_options(Some(0)).is_empty());
    }

    #[test]
    fn test_format_options_one() {
        assert!(format_options(Some(1)).is_empty());
    }

    #[test]
    fn test_format_options_two() {
        let out: String = format_options(Some(2)).join("");
        assert!(out.contains("threads: 2"));
    }

    #[test]
    fn test_format_options_eight() {
        let out: String = format_options(Some(8)).join("");
        assert!(out.contains("threads: 8"));
    }

    #[test]
    fn test_format_options_nine_clamped() {
        let out: String = format_options(Some(9)).join("");
        assert!(out.contains("threads: 8"));
        assert!(!out.contains("threads: 9"));
    }
}
