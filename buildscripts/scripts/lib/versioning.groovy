// library for calculation of version numbers
import java.text.SimpleDateFormat
import groovy.transform.Field

// TODO: Add the rules to exclude mkp-able folder regarding ntop integration under "managed"
@Field
def REPO_PATCH_RULES = [\
"raw": [\
    "folders_to_be_removed": [\
        "enterprise", \
        "managed", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cee}"],\
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/{cme,cee}"]], \
"enterprise": [\
    "folders_to_be_removed": [\
        "managed", \
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"], \
    "folders_to_be_created": [\
        "web/htdocs/themes/{facelift,modern-dark}/scss/cme"]], \
"managed": [\
    "folders_to_be_removed": [],\
    "folders_to_be_created": []] \
]

def get_branch(scm) {
    def BRANCH = scm.branches[0].name.replaceAll("/","-")
    return BRANCH
}

def get_cmk_version(scm, VERSION) {
    def BRANCH = get_branch(scm)
    def DATE_FORMAT = new SimpleDateFormat("yyyy.MM.dd")
    def DATE = new Date()

    if (BRANCH == 'master' && VERSION == 'daily') {
        return DATE_FORMAT.format(DATE) // Regular daily build of master branch
    } else if (BRANCH.startsWith('sandbox') && VERSION == 'daily') {
        return DATE_FORMAT.format(DATE) + '-' + BRANCH // Experimental builds
    } else if (VERSION == 'daily') {
        return BRANCH + '-' + DATE_FORMAT.format(DATE) // version branch dailies (e.g. 1.6.0)
    } else {
        return VERSION
    }
}

def get_branch_version() {
    return sh(returnStdout: true, script: "grep -m 1 BRANCH_VERSION defines.make | sed 's/^.*= //g'").trim()
}

def get_git_hash() {
    def HASH = sh(returnStdout: true, script: "git log -n 1 --pretty=format:'%h'").trim()
    return HASH
}

def get_date() {
    def DATE_FORMAT = new SimpleDateFormat("yyyy.MM.dd")
    def DATE = new Date()
    return DATE_FORMAT.format(DATE)
}

def get_docker_tag(scm) {
    def BRANCH = get_branch(scm)
    def DATE = get_date()
    def HASH = get_git_hash()
    return BRANCH + '-' + DATE + '-' + HASH
}

def select_docker_tag(BRANCH, BUILD_TAG, FOLDER_TAG) {
    // Empty folder prperties are null pointers
    // Other emput string variables have the value ''
    if (BUILD_TAG != '') {
        return BUILD_TAG
    }
    if (FOLDER_TAG != null) {
        return FOLDER_TAG
    }
    return BRANCH + '-latest'
}

def print_image_tag() {
    sh "cat /version.txt"
}

def patch_folders(EDITION) {
    REPO_PATCH_RULES[EDITION]["folders_to_be_removed"].each{FOLDER ->
            sh """
                rm -rf ${FOLDER}
            """ }

    REPO_PATCH_RULES[EDITION]["folders_to_be_created"].each{FOLDER ->
            sh """
                mkdir -p ${FOLDER}
            """ }
}

def patch_themes(EDITION) {
    def THEME_LIST = ["facelift", "modern-dark"]
    switch(EDITION) {
        case 'raw':
            // Workaround since scss does not support conditional includes
            THEME_LIST.each { THEME ->
                sh """
                    echo '@mixin graphs {}' > web/htdocs/themes/${THEME}/scss/cee/_graphs.scss
                    echo '@mixin reporting {}' > web/htdocs/themes/${THEME}/scss/cee/_reporting.scss
                    echo '@mixin ntop {}' > web/htdocs/themes/${THEME}/scss/cee/_ntop.scss
                    echo '@mixin managed {}' > web/htdocs/themes/${THEME}/scss/cme/_managed.scss
                """
            }
            break
        case 'enterprise':
            // Workaround since scss does not support conditional includes
            THEME_LIST.each { THEME ->
                sh """
                    echo '@mixin managed {}' > web/htdocs/themes/${THEME}/scss/cme/_managed.scss
                """
            }
            break
    }
}

def patch_demo(DEMO) {
    if (DEMO == 'yes') {
        sh '''sed -ri 's/^(DEMO_SUFFIX[[:space:]]*:?= *).*/\\1'" .demo/" defines.make'''
        sh 'mv omd/packages/nagios/{9999-demo-version.dif,patches/9999-demo-version.dif}'
        sh '''sed -i 's/#ifdef DEMOVERSION/#if 1/g' enterprise/core/src/{Core,World}.cc'''
    }
}

def set_version(CMK_VERS) {
    sh "make NEW_VERSION=${CMK_VERS} setversion"
}

def patch_git_after_checkout(EDITION, DEMO, CMK_VERS) {
    patch_folders(EDITION)
    patch_themes(EDITION)
    patch_demo(DEMO)
    set_version(CMK_VERS)
}

return this
