# Sign all PowerShell scripts in the current directory.
# `build bazel //agents/windows/plugins:all`
#
# We are using make variables, $, and $@ because we have no correct labels

TO_SIGN_SCRIPTS = [
    "arcserve_backup.ps1",
    "citrix_farm.ps1",
    "citrix_licenses.ps1",
    "citrix_xenapp.ps1",
    "hyperv_vms_guestinfos.ps1",
    "hyperv_vms.ps1",
    "iis_app_pool_state.ps1",
    "kaspersky_av_client.ps1",
    "mk_msoffice.ps1",
    "mk_oracle.ps1",
    "msexch_dag.ps1",
    "msexch_database.ps1",
    "nvidia_smi.ps1",
    "rds_licenses.ps1",
    "sansymphony.ps1",
    "veeam_backup_status.ps1",
    "win_printers.ps1",
    "windows_if.ps1",
    "windows_multipath.ps1",
    "windows_os_bonding.ps1",
    "windows_tasks.ps1",
    "windows_updates.ps1",
]

[
    genrule(
        name = "sign_" + n,
        srcs = [n],
        outs = ["signed/" + n],
        cmd_ps = "&$(execpath scripts/signer.ps1) $< $@",
        executable = True,
        tools = ["scripts/signer.ps1"],
        visibility = ["//visibility:public"],
    )
    for n in TO_SIGN_SCRIPTS
]
