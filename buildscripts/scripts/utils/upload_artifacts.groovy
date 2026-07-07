#!groovy
/// file: upload_artifacts.groovy
// library for uploading packages
package lib

hashfile_extension = ".hash";
downloads_path = "/var/downloads/checkmk/";
smb_base_path = "/smb-share-customer/checkmk/"
cache_directories = [".cache", ".java-caller"]
versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

/* groovylint-disable ParameterCount */
void download_deb(download_source, port, cmk_version, download_dest, edition, distro) {
    def cmk_version_rc_less = versioning.strip_rc_number_from_version(cmk_version);
    def file_pattern = "check-mk-${edition}-${cmk_version_rc_less}_0.${distro}_amd64.deb";
    download_version_dir(download_source, port, cmk_version, download_dest, file_pattern, distro);
}
/* groovylint-enable ParameterCount */

void download_source_tar(download_source, port, cmk_version, download_dest, edition) {
    def cmk_version_rc_less = versioning.strip_rc_number_from_version(cmk_version);
    def file_pattern = "check-mk-${edition}-${cmk_version_rc_less}.tar.gz";
    download_version_dir(download_source, port, cmk_version, download_dest, file_pattern, 'source tar');
}

/* groovylint-disable ParameterCount */
void download_version_dir(download_source, port, cmk_version, download_dest, pattern = "*", info = 'all packages', exclude_pattern = "") {
    println("""
        ||== download_version_dir() ================================================================
        || download_source = |${download_source}|
        || port =            |${port}|
        || cmk_version =     |${cmk_version}|
        || download_dest =   |${download_dest}|
        || pattern =         |${pattern}|
        || exclude_pattern = |${exclude_pattern}|
        || info =            |${info}|
        ||==========================================================================================
        """.stripMargin());

    withCredentials([
        sshUserPrivateKey(
            // We're using here a key which is usable for the fips server AND the other build nodes in order
            // to streamline the keys.
            credentialsId: 'jenkins-fips-server',
            keyFileVariable: 'ssh_key')
    ]) {
        sh("mkdir -p ${download_dest}");
        sh("""
            rsync --recursive --links --perms --times --verbose \
                --exclude=${exclude_pattern} \
                -e "ssh -o StrictHostKeyChecking=no -i ${ssh_key} -p ${port}" \
                ${download_source}/${cmk_version}/${pattern} \
                ${download_dest}/
        """);
    }
}
/* groovylint-enable ParameterCount */

void download_file(Map args) {
    println("""
        ||== download_file() ================================================================
        || base_url =        |${args.base_url}|
        || download_dest =   |${args.download_dest}|
        || file_name =       |${args.file_name}|
        ||==========================================================================================
        """.stripMargin());

    withCredentials([
        usernamePassword(
            credentialsId: 'cmk-credentials',
            usernameVariable: 'USER',
            passwordVariable: 'PASSWORD')
    ]) {
        sh("""
            mkdir -p ${args.download_dest}
            curl \
                --silent \
                --show-error \
                --fail \
                --user "${USER}:${PASSWORD}" \
                --parallel \
                --remote-name \
                --create-dirs \
                --output-dir ${args.download_dest} \
                "${args.base_url}/${args.file_name}{${hashfile_extension},}"
        """);
    }
}

/* groovylint-disable ParameterCount */
void upload_via_rsync(archive_base, cmk_version, filename, upload_dest, upload_port, exclude_pattern="") {
    println("""
        ||== upload_via_rsync() ================================================
        || archive_base = |${archive_base}|
        || cmk_version =  |${cmk_version}|
        || filename =     |${filename}|
        || upload_dest =  |${upload_dest}|
        || upload_port =  |${upload_port}|
        || exclude_pattern  = |${exclude_pattern}|
        ||======================================================================
        """.stripMargin());

    create_hash(archive_base + "/" + cmk_version + "/" + filename);
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {    // groovylint-disable DuplicateMapLiteral
        sh("""
            rsync -av --relative \
                --exclude '*dbgsym*.deb' \
                --exclude=${exclude_pattern} \
                -e "ssh -o StrictHostKeyChecking=no \
                -i ${RELEASE_KEY} -p ${upload_port}" \
                ${archive_base}/./${cmk_version}/${filename} \
                ${archive_base}/./${cmk_version}/${filename}${hashfile_extension} \
                ${upload_dest}
        """);
    }
}
/* groovylint-enable ParameterCount */

void upload_files_to_nexus(source_pattern, upload_dest) {
    println("""
        ||== upload_files_to_nexus() ================================================
        || source_pattern      = |${source_pattern}|
        || upload_dest      = |${upload_dest}|
        ||======================================================================
        """.stripMargin());

    withCredentials([usernamePassword(credentialsId: 'nexus', passwordVariable: 'NEXUS_PASSWORD', usernameVariable: 'NEXUS_USERNAME')]) {
        sh("""
            for i in ${source_pattern}; do
                echo "Upload \${i} to Nexus";
                curl -sSf -u "${NEXUS_USERNAME}:${NEXUS_PASSWORD}" --upload-file "\${i}" "${upload_dest}";
            done
        """);
    }
}

