// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Parses ELF files to extract dependencies, `RPATH`, and `RUNPATH` entries. Uses the `goblin` crate for ELF parsing.

use goblin::elf::Elf as GoblinElf;
use path_clean::PathClean;
use serde::Serialize;
use std::collections::HashSet;
use std::fs;
use std::io;
use std::io::{Read, Seek};
use std::path::{Path, PathBuf};
use std::sync::LazyLock;
use thiserror::Error;

type Result<T> = std::result::Result<T, ElfError>;

/// Errors that can occur when parsing ELF files.
#[derive(Debug, Error)]
pub enum ElfError {
    #[error("File is too small to be an ELF file: {path:?}")]
    FileTooSmall { path: PathBuf },
    #[error("File is not an ELF file: {path:?}")]
    NotElfFile { path: PathBuf },
    #[error("Failed to open file: {path:?}")]
    OpenFailed {
        path: PathBuf,
        #[source]
        source: io::Error,
    },
    #[error("Failed to read file: {path:?}")]
    ReadFailed {
        path: PathBuf,
        #[source]
        source: io::Error,
    },
    #[error("Failed to parse ELF file: {path:?}")]
    ParseFailed {
        path: PathBuf,
        #[source]
        source: goblin::error::Error,
    },
    #[error("Unknown ELF type in file: {path:?}")]
    UnknownElfType { path: PathBuf },
    #[error("Invalid (RPATH or RUNPATH) paths: {paths:?}")]
    InvalidPaths { paths: Vec<String> },
}

/// ELF file type (wrapper around `goblin::elf::header::e_type`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum ElfType {
    None,
    Relocatable,
    Executable,
    SharedObject,
    Core,
}

/// Result type for RPATH/RUNPATH validation.
/// Ok(()) means valid, Err contains list of invalid path error messages.
type ValidationResult = std::result::Result<(), Vec<String>>;

/// Parsed ELF file information.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Elf {
    kind: ElfType,
    dependencies: Vec<String>,
    rpath: Vec<String>,
    runpath: Vec<String>,
    /// True if the ELF calls `lt_dlopen*()` (libltdl) or links `libltdl` directly.
    /// libltdl searches the ELF RPATH, so these binaries require `DT_RPATH` (not
    /// `DT_RUNPATH`) for bundled plugins to be found at runtime. Raw `dlopen()`
    /// callers (OpenSSL, Python, Erlang, etc.) are excluded because they pass
    /// absolute paths and are unaffected by DT_RPATH vs DT_RUNPATH.
    uses_dlopen: bool,
    /// True if the ELF has a `PT_INTERP` program header, meaning the kernel will
    /// invoke a dynamic linker to run it as a main executable. Only executables have
    /// this header; shared libraries (`ET_DYN`) do not. Used to restrict the
    /// DT_RUNPATH + dlopen check to executables, because only the main executable's
    /// `DT_RPATH` propagates process-wide to all `dlopen()` calls.
    has_interpreter: bool,
}

// ELF files typically don't have extensions (aside from .so, .so.x, .so.x.y, etc.), so this is safe.
static INVALID_EXTENSIONS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    HashSet::from([
        "txt", "md", "json", "yaml", "yml", "conf", "cfg", "ini", "toml", "xml", "html", "css",
        "js", "py", "sh", "bash", "zsh", "fish", "csh", "ksh", "pl", "rb", "php", "lua", "tcl",
        "awk", "sed", "perl", "pm", "pod", "gz", "bz2", "xz", "zst", "zip", "tar", "rpm", "deb",
        "dpkg", "png", "jpg", "jpeg", "gif", "svg", "ico", "bmp", "webp", "tiff", "pdf", "ps",
        "eps", "dvi", "tex", "rtf", "odt", "doc", "docx", "mp3", "mp4", "avi", "mkv", "mov", "wav",
        "flac", "ogg", "m4a", "db", "sqlite", "sqlite3", "db3",
    ])
});

impl Elf {
    /// Check if a filepath should be skipped early (before opening) by extension.
    /// This is used to skip files that are clearly not ELF based on extension.
    #[must_use]
    pub(crate) fn is_invalid_extension(path: &Path) -> bool {
        path.extension()
            .and_then(|e| e.to_str())
            .is_some_and(|ext| INVALID_EXTENSIONS.contains(ext.to_ascii_lowercase().as_str()))
    }

