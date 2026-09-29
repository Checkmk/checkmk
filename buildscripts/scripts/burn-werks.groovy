#!groovy

/// file: burn-werks.groovy

/// Burns the release version into all werks without a version after a release
/// and pushes the result to review on the corresponding version branch.
/// Has to be executed after the final release tag has been created,
/// with CUSTOM_GIT_REF set to that tag, e.g. v2.4.0p12

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    check_job_parameters([
        ["CUSTOM_GIT_REF", true],
        "DRY_RUN",
        ["REVIEWER", true],
    ]);

    def version_tag = params.CUSTOM_GIT_REF.trim();
    def dry_run = params.DRY_RUN;
    def reviewer = params.REVIEWER.trim();

    // e.g. v2.4.0, v2.4.0p12, v2.5.0b3, v2.4.0p12+security
    def version = version_tag.startsWith("v") ? version_tag.substring(1) : "";
    def version_without_meta_data = version.replaceFirst(/\+security$/, "");
    if (!versioning.is_official_release(version_without_meta_data)
        || versioning.strip_rc_number_from_version(version_without_meta_data) != version_without_meta_data) {
        raise("CUSTOM_GIT_REF '${version_tag}' is not a final Checkmk release tag, e.g. 'v2.4.0p12'");
    }
    def commit_message = "Burn werk version after release of ${version}";
    def push_options = ["hashtag=burn-werks", "r=${reviewer}"];

    print(
        """
        |===== CONFIGURATION ===============================
        |version_tag:.............. │${version_tag}│
        |version:.................. │${version}│
        |dry_run:.................. │${dry_run}│
        |reviewer:................. │${reviewer}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    dir("${checkout_dir}") {
        // Everything runs in the branch specific k8s container or docker image (the job exists per branch),
        // never on the plain node
        inside_container() {
            def branch_version = "";
            stage("Burn werks") {
                branch_version = versioning.get_branch_version(checkout_dir);
                sh("bazel run //packages/cmk-werks:utils-bin -- burn \$PWD");
            }
            print("Version branch of ${version_tag}: ${branch_version}");

            // burning must only touch the werks, anything else (e.g. MODULE.bazel.lock) must not be pushed
            def changes_outside_werks = sh(
                script: "git status --porcelain --untracked-files=no -- . ':(exclude).werks'",
                returnStdout: true,
            ).trim();
            if (changes_outside_werks) {
                raise("Burning the werks modified files outside of .werks:\n${changes_outside_werks}");
            }

            if (sh(script: "git status --porcelain --untracked-files=no -- .werks", returnStdout: true).trim() == "") {
                // TODO: raise once all werks are created without a version
                print("No werks to burn (yet)");
                return;
            }

            withGerritSshKey {
                withEnv([
                    // no Groovy interpolation of the secret, git runs GIT_SSH_COMMAND via the shell
                    'GIT_SSH_COMMAND=ssh -o "StrictHostKeyChecking no" -i $GERRIT_SSH_KEY -l $GERRIT_USER',
                    // Set author and committer (also for the cherry-pick), `git commit --author ...` is not sufficient
                    "GIT_AUTHOR_NAME=Checkmk release system",
                    "GIT_AUTHOR_EMAIL=noreply@checkmk.com",
                    "GIT_COMMITTER_NAME=Checkmk release system",
                    "GIT_COMMITTER_EMAIL=noreply@checkmk.com",
                ]) {
                    stage("Create commit") {
                        sh("""
                            # Install Gerrit Change-Id hook via scp, using the same ssh key as for the push.
                            # Gerrit needs the legacy scp protocol (-O), the default is SFTP since OpenSSH 9.0
                            HOOK=\$(git rev-parse --git-path hooks)/commit-msg
                            HOOK_SRC=\$GERRIT_USER@review.lan.tribe29.com:hooks/commit-msg
                            # -p: apply the executable mode of the hook, also if the file already exists
                            scp -O -p -o StrictHostKeyChecking=no -i \$GERRIT_SSH_KEY -P 29418 \$HOOK_SRC \$HOOK

                            git add --update .werks
                            git commit --message '${commit_message}'
                            git show --format=fuller
                        """);
                    }

                    smart_stage(name: "Push to review", condition: !dry_run) {
                        def burn_commit = sh(script: "git rev-parse HEAD", returnStdout: true).trim();
                        sh("""
                            git fetch --no-tags --depth=1 origin '${branch_version}'
                            git checkout --detach FETCH_HEAD
                        """);
                        if (sh(script: "git cherry-pick ${burn_commit}", returnStatus: true) != 0) {
                            sh("git status; git cherry-pick --abort");
                            raise("Cherry-picking '${commit_message}' onto ${branch_version} failed due to merge conflicts");
                        }
                        sh("""
                            git show --format=fuller --stat
                            git push origin 'HEAD:refs/for/${branch_version}%${push_options.join(",")}'
                        """);
                    }
                }
            }
        }
    }
}

return this;
