#!groovy

/// file: versioning.groovy

// library for calculation of version numbers
import groovy.transform.Field

/* groovylint-disable DuplicateListLiteral */
// ATTENTION: The paths added here for removal MUST NOT include slashes, because
//            the command used in the function patch_folders will then fail and
//            paths will not be removed as expected.
@Field
def REPO_PATCH_RULES = [\
"raw": [\
    "paths_to_be_removed": [\
        "enterprise", \
        "cee", \
        "cee.py", \
        "managed", \
        "cme", \
        "cme.py", \
        "cloud", \
        "cce", \
        "cce.py", \
        "saas", \
        "cse", \
        "cse.py", \
        "cmk.cee.dcd.plugins.connectors.connectors_api"],\
    "folders_to_be_created": []], \
"enterprise": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "cloud", \
        "cce", \
        "cce.py", \
        "saas", \
        "cse", \
        "cse.py"], \
    "folders_to_be_created": []], \
"managed": [\
    "paths_to_be_removed": [\
        "saas", \
        "cse", \
        "cse.py"], \
    "folders_to_be_created": []], \
"cloud": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "saas", \
        "cse", \
        "cse.py"], \
    "folders_to_be_created": []], \
"saas": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py"], \
    "folders_to_be_created": []], \
];
/* groovylint-enable DuplicateListLiteral */

def branch_name_is_branch_version(String git_dir=".") {
    dir(git_dir) {
        return cmd_output("make --no-print-directory -f defines.make print-BRANCH_NAME_IS_BRANCH_VERSION") ? true : false;
    }
}

def branch_name() {
    if (params.CUSTOM_GIT_REF) {
        if (branch_name_is_branch_version("${checkout_dir}")) {
            // this is only required as "master" is called "stable branch + 0.1.0"
            // e.g. 2.3.0 (stable) + 0.1.0 = 2.4.0
            return env.GERRIT_BRANCH ?: get_branch_version("${checkout_dir}")
        } else {
            return env.GERRIT_BRANCH ?: "master"
        }
    } else {
        // defined in global-defaults.yml
        return env.GERRIT_BRANCH ?: branches_str;
    }
}

def safe_branch_name() {
    return branch_name().replaceAll("/", "-");
}

/* groovylint-disable DuplicateListLiteral */
def get_cmk_version(branch_name, branch_version, version) {
    return (
      // Experimental builds
      (branch_name.startsWith('sandbox') && version in ['daily', 'git']) ? "${build_date}-${branch_name}" :
      // Daily builds
      (version in ['daily', 'git']) ? "${branch_version}-${build_date}" :
      // else
      "${version}");
}
/* groovylint-enable DuplicateListLiteral */

def get_package_name(base_dir, package_type, edition, cmk_version) {
    print("FN get_package_name(base_dir=${base_dir}, package_type=${package_type}, cmk_version=${cmk_version})");
    dir(base_dir) {
        def file_pattern = (package_type == "deb" ?
            "check-mk-$edition-${cmk_version}_*.${package_type}" :  // FIXME do we need this?
            "check-mk-$edition-${cmk_version}-*.${package_type}");
        return (cmd_output("ls ${file_pattern}")
                ?: error("Found no package matching ${file_pattern} in ${base_dir}"));
    }
}

def get_distros(Map args) {
    def override_distros = args.override.trim() ?: "";

    /// retrieve all available distros if provided distro-list is 'all',
    /// respect provided arguments otherwise
    def edition = override_distros == "all" ? "all" : args.edition.trim() ?: "all";
    def use_case = override_distros == "all" ? "all" : args.use_case.trim() ?: "daily";

    /// return requested list if provided
    if(override_distros && override_distros != "all") {
        return override_distros.replaceAll(',', ' ').split(' ').grep();
    }

    /// read distros from edition.yml otherwise.
    dir("${checkout_dir}") {
        return cmd_output("""python3 \
              buildscripts/scripts/get_distros.py \
              --editions_file "${checkout_dir}/editions.yml" \
              use_cases \
              --edition "${edition}" \
              --use_case "${use_case}"
        """).split().grep();
    }
}

