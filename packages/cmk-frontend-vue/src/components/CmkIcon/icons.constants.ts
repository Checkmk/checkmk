/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cva } from 'class-variance-authority'
import { type IconNames, type IconSizes } from 'cmk-shared-typing/typescript/icon'
import lightAssumeBgPng from '~cmk-frontend/themes/facelift/images/assume_bg.png?url&no-inline'
import lightCheckboxHoverBgPng from '~cmk-frontend/themes/facelift/images/checkbox_hover_bg.png?url&no-inline'
import lightDashletAnchorSvg from '~cmk-frontend/themes/facelift/images/dashlet_anchor.svg?url&no-inline'
import lightDashletCloneSvg from '~cmk-frontend/themes/facelift/images/dashlet_clone.svg?url&no-inline'
import lightDashletDeleteSvg from '~cmk-frontend/themes/facelift/images/dashlet_delete.svg?url&no-inline'
import lightDashletEditSvg from '~cmk-frontend/themes/facelift/images/dashlet_edit.svg?url&no-inline'
import lightDashletResizeSvg from '~cmk-frontend/themes/facelift/images/dashlet_resize.svg?url&no-inline'
import lightFaviconIco from '~cmk-frontend/themes/facelift/images/favicon.ico?url&no-inline'
import lightFolderClosedPng from '~cmk-frontend/themes/facelift/images/folder_closed.png?url&no-inline'
import lightFolderHiPng from '~cmk-frontend/themes/facelift/images/folder_hi.png?url&no-inline'
import lightFolderOpenPng from '~cmk-frontend/themes/facelift/images/folder_open.png?url&no-inline'
import lightGlobePng from '~cmk-frontend/themes/facelift/images/globe.png?url&no-inline'
import lightIcon2faSvg from '~cmk-frontend/themes/facelift/images/icon_2fa.svg?url&no-inline'
import lightIcon2faBackupCodesSvg from '~cmk-frontend/themes/facelift/images/icon_2fa_backup_codes.svg?url&no-inline'
import lightIconAbortPng from '~cmk-frontend/themes/facelift/images/icon_abort.png?url&no-inline'
import lightIconAboutCheckmkSvg from '~cmk-frontend/themes/facelift/images/icon_about_checkmk.svg?url&no-inline'
import lightIconAcceptSvg from '~cmk-frontend/themes/facelift/images/icon_accept.svg?url&no-inline'
import lightIconAcceptAllSvg from '~cmk-frontend/themes/facelift/images/icon_accept_all.svg?url&no-inline'
import lightIconAckPng from '~cmk-frontend/themes/facelift/images/icon_ack.png?url&no-inline'
import lightIconAcknowledgeTestPng from '~cmk-frontend/themes/facelift/images/icon_acknowledge_test.png?url&no-inline'
import lightIconActionPng from '~cmk-frontend/themes/facelift/images/icon_action.png?url&no-inline'
import lightIconActivatePng from '~cmk-frontend/themes/facelift/images/icon_activate.png?url&no-inline'
import lightIconAddPng from '~cmk-frontend/themes/facelift/images/icon_add.png?url&no-inline'
import lightIconAddDashletPng from '~cmk-frontend/themes/facelift/images/icon_add_dashlet.png?url&no-inline'
import lightIconAddRuleSvg from '~cmk-frontend/themes/facelift/images/icon_add_rule.svg?url&no-inline'
import lightIconAgentOutputPng from '~cmk-frontend/themes/facelift/images/icon_agent_output.png?url&no-inline'
import lightIconAgentRegistrationSvg from '~cmk-frontend/themes/facelift/images/icon_agent_registration.svg?url&no-inline'
import lightIconAgentsSvg from '~cmk-frontend/themes/facelift/images/icon_agents.svg?url&no-inline'
import lightIconAggrSvg from '~cmk-frontend/themes/facelift/images/icon_aggr.svg?url&no-inline'
import lightIconAggrSingleSvg from '~cmk-frontend/themes/facelift/images/icon_aggr_single.svg?url&no-inline'
import lightIconAggrSingleProblemSvg from '~cmk-frontend/themes/facelift/images/icon_aggr_single_problem.svg?url&no-inline'
import lightIconAggrcompPng from '~cmk-frontend/themes/facelift/images/icon_aggrcomp.png?url&no-inline'
import lightIconAixTgzSvg from '~cmk-frontend/themes/facelift/images/icon_aix_tgz.svg?url&no-inline'
import lightIconAlertOverviewSvg from '~cmk-frontend/themes/facelift/images/icon_alert-overview.svg?url&no-inline'
import lightIconAlertPng from '~cmk-frontend/themes/facelift/images/icon_alert.png?url&no-inline'
import lightIconAlertAckPng from '~cmk-frontend/themes/facelift/images/icon_alert_ack.png?url&no-inline'
import lightIconAlertAckstopPng from '~cmk-frontend/themes/facelift/images/icon_alert_ackstop.png?url&no-inline'
import lightIconAlertAlertHandlerFailedPng from '~cmk-frontend/themes/facelift/images/icon_alert_alert_handler_failed.png?url&no-inline'
import lightIconAlertAlertHandlerStartedPng from '~cmk-frontend/themes/facelift/images/icon_alert_alert_handler_started.png?url&no-inline'
import lightIconAlertAlertHandlerStoppedPng from '~cmk-frontend/themes/facelift/images/icon_alert_alert_handler_stopped.png?url&no-inline'
import lightIconAlertCmkNotifyPng from '~cmk-frontend/themes/facelift/images/icon_alert_cmk_notify.png?url&no-inline'
import lightIconAlertCommandPng from '~cmk-frontend/themes/facelift/images/icon_alert_command.png?url&no-inline'
import lightIconAlertCritSvg from '~cmk-frontend/themes/facelift/images/icon_alert_crit.svg?url&no-inline'
import lightIconAlertDownPng from '~cmk-frontend/themes/facelift/images/icon_alert_down.png?url&no-inline'
import lightIconAlertDowntimePng from '~cmk-frontend/themes/facelift/images/icon_alert_downtime.png?url&no-inline'
import lightIconAlertDowntimestopPng from '~cmk-frontend/themes/facelift/images/icon_alert_downtimestop.png?url&no-inline'
import lightIconAlertFlappingPng from '~cmk-frontend/themes/facelift/images/icon_alert_flapping.png?url&no-inline'
import lightIconAlertHandlersSvg from '~cmk-frontend/themes/facelift/images/icon_alert_handlers.svg?url&no-inline'
import lightIconAlertNotifyPng from '~cmk-frontend/themes/facelift/images/icon_alert_notify.png?url&no-inline'
import lightIconAlertNotifyProgressPng from '~cmk-frontend/themes/facelift/images/icon_alert_notify_progress.png?url&no-inline'
import lightIconAlertNotifyResultPng from '~cmk-frontend/themes/facelift/images/icon_alert_notify_result.png?url&no-inline'
import lightIconAlertOkPng from '~cmk-frontend/themes/facelift/images/icon_alert_ok.png?url&no-inline'
import lightIconAlertReloadPng from '~cmk-frontend/themes/facelift/images/icon_alert_reload.png?url&no-inline'
import lightIconAlertRestartPng from '~cmk-frontend/themes/facelift/images/icon_alert_restart.png?url&no-inline'
import lightIconAlertStartPng from '~cmk-frontend/themes/facelift/images/icon_alert_start.png?url&no-inline'
import lightIconAlertStopPng from '~cmk-frontend/themes/facelift/images/icon_alert_stop.png?url&no-inline'
import lightIconAlertTimelineSvg from '~cmk-frontend/themes/facelift/images/icon_alert_timeline.svg?url&no-inline'
import lightIconAlertUnknownPng from '~cmk-frontend/themes/facelift/images/icon_alert_unknown.png?url&no-inline'
import lightIconAlertUnreachPng from '~cmk-frontend/themes/facelift/images/icon_alert_unreach.png?url&no-inline'
import lightIconAlertUpPng from '~cmk-frontend/themes/facelift/images/icon_alert_up.png?url&no-inline'
import lightIconAlertWarnPng from '~cmk-frontend/themes/facelift/images/icon_alert_warn.png?url&no-inline'
import lightIconAlertsSvg from '~cmk-frontend/themes/facelift/images/icon_alerts.svg?url&no-inline'
import lightIconAllStatesPng from '~cmk-frontend/themes/facelift/images/icon_all_states.png?url&no-inline'
import lightIconAnalysisSvg from '~cmk-frontend/themes/facelift/images/icon_analysis.svg?url&no-inline'
import lightIconAnalyzeSvg from '~cmk-frontend/themes/facelift/images/icon_analyze.svg?url&no-inline'
import lightIconAnalyzeConfigSvg from '~cmk-frontend/themes/facelift/images/icon_analyze_config.svg?url&no-inline'
import lightIconAnnotationPng from '~cmk-frontend/themes/facelift/images/icon_annotation.png?url&no-inline'
import lightIconApiSvg from '~cmk-frontend/themes/facelift/images/icon_api.svg?url&no-inline'
import lightIconAppMonitoringTopicSvg from '~cmk-frontend/themes/facelift/images/icon_app_monitoring_topic.svg?url&no-inline'
import lightIconApplyPng from '~cmk-frontend/themes/facelift/images/icon_apply.png?url&no-inline'
import lightIconArSimulatePng from '~cmk-frontend/themes/facelift/images/icon_ar_simulate.png?url&no-inline'
import lightIconArchiveEventPng from '~cmk-frontend/themes/facelift/images/icon_archive_event.png?url&no-inline'
import lightIconAssignSvg from '~cmk-frontend/themes/facelift/images/icon_assign.svg?url&no-inline'
import lightIconAssume0Png from '~cmk-frontend/themes/facelift/images/icon_assume_0.png?url&no-inline'
import lightIconAssume1Png from '~cmk-frontend/themes/facelift/images/icon_assume_1.png?url&no-inline'
import lightIconAssume2Png from '~cmk-frontend/themes/facelift/images/icon_assume_2.png?url&no-inline'
import lightIconAssume3Png from '~cmk-frontend/themes/facelift/images/icon_assume_3.png?url&no-inline'
import lightIconAssumeNonePng from '~cmk-frontend/themes/facelift/images/icon_assume_none.png?url&no-inline'
import lightIconAuditlogSvg from '~cmk-frontend/themes/facelift/images/icon_auditlog.svg?url&no-inline'
import lightIconAutherrPng from '~cmk-frontend/themes/facelift/images/icon_autherr.png?url&no-inline'
import lightIconAuthokPng from '~cmk-frontend/themes/facelift/images/icon_authok.png?url&no-inline'
import lightIconAvComputationPng from '~cmk-frontend/themes/facelift/images/icon_av_computation.png?url&no-inline'
import lightIconAvailabilitySvg from '~cmk-frontend/themes/facelift/images/icon_availability.svg?url&no-inline'
import lightIconAwsSvg from '~cmk-frontend/themes/facelift/images/icon_aws.svg?url&no-inline'
import lightIconAwsLogoSvg from '~cmk-frontend/themes/facelift/images/icon_aws_logo.svg?url&no-inline'
import lightIconAzureStorageSvg from '~cmk-frontend/themes/facelift/images/icon_azure_storage.svg?url&no-inline'
import lightIconAzureVmsSvg from '~cmk-frontend/themes/facelift/images/icon_azure_vms.svg?url&no-inline'
import lightIconBackPng from '~cmk-frontend/themes/facelift/images/icon_back.png?url&no-inline'
import lightIconBackOffPng from '~cmk-frontend/themes/facelift/images/icon_back_off.png?url&no-inline'
import lightIconBackgroundJobDetailsPng from '~cmk-frontend/themes/facelift/images/icon_background_job_details.png?url&no-inline'
import lightIconBackgroundJobsSvg from '~cmk-frontend/themes/facelift/images/icon_background_jobs.svg?url&no-inline'
import lightIconBackupSvg from '~cmk-frontend/themes/facelift/images/icon_backup.svg?url&no-inline'
import lightIconBackupRestoreStopPng from '~cmk-frontend/themes/facelift/images/icon_backup_restore_stop.png?url&no-inline'
import lightIconBackupStartPng from '~cmk-frontend/themes/facelift/images/icon_backup_start.png?url&no-inline'
import lightIconBackupStatePng from '~cmk-frontend/themes/facelift/images/icon_backup_state.png?url&no-inline'
import lightIconBackupStopPng from '~cmk-frontend/themes/facelift/images/icon_backup_stop.png?url&no-inline'
import lightIconBackupTargetEditPng from '~cmk-frontend/themes/facelift/images/icon_backup_target_edit.png?url&no-inline'
import lightIconBackupTargetsSvg from '~cmk-frontend/themes/facelift/images/icon_backup_targets.svg?url&no-inline'
import lightIconBakeSvg from '~cmk-frontend/themes/facelift/images/icon_bake.svg?url&no-inline'
import lightIconBakeResultPng from '~cmk-frontend/themes/facelift/images/icon_bake_result.png?url&no-inline'
import lightIconBarplotSvg from '~cmk-frontend/themes/facelift/images/icon_barplot.svg?url&no-inline'
import lightIconBiFreezeSvg from '~cmk-frontend/themes/facelift/images/icon_bi_freeze.svg?url&no-inline'
import lightIconBilistPng from '~cmk-frontend/themes/facelift/images/icon_bilist.png?url&no-inline'
import lightIconBitreePng from '~cmk-frontend/themes/facelift/images/icon_bitree.png?url&no-inline'
import lightIconBookmarkListSvg from '~cmk-frontend/themes/facelift/images/icon_bookmark_list.svg?url&no-inline'
import lightIconBottomPng from '~cmk-frontend/themes/facelift/images/icon_bottom.png?url&no-inline'
import lightIconBulkSvg from '~cmk-frontend/themes/facelift/images/icon_bulk.svg?url&no-inline'
import lightIconBulkImportPng from '~cmk-frontend/themes/facelift/images/icon_bulk_import.png?url&no-inline'
import lightIconCachedPng from '~cmk-frontend/themes/facelift/images/icon_cached.png?url&no-inline'
import lightIconCancelSvg from '~cmk-frontend/themes/facelift/images/icon_cancel.svg?url&no-inline'
import lightIconCancelNotificationsSvg from '~cmk-frontend/themes/facelift/images/icon_cancel_notifications.svg?url&no-inline'
import lightIconCannotReschedulePng from '~cmk-frontend/themes/facelift/images/icon_cannot_reschedule.png?url&no-inline'
import lightIconCertificateSvg from '~cmk-frontend/themes/facelift/images/icon_certificate.svg?url&no-inline'
import lightIconCheckSvg from '~cmk-frontend/themes/facelift/images/icon_check.svg?url&no-inline'
import lightIconCheckParametersSvg from '~cmk-frontend/themes/facelift/images/icon_check_parameters.svg?url&no-inline'
import lightIconCheckPluginsSvg from '~cmk-frontend/themes/facelift/images/icon_check_plugins.svg?url&no-inline'
import lightIconCheckboxSvg from '~cmk-frontend/themes/facelift/images/icon_checkbox.svg?url&no-inline'
import lightIconCheckmarkSvg from '~cmk-frontend/themes/facelift/images/icon_checkmark.svg?url&no-inline'
import lightIconCheckmarkBareSvg from '~cmk-frontend/themes/facelift/images/icon_checkmark_bare.svg?url&no-inline'
import lightIconCheckmarkBgWhiteSvg from '~cmk-frontend/themes/facelift/images/icon_checkmark_bg_white.svg?url&no-inline'
import lightIconCheckmarkOrangeSvg from '~cmk-frontend/themes/facelift/images/icon_checkmark_orange.svg?url&no-inline'
import lightIconCheckmarkPlusSvg from '~cmk-frontend/themes/facelift/images/icon_checkmark_plus.svg?url&no-inline'
import lightIconCheckmkSvg from '~cmk-frontend/themes/facelift/images/icon_checkmk.svg?url&no-inline'
import lightIconCheckmkLogoSvg from '~cmk-frontend/themes/facelift/images/icon_checkmk_logo.svg?url&no-inline'
import lightIconCheckmkLogoMinSvg from '~cmk-frontend/themes/facelift/images/icon_checkmk_logo_min.svg?url&no-inline'
import lightIconCleanupPng from '~cmk-frontend/themes/facelift/images/icon_cleanup.png?url&no-inline'
import lightIconClearPng from '~cmk-frontend/themes/facelift/images/icon_clear.png?url&no-inline'
import lightIconClipboardSvg from '~cmk-frontend/themes/facelift/images/icon_clipboard.svg?url&no-inline'
import lightIconClockSvg from '~cmk-frontend/themes/facelift/images/icon_clock.svg?url&no-inline'
import lightIconCloneSvg from '~cmk-frontend/themes/facelift/images/icon_clone.svg?url&no-inline'
import lightIconCloseSvg from '~cmk-frontend/themes/facelift/images/icon_close.svg?url&no-inline'
import lightIconClosetimewarpPng from '~cmk-frontend/themes/facelift/images/icon_closetimewarp.png?url&no-inline'
import lightIconCloudSvg from '~cmk-frontend/themes/facelift/images/icon_cloud.svg?url&no-inline'
import lightIconClusterPng from '~cmk-frontend/themes/facelift/images/icon_cluster.png?url&no-inline'
import lightIconCollapsePng from '~cmk-frontend/themes/facelift/images/icon_collapse.png?url&no-inline'
import lightIconCollapseArrowPng from '~cmk-frontend/themes/facelift/images/icon_collapse_arrow.png?url&no-inline'
import lightIconColorModeSvg from '~cmk-frontend/themes/facelift/images/icon_color_mode.svg?url&no-inline'
import lightIconCommandsSvg from '~cmk-frontend/themes/facelift/images/icon_commands.svg?url&no-inline'
import lightIconCommentSvg from '~cmk-frontend/themes/facelift/images/icon_comment.svg?url&no-inline'
import lightIconConditionPng from '~cmk-frontend/themes/facelift/images/icon_condition.png?url&no-inline'
import lightIconConfigurationSvg from '~cmk-frontend/themes/facelift/images/icon_configuration.svg?url&no-inline'
import lightIconConnectionTestsSvg from '~cmk-frontend/themes/facelift/images/icon_connection_tests.svg?url&no-inline'
import lightIconContactgroupsSvg from '~cmk-frontend/themes/facelift/images/icon_contactgroups.svg?url&no-inline'
import lightIconContinuePng from '~cmk-frontend/themes/facelift/images/icon_continue.png?url&no-inline'
import lightIconCopiedSvg from '~cmk-frontend/themes/facelift/images/icon_copied.svg?url&no-inline'
import lightIconCountingPng from '~cmk-frontend/themes/facelift/images/icon_counting.png?url&no-inline'
import lightIconCrashSvg from '~cmk-frontend/themes/facelift/images/icon_crash.svg?url&no-inline'
import lightIconCrashGlowPng from '~cmk-frontend/themes/facelift/images/icon_crash_glow.png?url&no-inline'
import lightIconCritProblemSvg from '~cmk-frontend/themes/facelift/images/icon_crit_problem.svg?url&no-inline'
import lightIconCriticalPng from '~cmk-frontend/themes/facelift/images/icon_critical.png?url&no-inline'
import lightIconCrossSvg from '~cmk-frontend/themes/facelift/images/icon_cross.svg?url&no-inline'
import lightIconCrossBgWhiteSvg from '~cmk-frontend/themes/facelift/images/icon_cross_bg_white.svg?url&no-inline'
import lightIconCrossGreySvg from '~cmk-frontend/themes/facelift/images/icon_cross_grey.svg?url&no-inline'
import lightIconCustomAttrSvg from '~cmk-frontend/themes/facelift/images/icon_custom_attr.svg?url&no-inline'
import lightIconCustomGraphPng from '~cmk-frontend/themes/facelift/images/icon_custom_graph.png?url&no-inline'
import lightIconCustomSnapinSvg from '~cmk-frontend/themes/facelift/images/icon_custom_snapin.svg?url&no-inline'
import lightIconCustomerManagementPng from '~cmk-frontend/themes/facelift/images/icon_customer_management.png?url&no-inline'
import lightIconD146n0571c5Png from '~cmk-frontend/themes/facelift/images/icon_d146n0571c5.png?url&no-inline'
import lightIconDashSvg from '~cmk-frontend/themes/facelift/images/icon_dash.svg?url&no-inline'
import lightIconDashboardSvg from '~cmk-frontend/themes/facelift/images/icon_dashboard.svg?url&no-inline'
import lightIconDashboardControlsPng from '~cmk-frontend/themes/facelift/images/icon_dashboard_controls.png?url&no-inline'
import lightIconDashboardEditSvg from '~cmk-frontend/themes/facelift/images/icon_dashboard_edit.svg?url&no-inline'
import lightIconDashboardGridSvg from '~cmk-frontend/themes/facelift/images/icon_dashboard_grid.svg?url&no-inline'
import lightIconDashboardMainSvg from '~cmk-frontend/themes/facelift/images/icon_dashboard_main.svg?url&no-inline'
import lightIconDashboardMenuarrowSvg from '~cmk-frontend/themes/facelift/images/icon_dashboard_menuarrow.svg?url&no-inline'
import lightIconDashboardProblemsSvg from '~cmk-frontend/themes/facelift/images/icon_dashboard_problems.svg?url&no-inline'
import lightIconDashboardSystemSvg from '~cmk-frontend/themes/facelift/images/icon_dashboard_system.svg?url&no-inline'
import lightIconDashletNetworkTopologyPng from '~cmk-frontend/themes/facelift/images/icon_dashlet_network_topology.png?url&no-inline'
import lightIconDashletNodataPng from '~cmk-frontend/themes/facelift/images/icon_dashlet_nodata.png?url&no-inline'
import lightIconDashletNotificationsBarChartPng from '~cmk-frontend/themes/facelift/images/icon_dashlet_notifications_bar_chart.png?url&no-inline'
import lightIconDashletUrlPng from '~cmk-frontend/themes/facelift/images/icon_dashlet_url.png?url&no-inline'
import lightIconDcdConnectionsSvg from '~cmk-frontend/themes/facelift/images/icon_dcd_connections.svg?url&no-inline'
import lightIconDcdExecutePng from '~cmk-frontend/themes/facelift/images/icon_dcd_execute.png?url&no-inline'
import lightIconDcdHistoryPng from '~cmk-frontend/themes/facelift/images/icon_dcd_history.png?url&no-inline'
import lightIconDelayedPng from '~cmk-frontend/themes/facelift/images/icon_delayed.png?url&no-inline'
import lightIconDeleteSvg from '~cmk-frontend/themes/facelift/images/icon_delete.svg?url&no-inline'
import lightIconDeployAgentsPng from '~cmk-frontend/themes/facelift/images/icon_deploy_agents.png?url&no-inline'
import lightIconDeploymentErrorPng from '~cmk-frontend/themes/facelift/images/icon_deployment_error.png?url&no-inline'
import lightIconDeploymentStatusPng from '~cmk-frontend/themes/facelift/images/icon_deployment_status.png?url&no-inline'
import lightIconDerivedDowntimePng from '~cmk-frontend/themes/facelift/images/icon_derived_downtime.png?url&no-inline'
import lightIconDetailPng from '~cmk-frontend/themes/facelift/images/icon_detail.png?url&no-inline'
import lightIconDeveloperResourcesSvg from '~cmk-frontend/themes/facelift/images/icon_developer_resources.svg?url&no-inline'
import lightIconDevelopmentSvg from '~cmk-frontend/themes/facelift/images/icon_development.svg?url&no-inline'
import lightIconDiagnosePng from '~cmk-frontend/themes/facelift/images/icon_diagnose.png?url&no-inline'
import lightIconDiagnosticsSvg from '~cmk-frontend/themes/facelift/images/icon_diagnostics.svg?url&no-inline'
import lightIconDiagnosticsDumpFilePng from '~cmk-frontend/themes/facelift/images/icon_diagnostics_dump_file.png?url&no-inline'
import lightIconDisableTestPng from '~cmk-frontend/themes/facelift/images/icon_disable_test.png?url&no-inline'
import lightIconDisabledSvg from '~cmk-frontend/themes/facelift/images/icon_disabled.svg?url&no-inline'
import lightIconDisabledServiceSvg from '~cmk-frontend/themes/facelift/images/icon_disabled_service.svg?url&no-inline'
import lightIconDissolveOperationPng from '~cmk-frontend/themes/facelift/images/icon_dissolve_operation.png?url&no-inline'
import lightIconDockerSvg from '~cmk-frontend/themes/facelift/images/icon_docker.svg?url&no-inline'
import lightIconDownPng from '~cmk-frontend/themes/facelift/images/icon_down.png?url&no-inline'
import lightIconDownloadPng from '~cmk-frontend/themes/facelift/images/icon_download.png?url&no-inline'
import lightIconDownloadAgentsSvg from '~cmk-frontend/themes/facelift/images/icon_download_agents.svg?url&no-inline'
import lightIconDownloadCsvPng from '~cmk-frontend/themes/facelift/images/icon_download_csv.png?url&no-inline'
import lightIconDownloadJsonPng from '~cmk-frontend/themes/facelift/images/icon_download_json.png?url&no-inline'
import lightIconDowntimeSvg from '~cmk-frontend/themes/facelift/images/icon_downtime.svg?url&no-inline'
import lightIconDowntimeForReportPng from '~cmk-frontend/themes/facelift/images/icon_downtime_for_report.png?url&no-inline'
import lightIconDragSvg from '~cmk-frontend/themes/facelift/images/icon_drag.svg?url&no-inline'
import lightIconEditSvg from '~cmk-frontend/themes/facelift/images/icon_edit.svg?url&no-inline'
import lightIconEditCustomGraphPng from '~cmk-frontend/themes/facelift/images/icon_edit_custom_graph.png?url&no-inline'
import lightIconEditForecastModelPng from '~cmk-frontend/themes/facelift/images/icon_edit_forecast_model.png?url&no-inline'
import lightIconEmailPng from '~cmk-frontend/themes/facelift/images/icon_email.png?url&no-inline'
import lightIconEmptyPng from '~cmk-frontend/themes/facelift/images/icon_empty.png?url&no-inline'
import lightIconEnableTestPng from '~cmk-frontend/themes/facelift/images/icon_enable_test.png?url&no-inline'
import lightIconEnabledPng from '~cmk-frontend/themes/facelift/images/icon_enabled.png?url&no-inline'
import lightIconEncryptedPng from '~cmk-frontend/themes/facelift/images/icon_encrypted.png?url&no-inline'
import lightIconEndPng from '~cmk-frontend/themes/facelift/images/icon_end.png?url&no-inline'
import lightIconErrorPng from '~cmk-frontend/themes/facelift/images/icon_error.png?url&no-inline'
import lightIconEventConsoleStatusSvg from '~cmk-frontend/themes/facelift/images/icon_event console_status.svg?url&no-inline'
import lightIconEventSvg from '~cmk-frontend/themes/facelift/images/icon_event.svg?url&no-inline'
import lightIconEventConsoleSvg from '~cmk-frontend/themes/facelift/images/icon_event_console.svg?url&no-inline'
import lightIconExpandPng from '~cmk-frontend/themes/facelift/images/icon_expand.png?url&no-inline'
import lightIconExportPng from '~cmk-frontend/themes/facelift/images/icon_export.png?url&no-inline'
import lightIconExportLinkSvg from '~cmk-frontend/themes/facelift/images/icon_export_link.svg?url&no-inline'
import lightIconExportRuleSvg from '~cmk-frontend/themes/facelift/images/icon_export_rule.svg?url&no-inline'
import lightIconExternalSvg from '~cmk-frontend/themes/facelift/images/icon_external.svg?url&no-inline'
import lightIconFactoryresetPng from '~cmk-frontend/themes/facelift/images/icon_factoryreset.png?url&no-inline'
import lightIconFakeCheckResultSvg from '~cmk-frontend/themes/facelift/images/icon_fake_check_result.svg?url&no-inline'
import lightIconFavoriteSvg from '~cmk-frontend/themes/facelift/images/icon_favorite.svg?url&no-inline'
import lightIconFilterSvg from '~cmk-frontend/themes/facelift/images/icon_filter.svg?url&no-inline'
import lightIconFilterLineSvg from '~cmk-frontend/themes/facelift/images/icon_filter_line.svg?url&no-inline'
import lightIconFiltersSetPng from '~cmk-frontend/themes/facelift/images/icon_filters_set.png?url&no-inline'
import lightIconFixallSvg from '~cmk-frontend/themes/facelift/images/icon_fixall.svg?url&no-inline'
import lightIconFlappingPng from '~cmk-frontend/themes/facelift/images/icon_flapping.png?url&no-inline'
import lightIconFolderSvg from '~cmk-frontend/themes/facelift/images/icon_folder.svg?url&no-inline'
import lightIconFolderBlueSvg from '~cmk-frontend/themes/facelift/images/icon_folder_blue.svg?url&no-inline'
import lightIconFolderpropertiesPng from '~cmk-frontend/themes/facelift/images/icon_folderproperties.png?url&no-inline'
import lightIconForecastGraphPng from '~cmk-frontend/themes/facelift/images/icon_forecast_graph.png?url&no-inline'
import lightIconForeignChangesPng from '~cmk-frontend/themes/facelift/images/icon_foreign_changes.png?url&no-inline'
import lightIconForthPng from '~cmk-frontend/themes/facelift/images/icon_forth.png?url&no-inline'
import lightIconForthOffPng from '~cmk-frontend/themes/facelift/images/icon_forth_off.png?url&no-inline'
import lightIconFrameurlSvg from '~cmk-frontend/themes/facelift/images/icon_frameurl.svg?url&no-inline'
import lightIconGaugeSvg from '~cmk-frontend/themes/facelift/images/icon_gauge.svg?url&no-inline'
import lightIconGcpSvg from '~cmk-frontend/themes/facelift/images/icon_gcp.svg?url&no-inline'
import lightIconGlobalSettingsSvg from '~cmk-frontend/themes/facelift/images/icon_global_settings.svg?url&no-inline'
import lightIconGraphSvg from '~cmk-frontend/themes/facelift/images/icon_graph.svg?url&no-inline'
import lightIconGraphCollectionPng from '~cmk-frontend/themes/facelift/images/icon_graph_collection.png?url&no-inline'
import lightIconGraphTimeSvg from '~cmk-frontend/themes/facelift/images/icon_graph_time.svg?url&no-inline'
import lightIconGraphTuningPng from '~cmk-frontend/themes/facelift/images/icon_graph_tuning.png?url&no-inline'
import lightIconGuiDesignPng from '~cmk-frontend/themes/facelift/images/icon_gui_design.png?url&no-inline'
import lightIconGuitestPng from '~cmk-frontend/themes/facelift/images/icon_guitest.png?url&no-inline'
import lightIconHardStatesPng from '~cmk-frontend/themes/facelift/images/icon_hard_states.png?url&no-inline'
import lightIconHardwareSvg from '~cmk-frontend/themes/facelift/images/icon_hardware.svg?url&no-inline'
import lightIconHelpSvg from '~cmk-frontend/themes/facelift/images/icon_help.svg?url&no-inline'
import lightIconHelpActivatedSvg from '~cmk-frontend/themes/facelift/images/icon_help_activated.svg?url&no-inline'
import lightIconHierarchySvg from '~cmk-frontend/themes/facelift/images/icon_hierarchy.svg?url&no-inline'
import lightIconHistoryPng from '~cmk-frontend/themes/facelift/images/icon_history.png?url&no-inline'
import lightIconHomeSvg from '~cmk-frontend/themes/facelift/images/icon_home.svg?url&no-inline'
import lightIconHostPng from '~cmk-frontend/themes/facelift/images/icon_host.png?url&no-inline'
import lightIconHostGraphSvg from '~cmk-frontend/themes/facelift/images/icon_host_graph.svg?url&no-inline'
import lightIconHostProblemsSvg from '~cmk-frontend/themes/facelift/images/icon_host_problems.svg?url&no-inline'
import lightIconHostStateSvg from '~cmk-frontend/themes/facelift/images/icon_host_state.svg?url&no-inline'
import lightIconHostStateSummarySvg from '~cmk-frontend/themes/facelift/images/icon_host_state_summary.svg?url&no-inline'
import lightIconHostStatisticsSvg from '~cmk-frontend/themes/facelift/images/icon_host_statistics.svg?url&no-inline'
import lightIconHostSvcProblemsSvg from '~cmk-frontend/themes/facelift/images/icon_host_svc_problems.svg?url&no-inline'
import lightIconHostSvcProblemsDarkSvg from '~cmk-frontend/themes/facelift/images/icon_host_svc_problems_dark.svg?url&no-inline'
import lightIconHostgroupsSvg from '~cmk-frontend/themes/facelift/images/icon_hostgroups.svg?url&no-inline'
import lightIconHyphenSvg from '~cmk-frontend/themes/facelift/images/icon_hyphen.svg?url&no-inline'
import lightIconIcalPng from '~cmk-frontend/themes/facelift/images/icon_ical.png?url&no-inline'
import lightIconIconsSvg from '~cmk-frontend/themes/facelift/images/icon_icons.svg?url&no-inline'
import lightIconIgnorePng from '~cmk-frontend/themes/facelift/images/icon_ignore.png?url&no-inline'
import lightIconInactivePng from '~cmk-frontend/themes/facelift/images/icon_inactive.png?url&no-inline'
import lightIconInfluxdbConnectionsSvg from '~cmk-frontend/themes/facelift/images/icon_influxdb_connections.svg?url&no-inline'
import lightIconInfoSvg from '~cmk-frontend/themes/facelift/images/icon_info.svg?url&no-inline'
import lightIconInfoCircleSvg from '~cmk-frontend/themes/facelift/images/icon_info_circle.svg?url&no-inline'
import lightIconInlineErrorSvg from '~cmk-frontend/themes/facelift/images/icon_inline_error.svg?url&no-inline'
import lightIconInsertSvg from '~cmk-frontend/themes/facelift/images/icon_insert.svg?url&no-inline'
import lightIconInsertdateSvg from '~cmk-frontend/themes/facelift/images/icon_insertdate.svg?url&no-inline'
import lightIconInstallPng from '~cmk-frontend/themes/facelift/images/icon_install.png?url&no-inline'
import lightIconIntegrationsCustomSvg from '~cmk-frontend/themes/facelift/images/icon_integrations_custom.svg?url&no-inline'
import lightIconIntegrationsOtherSvg from '~cmk-frontend/themes/facelift/images/icon_integrations_other.svg?url&no-inline'
import lightIconInvPng from '~cmk-frontend/themes/facelift/images/icon_inv.png?url&no-inline'
import lightIconInventorySvg from '~cmk-frontend/themes/facelift/images/icon_inventory.svg?url&no-inline'
import lightIconInventoryFailedPng from '~cmk-frontend/themes/facelift/images/icon_inventory_failed.png?url&no-inline'
import lightIconInvertedPng from '~cmk-frontend/themes/facelift/images/icon_inverted.png?url&no-inline'
import lightIconKubernetesSvg from '~cmk-frontend/themes/facelift/images/icon_kubernetes.svg?url&no-inline'
import lightIconLaptop50Png from '~cmk-frontend/themes/facelift/images/icon_laptop_50.png?url&no-inline'
import lightIconLdapSvg from '~cmk-frontend/themes/facelift/images/icon_ldap.svg?url&no-inline'
import lightIconLearningBeginnerSvg from '~cmk-frontend/themes/facelift/images/icon_learning_beginner.svg?url&no-inline'
import lightIconLearningCheckmkSvg from '~cmk-frontend/themes/facelift/images/icon_learning_checkmk.svg?url&no-inline'
import lightIconLearningForumSvg from '~cmk-frontend/themes/facelift/images/icon_learning_forum.svg?url&no-inline'
import lightIconLearningGuideSvg from '~cmk-frontend/themes/facelift/images/icon_learning_guide.svg?url&no-inline'
import lightIconLearningVideoTutorialsSvg from '~cmk-frontend/themes/facelift/images/icon_learning_video_tutorials.svg?url&no-inline'
import lightIconLicenseFailedPng from '~cmk-frontend/themes/facelift/images/icon_license_failed.png?url&no-inline'
import lightIconLicenseSuccessfulPng from '~cmk-frontend/themes/facelift/images/icon_license_successful.png?url&no-inline'
import lightIconLicenseUnknownStatePng from '~cmk-frontend/themes/facelift/images/icon_license_unknown_state.png?url&no-inline'
import lightIconLicensingSvg from '~cmk-frontend/themes/facelift/images/icon_licensing.svg?url&no-inline'
import lightIconLightbulbSvg from '~cmk-frontend/themes/facelift/images/icon_lightbulb.svg?url&no-inline'
import lightIconLightbulbIdeaSvg from '~cmk-frontend/themes/facelift/images/icon_lightbulb_idea.svg?url&no-inline'
import lightIconLinkPng from '~cmk-frontend/themes/facelift/images/icon_link.png?url&no-inline'
import lightIconLinuxSvg from '~cmk-frontend/themes/facelift/images/icon_linux.svg?url&no-inline'
import lightIconLinuxDebSvg from '~cmk-frontend/themes/facelift/images/icon_linux_deb.svg?url&no-inline'
import lightIconLinuxRpmSvg from '~cmk-frontend/themes/facelift/images/icon_linux_rpm.svg?url&no-inline'
import lightIconLinuxTgzSvg from '~cmk-frontend/themes/facelift/images/icon_linux_tgz.svg?url&no-inline'
import lightIconLocalrulePng from '~cmk-frontend/themes/facelift/images/icon_localrule.png?url&no-inline'
import lightIconLogSvg from '~cmk-frontend/themes/facelift/images/icon_log.svg?url&no-inline'
import lightIconLoginPng from '~cmk-frontend/themes/facelift/images/icon_login.png?url&no-inline'
import lightIconLogwatchPng from '~cmk-frontend/themes/facelift/images/icon_logwatch.png?url&no-inline'
import lightIconMagicMovePng from '~cmk-frontend/themes/facelift/images/icon_magic_move.png?url&no-inline'
import lightIconMainChangesSvg from '~cmk-frontend/themes/facelift/images/icon_main_changes.svg?url&no-inline'
import lightIconMainChangesActiveSvg from '~cmk-frontend/themes/facelift/images/icon_main_changes_active.svg?url&no-inline'
import lightIconMainCustomizeSvg from '~cmk-frontend/themes/facelift/images/icon_main_customize.svg?url&no-inline'
import lightIconMainCustomizeActiveSvg from '~cmk-frontend/themes/facelift/images/icon_main_customize_active.svg?url&no-inline'
import lightIconMainHelpSvg from '~cmk-frontend/themes/facelift/images/icon_main_help.svg?url&no-inline'
import lightIconMainHelpActiveSvg from '~cmk-frontend/themes/facelift/images/icon_main_help_active.svg?url&no-inline'
import lightIconMainMonitoringSvg from '~cmk-frontend/themes/facelift/images/icon_main_monitoring.svg?url&no-inline'
import lightIconMainMonitoringActiveSvg from '~cmk-frontend/themes/facelift/images/icon_main_monitoring_active.svg?url&no-inline'
import lightIconMainSearchSvg from '~cmk-frontend/themes/facelift/images/icon_main_search.svg?url&no-inline'
import lightIconMainSearchActiveSvg from '~cmk-frontend/themes/facelift/images/icon_main_search_active.svg?url&no-inline'
import lightIconMainSetupSvg from '~cmk-frontend/themes/facelift/images/icon_main_setup.svg?url&no-inline'
import lightIconMainSetupActiveSvg from '~cmk-frontend/themes/facelift/images/icon_main_setup_active.svg?url&no-inline'
import lightIconMainUserSvg from '~cmk-frontend/themes/facelift/images/icon_main_user.svg?url&no-inline'
import lightIconMainUserActiveSvg from '~cmk-frontend/themes/facelift/images/icon_main_user_active.svg?url&no-inline'
import lightIconManualSvg from '~cmk-frontend/themes/facelift/images/icon_manual.svg?url&no-inline'
import lightIconManualActiveSvg from '~cmk-frontend/themes/facelift/images/icon_manual_active.svg?url&no-inline'
import lightIconMatrixPng from '~cmk-frontend/themes/facelift/images/icon_matrix.png?url&no-inline'
import lightIconMenuPng from '~cmk-frontend/themes/facelift/images/icon_menu.png?url&no-inline'
import lightIconMenuItemCheckedPng from '~cmk-frontend/themes/facelift/images/icon_menu_item_checked.png?url&no-inline'
import lightIconMenuItemUncheckedPng from '~cmk-frontend/themes/facelift/images/icon_menu_item_unchecked.png?url&no-inline'
import lightIconMessageSvg from '~cmk-frontend/themes/facelift/images/icon_message.svg?url&no-inline'
import lightIconMigrateUsersSvg from '~cmk-frontend/themes/facelift/images/icon_migrate_users.svg?url&no-inline'
import lightIconMissingSvg from '~cmk-frontend/themes/facelift/images/icon_missing.svg?url&no-inline'
import lightIconMkeventdRulesPng from '~cmk-frontend/themes/facelift/images/icon_mkeventd_rules.png?url&no-inline'
import lightIconMkpsSvg from '~cmk-frontend/themes/facelift/images/icon_mkps.svg?url&no-inline'
import lightIconMonitoredServiceSvg from '~cmk-frontend/themes/facelift/images/icon_monitored_service.svg?url&no-inline'
import lightIconMovePng from '~cmk-frontend/themes/facelift/images/icon_move.png?url&no-inline'
import lightIconMovedownPng from '~cmk-frontend/themes/facelift/images/icon_movedown.png?url&no-inline'
import lightIconMoveupPng from '~cmk-frontend/themes/facelift/images/icon_moveup.png?url&no-inline'
import lightIconNagiosSvg from '~cmk-frontend/themes/facelift/images/icon_nagios.svg?url&no-inline'
import lightIconNagvisPng from '~cmk-frontend/themes/facelift/images/icon_nagvis.png?url&no-inline'
import lightIconNeedReplicatePng from '~cmk-frontend/themes/facelift/images/icon_need_replicate.png?url&no-inline'
import lightIconNeedRestartPng from '~cmk-frontend/themes/facelift/images/icon_need_restart.png?url&no-inline'
import lightIconNetworkSvg from '~cmk-frontend/themes/facelift/images/icon_network.svg?url&no-inline'
import lightIconNetworkServicesSvg from '~cmk-frontend/themes/facelift/images/icon_network_services.svg?url&no-inline'
import lightIconNetworkTopologySvg from '~cmk-frontend/themes/facelift/images/icon_network_topology.svg?url&no-inline'
import lightIconNetworkingSvg from '~cmk-frontend/themes/facelift/images/icon_networking.svg?url&no-inline'
import lightIconNewSvg from '~cmk-frontend/themes/facelift/images/icon_new.svg?url&no-inline'
import lightIconNewClusterPng from '~cmk-frontend/themes/facelift/images/icon_new_cluster.png?url&no-inline'
import lightIconNewMkpPng from '~cmk-frontend/themes/facelift/images/icon_new_mkp.png?url&no-inline'
import lightIconNewfolderPng from '~cmk-frontend/themes/facelift/images/icon_newfolder.png?url&no-inline'
import lightIconNoEntrySvg from '~cmk-frontend/themes/facelift/images/icon_no_entry.svg?url&no-inline'
import lightIconNoPendingChangesSvg from '~cmk-frontend/themes/facelift/images/icon_no_pending_changes.svg?url&no-inline'
import lightIconNoRevertSvg from '~cmk-frontend/themes/facelift/images/icon_no_revert.svg?url&no-inline'
import lightIconNodowntimePng from '~cmk-frontend/themes/facelift/images/icon_nodowntime.png?url&no-inline'
import lightIconNotesPng from '~cmk-frontend/themes/facelift/images/icon_notes.png?url&no-inline'
import lightIconNotifDisabledPng from '~cmk-frontend/themes/facelift/images/icon_notif_disabled.png?url&no-inline'
import lightIconNotifEnabledPng from '~cmk-frontend/themes/facelift/images/icon_notif_enabled.png?url&no-inline'
import lightIconNotifManDisabledPng from '~cmk-frontend/themes/facelift/images/icon_notif_man_disabled.png?url&no-inline'
import lightIconNotificationEnabledPng from '~cmk-frontend/themes/facelift/images/icon_notification_enabled.png?url&no-inline'
import lightIconNotificationTimelineSvg from '~cmk-frontend/themes/facelift/images/icon_notification_timeline.svg?url&no-inline'
import lightIconNotificationsSvg from '~cmk-frontend/themes/facelift/images/icon_notifications.svg?url&no-inline'
import lightIconNpassivePng from '~cmk-frontend/themes/facelift/images/icon_npassive.png?url&no-inline'
import lightIconNtopSvg from '~cmk-frontend/themes/facelift/images/icon_ntop.svg?url&no-inline'
import lightIconOpenTelemetrySvg from '~cmk-frontend/themes/facelift/images/icon_open_telemetry.svg?url&no-inline'
import lightIconOpentelemetrySvg from '~cmk-frontend/themes/facelift/images/icon_opentelemetry.svg?url&no-inline'
import lightIconOsOtherSvg from '~cmk-frontend/themes/facelift/images/icon_os_other.svg?url&no-inline'
import lightIconOtelCollectorSvg from '~cmk-frontend/themes/facelift/images/icon_otel_collector.svg?url&no-inline'
import lightIconOutofServiceperiodPng from '~cmk-frontend/themes/facelift/images/icon_outof_serviceperiod.png?url&no-inline'
import lightIconOutofnotPng from '~cmk-frontend/themes/facelift/images/icon_outofnot.png?url&no-inline'
import lightIconPackagesSvg from '~cmk-frontend/themes/facelift/images/icon_packages.svg?url&no-inline'
import lightIconPagetypeTopicSvg from '~cmk-frontend/themes/facelift/images/icon_pagetype_topic.svg?url&no-inline'
import lightIconPageurlSvg from '~cmk-frontend/themes/facelift/images/icon_pageurl.svg?url&no-inline'
import lightIconPainteroptionsSvg from '~cmk-frontend/themes/facelift/images/icon_painteroptions.svg?url&no-inline'
import lightIconPainteroptionsDownHiPng from '~cmk-frontend/themes/facelift/images/icon_painteroptions_down_hi.png?url&no-inline'
import lightIconPainteroptionsDownLoPng from '~cmk-frontend/themes/facelift/images/icon_painteroptions_down_lo.png?url&no-inline'
import lightIconPainteroptionsOffPng from '~cmk-frontend/themes/facelift/images/icon_painteroptions_off.png?url&no-inline'
import lightIconParentscanPng from '~cmk-frontend/themes/facelift/images/icon_parentscan.png?url&no-inline'
import lightIconPasswordsSvg from '~cmk-frontend/themes/facelift/images/icon_passwords.svg?url&no-inline'
import lightIconPausePng from '~cmk-frontend/themes/facelift/images/icon_pause.png?url&no-inline'
import lightIconPendingChangesSvg from '~cmk-frontend/themes/facelift/images/icon_pending_changes.svg?url&no-inline'
import lightIconPendingTaskSvg from '~cmk-frontend/themes/facelift/images/icon_pending_task.svg?url&no-inline'
import lightIconPercentageOfServiceProblemsSvg from '~cmk-frontend/themes/facelift/images/icon_percentage-of-service-problems.svg?url&no-inline'
import lightIconPerformanceDataSvg from '~cmk-frontend/themes/facelift/images/icon_performance_data.svg?url&no-inline'
import lightIconPersistPng from '~cmk-frontend/themes/facelift/images/icon_persist.png?url&no-inline'
import lightIconPieChartPng from '~cmk-frontend/themes/facelift/images/icon_pie_chart.png?url&no-inline'
import lightIconPluginsAgentlessSvg from '~cmk-frontend/themes/facelift/images/icon_plugins_agentless.svg?url&no-inline'
import lightIconPluginsAppPng from '~cmk-frontend/themes/facelift/images/icon_plugins_app.png?url&no-inline'
import lightIconPluginsCloudSvg from '~cmk-frontend/themes/facelift/images/icon_plugins_cloud.svg?url&no-inline'
import lightIconPluginsContainerizationSvg from '~cmk-frontend/themes/facelift/images/icon_plugins_containerization.svg?url&no-inline'
import lightIconPluginsGenericSvg from '~cmk-frontend/themes/facelift/images/icon_plugins_generic.svg?url&no-inline'
import lightIconPluginsHwPng from '~cmk-frontend/themes/facelift/images/icon_plugins_hw.png?url&no-inline'
import lightIconPluginsOsSvg from '~cmk-frontend/themes/facelift/images/icon_plugins_os.svg?url&no-inline'
import lightIconPluginsVirtualSvg from '~cmk-frontend/themes/facelift/images/icon_plugins_virtual.svg?url&no-inline'
import lightIconPlusSvg from '~cmk-frontend/themes/facelift/images/icon_plus.svg?url&no-inline'
import lightIconPnpPng from '~cmk-frontend/themes/facelift/images/icon_pnp.png?url&no-inline'
import lightIconPredefinedConditionsSvg from '~cmk-frontend/themes/facelift/images/icon_predefined_conditions.svg?url&no-inline'
import lightIconPredictionPng from '~cmk-frontend/themes/facelift/images/icon_prediction.png?url&no-inline'
import lightIconProblemSvg from '~cmk-frontend/themes/facelift/images/icon_problem.svg?url&no-inline'
import lightIconProductSvg from '~cmk-frontend/themes/facelift/images/icon_product.svg?url&no-inline'
import lightIconPrometheusSvg from '~cmk-frontend/themes/facelift/images/icon_prometheus.svg?url&no-inline'
import lightIconQaSvg from '~cmk-frontend/themes/facelift/images/icon_qa.svg?url&no-inline'
import lightIconQsAwsSvg from '~cmk-frontend/themes/facelift/images/icon_qs_aws.svg?url&no-inline'
import lightIconQsAzureSvg from '~cmk-frontend/themes/facelift/images/icon_qs_azure.svg?url&no-inline'
import lightIconQsGcpSvg from '~cmk-frontend/themes/facelift/images/icon_qs_gcp.svg?url&no-inline'
import lightIconQsOtelSvg from '~cmk-frontend/themes/facelift/images/icon_qs_otel.svg?url&no-inline'
import lightIconQsPrometheusSvg from '~cmk-frontend/themes/facelift/images/icon_qs_prometheus.svg?url&no-inline'
import lightIconQsRelaySvg from '~cmk-frontend/themes/facelift/images/icon_qs_relay.svg?url&no-inline'
import lightIconQuickSetupAwsSvg from '~cmk-frontend/themes/facelift/images/icon_quick_setup_aws.svg?url&no-inline'
import lightIconQuicksearchPng from '~cmk-frontend/themes/facelift/images/icon_quicksearch.png?url&no-inline'
import lightIconRandomPng from '~cmk-frontend/themes/facelift/images/icon_random.png?url&no-inline'
import lightIconRankSvg from '~cmk-frontend/themes/facelift/images/icon_rank.svg?url&no-inline'
import lightIconReadOnlySvg from '~cmk-frontend/themes/facelift/images/icon_read_only.svg?url&no-inline'
import lightIconRecreateBrokerCertificateSvg from '~cmk-frontend/themes/facelift/images/icon_recreate_broker_certificate.svg?url&no-inline'
import lightIconRedoSvg from '~cmk-frontend/themes/facelift/images/icon_redo.svg?url&no-inline'
import lightIconRelayMenuSvg from '~cmk-frontend/themes/facelift/images/icon_relay_menu.svg?url&no-inline'
import lightIconReleaseMkpPng from '~cmk-frontend/themes/facelift/images/icon_release_mkp.png?url&no-inline'
import lightIconReleaseMkpYellowPng from '~cmk-frontend/themes/facelift/images/icon_release_mkp_yellow.png?url&no-inline'
import lightIconReloadSvg from '~cmk-frontend/themes/facelift/images/icon_reload.svg?url&no-inline'
import lightIconReloadCmkSvg from '~cmk-frontend/themes/facelift/images/icon_reload_cmk.svg?url&no-inline'
import lightIconReloadsnapinPng from '~cmk-frontend/themes/facelift/images/icon_reloadsnapin.png?url&no-inline'
import lightIconReloadsnapinLoAltPng from '~cmk-frontend/themes/facelift/images/icon_reloadsnapin_lo_alt.png?url&no-inline'
import lightIconRenameHostSvg from '~cmk-frontend/themes/facelift/images/icon_rename_host.svg?url&no-inline'
import lightIconRepl25Png from '~cmk-frontend/themes/facelift/images/icon_repl_25.png?url&no-inline'
import lightIconRepl50Png from '~cmk-frontend/themes/facelift/images/icon_repl_50.png?url&no-inline'
import lightIconRepl75Png from '~cmk-frontend/themes/facelift/images/icon_repl_75.png?url&no-inline'
import lightIconReplFailedPng from '~cmk-frontend/themes/facelift/images/icon_repl_failed.png?url&no-inline'
import lightIconReplLockedPng from '~cmk-frontend/themes/facelift/images/icon_repl_locked.png?url&no-inline'
import lightIconReplPendingPng from '~cmk-frontend/themes/facelift/images/icon_repl_pending.png?url&no-inline'
import lightIconReplSuccessPng from '~cmk-frontend/themes/facelift/images/icon_repl_success.png?url&no-inline'
import lightIconReplayPng from '~cmk-frontend/themes/facelift/images/icon_replay.png?url&no-inline'
import lightIconReplicatePng from '~cmk-frontend/themes/facelift/images/icon_replicate.png?url&no-inline'
import lightIconReportSvg from '~cmk-frontend/themes/facelift/images/icon_report.svg?url&no-inline'
import lightIconReportElementPng from '~cmk-frontend/themes/facelift/images/icon_report_element.png?url&no-inline'
import lightIconReportFixedPng from '~cmk-frontend/themes/facelift/images/icon_report_fixed.png?url&no-inline'
import lightIconReportStorePng from '~cmk-frontend/themes/facelift/images/icon_report_store.png?url&no-inline'
import lightIconReportschedulerPng from '~cmk-frontend/themes/facelift/images/icon_reportscheduler.png?url&no-inline'
import lightIconResetPng from '~cmk-frontend/themes/facelift/images/icon_reset.png?url&no-inline'
import lightIconResetcountersPng from '~cmk-frontend/themes/facelift/images/icon_resetcounters.png?url&no-inline'
import lightIconResizePng from '~cmk-frontend/themes/facelift/images/icon_resize.png?url&no-inline'
import lightIconRestartPng from '~cmk-frontend/themes/facelift/images/icon_restart.png?url&no-inline'
import lightIconRestorePng from '~cmk-frontend/themes/facelift/images/icon_restore.png?url&no-inline'
import lightIconRevertSvg from '~cmk-frontend/themes/facelift/images/icon_revert.svg?url&no-inline'
import lightIconRj4550Png from '~cmk-frontend/themes/facelift/images/icon_rj45_50.png?url&no-inline'
import lightIconRolesSvg from '~cmk-frontend/themes/facelift/images/icon_roles.svg?url&no-inline'
import lightIconRotateLeftPng from '~cmk-frontend/themes/facelift/images/icon_rotate_left.png?url&no-inline'
import lightIconRuleSvg from '~cmk-frontend/themes/facelift/images/icon_rule.svg?url&no-inline'
import lightIconRuleNoPng from '~cmk-frontend/themes/facelift/images/icon_rule_no.png?url&no-inline'
import lightIconRuleNoOffPng from '~cmk-frontend/themes/facelift/images/icon_rule_no_off.png?url&no-inline'
import lightIconRuleYesPng from '~cmk-frontend/themes/facelift/images/icon_rule_yes.png?url&no-inline'
import lightIconRuleYesOffPng from '~cmk-frontend/themes/facelift/images/icon_rule_yes_off.png?url&no-inline'
import lightIconRulesSvg from '~cmk-frontend/themes/facelift/images/icon_rules.svg?url&no-inline'
import lightIconRulesetsSvg from '~cmk-frontend/themes/facelift/images/icon_rulesets.svg?url&no-inline'
import lightIconRulesetsDeprecatedPng from '~cmk-frontend/themes/facelift/images/icon_rulesets_deprecated.png?url&no-inline'
import lightIconRulesetsIneffectivePng from '~cmk-frontend/themes/facelift/images/icon_rulesets_ineffective.png?url&no-inline'
import lightIconSaasSvg from '~cmk-frontend/themes/facelift/images/icon_saas.svg?url&no-inline'
import lightIconSamlSvg from '~cmk-frontend/themes/facelift/images/icon_saml.svg?url&no-inline'
import lightIconSaveSvg from '~cmk-frontend/themes/facelift/images/icon_save.svg?url&no-inline'
import lightIconSaveDashboardSvg from '~cmk-frontend/themes/facelift/images/icon_save_dashboard.svg?url&no-inline'
import lightIconSaveGraphSvg from '~cmk-frontend/themes/facelift/images/icon_save_graph.svg?url&no-inline'
import lightIconSaveToFolderSvg from '~cmk-frontend/themes/facelift/images/icon_save_to_folder.svg?url&no-inline'
import lightIconSaveToServicesSvg from '~cmk-frontend/themes/facelift/images/icon_save_to_services.svg?url&no-inline'
import lightIconSaveViewSvg from '~cmk-frontend/themes/facelift/images/icon_save_view.svg?url&no-inline'
import lightIconScatterplotSvg from '~cmk-frontend/themes/facelift/images/icon_scatterplot.svg?url&no-inline'
import lightIconSearchSvg from '~cmk-frontend/themes/facelift/images/icon_search.svg?url&no-inline'
import lightIconSearchActionSvg from '~cmk-frontend/themes/facelift/images/icon_search_action.svg?url&no-inline'
import lightIconSearchActionButtonSvg from '~cmk-frontend/themes/facelift/images/icon_search_action_button.svg?url&no-inline'
import lightIconSelectArrowSvg from '~cmk-frontend/themes/facelift/images/icon_select_arrow.svg?url&no-inline'
import lightIconServiceDiscoverySvg from '~cmk-frontend/themes/facelift/images/icon_service_discovery.svg?url&no-inline'
import lightIconServiceDurationSvg from '~cmk-frontend/themes/facelift/images/icon_service_duration.svg?url&no-inline'
import lightIconServiceGraphSvg from '~cmk-frontend/themes/facelift/images/icon_service_graph.svg?url&no-inline'
import lightIconServiceLabelAddSvg from '~cmk-frontend/themes/facelift/images/icon_service_label_add.svg?url&no-inline'
import lightIconServiceLabelRemoveSvg from '~cmk-frontend/themes/facelift/images/icon_service_label_remove.svg?url&no-inline'
import lightIconServiceLabelUpdateSvg from '~cmk-frontend/themes/facelift/images/icon_service_label_update.svg?url&no-inline'
import lightIconServiceStateSvg from '~cmk-frontend/themes/facelift/images/icon_service_state.svg?url&no-inline'
import lightIconServiceToDisabledSvg from '~cmk-frontend/themes/facelift/images/icon_service_to_disabled.svg?url&no-inline'
import lightIconServiceToIgnoredSvg from '~cmk-frontend/themes/facelift/images/icon_service_to_ignored.svg?url&no-inline'
import lightIconServiceToMonitoredSvg from '~cmk-frontend/themes/facelift/images/icon_service_to_monitored.svg?url&no-inline'
import lightIconServiceToNewSvg from '~cmk-frontend/themes/facelift/images/icon_service_to_new.svg?url&no-inline'
import lightIconServiceToRemovedSvg from '~cmk-frontend/themes/facelift/images/icon_service_to_removed.svg?url&no-inline'
import lightIconServiceToUnchangedSvg from '~cmk-frontend/themes/facelift/images/icon_service_to_unchanged.svg?url&no-inline'
import lightIconServiceToUndecidedSvg from '~cmk-frontend/themes/facelift/images/icon_service_to_undecided.svg?url&no-inline'
import lightIconServicegroupsSvg from '~cmk-frontend/themes/facelift/images/icon_servicegroups.svg?url&no-inline'
import lightIconServicesSvg from '~cmk-frontend/themes/facelift/images/icon_services.svg?url&no-inline'
import lightIconServicesBlueSvg from '~cmk-frontend/themes/facelift/images/icon_services_blue.svg?url&no-inline'
import lightIconServicesFixAllSvg from '~cmk-frontend/themes/facelift/images/icon_services_fix_all.svg?url&no-inline'
import lightIconServicesGreenSvg from '~cmk-frontend/themes/facelift/images/icon_services_green.svg?url&no-inline'
import lightIconServicesRefreshSvg from '~cmk-frontend/themes/facelift/images/icon_services_refresh.svg?url&no-inline'
import lightIconServicesStopPng from '~cmk-frontend/themes/facelift/images/icon_services_stop.png?url&no-inline'
import lightIconServicesTabulaRasaSvg from '~cmk-frontend/themes/facelift/images/icon_services_tabula_rasa.svg?url&no-inline'
import lightIconShowLessSvg from '~cmk-frontend/themes/facelift/images/icon_show_less.svg?url&no-inline'
import lightIconShowLessGreenSvg from '~cmk-frontend/themes/facelift/images/icon_show_less_green.svg?url&no-inline'
import lightIconShowMoreSvg from '~cmk-frontend/themes/facelift/images/icon_show_more.svg?url&no-inline'
import lightIconShowMoreGreenSvg from '~cmk-frontend/themes/facelift/images/icon_show_more_green.svg?url&no-inline'
import lightIconShowbiPng from '~cmk-frontend/themes/facelift/images/icon_showbi.png?url&no-inline'
import lightIconShowhidePng from '~cmk-frontend/themes/facelift/images/icon_showhide.png?url&no-inline'
import lightIconSidebarSvg from '~cmk-frontend/themes/facelift/images/icon_sidebar.svg?url&no-inline'
import lightIconSidebarFoldedSvg from '~cmk-frontend/themes/facelift/images/icon_sidebar_folded.svg?url&no-inline'
import lightIconSidebarLogoutSvg from '~cmk-frontend/themes/facelift/images/icon_sidebar_logout.svg?url&no-inline'
import lightIconSidebarPositionSvg from '~cmk-frontend/themes/facelift/images/icon_sidebar_position.svg?url&no-inline'
import lightIconSignSvg from '~cmk-frontend/themes/facelift/images/icon_sign.svg?url&no-inline'
import lightIconSignatureKeySvg from '~cmk-frontend/themes/facelift/images/icon_signature_key.svg?url&no-inline'
import lightIconSignatureKeyPartialPng from '~cmk-frontend/themes/facelift/images/icon_signature_key_partial.png?url&no-inline'
import lightIconSingleMetricSvg from '~cmk-frontend/themes/facelift/images/icon_single_metric.svg?url&no-inline'
import lightIconSiteDeadSvg from '~cmk-frontend/themes/facelift/images/icon_site_dead.svg?url&no-inline'
import lightIconSiteDisabledSvg from '~cmk-frontend/themes/facelift/images/icon_site_disabled.svg?url&no-inline'
import lightIconSiteDownSvg from '~cmk-frontend/themes/facelift/images/icon_site_down.svg?url&no-inline'
import lightIconSiteGlobalsPng from '~cmk-frontend/themes/facelift/images/icon_site_globals.png?url&no-inline'
import lightIconSiteGlobalsModifiedPng from '~cmk-frontend/themes/facelift/images/icon_site_globals_modified.png?url&no-inline'
import lightIconSiteMissingSvg from '~cmk-frontend/themes/facelift/images/icon_site_missing.svg?url&no-inline'
import lightIconSiteOverviewSvg from '~cmk-frontend/themes/facelift/images/icon_site_overview.svg?url&no-inline'
import lightIconSiteUnreachSvg from '~cmk-frontend/themes/facelift/images/icon_site_unreach.svg?url&no-inline'
import lightIconSiteWaitingSvg from '~cmk-frontend/themes/facelift/images/icon_site_waiting.svg?url&no-inline'
import lightIconSitesSvg from '~cmk-frontend/themes/facelift/images/icon_sites.svg?url&no-inline'
import lightIconSlaSvg from '~cmk-frontend/themes/facelift/images/icon_sla.svg?url&no-inline'
import lightIconSlaConfigurationPng from '~cmk-frontend/themes/facelift/images/icon_sla_configuration.png?url&no-inline'
import lightIconSnapinGreyswitchOffPng from '~cmk-frontend/themes/facelift/images/icon_snapin_greyswitch_off.png?url&no-inline'
import lightIconSnapinGreyswitchOnPng from '~cmk-frontend/themes/facelift/images/icon_snapin_greyswitch_on.png?url&no-inline'
import lightIconSnapshotPng from '~cmk-frontend/themes/facelift/images/icon_snapshot.png?url&no-inline'
import lightIconSnapshotChecksumPng from '~cmk-frontend/themes/facelift/images/icon_snapshot_checksum.png?url&no-inline'
import lightIconSnapshotNchecksumPng from '~cmk-frontend/themes/facelift/images/icon_snapshot_nchecksum.png?url&no-inline'
import lightIconSnapshotPchecksumPng from '~cmk-frontend/themes/facelift/images/icon_snapshot_pchecksum.png?url&no-inline'
import lightIconSnmpSvg from '~cmk-frontend/themes/facelift/images/icon_snmp.svg?url&no-inline'
import lightIconSnmpmibSvg from '~cmk-frontend/themes/facelift/images/icon_snmpmib.svg?url&no-inline'
import lightIconSoftwareSvg from '~cmk-frontend/themes/facelift/images/icon_software.svg?url&no-inline'
import lightIconSolarisPkgSvg from '~cmk-frontend/themes/facelift/images/icon_solaris_pkg.svg?url&no-inline'
import lightIconSolarisTgzSvg from '~cmk-frontend/themes/facelift/images/icon_solaris_tgz.svg?url&no-inline'
import lightIconSparkleSvg from '~cmk-frontend/themes/facelift/images/icon_sparkle.svg?url&no-inline'
import lightIconSparkleWhiteSvg from '~cmk-frontend/themes/facelift/images/icon_sparkle_white.svg?url&no-inline'
import lightIconStaleSvg from '~cmk-frontend/themes/facelift/images/icon_stale.svg?url&no-inline'
import lightIconStarredPng from '~cmk-frontend/themes/facelift/images/icon_starred.png?url&no-inline'
import lightIconStartPng from '~cmk-frontend/themes/facelift/images/icon_start.png?url&no-inline'
import lightIconStaticChecksSvg from '~cmk-frontend/themes/facelift/images/icon_static_checks.svg?url&no-inline'
import lightIconStaticTextSvg from '~cmk-frontend/themes/facelift/images/icon_static_text.svg?url&no-inline'
import lightIconStatusSvg from '~cmk-frontend/themes/facelift/images/icon_status.svg?url&no-inline'
import lightIconSuggestionSvg from '~cmk-frontend/themes/facelift/images/icon_suggestion.svg?url&no-inline'
import lightIconSvcProblemsSvg from '~cmk-frontend/themes/facelift/images/icon_svc_problems.svg?url&no-inline'
import lightIconSyncGraphsPng from '~cmk-frontend/themes/facelift/images/icon_sync_graphs.png?url&no-inline'
import lightIconSyncMkpPng from '~cmk-frontend/themes/facelift/images/icon_sync_mkp.png?url&no-inline'
import lightIconSyntheticMonitoringPurpleSvg from '~cmk-frontend/themes/facelift/images/icon_synthetic_monitoring_purple.svg?url&no-inline'
import lightIconSyntheticMonitoringTopicSvg from '~cmk-frontend/themes/facelift/images/icon_synthetic_monitoring_topic.svg?url&no-inline'
import lightIconSyntheticMonitoringYellowSvg from '~cmk-frontend/themes/facelift/images/icon_synthetic_monitoring_yellow.svg?url&no-inline'
import lightIconTableActionsOffSvg from '~cmk-frontend/themes/facelift/images/icon_table_actions_off.svg?url&no-inline'
import lightIconTableActionsOnSvg from '~cmk-frontend/themes/facelift/images/icon_table_actions_on.svg?url&no-inline'
import lightIconTagSvg from '~cmk-frontend/themes/facelift/images/icon_tag.svg?url&no-inline'
import lightIconTickSvg from '~cmk-frontend/themes/facelift/images/icon_tick.svg?url&no-inline'
import lightIconTimelinePng from '~cmk-frontend/themes/facelift/images/icon_timeline.png?url&no-inline'
import lightIconTimeperiodsSvg from '~cmk-frontend/themes/facelift/images/icon_timeperiods.svg?url&no-inline'
import lightIconTimewarpPng from '~cmk-frontend/themes/facelift/images/icon_timewarp.png?url&no-inline'
import lightIconTimewarpOffPng from '~cmk-frontend/themes/facelift/images/icon_timewarp_off.png?url&no-inline'
import lightIconTlsSvg from '~cmk-frontend/themes/facelift/images/icon_tls.svg?url&no-inline'
import lightIconToggleContextPng from '~cmk-frontend/themes/facelift/images/icon_toggle_context.png?url&no-inline'
import lightIconToggleDetailsPng from '~cmk-frontend/themes/facelift/images/icon_toggle_details.png?url&no-inline'
import lightIconToggleOffSvg from '~cmk-frontend/themes/facelift/images/icon_toggle_off.svg?url&no-inline'
import lightIconToggleOnSvg from '~cmk-frontend/themes/facelift/images/icon_toggle_on.svg?url&no-inline'
import lightIconTopListSvg from '~cmk-frontend/themes/facelift/images/icon_top-list.svg?url&no-inline'
import lightIconTopPng from '~cmk-frontend/themes/facelift/images/icon_top.png?url&no-inline'
import lightIconTopic2faSvg from '~cmk-frontend/themes/facelift/images/icon_topic_2fa.svg?url&no-inline'
import lightIconTopicAdministrationPng from '~cmk-frontend/themes/facelift/images/icon_topic_administration.png?url&no-inline'
import lightIconTopicAgentsPng from '~cmk-frontend/themes/facelift/images/icon_topic_agents.png?url&no-inline'
import lightIconTopicAnalyzePng from '~cmk-frontend/themes/facelift/images/icon_topic_analyze.png?url&no-inline'
import lightIconTopicApplicationsPng from '~cmk-frontend/themes/facelift/images/icon_topic_applications.png?url&no-inline'
import lightIconTopicBiPng from '~cmk-frontend/themes/facelift/images/icon_topic_bi.png?url&no-inline'
import lightIconTopicChangePasswordPng from '~cmk-frontend/themes/facelift/images/icon_topic_change_password.png?url&no-inline'
import lightIconTopicCheckmkSvg from '~cmk-frontend/themes/facelift/images/icon_topic_checkmk.svg?url&no-inline'
import lightIconTopicEventsPng from '~cmk-frontend/themes/facelift/images/icon_topic_events.png?url&no-inline'
import lightIconTopicExporterSvg from '~cmk-frontend/themes/facelift/images/icon_topic_exporter.svg?url&no-inline'
import lightIconTopicGeneralPng from '~cmk-frontend/themes/facelift/images/icon_topic_general.png?url&no-inline'
import lightIconTopicGraphsPng from '~cmk-frontend/themes/facelift/images/icon_topic_graphs.png?url&no-inline'
import lightIconTopicHistoryPng from '~cmk-frontend/themes/facelift/images/icon_topic_history.png?url&no-inline'
import lightIconTopicHostsPng from '~cmk-frontend/themes/facelift/images/icon_topic_hosts.png?url&no-inline'
import lightIconTopicInventoryPng from '~cmk-frontend/themes/facelift/images/icon_topic_inventory.png?url&no-inline'
import lightIconTopicMaintenancePng from '~cmk-frontend/themes/facelift/images/icon_topic_maintenance.png?url&no-inline'
import lightIconTopicMonitoringSvg from '~cmk-frontend/themes/facelift/images/icon_topic_monitoring.svg?url&no-inline'
import lightIconTopicMyWorkplaceSvg from '~cmk-frontend/themes/facelift/images/icon_topic_my_workplace.svg?url&no-inline'
import lightIconTopicNetworkSvg from '~cmk-frontend/themes/facelift/images/icon_topic_network.svg?url&no-inline'
import lightIconTopicOtherPng from '~cmk-frontend/themes/facelift/images/icon_topic_other.png?url&no-inline'
import lightIconTopicOverviewPng from '~cmk-frontend/themes/facelift/images/icon_topic_overview.png?url&no-inline'
import lightIconTopicProblemsPng from '~cmk-frontend/themes/facelift/images/icon_topic_problems.png?url&no-inline'
import lightIconTopicProfilePng from '~cmk-frontend/themes/facelift/images/icon_topic_profile.png?url&no-inline'
import lightIconTopicQuickSetupsSvg from '~cmk-frontend/themes/facelift/images/icon_topic_quick_setups.svg?url&no-inline'
import lightIconTopicReportingSvg from '~cmk-frontend/themes/facelift/images/icon_topic_reporting.svg?url&no-inline'
import lightIconTopicServicesPng from '~cmk-frontend/themes/facelift/images/icon_topic_services.png?url&no-inline'
import lightIconTopicSitePng from '~cmk-frontend/themes/facelift/images/icon_topic_site.png?url&no-inline'
import lightIconTopicSystemSvg from '~cmk-frontend/themes/facelift/images/icon_topic_system.svg?url&no-inline'
import lightIconTopicUserInterfaceSvg from '~cmk-frontend/themes/facelift/images/icon_topic_user_interface.svg?url&no-inline'
import lightIconTopicUsersPng from '~cmk-frontend/themes/facelift/images/icon_topic_users.png?url&no-inline'
import lightIconTopicVisualizationPng from '~cmk-frontend/themes/facelift/images/icon_topic_visualization.png?url&no-inline'
import lightIconTransSvg from '~cmk-frontend/themes/facelift/images/icon_trans.svg?url&no-inline'
import lightIconTreeClosedSvg from '~cmk-frontend/themes/facelift/images/icon_tree_closed.svg?url&no-inline'
import lightIconTrustPng from '~cmk-frontend/themes/facelift/images/icon_trust.png?url&no-inline'
import lightIconUnacknowledgeTestPng from '~cmk-frontend/themes/facelift/images/icon_unacknowledge_test.png?url&no-inline'
import lightIconUnavailableSvg from '~cmk-frontend/themes/facelift/images/icon_unavailable.svg?url&no-inline'
import lightIconUndecidedServiceSvg from '~cmk-frontend/themes/facelift/images/icon_undecided_service.svg?url&no-inline'
import lightIconUndoSvg from '~cmk-frontend/themes/facelift/images/icon_undo.svg?url&no-inline'
import lightIconUnpackagedFilesPng from '~cmk-frontend/themes/facelift/images/icon_unpackaged_files.png?url&no-inline'
import lightIconUnusedbirulesPng from '~cmk-frontend/themes/facelift/images/icon_unusedbirules.png?url&no-inline'
import lightIconUpPng from '~cmk-frontend/themes/facelift/images/icon_up.png?url&no-inline'
import lightIconUpdatePng from '~cmk-frontend/themes/facelift/images/icon_update.png?url&no-inline'
import lightIconUpdateDiscoveryParametersSvg from '~cmk-frontend/themes/facelift/images/icon_update_discovery_parameters.svg?url&no-inline'
import lightIconUpdateHostLabelsSvg from '~cmk-frontend/themes/facelift/images/icon_update_host_labels.svg?url&no-inline'
import lightIconUpdateServiceLabelsSvg from '~cmk-frontend/themes/facelift/images/icon_update_service_labels.svg?url&no-inline'
import lightIconUpgradeSvg from '~cmk-frontend/themes/facelift/images/icon_upgrade.svg?url&no-inline'
import lightIconUploadPng from '~cmk-frontend/themes/facelift/images/icon_upload.png?url&no-inline'
import lightIconUrlPng from '~cmk-frontend/themes/facelift/images/icon_url.png?url&no-inline'
import lightIconUsedrulesetsPng from '~cmk-frontend/themes/facelift/images/icon_usedrulesets.png?url&no-inline'
import lightIconUserLockedPng from '~cmk-frontend/themes/facelift/images/icon_user_locked.png?url&no-inline'
import lightIconUsersSvg from '~cmk-frontend/themes/facelift/images/icon_users.svg?url&no-inline'
import lightIconUXSvg from '~cmk-frontend/themes/facelift/images/icon_ux.svg?url&no-inline'
import lightIconValidationErrorPng from '~cmk-frontend/themes/facelift/images/icon_validation_error.png?url&no-inline'
import lightIconVideoPng from '~cmk-frontend/themes/facelift/images/icon_video.png?url&no-inline'
import lightIconViewSvg from '~cmk-frontend/themes/facelift/images/icon_view.svg?url&no-inline'
import lightIconViewColumnsPng from '~cmk-frontend/themes/facelift/images/icon_view_columns.png?url&no-inline'
import lightIconViewCopySvg from '~cmk-frontend/themes/facelift/images/icon_view_copy.svg?url&no-inline'
import lightIconViewLinkSvg from '~cmk-frontend/themes/facelift/images/icon_view_link.svg?url&no-inline'
import lightIconViewRefreshPng from '~cmk-frontend/themes/facelift/images/icon_view_refresh.png?url&no-inline'
import lightIconVsphereSvg from '~cmk-frontend/themes/facelift/images/icon_vsphere.svg?url&no-inline'
import lightIconWarningPng from '~cmk-frontend/themes/facelift/images/icon_warning.png?url&no-inline'
import lightIconWatoPng from '~cmk-frontend/themes/facelift/images/icon_wato.png?url&no-inline'
import lightIconWatoChangesPng from '~cmk-frontend/themes/facelift/images/icon_wato_changes.png?url&no-inline'
import lightIconWatoNochangesPng from '~cmk-frontend/themes/facelift/images/icon_wato_nochanges.png?url&no-inline'
import lightIconWerkAckPng from '~cmk-frontend/themes/facelift/images/icon_werk_ack.png?url&no-inline'
import lightIconWidgetCloneSvg from '~cmk-frontend/themes/facelift/images/icon_widget_clone.svg?url&no-inline'
import lightIconWidgetDeleteSvg from '~cmk-frontend/themes/facelift/images/icon_widget_delete.svg?url&no-inline'
import lightIconWidgetEditSvg from '~cmk-frontend/themes/facelift/images/icon_widget_edit.svg?url&no-inline'
import lightIconWikisearchPng from '~cmk-frontend/themes/facelift/images/icon_wikisearch.png?url&no-inline'
import lightIconWindowsMsiSvg from '~cmk-frontend/themes/facelift/images/icon_windows_msi.svg?url&no-inline'
import lightIconWrongAgentPng from '~cmk-frontend/themes/facelift/images/icon_wrong_agent.png?url&no-inline'
import lightIconWwwPng from '~cmk-frontend/themes/facelift/images/icon_www.png?url&no-inline'
import lightIconZoomPng from '~cmk-frontend/themes/facelift/images/icon_zoom.png?url&no-inline'
import lightLoadGraphPng from '~cmk-frontend/themes/facelift/images/load_graph.png?url&no-inline'
import lightLogoCmkSmallPng from '~cmk-frontend/themes/facelift/images/logo_cmk_small.png?url&no-inline'
import lightOoservicePng from '~cmk-frontend/themes/facelift/images/ooservice.png?url&no-inline'
import lightPluginurlPng from '~cmk-frontend/themes/facelift/images/pluginurl.png?url&no-inline'
import lightQuicksearchFieldBgPng from '~cmk-frontend/themes/facelift/images/quicksearch_field_bg.png?url&no-inline'
import lightReleaseAutomatedSvg from '~cmk-frontend/themes/facelift/images/release_automated.svg?url&no-inline'
import lightReleaseDeploySvg from '~cmk-frontend/themes/facelift/images/release_deploy.svg?url&no-inline'
import lightReleaseScaleSvg from '~cmk-frontend/themes/facelift/images/release_scale.svg?url&no-inline'
import lightResizeGraphPng from '~cmk-frontend/themes/facelift/images/resize_graph.png?url&no-inline'
import lightSidebarTopPng from '~cmk-frontend/themes/facelift/images/sidebar_top.png?url&no-inline'
import lightSomeproblemPng from '~cmk-frontend/themes/facelift/images/someproblem.png?url&no-inline'
import lightSpeedometerSvg from '~cmk-frontend/themes/facelift/images/speedometer.svg?url&no-inline'
import lightStatusReportPng from '~cmk-frontend/themes/facelift/images/status_report.png?url&no-inline'
import darkDashletCloneSvg from '~cmk-frontend/themes/modern-dark/images/dashlet_clone.svg?url&no-inline'
import darkDashletDeleteSvg from '~cmk-frontend/themes/modern-dark/images/dashlet_delete.svg?url&no-inline'
import darkDashletEditSvg from '~cmk-frontend/themes/modern-dark/images/dashlet_edit.svg?url&no-inline'
import darkIconAddRuleSvg from '~cmk-frontend/themes/modern-dark/images/icon_add_rule.svg?url&no-inline'
import darkIconAgentRegistrationSvg from '~cmk-frontend/themes/modern-dark/images/icon_agent_registration.svg?url&no-inline'
import darkIconAnalyzeSvg from '~cmk-frontend/themes/modern-dark/images/icon_analyze.svg?url&no-inline'
import darkIconAssignSvg from '~cmk-frontend/themes/modern-dark/images/icon_assign.svg?url&no-inline'
import darkIconAwsSvg from '~cmk-frontend/themes/modern-dark/images/icon_aws.svg?url&no-inline'
import darkIconCancelNotificationsSvg from '~cmk-frontend/themes/modern-dark/images/icon_cancel_notifications.svg?url&no-inline'
import darkIconCheckmarkBgWhiteSvg from '~cmk-frontend/themes/modern-dark/images/icon_checkmark_bg_white.svg?url&no-inline'
import darkIconCheckmarkOrangeSvg from '~cmk-frontend/themes/modern-dark/images/icon_checkmark_orange.svg?url&no-inline'
import darkIconCheckmarkPlusSvg from '~cmk-frontend/themes/modern-dark/images/icon_checkmark_plus.svg?url&no-inline'
import darkIconCloseSvg from '~cmk-frontend/themes/modern-dark/images/icon_close.svg?url&no-inline'
import darkIconCommentSvg from '~cmk-frontend/themes/modern-dark/images/icon_comment.svg?url&no-inline'
import darkIconConfigurationSvg from '~cmk-frontend/themes/modern-dark/images/icon_configuration.svg?url&no-inline'
import darkIconCrossBgWhiteSvg from '~cmk-frontend/themes/modern-dark/images/icon_cross_bg_white.svg?url&no-inline'
import darkIconDashboardGridSvg from '~cmk-frontend/themes/modern-dark/images/icon_dashboard_grid.svg?url&no-inline'
import darkIconDashboardMenuarrowSvg from '~cmk-frontend/themes/modern-dark/images/icon_dashboard_menuarrow.svg?url&no-inline'
import darkIconDevelopmentSvg from '~cmk-frontend/themes/modern-dark/images/icon_development.svg?url&no-inline'
import darkIconDragSvg from '~cmk-frontend/themes/modern-dark/images/icon_drag.svg?url&no-inline'
import darkIconExportLinkSvg from '~cmk-frontend/themes/modern-dark/images/icon_export_link.svg?url&no-inline'
import darkIconExternalSvg from '~cmk-frontend/themes/modern-dark/images/icon_external.svg?url&no-inline'
import darkIconFavoriteSvg from '~cmk-frontend/themes/modern-dark/images/icon_favorite.svg?url&no-inline'
import darkIconFilterLineSvg from '~cmk-frontend/themes/modern-dark/images/icon_filter_line.svg?url&no-inline'
import darkIconFixallSvg from '~cmk-frontend/themes/modern-dark/images/icon_fixall.svg?url&no-inline'
import darkIconFolderBlueSvg from '~cmk-frontend/themes/modern-dark/images/icon_folder_blue.svg?url&no-inline'
import darkIconHelpSvg from '~cmk-frontend/themes/modern-dark/images/icon_help.svg?url&no-inline'
import darkIconHomeSvg from '~cmk-frontend/themes/modern-dark/images/icon_home.svg?url&no-inline'
import darkIconHostSvcProblemsSvg from '~cmk-frontend/themes/modern-dark/images/icon_host_svc_problems.svg?url&no-inline'
import darkIconHyphenSvg from '~cmk-frontend/themes/modern-dark/images/icon_hyphen.svg?url&no-inline'
import darkIconInfoCircleSvg from '~cmk-frontend/themes/modern-dark/images/icon_info_circle.svg?url&no-inline'
import darkIconMainChangesSvg from '~cmk-frontend/themes/modern-dark/images/icon_main_changes.svg?url&no-inline'
import darkIconMainCustomizeSvg from '~cmk-frontend/themes/modern-dark/images/icon_main_customize.svg?url&no-inline'
import darkIconMainHelpSvg from '~cmk-frontend/themes/modern-dark/images/icon_main_help.svg?url&no-inline'
import darkIconMainMonitoringSvg from '~cmk-frontend/themes/modern-dark/images/icon_main_monitoring.svg?url&no-inline'
import darkIconMainSearchSvg from '~cmk-frontend/themes/modern-dark/images/icon_main_search.svg?url&no-inline'
import darkIconMainSetupSvg from '~cmk-frontend/themes/modern-dark/images/icon_main_setup.svg?url&no-inline'
import darkIconMainUserSvg from '~cmk-frontend/themes/modern-dark/images/icon_main_user.svg?url&no-inline'
import darkIconManualSvg from '~cmk-frontend/themes/modern-dark/images/icon_manual.svg?url&no-inline'
import darkIconNagiosSvg from '~cmk-frontend/themes/modern-dark/images/icon_nagios.svg?url&no-inline'
import darkIconNetworkSvg from '~cmk-frontend/themes/modern-dark/images/icon_network.svg?url&no-inline'
import darkIconPerformanceDataSvg from '~cmk-frontend/themes/modern-dark/images/icon_performance_data.svg?url&no-inline'
import darkIconProductSvg from '~cmk-frontend/themes/modern-dark/images/icon_product.svg?url&no-inline'
import darkIconQaSvg from '~cmk-frontend/themes/modern-dark/images/icon_qa.svg?url&no-inline'
import darkIconReloadCmkSvg from '~cmk-frontend/themes/modern-dark/images/icon_reload_cmk.svg?url&no-inline'
import darkIconRulesetsSvg from '~cmk-frontend/themes/modern-dark/images/icon_rulesets.svg?url&no-inline'
import darkIconSaasSvg from '~cmk-frontend/themes/modern-dark/images/icon_saas.svg?url&no-inline'
import darkIconSearchSvg from '~cmk-frontend/themes/modern-dark/images/icon_search.svg?url&no-inline'
import darkIconSearchActionSvg from '~cmk-frontend/themes/modern-dark/images/icon_search_action.svg?url&no-inline'
import darkIconSearchActionButtonSvg from '~cmk-frontend/themes/modern-dark/images/icon_search_action_button.svg?url&no-inline'
import darkIconSelectArrowSvg from '~cmk-frontend/themes/modern-dark/images/icon_select_arrow.svg?url&no-inline'
import darkIconServicesBlueSvg from '~cmk-frontend/themes/modern-dark/images/icon_services_blue.svg?url&no-inline'
import darkIconShowLessSvg from '~cmk-frontend/themes/modern-dark/images/icon_show_less.svg?url&no-inline'
import darkIconShowMoreSvg from '~cmk-frontend/themes/modern-dark/images/icon_show_more.svg?url&no-inline'
import darkIconSidebarFoldedSvg from '~cmk-frontend/themes/modern-dark/images/icon_sidebar_folded.svg?url&no-inline'
import darkIconSiteDeadSvg from '~cmk-frontend/themes/modern-dark/images/icon_site_dead.svg?url&no-inline'
import darkIconSiteDisabledSvg from '~cmk-frontend/themes/modern-dark/images/icon_site_disabled.svg?url&no-inline'
import darkIconSiteDownSvg from '~cmk-frontend/themes/modern-dark/images/icon_site_down.svg?url&no-inline'
import darkIconSiteMissingSvg from '~cmk-frontend/themes/modern-dark/images/icon_site_missing.svg?url&no-inline'
import darkIconSiteUnreachSvg from '~cmk-frontend/themes/modern-dark/images/icon_site_unreach.svg?url&no-inline'
import darkIconSiteWaitingSvg from '~cmk-frontend/themes/modern-dark/images/icon_site_waiting.svg?url&no-inline'
import darkIconSnmpmibSvg from '~cmk-frontend/themes/modern-dark/images/icon_snmpmib.svg?url&no-inline'
import darkIconSparkleSvg from '~cmk-frontend/themes/modern-dark/images/icon_sparkle.svg?url&no-inline'
import darkIconSparkleWhiteSvg from '~cmk-frontend/themes/modern-dark/images/icon_sparkle_white.svg?url&no-inline'
import darkIconStaleSvg from '~cmk-frontend/themes/modern-dark/images/icon_stale.svg?url&no-inline'
import darkIconSuggestionSvg from '~cmk-frontend/themes/modern-dark/images/icon_suggestion.svg?url&no-inline'
import darkIconTableActionsOffSvg from '~cmk-frontend/themes/modern-dark/images/icon_table_actions_off.svg?url&no-inline'
import darkIconTableActionsOnSvg from '~cmk-frontend/themes/modern-dark/images/icon_table_actions_on.svg?url&no-inline'
import darkIconTickSvg from '~cmk-frontend/themes/modern-dark/images/icon_tick.svg?url&no-inline'
import darkIconToggleOffSvg from '~cmk-frontend/themes/modern-dark/images/icon_toggle_off.svg?url&no-inline'
import darkIconTreeClosedSvg from '~cmk-frontend/themes/modern-dark/images/icon_tree_closed.svg?url&no-inline'
import darkIconUnavailableSvg from '~cmk-frontend/themes/modern-dark/images/icon_unavailable.svg?url&no-inline'
import darkIconUXSvg from '~cmk-frontend/themes/modern-dark/images/icon_ux.svg?url&no-inline'
import darkReleaseAutomatedSvg from '~cmk-frontend/themes/modern-dark/images/release_automated.svg?url&no-inline'
import darkSpeedometerSvg from '~cmk-frontend/themes/modern-dark/images/speedometer.svg?url&no-inline'