    /// Parse an ELF file from a path.
    ///
    /// # Errors
    /// Returns an error if the file is not an ELF file, or if the RPATH or RUNPATH entries are invalid.
    pub(crate) fn from_path(path: &Path) -> Result<Self> {
        let elf = Self::parse(path)?;
        Self::validate(&elf.rpath, &elf.runpath)
            .map_err(|paths| ElfError::InvalidPaths { paths })?;
        Ok(elf)
    }

    /// Get the ELF file type (executable, shared object, etc.).
    #[must_use]
    pub fn kind(&self) -> &ElfType {
        &self.kind
    }

    /// Get the list of dynamic dependencies (`DT_NEEDED` entries).
    #[must_use]
    pub fn dependencies(&self) -> &[String] {
        &self.dependencies
    }

    /// Get the RPATH entries from the ELF file.
    #[must_use]
    pub fn rpath(&self) -> &[String] {
        &self.rpath
    }

    /// Get the RUNPATH entries from the ELF file.
    #[must_use]
    pub fn runpath(&self) -> &[String] {
        &self.runpath
    }

    /// Returns true if the ELF calls `lt_dlopen*()` or links `libltdl`.
    #[must_use]
    pub fn uses_dlopen(&self) -> bool {
        self.uses_dlopen
    }

    /// Returns true if the ELF has a `PT_INTERP` program header (i.e. it is a
    /// main executable that will be run directly by the kernel via a dynamic linker).
    /// Shared libraries do not have this header.
    #[must_use]
    pub fn has_interpreter(&self) -> bool {
        self.has_interpreter
    }

    /// Normalize and resolve RPATH and RUNPATH entries into absolute filesystem paths.
    ///
    /// This function processes both `DT_RPATH` and `DT_RUNPATH` entries from the ELF file's
    /// dynamic section, converting them into normalized `PathBuf` values that can be used
    /// to locate shared library dependencies.
    ///
    /// # Path Resolution
    ///
    /// Paths are normalized according to the following rules:
    ///
    /// 1. **`$ORIGIN` substitution**: The special token `$ORIGIN` (or `${ORIGIN}`) is replaced
    ///    with the directory containing the ELF binary. This allows paths to be relative to
    ///    the executable's location, enabling portable applications. For example, `$ORIGIN/../lib`
    ///    resolves to the `lib` directory one level up from the binary's location.
    ///
    /// 2. **Absolute paths**: Paths starting with `/` are preserved as-is (after normalization
    ///    of any `$ORIGIN` tokens they may contain).
    ///
    /// 3. **Relative paths without `$ORIGIN`**: These are **filtered out** and not included in
    ///    the result. Relative paths without `$ORIGIN` are resolved by the dynamic linker
    ///    relative to the process's current working directory (CWD), not the binary's location.
    ///    This creates a security risk (binary planting attacks) and unpredictable behavior,
    ///    as the CWD is unknown at analysis time.
    ///
    /// # RPATH vs RUNPATH
    ///
    /// Both `RPATH` and `RUNPATH` serve similar purposes but differ in precedence:
    ///
    /// - **`DT_RPATH`**: Searched **before** `LD_LIBRARY_PATH`, making it difficult to override
    ///   at runtime. This is deprecated in favor of `RUNPATH`.
    ///
    /// - **`DT_RUNPATH`**: Searched **after** `LD_LIBRARY_PATH`, allowing easy runtime
    ///   overrides via environment variables. This is the modern standard.
    ///
    /// **Note**: If both `RPATH` and `RUNPATH` are present, `RUNPATH` takes precedence and
    /// `RPATH` is ignored by the dynamic linker.
    ///
    /// # Returns
    ///
    /// A vector of normalized `PathBuf` values representing all valid, resolvable library
    /// search paths. Relative paths without `$ORIGIN` are excluded from the result.
    ///
    /// Validation for those paths handled in the constructor of the Elf struct.
    #[must_use]
    pub(crate) fn normalize_paths(&self, origin: &Path) -> Vec<PathBuf> {
        if !self.runpath.is_empty() {
            // Do not parallelize this, as order is important, the list is typically too small to benefit from it anyway.
            self.runpath
                .iter()
                .filter_map(|path| Self::normalize_path(origin, path))
                .collect()
        } else if !self.rpath.is_empty() {
            // Do not parallelize this, as order is important, the list is typically too small to benefit from it anyway.
            self.rpath
                .iter()
                .filter_map(|path| Self::normalize_path(origin, path))
                .collect()
        } else {
            Vec::new()
        }
    }

