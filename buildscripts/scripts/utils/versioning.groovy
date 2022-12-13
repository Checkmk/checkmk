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
        "plus", \
        "cpe", \
        "cpe.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cee,cpe}"],\
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cee,cpe}"]], \
"enterprise": [\
    "paths_to_be_removed": [\
        "managed", \
        "cme", \
        "cme.py", \
        "plus", \
        "cpe", \
        "cpe.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cpe}"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cpe}"]], \
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
        "plus", \
        "cpe", \
        "cpe.py", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/cpe"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/cpe"]], \
"plus": [\
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

def configured_or_overridden_distros(edition, distro_list, distro_key="DISTROS") {
    if(distro_list) {
        return distro_list.trim().split(' ');
    }
    try {
        return load_json("${checkout_dir}/editions.json")[edition][distro_key];
    } catch (Exception exc) {
        raise("Could not find editions.json:'${edition}':'{distro_key}'");
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
        case 'plus':
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
        sh 'mv omd/packages/nagios/{9999-demo-version.dif,patches/9999-demo-version.dif}'
        sh '''sed -i 's/#ifdef DEMOVERSION/#if 1/g' enterprise/core/src/{TrialManager.h,test/test_TrialManager.cc}'''
        sh '''sed -i 's/#ifdef DEMOVERSION/#if 1/g' livestatus/src/TableStatus.cc'''
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
        "plus",
        "check_mk_enterprise",
        "check_mk_managed",
        "cee",
        "cme",
        "cpe",
        "cee.py",
        "cme.py",
        "cpe.py",
    ]
    find_pattern = non_cre_paths.collect({p -> "-name ${p}"}).join(" -or ")
    sh "bash -c \"find . \\( ${find_pattern} \\) -prune -print -exec rm -r {} \\;\""
}

return this