export const emblems = [
  'add',
  'api',
  'disable',
  'download',
  'downtime',
  'edit',
  'enable',
  'more',
  'pending',
  'refresh',
  'remove',
  'rulesets',
  'search',
  'settings',
  'sign',
  'statistic',
  'time',
  'trans',
  'warning'
] as const

export const oneColorIcons = [
  'changes',
  'check-circle',
  'checkmark',
  'customize',
  'db-widget-clone',
  'db-widget-delete',
  'db-widget-edit',
  'error',
  'help',
  'info',
  'menu',
  'monitoring',
  'saas',
  'search',
  'services',
  'setup',
  'show-less',
  'show-more',
  'sidebar',
  'success',
  'user',
  'warning',
  'back',
  'chain',
  'broken-chain',
  'share'
] as const
export const twoColorIcons = ['aggr'] as const

export const iconSizes: Record<IconSizes, number> = {
  xxsmall: 8,
  xsmall: 10,
  small: 12,
  medium: 15,
  large: 18,
  xlarge: 20,
  xxlarge: 32,
  xxxlarge: 77
}

export const cmkIconVariants = cva('', {
  variants: {
    variant: {
      plain: '',
      inline: 'cmk-icon--inline'
    },
    colored: {
      true: '',
      false: 'cmk-icon--colorless'
    },
    size: {
      xxsmall: 'cmk-icon--xxsmall',
      xsmall: 'cmk-icon--xsmall',
      small: 'cmk-icon--small',
      medium: 'cmk-icon--medium',
      large: 'cmk-icon--large',
      xlarge: 'cmk-icon--xlarge',
      xxlarge: 'cmk-icon--xxlarge',
      xxxlarge: 'cmk-icon--xxxlarge'
    } satisfies Record<IconSizes, string>
  },
  defaultVariants: {
    variant: 'plain',
    colored: true,
    size: 'medium'
  }
})

