#!groovy

/// file: compile-all-werks.groovy

def main() {
    def target_path = "/home/mkde/werks/all_werks_v2.json";
    def targets_credentials = [
        [env.WEB_STAGING, "web-staging"],
        ["checkmk.com", "checkmk-deploy"],
        ["customer.checkmk.com", "customer-deploy"],
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    stage("Checkout repositories") {
        // this will checkout the repo at "${WORKSPACE}/${repo_name}"
        // but check again if you modify it here
        provide_clone("checkmk_kube_agent", "ssh-git-gerrit-jenkins");
        provide_clone("cma", "ssh-git-gerrit-jenkins");
    }

    stage("Compile werks") {
        inside_container() {
            dir("${checkout_dir}") {
                /* groovylint-disable LineLength */
                sh("""
                    scripts/run-uvenv echo build venv...
                    scripts/run-uvenv python3 -m cmk.utils.werks collect cmk ./ > cmk.json
                    scripts/run-uvenv python3 -m cmk.utils.werks collect cma ${WORKSPACE}/cma > cma.json
                    scripts/run-uvenv python3 -m cmk.utils.werks collect checkmk_kube_agent ${WORKSPACE}/checkmk_kube_agent > kube.json

                    # jq -s '.[0] * .[1] * .[2]' cma.json cmk.json kube.json > all_werks.json
                    # no need to install jq!!!!!
                    python3 -c 'import json, sys; print(json.dumps({k: v for f in sys.argv[1:] for k, v in json.load(open(f)).items()}, indent=4))' \
                        cmk.json \
                        cma.json \
                        kube.json \
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
                        artifacts: "validate-werks.*, all_werks.json",
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

    targets_credentials.each{target_credential ->
        def target = target_credential[0];
        def credentials_id = target_credential[1];

        stage("Update werks on ${target}") {
            withCredentials([
                sshUserPrivateKey(
                    credentialsId: credentials_id,
                    keyFileVariable: 'keyfile',
                    usernameVariable: 'user')
            ]) {
                sh("""
                    rsync --verbose \
                        -e "ssh -o StrictHostKeyChecking=no -i ${keyfile} -p ${WEB_STAGING_PORT}" \
                        ${checkout_dir}/all_werks.json \
                        ${user}@${target}:${target_path}
                """);
            }
        }
    }
}

return this;