void clean_caches() {
    def dirs = cache_directories.collect { "~/${it}/" }.join(" ");
    sh("""
        rm -rf ${dirs}
    """);
}

boolean download_hot_cache(Map args) {
    try {
        // average runtime of this part is up to 60sec when transfering a 11GB linter archive
        timeout(time: 300, unit: 'SECONDS') {
            def cp_or_rysnc = env.USE_CP_TO_COPY_FILE_FROM_NAS == "1" ? "cp" : "rsync -ah --update --ignore-existing --stats"

            sh(label: "download_hot_cache", script: """
                mkdir -p ${args.download_dest}
                ${cp_or_rysnc} \
                    ${env.PERSISTENT_K8S_VOLUME_PATH}/${args.file_pattern}{${hashfile_extension},} \
                    ${args.download_dest}
            """);
        }
    } catch (Exception exc) {
        println("hot cache: Warning - ran into exception while copying artifact from network volume: ${exc}");
        return true;
    }

    try {
        if (!is_hash_verified("${args.download_dest}/${args.file_pattern}")) {
            raise("The sha256sum of the downloaded file does not match the expectation");
        }
    }
    catch (Exception exc) {
        print("hot cache: ran into exception while verifying artifact integrity of ${args.file_pattern}: ${exc}");
        return true;
    }

    try {
        timeout(time: 300, unit: 'SECONDS') {
            println("hot cache: Decompressing ${args.file_pattern} in ${args.download_dest}");

            sh(label: "decompress_hot_cache", script: """
                cd ${args.download_dest}
                CGROUP_CPU=\$(cat /sys/fs/cgroup/cpu.max | cut -d' ' -f1)
                LZ4_CORES=\$(( CGROUP_CPU / 100 / 1000 ))
                time lz4 --threads=\${LZ4_CORES} -dc ${args.file_pattern} | tar -xf - 2>/dev/null

                du -sh ~/.cache
            """);
        }
    }
    catch (Exception exc) {
        print("hot cache: Decompression failed, contact your local CI dealer and tell: ${exc}");
        // Clean-up any partial extraction - this might otherwise result in broken cache archives
        // See https://wiki.lan.checkmk.net/spaces/DEV/pages/181605060/2026-01-07+Corrupt+hot+cache+breaks+CV
        clean_caches()
        return true;
    }

    return false;
}

void upload_hot_cache(Map args) {
    try {
        def dirs = cache_directories.join(" ");
        def check_conditions = cache_directories.collect { "[ -d \"${it}\" ]" }.join(" || ");
        def du_commands = cache_directories.collect { "[ -d \"${it}\" ] && du -sh ${it}" }.join("\n            ");

        def cp_or_rysnc = env.USE_CP_TO_COPY_FILE_FROM_NAS == "1" ? "cp" : "rsync -ah --update --ignore-existing --stats"

        // do not even create the file, if it exists already on remote
        // the file might have been created by a little bit earlier running job
        // evaluation of calling this function is done at the beginning of a job and might be outdated by the time reaching these lines
        sh("""
            if [ ! -s "${env.PERSISTENT_K8S_VOLUME_PATH}/${args.file_pattern}" ]; then
                cd ${args.download_dest}
                if ${check_conditions}; then
                    ${du_commands}
                    CGROUP_CPU=\$(cat /sys/fs/cgroup/cpu.max | cut -d' ' -f1)
                    LZ4_CORES=\$(( CGROUP_CPU / 100 / 1000 ))
                    time tar -cf - ${dirs} 2>/dev/null | lz4 --threads=\${LZ4_CORES} > ${args.file_pattern}
                fi
            fi
        """);

        if (!sh(script:"test -f ${args.download_dest}/${args.file_pattern}", returnStatus:true)) {
            create_hash("${args.download_dest}/${args.file_pattern}");
            sh("""
                if [ ! -s "${env.PERSISTENT_K8S_VOLUME_PATH}/${args.file_pattern}" ]; then
                    ${cp_or_rysnc} ${args.download_dest}/${args.file_pattern}{${hashfile_extension},} ${env.PERSISTENT_K8S_VOLUME_PATH}/
                fi
            """);
        }
    }
    catch (Exception exc) {
        print("hot cache: uploading the cache failed, contact your local CI dealer and tell: ${exc}");
    }
}

String hashFiles(files) {
    return files.collect({ path ->
        cmd_output("sha256sum ${path} | cut -c 1-8")?.toString();
    }).join("-");
}