export const cmkMultitoneIconVariants = cva('', {
  variants: {
    color: {
      success: 'green',
      hosts: 'blue',
      info: 'blue',
      warning: 'yellow',
      services: 'yellow',
      danger: 'red',
      customization: 'pink',
      others: 'grey',
      users: 'purple',
      specialAgents: 'cyan',
      font: 'font'
    }
  }
})

export const unthemedIcons: Partial<Record<IconNames | '2fa' | '2fa-backup-codes', string>> = {
  '2fa': lightIcon2faSvg,
  '2fa-backup-codes': lightIcon2faBackupCodesSvg,
  abort: lightIconAbortPng,
  'about-checkmk': lightIconAboutCheckmkSvg,
  accept: lightIconAcceptSvg,
  'accept-all': lightIconAcceptAllSvg,
  ack: lightIconAckPng,
  'acknowledge-test': lightIconAcknowledgeTestPng,
  action: lightIconActionPng,
  activate: lightIconActivatePng,
  add: lightIconAddPng,
  'add-dashlet': lightIconAddDashletPng,
  'agent-output': lightIconAgentOutputPng,
  agents: lightIconAgentsSvg,
  aggr: lightIconAggrSvg,
  'aggr-single': lightIconAggrSingleSvg,
  'aggr-single-problem': lightIconAggrSingleProblemSvg,
  aggrcomp: lightIconAggrcompPng,
  'aix-tgz': lightIconAixTgzSvg,
  alert: lightIconAlertPng,
  'alert-ack': lightIconAlertAckPng,
  'alert-ackstop': lightIconAlertAckstopPng,
  'alert-alert-handler-failed': lightIconAlertAlertHandlerFailedPng,
  'alert-alert-handler-started': lightIconAlertAlertHandlerStartedPng,
  'alert-alert-handler-stopped': lightIconAlertAlertHandlerStoppedPng,
  'alert-cmk-notify': lightIconAlertCmkNotifyPng,
  'alert-command': lightIconAlertCommandPng,
  'alert-crit': lightIconAlertCritSvg,
  'alert-down': lightIconAlertDownPng,
  'alert-downtime': lightIconAlertDowntimePng,
  'alert-downtimestop': lightIconAlertDowntimestopPng,
  'alert-flapping': lightIconAlertFlappingPng,
  'alert-handlers': lightIconAlertHandlersSvg,
  'alert-notify': lightIconAlertNotifyPng,
  'alert-notify-progress': lightIconAlertNotifyProgressPng,
  'alert-notify-result': lightIconAlertNotifyResultPng,
  'alert-ok': lightIconAlertOkPng,
  'alert-overview': lightIconAlertOverviewSvg,
  'alert-reload': lightIconAlertReloadPng,
  'alert-restart': lightIconAlertRestartPng,
  'alert-start': lightIconAlertStartPng,
  'alert-stop': lightIconAlertStopPng,
  'alert-timeline': lightIconAlertTimelineSvg,
  'alert-unknown': lightIconAlertUnknownPng,
  'alert-unreach': lightIconAlertUnreachPng,
  'alert-up': lightIconAlertUpPng,
  'alert-warn': lightIconAlertWarnPng,
  alerts: lightIconAlertsSvg,
  'all-states': lightIconAllStatesPng,
  analysis: lightIconAnalysisSvg,
  'analyze-config': lightIconAnalyzeConfigSvg,
  annotation: lightIconAnnotationPng,
  api: lightIconApiSvg,
  'app-monitoring-topic': lightIconAppMonitoringTopicSvg,
  apply: lightIconApplyPng,
  'ar-simulate': lightIconArSimulatePng,
  'archive-event': lightIconArchiveEventPng,
  'assume-0': lightIconAssume0Png,
  'assume-1': lightIconAssume1Png,
  'assume-2': lightIconAssume2Png,
  'assume-3': lightIconAssume3Png,
  'assume-bg': lightAssumeBgPng,
  'assume-none': lightIconAssumeNonePng,
  auditlog: lightIconAuditlogSvg,
  autherr: lightIconAutherrPng,
  authok: lightIconAuthokPng,
  'av-computation': lightIconAvComputationPng,
  availability: lightIconAvailabilitySvg,
  'aws-logo': lightIconAwsLogoSvg,
  'azure-storage': lightIconAzureStorageSvg,
  'azure-vms': lightIconAzureVmsSvg,
  back: lightIconBackPng,
  'back-off': lightIconBackOffPng,
  'background-job-details': lightIconBackgroundJobDetailsPng,
  'background-jobs': lightIconBackgroundJobsSvg,
  backup: lightIconBackupSvg,
  'backup-restore-stop': lightIconBackupRestoreStopPng,
  'backup-start': lightIconBackupStartPng,
  'backup-state': lightIconBackupStatePng,
  'backup-stop': lightIconBackupStopPng,
  'backup-target-edit': lightIconBackupTargetEditPng,
  'backup-targets': lightIconBackupTargetsSvg,
  bake: lightIconBakeSvg,
  'bake-result': lightIconBakeResultPng,
  barplot: lightIconBarplotSvg,
  'bi-freeze': lightIconBiFreezeSvg,
  bilist: lightIconBilistPng,
  bitree: lightIconBitreePng,
  'bookmark-list': lightIconBookmarkListSvg,
  bottom: lightIconBottomPng,
  bulk: lightIconBulkSvg,
  'bulk-import': lightIconBulkImportPng,
  cached: lightIconCachedPng,
  cancel: lightIconCancelSvg,
  'cannot-reschedule': lightIconCannotReschedulePng,
  certificate: lightIconCertificateSvg,
  check: lightIconCheckSvg,
  'check-parameters': lightIconCheckParametersSvg,
  'check-plugins': lightIconCheckPluginsSvg,
  checkbox: lightIconCheckboxSvg,
  'checkbox-hover-bg': lightCheckboxHoverBgPng,
  checkmark: lightIconCheckmarkSvg,
  'checkmark-bare': lightIconCheckmarkBareSvg,
  checkmk: lightIconCheckmkSvg,
  'checkmk-logo': lightIconCheckmkLogoSvg,
  'checkmk-logo-min': lightIconCheckmkLogoMinSvg,
  cleanup: lightIconCleanupPng,
  clear: lightIconClearPng,
  clipboard: lightIconClipboardSvg,
  clone: lightIconCloneSvg,
  clock: lightIconClockSvg,
  closetimewarp: lightIconClosetimewarpPng,
  cloud: lightIconCloudSvg,
  cluster: lightIconClusterPng,
  collapse: lightIconCollapsePng,
  'collapse-arrow': lightIconCollapseArrowPng,
  'color-mode': lightIconColorModeSvg,
  commands: lightIconCommandsSvg,
  condition: lightIconConditionPng,
  'connection-tests': lightIconConnectionTestsSvg,
  contactgroups: lightIconContactgroupsSvg,
  continue: lightIconContinuePng,
  copied: lightIconCopiedSvg,
  counting: lightIconCountingPng,
  crash: lightIconCrashSvg,
  'crash-glow': lightIconCrashGlowPng,
  'crit-problem': lightIconCritProblemSvg,
  critical: lightIconCriticalPng,
  cross: lightIconCrossSvg,
  'cross-grey': lightIconCrossGreySvg,
  'custom-attr': lightIconCustomAttrSvg,
  'custom-graph': lightIconCustomGraphPng,
  'custom-snapin': lightIconCustomSnapinSvg,
  'customer-management': lightIconCustomerManagementPng,
  d146n0571c5: lightIconD146n0571c5Png,
  dash: lightIconDashSvg,
  dashboard: lightIconDashboardSvg,
  'dashboard-controls': lightIconDashboardControlsPng,
  'dashboard-edit': lightIconDashboardEditSvg,
  'dashboard-main': lightIconDashboardMainSvg,
  'dashboard-problems': lightIconDashboardProblemsSvg,
  'dashboard-system': lightIconDashboardSystemSvg,
  'dashlet-anchor': lightDashletAnchorSvg,
  'dashlet-network-topology': lightIconDashletNetworkTopologyPng,
  'dashlet-nodata': lightIconDashletNodataPng,
  'dashlet-notifications-bar-chart': lightIconDashletNotificationsBarChartPng,
  'dashlet-resize': lightDashletResizeSvg,
  'dashlet-url': lightIconDashletUrlPng,
  'dcd-connections': lightIconDcdConnectionsSvg,
  'dcd-execute': lightIconDcdExecutePng,
  'dcd-history': lightIconDcdHistoryPng,
  delayed: lightIconDelayedPng,
  delete: lightIconDeleteSvg,
  'deploy-agents': lightIconDeployAgentsPng,
  'deployment-error': lightIconDeploymentErrorPng,
  'deployment-status': lightIconDeploymentStatusPng,
  'derived-downtime': lightIconDerivedDowntimePng,
  detail: lightIconDetailPng,
  'developer-resources': lightIconDeveloperResourcesSvg,
  diagnose: lightIconDiagnosePng,
  diagnostics: lightIconDiagnosticsSvg,
  'diagnostics-dump-file': lightIconDiagnosticsDumpFilePng,
  'disable-test': lightIconDisableTestPng,
  disabled: lightIconDisabledSvg,
  'disabled-service': lightIconDisabledServiceSvg,
  'dissolve-operation': lightIconDissolveOperationPng,
  docker: lightIconDockerSvg,
  down: lightIconDownPng,
  download: lightIconDownloadPng,
  'download-agents': lightIconDownloadAgentsSvg,
  'download-csv': lightIconDownloadCsvPng,
  'download-json': lightIconDownloadJsonPng,
  downtime: lightIconDowntimeSvg,
  'downtime-for-report': lightIconDowntimeForReportPng,
  edit: lightIconEditSvg,
  'edit-custom-graph': lightIconEditCustomGraphPng,
  'edit-forecast-model': lightIconEditForecastModelPng,
  email: lightIconEmailPng,
  empty: lightIconEmptyPng,
  'enable-test': lightIconEnableTestPng,
  enabled: lightIconEnabledPng,
  encrypted: lightIconEncryptedPng,
  end: lightIconEndPng,
  error: lightIconErrorPng,
  'event console-status': lightIconEventConsoleStatusSvg,
  event: lightIconEventSvg,
  'event-console': lightIconEventConsoleSvg,
  expand: lightIconExpandPng,
  export: lightIconExportPng,
  'export-rule': lightIconExportRuleSvg,
  factoryreset: lightIconFactoryresetPng,
  'fake-check-result': lightIconFakeCheckResultSvg,
  favicon: lightFaviconIco,
  filter: lightIconFilterSvg,
  'filters-set': lightIconFiltersSetPng,
  flapping: lightIconFlappingPng,
  folder: lightIconFolderSvg,
  'folder-closed': lightFolderClosedPng,
  'folder-hi': lightFolderHiPng,
  'folder-open': lightFolderOpenPng,
  folderproperties: lightIconFolderpropertiesPng,
  'forecast-graph': lightIconForecastGraphPng,
  'foreign-changes': lightIconForeignChangesPng,
  forth: lightIconForthPng,
  'forth-off': lightIconForthOffPng,
  frameurl: lightIconFrameurlSvg,
  gauge: lightIconGaugeSvg,
  gcp: lightIconGcpSvg,
  'global-settings': lightIconGlobalSettingsSvg,
  globe: lightGlobePng,
  graph: lightIconGraphSvg,
  'graph-collection': lightIconGraphCollectionPng,
  'graph-time': lightIconGraphTimeSvg,
  'graph-tuning': lightIconGraphTuningPng,
  'gui-design': lightIconGuiDesignPng,
  guitest: lightIconGuitestPng,
  'hard-states': lightIconHardStatesPng,
  hardware: lightIconHardwareSvg,
  'help-activated': lightIconHelpActivatedSvg,
  hierarchy: lightIconHierarchySvg,
  history: lightIconHistoryPng,
  host: lightIconHostPng,
  'host-graph': lightIconHostGraphSvg,
  'host-problems': lightIconHostProblemsSvg,
  'host-state': lightIconHostStateSvg,
  'host-state-summary': lightIconHostStateSummarySvg,
  'host-statistics': lightIconHostStatisticsSvg,
  'host-svc-problems-dark': lightIconHostSvcProblemsDarkSvg,
  hostgroups: lightIconHostgroupsSvg,
  ical: lightIconIcalPng,
  icons: lightIconIconsSvg,
  ignore: lightIconIgnorePng,
  inactive: lightIconInactivePng,
  'influxdb-connections': lightIconInfluxdbConnectionsSvg,
  info: lightIconInfoSvg,
  'inline-error': lightIconInlineErrorSvg,
  insert: lightIconInsertSvg,
  insertdate: lightIconInsertdateSvg,
  install: lightIconInstallPng,
  'integrations-custom': lightIconIntegrationsCustomSvg,
  'integrations-other': lightIconIntegrationsOtherSvg,
  inv: lightIconInvPng,
  inventory: lightIconInventorySvg,
  'inventory-failed': lightIconInventoryFailedPng,
  inverted: lightIconInvertedPng,
  kubernetes: lightIconKubernetesSvg,
  'laptop-50': lightIconLaptop50Png,
  ldap: lightIconLdapSvg,
  'learning-beginner': lightIconLearningBeginnerSvg,
  'learning-checkmk': lightIconLearningCheckmkSvg,
  'learning-forum': lightIconLearningForumSvg,
  'learning-guide': lightIconLearningGuideSvg,
  'learning-video-tutorials': lightIconLearningVideoTutorialsSvg,
  'license-failed': lightIconLicenseFailedPng,
  'license-successful': lightIconLicenseSuccessfulPng,
  'license-unknown-state': lightIconLicenseUnknownStatePng,
  licensing: lightIconLicensingSvg,
  lightbulb: lightIconLightbulbSvg,
  'lightbulb-idea': lightIconLightbulbIdeaSvg,
  link: lightIconLinkPng,
  linux: lightIconLinuxSvg,
  'linux-deb': lightIconLinuxDebSvg,
  'linux-rpm': lightIconLinuxRpmSvg,
  'linux-tgz': lightIconLinuxTgzSvg,
  'load-graph': lightLoadGraphPng,
  localrule: lightIconLocalrulePng,
  log: lightIconLogSvg,
  login: lightIconLoginPng,
  'logo-cmk-small': lightLogoCmkSmallPng,
  logwatch: lightIconLogwatchPng,
  'magic-move': lightIconMagicMovePng,
  'main-changes-active': lightIconMainChangesActiveSvg,
  'main-customize-active': lightIconMainCustomizeActiveSvg,
  'main-help-active': lightIconMainHelpActiveSvg,
  'main-monitoring-active': lightIconMainMonitoringActiveSvg,
  'main-search-active': lightIconMainSearchActiveSvg,
  'main-setup-active': lightIconMainSetupActiveSvg,
  'main-user-active': lightIconMainUserActiveSvg,
  'manual-active': lightIconManualActiveSvg,
  matrix: lightIconMatrixPng,
  menu: lightIconMenuPng,
  'menu-item-checked': lightIconMenuItemCheckedPng,
  'menu-item-unchecked': lightIconMenuItemUncheckedPng,
  message: lightIconMessageSvg,
  'migrate-users': lightIconMigrateUsersSvg,
  missing: lightIconMissingSvg,
  'mkeventd-rules': lightIconMkeventdRulesPng,
  mkps: lightIconMkpsSvg,
  'monitored-service': lightIconMonitoredServiceSvg,
  move: lightIconMovePng,
  movedown: lightIconMovedownPng,
  moveup: lightIconMoveupPng,
  nagvis: lightIconNagvisPng,
  'need-replicate': lightIconNeedReplicatePng,
  'need-restart': lightIconNeedRestartPng,
  'network-services': lightIconNetworkServicesSvg,
  'network-topology': lightIconNetworkTopologySvg,
  networking: lightIconNetworkingSvg,
  new: lightIconNewSvg,
  'new-cluster': lightIconNewClusterPng,
  'new-mkp': lightIconNewMkpPng,
  newfolder: lightIconNewfolderPng,
  'no-entry': lightIconNoEntrySvg,
  'no-pending-changes': lightIconNoPendingChangesSvg,
  'no-revert': lightIconNoRevertSvg,
  nodowntime: lightIconNodowntimePng,
  notes: lightIconNotesPng,
  'notif-disabled': lightIconNotifDisabledPng,
  'notif-enabled': lightIconNotifEnabledPng,
  'notif-man-disabled': lightIconNotifManDisabledPng,
  'notification-enabled': lightIconNotificationEnabledPng,
  'notification-timeline': lightIconNotificationTimelineSvg,
  notifications: lightIconNotificationsSvg,
  npassive: lightIconNpassivePng,
  ntop: lightIconNtopSvg,
  ooservice: lightOoservicePng,
  'open-telemetry': lightIconOpenTelemetrySvg,
  opentelemetry: lightIconOpentelemetrySvg,
  'os-other': lightIconOsOtherSvg,
  'otel-collector': lightIconOtelCollectorSvg,
  'outof-serviceperiod': lightIconOutofServiceperiodPng,
  outofnot: lightIconOutofnotPng,
  packages: lightIconPackagesSvg,
  'pagetype-topic': lightIconPagetypeTopicSvg,
  pageurl: lightIconPageurlSvg,
  painteroptions: lightIconPainteroptionsSvg,
  'painteroptions-down-hi': lightIconPainteroptionsDownHiPng,
  'painteroptions-down-lo': lightIconPainteroptionsDownLoPng,
  'painteroptions-off': lightIconPainteroptionsOffPng,
  parentscan: lightIconParentscanPng,
  passwords: lightIconPasswordsSvg,
  pause: lightIconPausePng,
  'pending-changes': lightIconPendingChangesSvg,
  'pending-task': lightIconPendingTaskSvg,
  'percentage-of-service-problems': lightIconPercentageOfServiceProblemsSvg,
  persist: lightIconPersistPng,
  'pie-chart': lightIconPieChartPng,
  'plugins-agentless': lightIconPluginsAgentlessSvg,
  'plugins-app': lightIconPluginsAppPng,
  'plugins-cloud': lightIconPluginsCloudSvg,
  'plugins-containerization': lightIconPluginsContainerizationSvg,
  'plugins-generic': lightIconPluginsGenericSvg,
  'plugins-hw': lightIconPluginsHwPng,
  'plugins-os': lightIconPluginsOsSvg,
  'plugins-virtual': lightIconPluginsVirtualSvg,
  pluginurl: lightPluginurlPng,
  plus: lightIconPlusSvg,
  pnp: lightIconPnpPng,
  'predefined-conditions': lightIconPredefinedConditionsSvg,
  prediction: lightIconPredictionPng,
  problem: lightIconProblemSvg,
  prometheus: lightIconPrometheusSvg,
  'qs-aws': lightIconQsAwsSvg,
  'qs-azure': lightIconQsAzureSvg,
  'qs-gcp': lightIconQsGcpSvg,
  'qs-otel': lightIconQsOtelSvg,
  'qs-prometheus': lightIconQsPrometheusSvg,
  'qs-relay': lightIconQsRelaySvg,
  'quick-setup-aws': lightIconQuickSetupAwsSvg,
  quicksearch: lightIconQuicksearchPng,
  'quicksearch-field-bg': lightQuicksearchFieldBgPng,
  random: lightIconRandomPng,
  rank: lightIconRankSvg,
  'read-only': lightIconReadOnlySvg,
  'recreate-broker-certificate': lightIconRecreateBrokerCertificateSvg,
  redo: lightIconRedoSvg,
  'relay-menu': lightIconRelayMenuSvg,
  'release-deploy': lightReleaseDeploySvg,
  'release-mkp': lightIconReleaseMkpPng,
  'release-mkp-yellow': lightIconReleaseMkpYellowPng,
  'release-scale': lightReleaseScaleSvg,
  reload: lightIconReloadSvg,
  reloadsnapin: lightIconReloadsnapinPng,
  'reloadsnapin-lo-alt': lightIconReloadsnapinLoAltPng,
  'rename-host': lightIconRenameHostSvg,
  'repl-25': lightIconRepl25Png,
  'repl-50': lightIconRepl50Png,
  'repl-75': lightIconRepl75Png,
  'repl-failed': lightIconReplFailedPng,
  'repl-locked': lightIconReplLockedPng,
  'repl-pending': lightIconReplPendingPng,
  'repl-success': lightIconReplSuccessPng,
  replay: lightIconReplayPng,
  replicate: lightIconReplicatePng,
  report: lightIconReportSvg,
  'report-element': lightIconReportElementPng,
  'report-fixed': lightIconReportFixedPng,
  'report-store': lightIconReportStorePng,
  reportscheduler: lightIconReportschedulerPng,
  reset: lightIconResetPng,
  resetcounters: lightIconResetcountersPng,
  resize: lightIconResizePng,
  'resize-graph': lightResizeGraphPng,
  restart: lightIconRestartPng,
  restore: lightIconRestorePng,
  revert: lightIconRevertSvg,
  'rj45-50': lightIconRj4550Png,
  roles: lightIconRolesSvg,
  'rotate-left': lightIconRotateLeftPng,
  rule: lightIconRuleSvg,
  'rule-no': lightIconRuleNoPng,
  'rule-no-off': lightIconRuleNoOffPng,
  'rule-yes': lightIconRuleYesPng,
  'rule-yes-off': lightIconRuleYesOffPng,
  rules: lightIconRulesSvg,
  'rulesets-deprecated': lightIconRulesetsDeprecatedPng,
  'rulesets-ineffective': lightIconRulesetsIneffectivePng,
  saml: lightIconSamlSvg,
  save: lightIconSaveSvg,
  'save-dashboard': lightIconSaveDashboardSvg,
  'save-graph': lightIconSaveGraphSvg,
  'save-to-folder': lightIconSaveToFolderSvg,
  'save-to-services': lightIconSaveToServicesSvg,
  'save-view': lightIconSaveViewSvg,
  scatterplot: lightIconScatterplotSvg,
  'service-discovery': lightIconServiceDiscoverySvg,
  'service-duration': lightIconServiceDurationSvg,
  'service-graph': lightIconServiceGraphSvg,
  'service-label-add': lightIconServiceLabelAddSvg,
  'service-label-remove': lightIconServiceLabelRemoveSvg,
  'service-label-update': lightIconServiceLabelUpdateSvg,
  'service-state': lightIconServiceStateSvg,
  'service-to-disabled': lightIconServiceToDisabledSvg,
  'service-to-ignored': lightIconServiceToIgnoredSvg,
  'service-to-monitored': lightIconServiceToMonitoredSvg,
  'service-to-new': lightIconServiceToNewSvg,
  'service-to-removed': lightIconServiceToRemovedSvg,
  'service-to-unchanged': lightIconServiceToUnchangedSvg,
  'service-to-undecided': lightIconServiceToUndecidedSvg,
  servicegroups: lightIconServicegroupsSvg,
  services: lightIconServicesSvg,
  'services-fix-all': lightIconServicesFixAllSvg,
  'services-green': lightIconServicesGreenSvg,
  'services-refresh': lightIconServicesRefreshSvg,
  'services-stop': lightIconServicesStopPng,
  'services-tabula-rasa': lightIconServicesTabulaRasaSvg,
  'show-less-green': lightIconShowLessGreenSvg,
  'show-more-green': lightIconShowMoreGreenSvg,
  showbi: lightIconShowbiPng,
  showhide: lightIconShowhidePng,
  sidebar: lightIconSidebarSvg,
  'sidebar-logout': lightIconSidebarLogoutSvg,
  'sidebar-position': lightIconSidebarPositionSvg,
  'sidebar-top': lightSidebarTopPng,
  sign: lightIconSignSvg,
  'signature-key': lightIconSignatureKeySvg,
  'signature-key-partial': lightIconSignatureKeyPartialPng,
  'single-metric': lightIconSingleMetricSvg,
  'site-globals': lightIconSiteGlobalsPng,
  'site-globals-modified': lightIconSiteGlobalsModifiedPng,
  'site-overview': lightIconSiteOverviewSvg,
  sites: lightIconSitesSvg,
  sla: lightIconSlaSvg,
  'sla-configuration': lightIconSlaConfigurationPng,
  'snapin-greyswitch-off': lightIconSnapinGreyswitchOffPng,
  'snapin-greyswitch-on': lightIconSnapinGreyswitchOnPng,
  snapshot: lightIconSnapshotPng,
  'snapshot-checksum': lightIconSnapshotChecksumPng,
  'snapshot-nchecksum': lightIconSnapshotNchecksumPng,
  'snapshot-pchecksum': lightIconSnapshotPchecksumPng,
  snmp: lightIconSnmpSvg,
  software: lightIconSoftwareSvg,
  'solaris-pkg': lightIconSolarisPkgSvg,
  'solaris-tgz': lightIconSolarisTgzSvg,
  someproblem: lightSomeproblemPng,
  starred: lightIconStarredPng,
  start: lightIconStartPng,
  'static-checks': lightIconStaticChecksSvg,
  'static-text': lightIconStaticTextSvg,
  status: lightIconStatusSvg,
  'status-report': lightStatusReportPng,
  'svc-problems': lightIconSvcProblemsSvg,
  'sync-graphs': lightIconSyncGraphsPng,
  'sync-mkp': lightIconSyncMkpPng,
  'synthetic-monitoring-purple': lightIconSyntheticMonitoringPurpleSvg,
  'synthetic-monitoring-topic': lightIconSyntheticMonitoringTopicSvg,
  'synthetic-monitoring-yellow': lightIconSyntheticMonitoringYellowSvg,
  tag: lightIconTagSvg,
  timeline: lightIconTimelinePng,
  timeperiods: lightIconTimeperiodsSvg,
  timewarp: lightIconTimewarpPng,
  'timewarp-off': lightIconTimewarpOffPng,
  tls: lightIconTlsSvg,
  'toggle-context': lightIconToggleContextPng,
  'toggle-details': lightIconToggleDetailsPng,
  'toggle-on': lightIconToggleOnSvg,
  top: lightIconTopPng,
  'top-list': lightIconTopListSvg,
  'topic-2fa': lightIconTopic2faSvg,
  'topic-administration': lightIconTopicAdministrationPng,
  'topic-agents': lightIconTopicAgentsPng,
  'topic-analyze': lightIconTopicAnalyzePng,
  'topic-applications': lightIconTopicApplicationsPng,
  'topic-bi': lightIconTopicBiPng,
  'topic-change-password': lightIconTopicChangePasswordPng,
  'topic-checkmk': lightIconTopicCheckmkSvg,
  'topic-events': lightIconTopicEventsPng,
  'topic-exporter': lightIconTopicExporterSvg,
  'topic-general': lightIconTopicGeneralPng,
  'topic-graphs': lightIconTopicGraphsPng,
  'topic-history': lightIconTopicHistoryPng,
  'topic-hosts': lightIconTopicHostsPng,
  'topic-inventory': lightIconTopicInventoryPng,
  'topic-maintenance': lightIconTopicMaintenancePng,
  'topic-monitoring': lightIconTopicMonitoringSvg,
  'topic-my-workplace': lightIconTopicMyWorkplaceSvg,
  'topic-network': lightIconTopicNetworkSvg,
  'topic-other': lightIconTopicOtherPng,
  'topic-overview': lightIconTopicOverviewPng,
  'topic-problems': lightIconTopicProblemsPng,
  'topic-profile': lightIconTopicProfilePng,
  'topic-quick-setups': lightIconTopicQuickSetupsSvg,
  'topic-reporting': lightIconTopicReportingSvg,
  'topic-services': lightIconTopicServicesPng,
  'topic-site': lightIconTopicSitePng,
  'topic-system': lightIconTopicSystemSvg,
  'topic-user-interface': lightIconTopicUserInterfaceSvg,
  'topic-users': lightIconTopicUsersPng,
  'topic-visualization': lightIconTopicVisualizationPng,
  trans: lightIconTransSvg,
  trust: lightIconTrustPng,
  twofa: lightIcon2faSvg,
  'twofa-backup-codes': lightIcon2faBackupCodesSvg,
  'unacknowledge-test': lightIconUnacknowledgeTestPng,
  'undecided-service': lightIconUndecidedServiceSvg,
  undo: lightIconUndoSvg,
  'unpackaged-files': lightIconUnpackagedFilesPng,
  unusedbirules: lightIconUnusedbirulesPng,
  up: lightIconUpPng,
  update: lightIconUpdatePng,
  'update-discovery-parameters': lightIconUpdateDiscoveryParametersSvg,
  'update-host-labels': lightIconUpdateHostLabelsSvg,
  'update-service-labels': lightIconUpdateServiceLabelsSvg,
  upgrade: lightIconUpgradeSvg,
  upload: lightIconUploadPng,
  url: lightIconUrlPng,
  usedrulesets: lightIconUsedrulesetsPng,
  'user-locked': lightIconUserLockedPng,
  users: lightIconUsersSvg,
  'validation-error': lightIconValidationErrorPng,
  video: lightIconVideoPng,
  view: lightIconViewSvg,
  'view-columns': lightIconViewColumnsPng,
  'view-copy': lightIconViewCopySvg,
  'view-link': lightIconViewLinkSvg,
  'view-refresh': lightIconViewRefreshPng,
  vsphere: lightIconVsphereSvg,
  warning: lightIconWarningPng,
  wato: lightIconWatoPng,
  'wato-changes': lightIconWatoChangesPng,
  'wato-nochanges': lightIconWatoNochangesPng,
  'werk-ack': lightIconWerkAckPng,
  'widget-clone': lightIconWidgetCloneSvg,
  'widget-delete': lightIconWidgetDeleteSvg,
  'widget-edit': lightIconWidgetEditSvg,
  wikisearch: lightIconWikisearchPng,
  'windows-msi': lightIconWindowsMsiSvg,
  'wrong-agent': lightIconWrongAgentPng,
  www: lightIconWwwPng,
  zoom: lightIconZoomPng
}

