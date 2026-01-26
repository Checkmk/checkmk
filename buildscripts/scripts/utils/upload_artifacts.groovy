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
void download_deb(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION, DISTRO) {
    CMK_VERSION_RC_LESS = versioning.strip_rc_number_from_version(CMK_VERSION);
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION_RC_LESS}_0.${DISTRO}_amd64.deb";
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, DISTRO);
}
/* groovylint-enable ParameterCount */

void download_source_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION) {
    CMK_VERSION_RC_LESS = versioning.strip_rc_number_from_version(CMK_VERSION);
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION_RC_LESS}.tar.gz";
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, 'source tar');
}

/* groovylint-disable ParameterCount */
void download_version_dir(DOWNLOAD_SOURCE,
                         PORT,
                         CMK_VERSION,
                         DOWNLOAD_DEST,
                         PATTERN = "*",
                         INFO = 'all packages',
                         EXCLUDE_PATTERN = ""
) {
    println("""
        ||== download_version_dir() ================================================================
        || DOWNLOAD_SOURCE = |${DOWNLOAD_SOURCE}|
        || PORT =            |${PORT}|
        || CMK_VERSION =     |${CMK_VERSION}|
        || DOWNLOAD_DEST =   |${DOWNLOAD_DEST}|
        || PATTERN =         |${PATTERN}|
        || EXCLUDE_PATTERN = |${EXCLUDE_PATTERN}|
        || INFO =            |${INFO}|
        ||==========================================================================================
        """.stripMargin());

    withCredentials([
        sshUserPrivateKey(
            // We're using here a key which is usable for the fips server AND the other build nodes in order
            // to streamline the keys.
            credentialsId: 'jenkins-fips-server',
            keyFileVariable: 'ssh_key')
    ]) {
        sh("mkdir -p ${DOWNLOAD_DEST}");
        sh("""
            rsync --recursive --links --perms --times --verbose \
                --exclude=${EXCLUDE_PATTERN} \
                -e "ssh -o StrictHostKeyChecking=no -i ${ssh_key} -p ${PORT}" \
                ${DOWNLOAD_SOURCE}/${CMK_VERSION}/${PATTERN} \
                ${DOWNLOAD_DEST}/
        """);
    }
}
/* groovylint-enable ParameterCount */