def get_editions() {
    /// read editions from edition.yml
    dir("${checkout_dir}") {
        return cmd_output("""python3 \
              buildscripts/scripts/get_distros.py \
              --editions_file "${checkout_dir}/editions.yml" \
              editions
        """).split().grep();
    }
}

def get_internal_artifacts_pattern() {
    dir("${checkout_dir}") {
        return sh(script: """python3 \
              buildscripts/scripts/get_distros.py \
              --editions_file "editions.yml" \
              internal_build_artifacts \
              --as-codename \
              --as-rsync-exclude-pattern;
        """, returnStdout: true).trim();
    }
}

def get_branch_version(String git_dir=".") {
    dir(git_dir) {
        return (cmd_output("make --no-print-directory -f defines.make print-BRANCH_VERSION").trim()
                ?: raise("Could not read BRANCH_VERSION from defines.make - wrong directory?"));
    }
}

def get_git_hash(String git_dir=".") {
    dir(git_dir) {
        return (cmd_output("git log -n 1 --pretty=format:'%h'")
                ?: raise("Could not read git commit hash - wrong directory?"));
    }
}

distro_package_type = { distro ->
    return (
      (distro ==~ /centos.*|rh.*|sles.*|opensuse.*|alma.*/) ? "rpm" :
      (distro ==~ /cma.*/) ? "cma" :
      (distro ==~ /debian.*|ubuntu.*/) ? "deb" :
      raise("Cannot associate distro ${distro}"));
}

def get_docker_tag(String git_dir=".") {
    return "${safe_branch_name()}-${build_date}-${get_git_hash(git_dir)}";
}

def get_docker_artifact_name(edition, cmk_version) {
    return "check-mk-${edition}-docker-${cmk_version}.tar.gz";
}

def select_docker_tag(build_tag, branch_name) {
    // build_tag > branch_name
    return build_tag ?: "${branch_name}-latest";
}

def print_image_tag() {
    sh("cat /version.txt");
}

def patch_folders(edition) {
    REPO_PATCH_RULES[edition]["paths_to_be_removed"].each{FOLDER ->
        sh("find -name ${FOLDER} -exec rm -rf {} ';' || true");
    }

    REPO_PATCH_RULES[edition]["folders_to_be_created"].each{FOLDER ->
        sh("mkdir -p ${FOLDER}");
    }
}

def set_version(cmk_version) {
    sh("make NEW_VERSION=${cmk_version} setversion");
}

def configure_checkout_folder(edition, cmk_version) {
    assert edition in REPO_PATCH_RULES: "edition=${edition} not known";
    patch_folders(edition);
    set_version(cmk_version);
}

def delete_non_cre_files() {
    non_cre_paths = [
        "non-free",
        "enterprise",
        "managed",
        "cloud",
        "saas",
        "check_mk_enterprise",
        "check_mk_managed",
        "cee",
        "cme",
        "cce",
        "cse",
        "cee.py",
        "cme.py",
        "cce.py",
        "cse.py",
    ]
    find_pattern = non_cre_paths.collect({p -> "-name ${p}"}).join(" -or ")
    // Do not remove files in .git, .venv, .mypy_cache directories
    sh("""
        bash -c \"find . \\
        -not \\( -path ./.\\* -prune \\) \\
        \\( ${find_pattern} \\) -prune -print -exec rm -r {} \\;\"
    """);
}

def strip_rc_number_from_version(VERSION) {
    return VERSION.split("-rc")[0];
}

def is_official_release(version) {
    if (strip_rc_number_from_version(version) ==~ /((\d+.\d+.\d+)(([pib])(\d+))?)/) {
        return true;
    } else {
        return false;
    }
}

def path_hashes(includedRegions) {
    return directory_hashes(includedRegions.collect({entry ->
        // truncate at last occurrence of '/' if available
        def last_slash_pos = entry.lastIndexOf('/');
        last_slash_pos > 0 ? entry.substring(0, last_slash_pos) : entry
    }));
}

return this;
