#!groovy

/// file: create-dependency-update-changeset.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();
    def repo_name = "check_mk"

    def reviewers = ["maximilian.wirtz", "hannes.rantzsch"]
    def url_reviewers = reviewers.collect { "reviewer=$it" }.join(",")

    dir("${checkout_dir}") {
        stage("Relock deps") {
            inside_container {
                sh("python3 scripts/update_python_libs.py")
            }
        }

        stage("Create commit"){
            if(sh(returnStdout: true, script: "git status --porcelain --untracked-files=no") == "") {
                echo "No changes, no commit ;-)"
                return
            }

            sh("""
                git status
                git add -u

                # Set the author, setting it via `git commit --author ...` was not sufficient, see `git show --format=fuller`...
                git config user.name svc-dev-sec-codebot
                git config user.email security+svc-dev-sec-codebot@checkmk.com

                # Install Change-Id hook
                curl -Lo .git/hooks/commit-msg https://review.lan.tribe29.com/tools/hooks/commit-msg
                chmod u+x .git/hooks/commit-msg

                git commit -F .git-commit-msg
                git log
                # it was checked out with jenkins@...
                git remote add update_remote ssh://svc-dev-sec-codebot@review.lan.tribe29.com/${repo_name}
            """)
            // when not setting the port in the GIT_SSH_COMMAND I got an error that setting the port in the URL does not work with ssh simple...
            withCredentials([sshUserPrivateKey(credentialsId: 'svc-dev-sec-codebot-ssh', keyFileVariable: 'SSH_KEY', usernameVariable: "USER")]) {
                withEnv(['GIT_SSH_COMMAND=ssh -i ${SSH_KEY} -p 29418']) {
                    sh("git push update_remote HEAD:refs/for/${safe_branch_name}%hashtag=dependency_update,${url_reviewers}")
                }
            }
        }
    }
}

return this;
