#!groovy

/// file: test-werks-commands.groovy

def main() {
    def results_dir = "results";

    dir("${checkout_dir}") {
        stage("Prepare workspace") {
            sh("rm -rf '${results_dir}/'*; mkdir -p '${results_dir}'");
        }

        stage("Checkout repositories") {
            checkout(
                changelog: false,
                poll: false,
                scm: scmGit(
                    branches: [new hudson.plugins.git.BranchSpec(params.CUSTOM_GIT_REF ?: params.GERRIT_PATCHSET_REVISION)],
                    browser: [
                        $class: 'GitWeb',
                        repoUrl: 'https://review.lan.tribe29.com/gitweb?p=check_mk.git',
                    ],
                    extensions: [
                        [$class: 'CloneOption',
                            noTags: false,
                            timeout: 20],
                        [$class: 'RelativeTargetDirectory',
                            relativeTargetDir: "check_mk",
                        ],
                    ],
                    userRemoteConfigs: [[
                        credentialsId: "ssh-git-gerrit-jenkins",
                        url: "ssh://jenkins@review.lan.tribe29.com:29418/check_mk",
                        refspec: "${params.CUSTOM_GIT_REF ?: params.GERRIT_PATCHSET_REVISION}",
                    ]],
                )
            );
        }
    }

    stage("Test werks commands") {
        inside_container() {
            dir("${checkout_dir}") {
                sh("""
                    # check the log of check_mk repo, not the job checkout history
                    cd check_mk
                    this_date=\$(date --date="4 weeks ago" --iso=seconds)
                    git_log=\$(git log --before="\${this_date}" --format="%H" --max-count=1)
                    make_print_version=\$(make print-VERSION)
                    cd ..

                    scripts/run-uvenv python3 -m \
                        cmk.werks.utils \
                        collect \
                        cmk check_mk \
                        --substitute-branches master:HEAD &> ${results_dir}/werk_commands.txt

                    scripts/run-uvenv python3 -m \
                        cmk.utils.werks \
                        announce \
                        check_mk/.werks \
                        \${make_print_version} \
                        --format md &>> ${results_dir}/werk_commands.txt

                    scripts/run-uvenv python3 -m \
                        cmk.utils.werks \
                        announce \
                        check_mk/.werks \
                        \${make_print_version} \
                        --format txt &>> ${results_dir}/werk_commands.txt

                    scripts/run-uvenv python3 -m \
                        cmk.werks.utils \
                        precompile \
                        check_mk/.werks \
                        precompiled.json &>> ${results_dir}/werk_commands.txt

                    scripts/run-uvenv python3 -m \
                        cmk.werks.utils \
                        changelog \
                        CHANGELOG \
                        precompiled.json &>> ${results_dir}/werk_commands.txt

                    scripts/run-uvenv python3 -m \
                        cmk.utils.werks \
                        mail \
                        check_mk \
                        HEAD \
                        werk_mail \
                        --assume-no-notes-but=\${git_log} &>> ${results_dir}/werk_commands.txt

                    scripts/run-uvenv \
                        werk \
                        list &>> ${results_dir}/werk_commands.txt
                """);
            }
        }
    }

    stage("Compile werks") {
        inside_container() {
            dir("${checkout_dir}") {
                /* groovylint-disable LineLength */
                sh("""
                    scripts/run-uvenv echo build venv...

                    scripts/run-uvenv python3 -m cmk.werks.utils collect cmk check_mk > cmk.json

                    # jq -s '.[0] * .[1] * .[2]' cma.json cmk.json kube.json > all_werks.json
                    # no need to install jq!!!!!
                    python3 -c 'import json, sys; print(json.dumps({k: v for f in sys.argv[1:] for k, v in json.load(open(f)).items()}, indent=4))' \
                        cmk.json \
                        > all_werks.json
                """);
                /* groovylint-enable LineLength */

                archiveArtifacts(
                    artifacts: "all_werks.json",
                    fingerprint: true,
                );
            }
        }
    }

    stage("Validate HTML") {
        inside_container() {
            dir("${checkout_dir}") {
                try {
                    /* groovylint-disable LineLength */
                    sh(script: """
                        ./packages/cmk-frontend/run --clean --build  # we just want to install the dependencies, but there is no target for that
                        echo '<!DOCTYPE html><html lang="en"><head><title>werks</title></head><body>' > validate-werks.html
                        # still no need for jq!
                        python3 -c 'import json; print("\\n".join(("\\n\\n<p>{}</p>\\n{}".format(key, value["description"]) for key, value in json.load(open("all_werks.json")).items())))' >> validate-werks.html
                        echo '</body></html>' >> validate-werks.html
                        java \
                            -jar packages/cmk-frontend/node_modules/vnu-jar/build/dist/vnu.jar \
                            --filterpattern 'The .tt. element is obsolete\\. Use CSS instead\\.' \
                            --stdout \
                            --format gnu \
                            - < validate-werks.html \
                            > validate-werks.error.txt
                    """);
                    /* groovylint-enable LineLength */
                } catch(Exception e) {
                    archiveArtifacts(
                        artifacts: "validate-werks.*, all_werks.json, ${results_dir}/werk_commands.txt",
                        fingerprint: true,
                    );
                    sh("""
                        cat "validate-werks.error.txt"
                        echo "Found invalid HTML. See errors above, compare the line numbers with validate-werks.html artifact."
                    """);
                    throw e;
                }
            }
        }
    }

    stage("Archive artifacts") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    allowEmptyArchive: true,
                    artifacts: "validate-werks.*, all_werks.json, ${results_dir}/werk_commands.txt",
                );
            }
        }
    }
}

return this;
