// library for calculation fo v3ersion numbers
import java.text.SimpleDateFormat

def get_branch(scm) {
    def BRANCH = scm.branches[0].name.replaceAll("/","-")
    return BRANCH
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

return this
