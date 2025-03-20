#!groovy

/// file: versioning.groovy

// library for calculation of version numbers
import groovy.transform.Field

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
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cee,cce}"],\
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cee,cce}"]], \
"enterprise": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "cloud", \
        "cce", \
        "cce.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cce}"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cce}"]], \
"free": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"]], \
"managed": [\
    "paths_to_be_removed": [\
        "cloud", \
        "cce", \
        "cce.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/cce"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/cce"]], \
"cloud": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"]], \
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
def get_cmk_version(branch, version) {
    return (
      // Regular daily build of master branch
      (branch == 'master' && version == 'daily') ? "${build_date}" :
      // Experimental builds
      (branch.startsWith('sandbox') && version == 'daily') ? "${build_date}-${branch}" :
      // version branch dailies (e.g. 1.6.0)
      (version == 'daily') ? "${branch}-${build_date}" :
      // else
      "${version}");
}

def get_cmk_version_deploy(branch_name, branch_version, version) {
    return (
      // Experimental builds
      (branch_name.startsWith('sandbox') && version in ['daily', 'git']) ? "${build_date}-${branch_name}" :
      // Daily builds
      (version in ['daily', 'git']) ? "${branch_version}-${build_date}" :
      // else
      "${version}");
}
/* groovylint-enable DuplicateListLiteral */

def configured_or_overridden_distros(edition, distros, use_case="daily") {
    def distro_list = (distros ?: "").replaceAll(',', ' ').split(' ').grep();
    if(distro_list) {
        return distro_list;
    }
    docker_image_from_alias("IMAGE_TESTING").inside() {
        dir("${checkout_dir}") {
            return sh(script: """scripts/run-pipenv run \
                  buildscripts/scripts/get_distros.py \
                  --editions_file "${checkout_dir}/editions.yml" \
                  use_cases \
                  --edition "${edition}" \
                  --use_case "${use_case}"
            """, returnStdout: true).trim().split();
        }
    }
}

def get_editions() {
    /// read editions from edition.yml
    docker_image_from_alias("IMAGE_TESTING").inside() {
        dir("${checkout_dir}") {
            return cmd_output("""scripts/run-pipenv run \
                  buildscripts/scripts/get_distros.py \
                  --editions_file "${checkout_dir}/editions.yml" \
                  editions
            """).split().grep();
        }
    }
}

def get_internal_distros_pattern() {
    docker_image_from_alias("IMAGE_TESTING").inside() {
        dir("${checkout_dir}") {
            return sh(script: """scripts/run-pipenv run \
                  buildscripts/scripts/get_distros.py \
                  --editions_file "editions.yml" \
                  internal_distros \
                  --as-codename \
                  --as-rsync-exclude-pattern;
            """, returnStdout: true).trim();
        }
    }
}

def get_branch_version(String git_dir=".") {
    dir(git_dir) {
        return (cmd_output("grep -m 1 BRANCH_VERSION defines.make | sed 's/^.*= //g'")
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

def patch_themes(EDITION) {
    def THEME_LIST = ["facelift", "modern-dark"]
    switch(EDITION) {
        case 'raw':
            // Workaround since scss does not support conditional includes
            THEME_LIST.each { THEME ->
                sh """
                    echo '@mixin graphs_cee {}' > web/htdocs/themes/${THEME}/scss/cee/_graphs_cee.scss
                    echo '@mixin reporting {}' > web/htdocs/themes/${THEME}/scss/cee/_reporting.scss
                    echo '@mixin ntop {}' > web/htdocs/themes/${THEME}/scss/cee/_ntop.scss
                    echo '@mixin license_usage {}' > web/htdocs/themes/${THEME}/scss/cee/_license_usage.scss
                    echo '@mixin managed {}' > web/htdocs/themes/${THEME}/scss/cme/_managed.scss
                """
            }
            break
        case 'cloud':
        case 'enterprise':
        case 'free':
            // Workaround since scss does not support conditional includes
            THEME_LIST.each { THEME ->
                sh("""
                    echo '@mixin managed {}' > web/htdocs/themes/${THEME}/scss/cme/_managed.scss
                """);
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
        "check_mk_enterprise",
        "check_mk_managed",
        "cee",
        "cme",
        "cce",
        "cee.py",
        "cme.py",
        "cce.py",
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
