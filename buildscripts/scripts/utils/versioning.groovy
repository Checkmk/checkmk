#!groovy

/// file: versioning.groovy

// library for calculation of version numbers
import groovy.transform.Field

/* groovylint-disable DuplicateListLiteral */
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
        "packages/cmk-frontend/src/themes/{facelift,modern-dark}/scss/{cme,cee,cce}"],\
    "folders_to_be_created": [\
        "packages/cmk-frontend/src/themes/{facelift,modern-dark}/scss/{cme,cee,cce}"]], \
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
        "cse.py", \
        "packages/cmk-frontend/src/themes/{facelift,modern-dark}/scss/{cme,cce}"], \
    "folders_to_be_created": [\
        "packages/cmk-frontend/src/themes/{facelift,modern-dark}/scss/{cme,cce}"]], \
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
        "cse.py", \
        "packages/cmk-frontend/src/themes/{facelift,modern-dark}/scss/cme"], \
    "folders_to_be_created": [\
        "packages/cmk-frontend/src/themes/{facelift,modern-dark}/scss/cme"]], \
"saas": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "packages/cmk-frontend/src/themes/{facelift,modern-dark}/scss/cme"], \
    "folders_to_be_created": [\
        "packages/cmk-frontend/src/themes/{facelift,modern-dark}/scss/cme"]], \
];
/* groovylint-enable DuplicateListLiteral */

def branch_name(scm) {
    return env.GERRIT_BRANCH ?: scm.branches[0].name;
}

def safe_branch_name(scm) {
    return branch_name(scm).replaceAll("/", "-");
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

def get_docker_tag(scm, String git_dir=".") {
    return "${safe_branch_name(scm)}-${build_date}-${get_git_hash(git_dir)}";
}

def get_docker_artifact_name(edition, cmk_version) {
    return "check-mk-${edition}-docker-${cmk_version}.tar.gz";
}

def select_docker_tag(BRANCH, BUILD_TAG, FOLDER_TAG) {
    return BUILD_TAG ?: FOLDER_TAG ?: "${BRANCH}-latest";
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

def patch_themes(EDITION) {
    def THEME_LIST = ["facelift", "modern-dark"]
    switch(EDITION) {
        case 'raw':
            // Workaround since scss does not support conditional includes
            THEME_LIST.each { THEME ->
                sh """
                    echo '@mixin graphs_cee {\n}' > packages/cmk-frontend/src/themes/${THEME}/scss/cee/_graphs_cee.scss
                    echo '@mixin reporting {\n}' > packages/cmk-frontend/src/themes/${THEME}/scss/cee/_reporting.scss
                    echo '@mixin ntop {\n}' > packages/cmk-frontend/src/themes/${THEME}/scss/cee/_ntop.scss
                    echo '@mixin license_usage {\n}' > packages/cmk-frontend/src/themes/${THEME}/scss/cee/_license_usage.scss
                    echo '@mixin robotmk {\n}' > packages/cmk-frontend/src/themes/${THEME}/scss/cee/_robotmk.scss
                """
            }
            break
    }
}

def patch_demo(EDITION) {
    if (EDITION == 'free') {
        sh('''sed -ri 's/^(FREE[[:space:]]*:?= *).*/\\1'"yes/" defines.make''');
    }
}

def set_version(cmk_version) {
    sh("make NEW_VERSION=${cmk_version} setversion");
}

def configure_checkout_folder(edition, cmk_version) {
    assert edition in REPO_PATCH_RULES: "edition=${edition} not known";
    patch_folders(edition);
    patch_themes(edition);
    patch_demo(edition);
    set_version(cmk_version);
}

def delete_non_cre_files() {
    non_cre_paths = [
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

return this;