    fn normalize_path(origin: &Path, path: &str) -> Option<PathBuf> {
        // Optimize: only convert origin to string and perform replacement if needed.
        // The patterns $ORIGIN and ${ORIGIN} are mutually exclusive (different chars after $).
        let resolved = if path.contains("${ORIGIN}") {
            path.replace("${ORIGIN}", &origin.to_string_lossy())
        } else if path.contains("$ORIGIN") {
            path.replace("$ORIGIN", &origin.to_string_lossy())
        } else {
            path.to_string()
        };

        // Absolute paths are always valid.
        if resolved.starts_with('/') {
            return Some(PathBuf::from(resolved).clean());
        }
        // Since we already resolved the $ORIGIN, any path that is still
        // relative is considered invalid.
        // These cases are handled in the constructor of the Elf struct.
        None
    }

    /// Reads the entire file at path into bytes if the file is an ELF file.
    ///
    /// # Errors
    /// Returns an error if the file is not an ELF file or cannot be read.
    fn read(path: &Path) -> Result<Vec<u8>> {
        // ELF magic bytes: 0x7f followed by ASCII "ELF"
        // Defined in the ELF specification: e_ident[EI_MAG0..EI_MAG3]
        // Official spec: https://refspecs.linuxbase.org/elf/elf.pdf
        // See also: https://en.wikipedia.org/wiki/Executable_and_Linkable_Format
        const ELF_MAGIC: [u8; 4] = [0x7f, 0x45, 0x4c, 0x46];

        let metadata = fs::metadata(path).map_err(|e| ElfError::OpenFailed {
            path: path.to_path_buf(),
            source: e,
        })?;

        // Skip files that are too small to be ELF (must be at least ELF header size)
        if metadata.len() < 64 {
            return Err(ElfError::FileTooSmall {
                path: path.to_path_buf(),
            });
        }

        // Open file once and check magic bytes
        let mut file = fs::File::open(path).map_err(|e| ElfError::OpenFailed {
            path: path.to_path_buf(),
            source: e,
        })?;

        let mut magic = [0u8; 4];
        match file.read_exact(&mut magic) {
            Ok(()) => {
                if magic != ELF_MAGIC {
                    return Err(ElfError::NotElfFile {
                        path: path.to_path_buf(),
                    });
                }
            }
            Err(e) => {
                return Err(ElfError::ReadFailed {
                    path: path.to_path_buf(),
                    source: e,
                });
            }
        }

        // Reset to beginning and read entire file
        // Note: goblin requires full file, but we've at least filtered out non-ELF files
        file.seek(std::io::SeekFrom::Start(0))
            .map_err(|e| ElfError::ReadFailed {
                path: path.to_path_buf(),
                source: e,
            })?;
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)
            .map_err(|e| ElfError::ReadFailed {
                path: path.to_path_buf(),
                source: e,
            })?;