export const themedIcons: Record<string, Partial<Record<IconNames, string>>> = {
  light: {
    'add-rule': lightIconAddRuleSvg,
    'agent-registration': lightIconAgentRegistrationSvg,
    analyze: lightIconAnalyzeSvg,
    assign: lightIconAssignSvg,
    aws: lightIconAwsSvg,
    'cancel-notifications': lightIconCancelNotificationsSvg,
    'checkmark-bg-white': lightIconCheckmarkBgWhiteSvg,
    'checkmark-orange': lightIconCheckmarkOrangeSvg,
    'checkmark-plus': lightIconCheckmarkPlusSvg,
    close: lightIconCloseSvg,
    comment: lightIconCommentSvg,
    configuration: lightIconConfigurationSvg,
    'cross-bg-white': lightIconCrossBgWhiteSvg,
    'dashboard-grid': lightIconDashboardGridSvg,
    'dashboard-menuarrow': lightIconDashboardMenuarrowSvg,
    'dashlet-clone': lightDashletCloneSvg,
    'dashlet-delete': lightDashletDeleteSvg,
    'dashlet-edit': lightDashletEditSvg,
    drag: lightIconDragSvg,
    'export-link': lightIconExportLinkSvg,
    external: lightIconExternalSvg,
    favorite: lightIconFavoriteSvg,
    'filter-line': lightIconFilterLineSvg,
    fixall: lightIconFixallSvg,
    'folder-blue': lightIconFolderBlueSvg,
    help: lightIconHelpSvg,
    home: lightIconHomeSvg,
    'host-svc-problems': lightIconHostSvcProblemsSvg,
    hyphen: lightIconHyphenSvg,
    'info-circle': lightIconInfoCircleSvg,
    'main-changes': lightIconMainChangesSvg,
    'main-customize': lightIconMainCustomizeSvg,
    'main-help': lightIconMainHelpSvg,
    'main-monitoring': lightIconMainMonitoringSvg,
    'main-search': lightIconMainSearchSvg,
    'main-setup': lightIconMainSetupSvg,
    'main-user': lightIconMainUserSvg,
    manual: lightIconManualSvg,
    nagios: lightIconNagiosSvg,
    network: lightIconNetworkSvg,
    'performance-data': lightIconPerformanceDataSvg,
    'release-automated': lightReleaseAutomatedSvg,
    'reload-cmk': lightIconReloadCmkSvg,
    rulesets: lightIconRulesetsSvg,
    saas: lightIconSaasSvg,
    search: lightIconSearchSvg,
    'search-action': lightIconSearchActionSvg,
    'search-action-button': lightIconSearchActionButtonSvg,
    'select-arrow': lightIconSelectArrowSvg,
    'services-blue': lightIconServicesBlueSvg,
    'show-less': lightIconShowLessSvg,
    'show-more': lightIconShowMoreSvg,
    'sidebar-folded': lightIconSidebarFoldedSvg,
    'site-dead': lightIconSiteDeadSvg,
    'site-disabled': lightIconSiteDisabledSvg,
    'site-down': lightIconSiteDownSvg,
    'site-missing': lightIconSiteMissingSvg,
    'site-unreach': lightIconSiteUnreachSvg,
    'site-waiting': lightIconSiteWaitingSvg,
    snmpmib: lightIconSnmpmibSvg,
    sparkle: lightIconSparkleSvg,
    'sparkle-white': lightIconSparkleWhiteSvg,
    speedometer: lightSpeedometerSvg,
    stale: lightIconStaleSvg,
    suggestion: lightIconSuggestionSvg,
    'table-actions-off': lightIconTableActionsOffSvg,
    'table-actions-on': lightIconTableActionsOnSvg,
    tick: lightIconTickSvg,
    'toggle-off': lightIconToggleOffSvg,
    'tree-closed': lightIconTreeClosedSvg,
    qa: lightIconQaSvg,
    development: lightIconDevelopmentSvg,
    product: lightIconProductSvg,
    unavailable: lightIconUnavailableSvg,
    ux: lightIconUXSvg
  },
  dark: {
    'add-rule': darkIconAddRuleSvg,
    'agent-registration': darkIconAgentRegistrationSvg,
    analyze: darkIconAnalyzeSvg,
    assign: darkIconAssignSvg,
    aws: darkIconAwsSvg,
    'cancel-notifications': darkIconCancelNotificationsSvg,
    'checkmark-bg-white': darkIconCheckmarkBgWhiteSvg,
    'checkmark-orange': darkIconCheckmarkOrangeSvg,
    'checkmark-plus': darkIconCheckmarkPlusSvg,
    close: darkIconCloseSvg,
    comment: darkIconCommentSvg,
    configuration: darkIconConfigurationSvg,
    'cross-bg-white': darkIconCrossBgWhiteSvg,
    'dashboard-grid': darkIconDashboardGridSvg,
    'dashboard-menuarrow': darkIconDashboardMenuarrowSvg,
    'dashlet-clone': darkDashletCloneSvg,
    'dashlet-delete': darkDashletDeleteSvg,
    'dashlet-edit': darkDashletEditSvg,
    drag: darkIconDragSvg,
    'export-link': darkIconExportLinkSvg,
    external: darkIconExternalSvg,
    favorite: darkIconFavoriteSvg,
    'filter-line': darkIconFilterLineSvg,
    fixall: darkIconFixallSvg,
    'folder-blue': darkIconFolderBlueSvg,
    help: darkIconHelpSvg,
    home: darkIconHomeSvg,
    'host-svc-problems': darkIconHostSvcProblemsSvg,
    hyphen: darkIconHyphenSvg,
    'info-circle': darkIconInfoCircleSvg,
    'main-changes': darkIconMainChangesSvg,
    'main-customize': darkIconMainCustomizeSvg,
    'main-help': darkIconMainHelpSvg,
    'main-monitoring': darkIconMainMonitoringSvg,
    'main-search': darkIconMainSearchSvg,
    'main-setup': darkIconMainSetupSvg,
    'main-user': darkIconMainUserSvg,
    manual: darkIconManualSvg,
    nagios: darkIconNagiosSvg,
    network: darkIconNetworkSvg,
    'performance-data': darkIconPerformanceDataSvg,
    'release-automated': darkReleaseAutomatedSvg,
    'reload-cmk': darkIconReloadCmkSvg,
    rulesets: darkIconRulesetsSvg,
    saas: darkIconSaasSvg,
    search: darkIconSearchSvg,
    'search-action': darkIconSearchActionSvg,
    'search-action-button': darkIconSearchActionButtonSvg,
    'select-arrow': darkIconSelectArrowSvg,
    'services-blue': darkIconServicesBlueSvg,
    'show-less': darkIconShowLessSvg,
    'show-more': darkIconShowMoreSvg,
    'sidebar-folded': darkIconSidebarFoldedSvg,
    'site-dead': darkIconSiteDeadSvg,
    'site-disabled': darkIconSiteDisabledSvg,
    'site-down': darkIconSiteDownSvg,
    'site-missing': darkIconSiteMissingSvg,
    'site-unreach': darkIconSiteUnreachSvg,
    'site-waiting': darkIconSiteWaitingSvg,
    snmpmib: darkIconSnmpmibSvg,
    sparkle: darkIconSparkleSvg,
    'sparkle-white': darkIconSparkleWhiteSvg,
    speedometer: darkSpeedometerSvg,
    stale: darkIconStaleSvg,
    suggestion: darkIconSuggestionSvg,
    'table-actions-off': darkIconTableActionsOffSvg,
    'table-actions-on': darkIconTableActionsOnSvg,
    tick: darkIconTickSvg,
    'toggle-off': darkIconToggleOffSvg,
    'tree-closed': darkIconTreeClosedSvg,
    qa: darkIconQaSvg,
    development: darkIconDevelopmentSvg,
    product: darkIconProductSvg,
    unavailable: darkIconUnavailableSvg,
    ux: darkIconUXSvg
  }
}
