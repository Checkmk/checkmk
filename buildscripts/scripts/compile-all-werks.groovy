#!groovy

/// file: compile-all-werks.groovy

void main() {
    if (params.CUSTOM_GIT_REF != "") {
        raise("The werk jobs are not meant to be triggered with a custom git ref to not miss any werks.");
    }

    def mkde_target_path = "/home/mkde/werks/all_werks_v3.json";
    def targets = [
        [
            host: env.WEB_STAGING,
            port: env.WEB_STAGING_PORT,
            credentials_id: "web-staging",
            path: mkde_target_path,
        ],
        [
            host: "checkmk.com",
            port: env.WEB_STAGING_PORT,
            credentials_id: "checkmk-deploy",
            path: mkde_target_path,
        ],
        [
            host: "customer.checkmk.com",
            port: env.WEB_STAGING_PORT,
            credentials_id: "customer-deploy",
            path: mkde_target_path,
        ],
        [
            host: "werks.checkmk.com",
            port: "52022",
            credentials_id: "werks-deploy",
            path: "/var/www/werks.checkmk.com/incoming/all_werks_v3.json",
            known_host: "[werks.checkmk.com]:52022 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJOR6bj9+Q84vW0GL/bfogPIVT8D4wEz9RY5uN/umRup",
        ],
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
        provide_clone("check_mk", "jenkins-gerrit-fips-compliant-ssh-key");
        provide_clone("checkmk_kube_agent", "jenkins-gerrit-fips-compliant-ssh-key");
        provide_clone("cma", "jenkins-gerrit-fips-compliant-ssh-key");

        // check_mk has to be on master
        dir("${WORKSPACE}/check_mk") {
            sh("git checkout master");
        }
    }

    stage("Compile werks") {
        inside_container() {
            dir("${checkout_dir}") {
                /* groovylint-disable LineLength */
                sh("""
                    bazel run //packages/cmk-werks:utils-bin -- collect cmk ${WORKSPACE}/check_mk > cmk.json
                    bazel run //packages/cmk-werks:utils-bin -- collect cma ${WORKSPACE}/cma > cma.json
                    bazel run //packages/cmk-werks:utils-bin -- collect checkmk_kube_agent ${WORKSPACE}/checkmk_kube_agent > kube.json

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
                        echo '<!DOCTYPE html><html lang="en"><head><title>werks</title></head><body>' > validate-werks.html
                        # still no need for jq!
                        python3 -c 'import json; print("\\n".join(("\\n\\n<p>{}</p>\\n{}".format(key, value["description"]) for key, value in json.load(open("all_werks.json")).items())))' >> validate-werks.html
                        echo '</body></html>' >> validate-werks.html
                        bazel run //packages/cmk-werks:vnu -- \
                            --filterpattern 'The .tt. element is obsolete\\. Use CSS instead\\.' \
                            --stdout \
                            --format gnu \
                            - < validate-werks.html \
                            > validate-werks.error.txt
                    """);
                    /* groovylint-enable LineLength */
                } catch (Exception e) {
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

    targets.each { target ->
        stage("Update werks on ${target.host}") {
            def host_key_options = "-o StrictHostKeyChecking=no";
            if (target.known_host) {
                def known_hosts_file = "known_hosts_${target.host}";
                writeFile(file: known_hosts_file, text: "${target.known_host}\n");
                host_key_options = "-o StrictHostKeyChecking=yes -o UserKnownHostsFile=${WORKSPACE}/${known_hosts_file}";
            }

            withCredentials([
                sshUserPrivateKey(
                    credentialsId: target.credentials_id,
                    keyFileVariable: 'keyfile',
                    usernameVariable: 'user',
                )
            ]) {
                sh("""
                    rsync --verbose \
                        -e "ssh ${host_key_options} -i ${keyfile} -p ${target.port}" \
                        ${checkout_dir}/all_werks.json \
                        ${user}@${target.host}:${target.path}
                """);
            }
        }
    }
}

return this;