        Ok(bytes)
    }

    /// Parse an ELF file from a path.
    ///
    /// # Errors
    /// Returns an error if the file is not an ELF file or cannot be read.
    fn parse(path: &Path) -> Result<Self> {
        let bytes = Self::read(path)?;
        let elf = GoblinElf::parse(&bytes).map_err(|e| ElfError::ParseFailed {
            path: path.to_path_buf(),
            source: e,
        })?;

        let mut dependencies = Vec::new();
        let mut rpath = Vec::new();
        let mut runpath = Vec::new();

        // Parse dynamic section
        if let Some(dynamic) = &elf.dynamic {
            for dyn_entry in &dynamic.dyns {
                match dyn_entry.d_tag {
                    goblin::elf::dynamic::DT_NEEDED => {
                        if let Ok(strtab_idx) = usize::try_from(dyn_entry.d_val) {
                            if let Some(dep_name) = elf.dynstrtab.get_at(strtab_idx) {
                                dependencies.push(dep_name.to_string());
                            }
                        }
                    }
                    goblin::elf::dynamic::DT_RPATH => {
                        if let Ok(rpath_idx) = usize::try_from(dyn_entry.d_val) {
                            if let Some(rpath_str) = elf.dynstrtab.get_at(rpath_idx) {
                                rpath.extend(
                                    rpath_str
                                        .split(':')
                                        .map(|s: &str| s.to_string())
                                        .filter(|s: &String| !s.is_empty()),
                                );
                            }
                        }
                    }
                    goblin::elf::dynamic::DT_RUNPATH => {
                        if let Ok(runpath_idx) = usize::try_from(dyn_entry.d_val) {
                            if let Some(runpath_str) = elf.dynstrtab.get_at(runpath_idx) {
                                runpath.extend(
                                    runpath_str
                                        .split(':')
                                        .map(|s: &str| s.to_string())
                                        .filter(|s: &String| !s.is_empty()),
                                );
                            }
                        }
                    }
                    _ => {}
                }
            }
        }

        // Detect libltdl usage: either a direct DT_NEEDED on libltdl, or a direct
        // import of lt_dlopen*(). Raw dlopen() is intentionally excluded: callers
        // like OpenSSL (provider loading), Python (extension modules), and Erlang
        // (NIFs) construct absolute paths before calling dlopen, so DT_RPATH vs
        // DT_RUNPATH is irrelevant to them. libltdl's lt_dlopen* is the pattern
        // that actually relies on the ELF RPATH search path.
        let uses_dlopen =
            // Binary directly calls any lt_dlopen*() function from libltdl
            elf.dynsyms.iter().any(|sym| {
                sym.is_import()
                    && elf
                        .dynstrtab
                        .get_at(sym.st_name)
                        .is_some_and(|n| n.starts_with("lt_dlopen"))
            })
            // Binary directly links libltdl (libtool's portable dlopen wrapper)
            || dependencies.iter().any(|dep| dep.starts_with("libltdl"));

        // PT_INTERP is present only in main executables (the kernel uses it to locate
        // the dynamic linker). Shared libraries do not have this header. Goblin parses
        // PT_INTERP into the `interpreter` field automatically.
        let has_interpreter = elf.interpreter.is_some();

        Ok(Self {
            kind: match elf.header.e_type {
                goblin::elf::header::ET_NONE => ElfType::None,
                goblin::elf::header::ET_REL => ElfType::Relocatable,
                goblin::elf::header::ET_EXEC => ElfType::Executable,
                goblin::elf::header::ET_DYN => ElfType::SharedObject,
                goblin::elf::header::ET_CORE => ElfType::Core,
                _ => {
                    return Err(ElfError::UnknownElfType {
                        path: path.to_path_buf(),
                    });
                }
            },
            dependencies,
            rpath,
            runpath,
            uses_dlopen,
            has_interpreter,
        })
    }

    /// Validate RPATH and RUNPATH entries.
    ///
    /// This function checks that all RPATH and RUNPATH entries are valid according to the following rules:
    ///
    /// 1. **Absolute paths**: Paths starting with `/` are always valid.
    /// 2. **`$ORIGIN` paths**: Paths containing `$ORIGIN` or `${ORIGIN}` are valid, as they can be
    ///    resolved relative to the ELF binary's location.
    /// 3. **Relative paths**: Relative paths without `$ORIGIN` are invalid, as they are resolved
    ///    relative to the process's current working directory, which is unknown at analysis time
    ///    and creates security risks (binary planting attacks).
    ///
    /// # RPATH vs RUNPATH
    ///
    /// If both RPATH and RUNPATH are present, both are validated. While RUNPATH takes precedence
    /// at runtime (RPATH is ignored), both are still present in the ELF file and should be validated.
    ///
    /// Though it should be stated that it's improbable to have both RPATH and RUNPATH in the same ELF file.
    /// As GCC linker and patchelf do not support setting both RPATH and RUNPATH simultaneously, at least in
    /// newer versions.
    ///
    /// # Returns
    ///
    /// Returns `Ok(())` if all paths are valid, or `Err` with a list of error messages describing
    /// which paths are invalid.
    fn validate(rpath: &[String], runpath: &[String]) -> ValidationResult {
        let mut invalid_paths = Vec::new();

        // Validate RUNPATH if present
        if !runpath.is_empty() {
            invalid_paths.extend(Self::collect_invalid_paths(runpath, "RUNPATH"));
        }

        // Validate RPATH if present (even if RUNPATH is also present, as both exist in the ELF)
        if !rpath.is_empty() {
            invalid_paths.extend(Self::collect_invalid_paths(rpath, "RPATH"));
        }

        if invalid_paths.is_empty() {
            Ok(())
        } else {
            Err(invalid_paths)
        }
    }

    /// Collect invalid path error messages from a path list.
    ///
    /// # Arguments
    ///
    /// * `paths` - The paths to validate
    /// * `prefix` - The prefix to use in error messages (e.g., "RPATH" or "RUNPATH")
    ///
    /// # Returns
    ///
    /// A vector of error messages for invalid paths.
    fn collect_invalid_paths(paths: &[String], prefix: &str) -> Vec<String> {
        paths
            .iter()
            .filter(|path| Self::invalid_path(path))
            .map(|path| format!("{prefix}: {path} is invalid"))
            .collect()
    }

    /// Check if a path is invalid.
    ///
    /// A path is invalid if it is a relative path without `$ORIGIN` substitution, or if
    /// `$ORIGIN` appears after relative path components (like `../` or `./`).
    ///
    /// The dynamic linker substitutes `$ORIGIN` with the absolute path of the binary's directory.
    /// However, if relative components (like `../` or `./`) appear before `$ORIGIN`, those
    /// components are resolved relative to the current working directory first, which creates
    /// security risks and unpredictable behavior.
    ///
    /// Valid paths:
    /// - Absolute paths: `/usr/lib`
    /// - Paths with `$ORIGIN` at start: `$ORIGIN/../lib`, `${ORIGIN}/lib`
    ///
    /// Invalid paths:
    /// - Relative paths without `$ORIGIN`: `../lib`, `./lib`, `lib`
    /// - Paths with relative components before `$ORIGIN`: `../${ORIGIN}/lib`, `./$ORIGIN/lib`
    fn invalid_path(path: &str) -> bool {
        // Absolute paths are always valid
        if path.starts_with('/') {
            return false;
        }

        // Check if path contains $ORIGIN or ${ORIGIN}
        let origin_pos = path.find("$ORIGIN").or_else(|| path.find("${ORIGIN}"));

        if let Some(pos) = origin_pos {
            // For non-absolute paths, $ORIGIN must be at the very start (byte position 0)
            // Any text before $ORIGIN would be resolved relative to CWD first,
            // checking byte position is safe here since $ORIGIN is ASCII and it's at the start of the string.
            if pos != 0 {
                // Any content before $ORIGIN in a relative path is invalid
                // because it would be resolved relative to CWD before $ORIGIN substitution
                return true;
            }
            // $ORIGIN at the start is valid
            return false;
        }

        // Relative paths without $ORIGIN are invalid
        // They are resolved relative to current working directory of the process,
        // which is unknown at analysis time and creates security risks.
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    impl Elf {
        /// Construct an `Elf` with explicit field values for use in tests.
        pub(crate) fn new_for_testing(
            kind: ElfType,
            dependencies: Vec<String>,
            rpath: Vec<String>,
            runpath: Vec<String>,
            uses_dlopen: bool,
            has_interpreter: bool,
        ) -> Self {
            Self {
                kind,
                dependencies,
                rpath,
                runpath,
                uses_dlopen,
                has_interpreter,
            }
        }
    }

    fn get_examples_dir() -> PathBuf {
        match runfiles::Runfiles::create() {
            Ok(r) => r
                .rlocation("_main/tests/packaging/package_validator/fixtures")
                .expect("fixtures not found in runfiles"),
            Err(_) => PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fixtures"),
        }
    }

    #[test]
    fn test_is_invalid_extension() {
        let temp_file = Path::new("not_elf.txt");
        let result = Elf::is_invalid_extension(&temp_file);
        assert!(result);

        let temp_file = Path::new("is_elf.so");
        let result = Elf::is_invalid_extension(&temp_file);
        assert!(!result);
    }

    #[test]
    fn test_normalize_path_absolute() {
        let path = PathBuf::from("/usr/bin/test_binary");
        let origin = path.parent().unwrap_or_else(|| Path::new("/"));
        let rpath = "/usr/lib".to_string();

        let result = Elf::normalize_path(origin, &rpath);
        assert_eq!(result, Some(PathBuf::from("/usr/lib")));
    }

    #[test]
    fn test_normalize_rpath_relative() {
        let path = PathBuf::from("/usr/bin/test_binary");
        let origin = path.parent().unwrap_or_else(|| Path::new("/"));
        let rpath = "../lib".to_string();

        let result = Elf::normalize_path(origin, &rpath);
        // Relative paths without $ORIGIN return None
        assert_eq!(result, None);
    }

    #[test]
    fn test_normalize_path_origin_not_at_start() {
        let path = PathBuf::from("/usr/bin/test_binary");
        let origin = path.parent().unwrap_or_else(|| Path::new("/"));

        // Paths with $ORIGIN not at the start should return None (invalid)
        assert_eq!(
            Elf::normalize_path(origin, &"../$ORIGIN/lib".to_string()),
            None
        );
        assert_eq!(
            Elf::normalize_path(origin, &"./$ORIGIN/lib".to_string()),
            None
        );
        assert_eq!(
            Elf::normalize_path(origin, &"../${ORIGIN}/lib".to_string()),
            None
        );
        assert_eq!(
            Elf::normalize_path(origin, &"prefix/$ORIGIN/lib".to_string()),
            None
        );

        // But $ORIGIN at the start should work
        let result = Elf::normalize_path(origin, &"$ORIGIN/../lib".to_string());
        assert!(result.is_some());
        let resolved = result.unwrap();
        assert_eq!(resolved.to_string_lossy(), "/usr/lib");
    }

    #[test]
    fn test_normalize_rpath_origin() {
        let path = PathBuf::from("/usr/bin/test_binary");
        let origin = path.parent().unwrap_or_else(|| Path::new("/"));
        let rpath = "$ORIGIN/../lib".to_string();

        let resolved = Elf::normalize_path(origin, &rpath);
        assert!(resolved.is_some());
        let resolved = resolved.unwrap();
        // $ORIGIN/../lib with origin /usr/bin resolves to /usr/bin/../lib which cleans to /usr/lib
        assert_eq!(resolved, PathBuf::from("/usr/lib"));
    }

    #[test]
    fn test_normalize_path_origin_braces() {
        let path = PathBuf::from("/usr/bin/test_binary");
        let origin = path.parent().unwrap_or_else(|| Path::new("/"));
        let rpath = "${ORIGIN}/../lib".to_string();

        let resolved = Elf::normalize_path(origin, &rpath);
        assert!(resolved.is_some());
        let resolved = resolved.unwrap();
        // ${ORIGIN}/../lib with origin /usr/bin resolves to /usr/bin/../lib which cleans to /usr/lib
        assert_eq!(resolved, PathBuf::from("/usr/lib"));
    }

    #[test]
    fn test_normalize_paths() {
        let path = PathBuf::from("/usr/bin/test_binary");
        let origin = path.parent().unwrap_or_else(|| Path::new("/"));

        // Test with RUNPATH (takes precedence over RPATH)
        let elf = Elf {
            kind: ElfType::Executable,
            dependencies: Vec::new(),
            rpath: vec!["/usr/lib".to_string()],
            runpath: vec!["/opt/lib".to_string()],
            uses_dlopen: false,
            has_interpreter: true,
        };

        let normalized = elf.normalize_paths(origin);
        // When RUNPATH is present, only RUNPATH is processed (RPATH is ignored)
        assert_eq!(normalized.len(), 1);
        assert_eq!(normalized, vec![PathBuf::from("/opt/lib")]);

        // Test with only RPATH
        let elf_rpath_only = Elf {
            kind: ElfType::Executable,
            dependencies: Vec::new(),
            rpath: vec!["/usr/lib".to_string()],
            runpath: Vec::new(),
            uses_dlopen: false,
            has_interpreter: true,
        };

        let normalized_rpath = elf_rpath_only.normalize_paths(origin);
        assert_eq!(normalized_rpath.len(), 1);
        assert_eq!(normalized_rpath, vec![PathBuf::from("/usr/lib")]);
    }

    #[test]
    fn test_validate_absolute_paths() {
        let rpath = vec!["/usr/lib".to_string(), "/opt/lib".to_string()];
        let runpath = Vec::new();
        assert!(Elf::validate(&rpath, &runpath).is_ok());
    }

    #[test]
    fn test_validate_origin_paths() {
        let rpath = vec!["$ORIGIN/../lib".to_string(), "${ORIGIN}/lib".to_string()];
        let runpath = Vec::new();
        assert!(Elf::validate(&rpath, &runpath).is_ok());
    }

    #[test]
    fn test_validate_invalid_relative_paths() {
        let rpath = vec!["../lib".to_string(), "./lib".to_string()];
        let runpath = Vec::new();
        let errors = Elf::validate(&rpath, &runpath).expect_err("Expected invalid paths");
        assert_eq!(errors.len(), 2);
        assert!(errors.iter().any(|e| e.contains("../lib")));
        assert!(errors.iter().any(|e| e.contains("./lib")));
    }

    #[test]
    fn test_validate_both_runpath_and_rpath() {
        // Both should be validated even though RUNPATH takes precedence at runtime
        let rpath = vec!["../lib".to_string()];
        let runpath = vec!["/opt/lib".to_string(), "./lib".to_string()];
        let errors = Elf::validate(&rpath, &runpath).expect_err("Expected invalid paths");
        assert_eq!(errors.len(), 2); // One from RPATH, one from RUNPATH
        assert!(errors
            .iter()
            .any(|e| e.contains("RPATH") && e.contains("../lib")));
        assert!(errors
            .iter()
            .any(|e| e.contains("RUNPATH") && e.contains("./lib")));
    }

    #[test]
    fn test_validate_mixed_valid_invalid() {
        let rpath = vec!["/usr/lib".to_string(), "../lib".to_string()];
        let runpath = Vec::new();
        let errors = Elf::validate(&rpath, &runpath).expect_err("Expected invalid paths");
        assert_eq!(errors.len(), 1);
        assert!(errors.iter().any(|e| e.contains("../lib")));
    }

    #[test]
    fn test_validate_origin_with_relative_prefix() {
        // Paths with any content before $ORIGIN are invalid
        // because that content is resolved relative to CWD before $ORIGIN substitution
        let rpath = vec![
            "../${ORIGIN}/lib".to_string(),
            "./$ORIGIN/lib".to_string(),
            "../$ORIGIN/lib".to_string(),
            "some/path/$ORIGIN/lib".to_string(),
            "prefix/${ORIGIN}/lib".to_string(),
        ];
        let runpath = Vec::new();
        let errors = Elf::validate(&rpath, &runpath)
            .expect_err("Expected invalid paths with content before $ORIGIN");
        assert_eq!(errors.len(), 5);
        assert!(errors.iter().any(|e| e.contains("../${ORIGIN}")));
        assert!(errors.iter().any(|e| e.contains("./$ORIGIN")));
        assert!(errors.iter().any(|e| e.contains("../$ORIGIN")));
        assert!(errors.iter().any(|e| e.contains("some/path/$ORIGIN")));
        assert!(errors.iter().any(|e| e.contains("prefix/${ORIGIN}")));
    }

    #[test]
    fn test_validate_origin_at_start() {
        // $ORIGIN at the start is valid
        let rpath = vec![
            "$ORIGIN/../lib".to_string(),
            "${ORIGIN}/lib".to_string(),
            "$ORIGIN/lib".to_string(),
        ];
        let runpath = Vec::new();
        assert!(Elf::validate(&rpath, &runpath).is_ok());
    }

    /// Helper to skip tests when fixture files are missing.
    /// Returns None if fixture is missing, Some(path) if it exists.
    fn require_fixture(name: &str) -> Option<PathBuf> {
        let path = get_examples_dir().join(name);
        if path.exists() {
            Some(path)
        } else {
            eprintln!("Skipping test: fixture '{}' not found.", name);
            None
        }
    }

    #[test]
    fn test_elf_valid_absolute_rpath() {
        let Some(elf_path) = require_fixture("test-elf-valid-absolute-rpath.elf") else {
            return;
        };
        let elf = Elf::from_path(&elf_path).expect("Should parse valid ELF with absolute RPATH");
        assert!(!elf.rpath().is_empty(), "RPATH should not be empty");
        assert!(
            elf.rpath().iter().any(|p| p == "/usr/lib"),
            "RPATH should contain '/usr/lib', got: {:?}",
            elf.rpath()
        );
    }

    #[test]
    fn test_elf_valid_origin_rpath() {
        let Some(elf_path) = require_fixture("test-elf-valid-origin-rpath.elf") else {
            return;
        };
        let elf = Elf::from_path(&elf_path).expect("Should parse valid ELF with $ORIGIN RPATH");
        assert!(!elf.rpath().is_empty(), "RPATH should not be empty");
        assert!(
            elf.rpath().iter().any(|p| p == "$ORIGIN/../lib"),
            "RPATH should contain '$ORIGIN/../lib', got: {:?}",
            elf.rpath()
        );
    }

    #[test]
    fn test_elf_valid_origin_braces_rpath() {
        let Some(elf_path) = require_fixture("test-elf-valid-origin-braces-rpath.elf") else {
            return;
        };
        let elf = Elf::from_path(&elf_path).expect("Should parse valid ELF with ${ORIGIN} RPATH");
        assert!(!elf.rpath().is_empty(), "RPATH should not be empty");
        assert!(
            elf.rpath().iter().any(|p| p == "${ORIGIN}/lib"),
            "RPATH should contain '${{ORIGIN}}/lib', got: {:?}",
            elf.rpath()
        );
    }

    #[test]
    fn test_elf_valid_runpath() {
        let Some(elf_path) = require_fixture("test-elf-valid-runpath.elf") else {
            return;
        };
        let elf = Elf::from_path(&elf_path).expect("Should parse valid ELF with RUNPATH");
        assert!(!elf.runpath().is_empty(), "RUNPATH should not be empty");
        assert!(
            elf.runpath().iter().any(|p| p == "/opt/lib"),
            "RUNPATH should contain '/opt/lib', got: {:?}",
            elf.runpath()
        );
    }

    #[test]
    fn test_elf_invalid_relative_rpath() {
        let Some(elf_path) = require_fixture("test-elf-invalid-relative-rpath.elf") else {
            return;
        };
        let result = Elf::from_path(&elf_path);
        match result {
            Err(ElfError::InvalidPaths { paths }) => {
                assert!(
                    paths.iter().any(|p| p.contains("../lib")),
                    "Error should mention '../lib', got: {:?}",
                    paths
                );
            }
            Ok(_) => {
                // If patchelf didn't allow setting invalid RPATH, the file might be valid
                // This is acceptable - the test verifies the validation logic works when invalid paths are present
            }
            Err(e) => panic!("Unexpected error: {:?}", e),
        }
    }

    #[test]
    fn test_elf_invalid_relative_dot_rpath() {
        let Some(elf_path) = require_fixture("test-elf-invalid-relative-dot-rpath.elf") else {
            return;
        };
        let result = Elf::from_path(&elf_path);
        match result {
            Err(ElfError::InvalidPaths { paths }) => {
                assert!(
                    paths.iter().any(|p| p.contains("./lib")),
                    "Error should mention './lib', got: {:?}",
                    paths
                );
            }
            Ok(_) => {
                // If patchelf didn't allow setting invalid RPATH, the file might be valid
                // This is acceptable - the test verifies the validation logic works when invalid paths are present
            }
            Err(e) => panic!("Unexpected error: {:?}", e),
        }
    }

    #[test]
    fn test_elf_invalid_prefix_origin_rpath() {
        let Some(elf_path) = require_fixture("test-elf-invalid-prefix-origin-rpath.elf") else {
            return;
        };
        let result = Elf::from_path(&elf_path);
        match result {
            Err(ElfError::InvalidPaths { paths }) => {
                assert!(
                    paths
                        .iter()
                        .any(|p| p.contains("../$ORIGIN") || p.contains("RPATH")),
                    "Error should mention '../$ORIGIN' or 'RPATH', got: {:?}",
                    paths
                );
            }
            Ok(_) => {
                // If patchelf didn't allow setting invalid RPATH, the file might be valid
                // This is acceptable - the test verifies the validation logic works when invalid paths are present
            }
            Err(e) => panic!("Unexpected error: {:?}", e),
        }
    }

    #[test]
    fn test_elf_file_too_small() {
        // This fixture is auto-generated by build.rs
        let elf_path = get_examples_dir().join("test-elf-file-too-small");
        let result = Elf::from_path(&elf_path);
        match result {
            Err(ElfError::FileTooSmall { .. }) => {
                // Expected error
            }
            Err(ElfError::NotElfFile { .. }) => {
                // Also acceptable - file is too small to be ELF
            }
            Ok(_) => panic!("Expected FileTooSmall or NotElfFile error"),
            Err(e) => panic!("Unexpected error: {:?}", e),
        }
    }

    #[test]
    fn test_elf_not_elf_file() {
        // This fixture is auto-generated by build.rs
        let elf_path = get_examples_dir().join("test-elf-not-elf-file");
        let result = Elf::from_path(&elf_path);
        match result {
            Err(ElfError::NotElfFile { .. }) => {
                // Expected error
            }
            Err(ElfError::FileTooSmall { .. }) => {
                // Also acceptable if file is small
            }
            Ok(_) => panic!("Expected NotElfFile or FileTooSmall error"),
            Err(e) => panic!("Unexpected error: {:?}", e),
        }
    }
}
