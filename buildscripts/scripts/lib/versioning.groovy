// library for calculation of version numbers
import java.text.SimpleDateFormat

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

def patch_themes(EDITION) {
    def THEME_LIST = ["classic", "facelift", "modern-dark"]
    switch(EDITION) {
        case 'raw':
            sh 'rm -rf enterprise managed'
            // Workaround since scss does not support conditional includes
            THEME_LIST.each { THEME ->
                sh """
                    rm -rf web/htdocs/themes/${THEME}/scss/{cme,cee}
                    mkdir -p web/htdocs/themes/${THEME}/scss/{cme,cee}
                    echo '@mixin graphs {}' > web/htdocs/themes/${THEME}/scss/cee/_graphs.scss
                    echo '@mixin reporting {}' > web/htdocs/themes/${THEME}/scss/cee/_reporting.scss
                    echo '@mixin managed {}' > web/htdocs/themes/${THEME}/scss/cme/_managed.scss
                """
            }
            break
        case 'enterprise':
            sh 'rm -rf  managed'
            // Workaround since scss does not support conditional includes
            THEME_LIST.each { THEME ->
                sh """
                    rm -rf web/htdocs/themes/${THEME}/scss/cme
                    mkdir -p web/htdocs/themes/${THEME}/scss/cme
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
    patch_themes(EDITION)
    patch_demo(DEMO)
    set_version(CMK_VERS)
}

return this
