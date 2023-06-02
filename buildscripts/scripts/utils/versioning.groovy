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
        "saas", \
        "cse", \
        "cse.py", \
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
        "saas", \
        "cse", \
        "cse.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cce}"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cce}"]], \
"managed": [\
    "paths_to_be_removed": [\
        "cloud", \
        "cce", \
        "cce.py", \
        "saas", \
        "cse", \
        "cse.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/cce"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/cce"]], \
"cloud": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "saas", \
        "cse", \
        "cse.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"]], \
"saas": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"]], \
]

def branch_name(scm) {
    return env.GERRIT_BRANCH ?: scm.branches[0].name;
}

def safe_branch_name(scm) {
    return branch_name(scm).replaceAll("/", "-");
}

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

def configured_or_overridden_distros(edition, distro_list, use_case="daily") {
    if(distro_list) {
        return distro_list.trim().split(' ');
    }
    docker_image_from_alias("IMAGE_TESTING").inside() {
        dir("${checkout_dir}") {
            return sh(script: """scripts/run-pipenv run \
                  buildscripts/scripts/get_distros.py \
                  --edition "${edition}" \
                  --editions_file "${checkout_dir}/editions.yml" \
                  --use_case "${use_case}" 
            """, returnStdout: true).trim().split();
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

def get_docker_tag(scm, String git_dir=".") {
    return "${safe_branch_name(scm)}-${build_date}-${get_git_hash(git_dir)}";
}

def get_docker_artifact_name(edition, cmk_version) {
    return "check-mk-${edition}-docker-${cmk_version}.tar.gz"
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
                    echo '@mixin graphs_cee {}' > web/htdocs/themes/${THEME}/scss/cee/_graphs_cee.scss
                    echo '@mixin reporting {}' > web/htdocs/themes/${THEME}/scss/cee/_reporting.scss
                    echo '@mixin ntop {}' > web/htdocs/themes/${THEME}/scss/cee/_ntop.scss
                    echo '@mixin license_usage {}' > web/htdocs/themes/${THEME}/scss/cee/_license_usage.scss
                    echo '@mixin managed {}' > web/htdocs/themes/${THEME}/scss/cme/_managed.scss
                """
            }
            break
        case 'cloud':
        case 'saas':
        case 'enterprise':
        case 'free':
            // Workaround since scss does not support conditional includes
            THEME_LIST.each { THEME ->
                sh """
                    echo '@mixin managed {}' > web/htdocs/themes/${THEME}/scss/cme/_managed.scss
                """
            }
            break
    }
}

def patch_demo(EDITION) {
    if (EDITION == 'free') {
        sh '''sed -ri 's/^(FREE[[:space:]]*:?= *).*/\\1'"yes/" defines.make'''
    }
}

def set_version(cmk_version) {
    sh("make NEW_VERSION=${cmk_version} setversion");
}

def configure_checkout_folder(edition, cmk_version) {
    assert edition in REPO_PATCH_RULES: "edition=${edition} not known"
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
    sh """bash -c \"find . \\
        -not \\( -path ./.\\* -prune \\) \\
        \\( ${find_pattern} \\) -prune -print -exec rm -r {} \\;\""""
}

def strip_rc_number_from_version(VERSION) {
    return VERSION.split("-rc")[0]
}

return this