void download_file(Map args) {
    println("""
        ||== download_file() ================================================================
        || BASE_URL =        |${args.base_url}|
        || DOWNLOAD_DEST =   |${args.download_dest}|
        || FILE_NAME =       |${args.file_name}|
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

void upload_files_to_nexus(SOURCE_PATTERN, UPLOAD_DEST) {
    println("""
        ||== upload_files_to_nexus() ================================================
        || SOURCE_PATTERN      = |${SOURCE_PATTERN}|
        || UPLOAD_DEST      = |${UPLOAD_DEST}|
        ||======================================================================
        """.stripMargin());

    withCredentials([usernamePassword(credentialsId: 'nexus', passwordVariable: 'NEXUS_PASSWORD', usernameVariable: 'NEXUS_USERNAME')]) {
        sh("""
            for i in ${SOURCE_PATTERN}; do
                echo "Upload \${i} to Nexus";
                curl -sSf -u "${NEXUS_USERNAME}:${NEXUS_PASSWORD}" --upload-file "\${i}" "${UPLOAD_DEST}";
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
        if (args.remote_download) {
            download_file(
                base_url: "${INTERNAL_DEPLOY_URL}/caches",
                download_dest: "${args.download_dest}",
                file_name: "${args.file_pattern}",
            );
        } else {
            sh("""
                mkdir -p ${args.download_dest}
                cp ${env.PERSISTENT_K8S_VOLUME_PATH}/${args.file_pattern}{${hashfile_extension},} ${args.download_dest}
            """);
        }

        if (!verify_hash("${args.download_dest}/${args.file_pattern}")) {
            raise("The sha256sum of the downloaded file does not match the expectation");
        }
    }
    catch (Exception exc) {
        print("hot cache: ran into exception while running download_hot_cache() for ${args.file_pattern}: ${exc}");
        return true;
    }

    try {
        println("hot cache: Decompressing ${args.file_pattern} in ${args.download_dest}");

        sh("""
            cd ${args.download_dest}
            time lz4 -dc ${args.file_pattern} | tar -xf - 2>/dev/null
            du -sh ~/.cache
        """);
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

        sh("""
            cd ${args.download_dest}
            if ${check_conditions}; then
                ${du_commands}
                time tar -cf - ${dirs} 2>/dev/null | lz4 > ${args.file_pattern}
            fi
        """);

        if (!sh(script:"test -f ${args.download_dest}/${args.file_pattern}", returnStatus:true)) {
            if (args.remote_upload) {
                upload_via_rsync(
                    "${args.download_dest}",
                    "",
                    "${args.file_pattern}",
                    "${INTERNAL_DEPLOY_DEST}" + "caches",
                    INTERNAL_DEPLOY_PORT,
                );
            } else {
                create_hash("${args.download_dest}/${args.file_pattern}");
                sh("""
                    if [ ! -s "${env.PERSISTENT_K8S_VOLUME_PATH}/${args.file_pattern}" ]; then
                        cp ${args.download_dest}/${args.file_pattern}{${hashfile_extension},} ${env.PERSISTENT_K8S_VOLUME_PATH}/
                    fi
                """);
            }
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

Map capture_folder_state(download_dest) {
    // Capture all folders in download_dest with their sizes
    // Note: .cache/bazel is excluded as it's managed by MOUNT_SHARED_REPOSITORY_CACHE
    def folder_state = [:];
    try {
        def output = sh(script: """
            cd ${download_dest}
            find . -maxdepth 1 -type d ! -name '.' -exec du -sb {} \\; | sort
        """, returnStdout: true).trim();

        if (output) {
            output.split('\n').each { line ->
                def parts = line.split('\t');
                if (parts.size() == 2) {
                    def size = parts[0];
                    def folder = parts[1];
                    folder_state[folder] = size;
                }
            }
        }
    } catch (Exception exc) {
        println("hot cache: Warning - could not capture folder state: ${exc}");
    }
    return folder_state;
}

void verify_folder_integrity(Map before_state, String download_dest) {
    def after_state = capture_folder_state(download_dest);

    // Check for new folders
    def new_folders = after_state.keySet() - before_state.keySet();
    if (new_folders.size() > 0) {
        println("hot cache: WARNING - New folders detected in ${download_dest}: ${new_folders.join(', ')}");
    }

    // Check for size changes in existing folders
    def size_changes = [];
    before_state.each { folder, size ->
        if (after_state.containsKey(folder) && after_state[folder] != size) {
            def before_mb = (size as Long) / (1024 * 1024);
            def after_mb = (after_state[folder] as Long) / (1024 * 1024);
            def before_mb_rounded = String.format("%.2f", before_mb);
            def after_mb_rounded = String.format("%.2f", after_mb);
            size_changes.add("${folder}: ${before_mb_rounded} MB -> ${after_mb_rounded} MB");
        }
    }

    if (size_changes.size() > 0) {
        println("hot cache: WARNING - Folder size changes detected:");
        size_changes.each { change ->
            println("  - ${change}");
        }
    }

    // Check for removed folders
    def removed_folders = before_state.keySet() - after_state.keySet();
    if (removed_folders.size() > 0) {
        println("hot cache: WARNING - Folders removed from ${download_dest}: ${removed_folders.join(', ')}");
    }
}

void withHotCache(Map args, Closure body) {
    body.resolveStrategy = Closure.OWNER_FIRST;
    body.delegate = [:];

    // TODO: Remove me as soon as this is stable
    // Skip restoring "All unit tests" as it might take up to 30min due to massive 27GB and high disk utilization
    if (env.USE_STASHED_BAZEL_FOLDER == "0" || args.target_name in ["All unit tests", "C++ unit tests"]) {
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
        remote_download: args.remote_download == null ? true : args.remote_download.asBoolean(),
    ]);

    def folder_state_after_extraction = capture_folder_state(args.download_dest);

    body();

    verify_folder_integrity(folder_state_after_extraction, args.download_dest);

    if (upload_new_bazel_folder_artifact) {
        println("hot cache: Creating ${args.download_dest}/${file_pattern}");

        upload_hot_cache([
            file_pattern: "${file_pattern}",
            download_dest: args.download_dest,
            remote_upload: args.remote_upload == null ? true : args.remote_upload.asBoolean(),
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

boolean verify_hash(HASH_FILE) {
    return sh(script: """
        cd \$(dirname ${HASH_FILE});
        sha256sum --check --status \$(basename ${HASH_FILE})
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

void deploy_to_website(CMK_VERS) {
    stage("Deploy to Website") {
        // CMK_VERS can contain a rc information like v2.1.0p6-rc1.
        // On the website, we only want to have official releases.
        def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS);
        def SYMLINK_PATH = smb_base_path + TARGET_VERSION;

        // We also do not want to keep rc versions on the archive.
        // So rename the folder in case we have a rc
        if (TARGET_VERSION != CMK_VERS) {
            execute_cmd_on_archive_server("mv ${downloads_path}${CMK_VERS} ${downloads_path}${TARGET_VERSION};");
        }
        execute_cmd_on_archive_server("ln -sf --no-dereference ${downloads_path}${TARGET_VERSION} ${SYMLINK_PATH};");
    }
}

void update_bom_symlinks(CMK_VERS, branch_latest=false, latest=false) {
    def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS);

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
                            --version ${TARGET_VERSION} \
                        """,
                        returnStdout: true)
                );
                bom_mapping_branch_latest.each { symlink, target ->
                    execute_cmd_on_archive_server(
                        "ln -sf --no-dereference ${downloads_path}${TARGET_VERSION}/${target} ${smb_base_path}${symlink};"
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
                            --version ${TARGET_VERSION} \
                        """,
                        returnStdout: true)
                );
                mapping_latest.each { symlink, target ->
                    execute_cmd_on_archive_server(
                        "ln -sf --no-dereference ${downloads_path}${TARGET_VERSION}/${target} ${smb_base_path}${symlink};"
                    );
                }
            }
        }
    }
}

void cleanup_rc_candidates_of_version(CMK_VERS) {
    def TARGET_VERSION = versioning.strip_rc_number_from_version(CMK_VERS);
    execute_cmd_on_archive_server("rm -rf ${downloads_path}${TARGET_VERSION}-rc*;");
// cleanup of tst server would come to early as "build-cmk-container" needs the rc candiates available
// that cleanup is and will be done by bw-release
}

return this;