void withHotCache(Map args, Closure body) {
    body.resolveStrategy = Closure.OWNER_FIRST;
    body.delegate = [:];

    // TODO: Remove me as soon as this is stable
    // Skip restoring "All unit tests" as it might take up to 30min due to massive 27GB and high disk utilization
    // Skip restoring "test-mypy-docker" because restoring the 24GB archive takes around 20 minutes and causes high disk utilization
    if (
        args.disable_hot_cache || args.target_name in ["All unit tests", "C++ unit tests", "Type repository with mypy"]
    ) {
        body();
        return;
    }

    if (args.remove_existing_cache == null ? false : args.remove_existing_cache.asBoolean()) {
        clean_caches()
    }

    // use a combination of "JOB_BASE_NAME" and "arg.name"
    // as a single job might execute multiple targts (e.g. test-github-actions)
    // groovylint-disable-next-line LineLength
    def file_pattern = "${args.cache_prefix}-cache-${hashFiles(args.files_to_consider)}-${args.target_name.replaceAll(' ', '-').replaceAll('/', '-')}-${JOB_BASE_NAME}.tar.lz4";

    def upload_new_bazel_folder_artifact = download_hot_cache([
        file_pattern: "${file_pattern}",
        download_dest: args.download_dest,
    ]);

    body();

    if (upload_new_bazel_folder_artifact) {
        println("hot cache: Creating ${args.download_dest}/${file_pattern}");

        upload_hot_cache([
            file_pattern: "${file_pattern}",
            download_dest: args.download_dest,
        ]);
    } else {
        println("hot cache: No need to re-upload an existing artifact");
    }

    return;
}

void create_hash(FILE_PATH) {
    sh("""
        cd \$(dirname ${FILE_PATH});
        sha256sum -- \$(basename ${FILE_PATH}) > "\$(basename ${FILE_PATH})${hashfile_extension}";
    """);
}

boolean is_hash_verified(FILE_PATH) {
    // sha256sum exits with 0 on success
    return !sh(script: """
        cd \$(dirname ${FILE_PATH});
        sha256sum --check --status \$(basename ${FILE_PATH})${hashfile_extension}
        """,
        returnStatus: true
    );
}

void execute_cmd_on_archive_server(cmd) {
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {    // groovylint-disable DuplicateMapLiteral
        sh("""
           ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${WEB_DEPLOY_PORT} ${WEB_DEPLOY_URL} "${cmd}"
        """);
    }
}

void deploy_to_website(cmk_vers) {
    stage("Deploy to Website") {
        // cmk_vers can contain a rc information like v2.1.0p6-rc1.
        // On the website, we only want to have official releases.
        def target_version = versioning.strip_rc_number_from_version(cmk_vers);
        def symlink_pattern = smb_base_path + target_version;

        // We also do not want to keep rc versions on the archive.
        // Move contents of the RC folder into the release folder. Using mv with glob (src/*)
        // avoids the nested-folder trap of "mv src dest/" when dest already exists. Skip
        // entirely on re-runs when cmk_vers no longer exists (already deployed).
        if (target_version != cmk_vers) {
            assert cmk_vers : "cmk_vers must not be empty (would make operations unsafe on ${downloads_path})";
            assert target_version : "target_version must not be empty (would make operations unsafe on ${downloads_path})";
            execute_cmd_on_archive_server(
                "mkdir -p ${downloads_path}${target_version} && " +
                "mv ${downloads_path}${cmk_vers}/* ${downloads_path}${target_version}/ && " +
                "rmdir ${downloads_path}${cmk_vers} || true"
            );
        }
        execute_cmd_on_archive_server("ln -sf --no-dereference ${downloads_path}${target_version} ${symlink_pattern};");
    }
}

void update_bom_symlinks(cmk_vers, branch_latest=false, latest=false) {
    def target_version = versioning.strip_rc_number_from_version(cmk_vers);

    inside_container(set_docker_group_id: true,
        mount_credentials: true,
        privileged: true,
    ) {
        dir("${checkout_dir}") {
            if (branch_latest) {
                def bom_mapping_branch_latest = readJSON(
                    text: sh(script: """
                        scripts/run-uvenv \
                            buildscripts/scripts/assert_build_artifacts.py \
                            --editions_file "${checkout_dir}/editions.yml" \
                            dump_meta_artifacts_mapping \
                            --version ${target_version} \
                        """,
                        returnStdout: true)
                );
                bom_mapping_branch_latest.each { symlink, target ->
                    execute_cmd_on_archive_server(
                        "ln -sf --no-dereference ${downloads_path}${target_version}/${target} ${smb_base_path}${symlink};"
                    );
                }
            }

            if (latest) {
                def mapping_latest = readJSON(
                    text: sh(script: """
                        scripts/run-uvenv \
                            buildscripts/scripts/assert_build_artifacts.py \
                            --editions_file "${checkout_dir}/editions.yml" \
                            dump_meta_artifacts_mapping \
                            --version_agnostic \
                            --version ${target_version} \
                        """,
                        returnStdout: true)
                );
                mapping_latest.each { symlink, target ->
                    execute_cmd_on_archive_server(
                        "ln -sf --no-dereference ${downloads_path}${target_version}/${target} ${smb_base_path}${symlink};"
                    );
                }
            }
        }
    }
}

void cleanup_rc_candidates_of_version(cmk_vers) {
    def target_version = versioning.strip_rc_number_from_version(cmk_vers);
    execute_cmd_on_archive_server("rm -rf ${downloads_path}${target_version}-rc*;");
// cleanup of tst server would come to early as "build-cmk-container" needs the rc candiates available
// that cleanup is and will be done by bw-release
}

return this;
