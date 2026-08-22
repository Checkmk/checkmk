/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import DynamicIconApp from 'cmk-ui-library/components/CmkIcon/CmkDynamicIcon/DynamicIconApp.vue'
import IconApp from 'cmk-ui-library/components/CmkIcon/IconApp.vue'
import RnbwApp from 'cmk-ui-library/components/graphics/RnbwApp.vue'
import initCmkUi from 'cmk-ui-library/lib/initCmkUi'

import { FormApp } from '@/form'
import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

import '@/assets/variables.css'
import { registerGraphDesignerFormComponents } from '@/graph-designer/registerFormComponents'
import ModeHostApp from '@/mode-host/ModeHostApp.vue'
import NotificationParametersOverviewApp from '@/notification/NotificationParametersOverviewApp.vue'
import { translationLoader } from '@/translationLoader'

import AiExplainThisIssueApp from './ai/AiExplainButtonApp.vue'
import Dashboard from './dashboard/DashboardApp.vue'
import SharedDashboard from './dashboard/DashboardSharedApp.vue'
import DateTimePickerApp from './date-time-picker/CmkDateTimePickerApp.vue'
import DialogApp from './dialog/DialogApp.vue'
import GlobalSettingsApp from './global-settings/GlobalSettingsApp.vue'
import { GlobalTimePickerApp } from './graphing/GlobalTimePicker'
import GraphGroup from './graphing/components/GraphGroup.vue'
import CustomGraphDesignerApp from './graphing/designer/CustomGraphDesignerApp.vue'
import { registerMetricBackendFormComponents } from './metric-backend/registerFormComponents'
import CustomServicesWizardApp from './mode-custom-services/CustomServicesWizardApp.vue'
import ModeCreateOAuth2ConnectionApp from './mode-oauth2-connection/ModeCreateOAuth2ConnectionApp.vue'
import ModeRedirectOAuth2ConnectionAppCopy from './mode-oauth2-connection/ModeRedirectOAuth2ConnectionApp.vue'
import OAuth2ConnectionInfoApp from './mode-oauth2-connection/OAuth2ConnectionInfoApp.vue'
import { registerOAuth2ConnectionFormComponents } from './mode-oauth2-connection/registerFormComponents'
import ModeCreateOTelConfApp from './mode-otel/ModeCreateOTelConfApp.vue'
import ModeCreatePrometheusConfApp from './mode-otel/ModeCreatePrometheusConfApp.vue'
import ModeCreateRelayApp from './mode-relay/ModeCreateRelayApp.vue'
import AllHostsApp from './monitoring/all-hosts/AllHostsApp.vue'
import HostServicesApp from './monitoring/host-services/HostServicesApp.vue'
import MonitoringPageLinkButton from './monitoring/shared/components/MonitoringPageLinkButton.vue'
import FlowExplorerApp from './network-flow/flow-explorer/FlowExplorerApp.vue'
import NotificationOverview from './notification/NotificationOverviewApp.vue'
import ProductUsageAnalyticsApp from './product-usage-analytics/ProductUsageAnalyticsApp.vue'
import ProfilingFlamegraphApp from './profiling/ProfilingFlamegraphApp.vue'
import ProfilingProfilesListApp from './profiling/ProfilingProfilesListApp.vue'
import QuickSetup from './quick-setup/QuickSetupApp.vue'
import AgentDownload from './setup/AgentDownloadApp.vue'
import TrialModeSelectionApp from './trial-mode-selection/TrialModeSelectionApp.vue'
import TwoFactorAuthApp from './two-factor-auth/TwoFactorAuthApp.vue'
import WebAuthnRegisterButtonApp from './two-factor-auth/WebAuthnRegisterButtonApp.vue'
import UnifiedSearchApp from './unified-search/UnifiedSearchApp.vue'
import WelcomeApp from './welcome/WelcomeApp.vue'
import WelcomeSnapin from './welcome/components/snapin/WelcomeSnapin.vue'

// Inject monolithic translation catalog from cmk-frontend-vue.
const { defineCmkComponent } = initCmkUi({ translationLoader })

initializeComponentRegistry()
registerGraphDesignerFormComponents()
registerOAuth2ConnectionFormComponents()
registerMetricBackendFormComponents()

defineCmkComponent('cmk-form-spec', FormApp)
defineCmkComponent('cmk-quick-setup', QuickSetup)
defineCmkComponent('cmk-dashboard', Dashboard)
defineCmkComponent('cmk-shared-dashboard', SharedDashboard)
defineCmkComponent('cmk-notification-overview', NotificationOverview)
defineCmkComponent('cmk-agent-download', AgentDownload)
defineCmkComponent('cmk-notification-parameters-overview', NotificationParametersOverviewApp)
defineCmkComponent('cmk-mode-host', ModeHostApp)
defineCmkComponent('cmk-mode-create-otel-conf', ModeCreateOTelConfApp)
defineCmkComponent('cmk-mode-create-prometheus-conf', ModeCreatePrometheusConfApp)
defineCmkComponent('cmk-mode-custom-services', CustomServicesWizardApp)
defineCmkComponent('cmk-mode-create-relay', ModeCreateRelayApp)
defineCmkComponent('cmk-mode-create-oauth2-connection', ModeCreateOAuth2ConnectionApp)
defineCmkComponent('cmk-oauth2-connection-info', OAuth2ConnectionInfoApp)
defineCmkComponent('cmk-mode-redirect-oauth2-connection', ModeRedirectOAuth2ConnectionAppCopy)
defineCmkComponent('cmk-monitoring-all-hosts', AllHostsApp)
defineCmkComponent('cmk-monitoring-host-services', HostServicesApp)
defineCmkComponent('cmk-monitoring-page-link-button', MonitoringPageLinkButton)
defineCmkComponent('cmk-network-flow-explorer', FlowExplorerApp)
defineCmkComponent('cmk-unified-search', UnifiedSearchApp)
defineCmkComponent('cmk-welcome', WelcomeApp)
defineCmkComponent('cmk-welcome-snapin', WelcomeSnapin)
defineCmkComponent('cmk-global-settings', GlobalSettingsApp)
defineCmkComponent('cmk-rnbw', RnbwApp, { pure: true })
defineCmkComponent('cmk-ai-explain-button', AiExplainThisIssueApp)
defineCmkComponent('cmk-dialog', DialogApp)
defineCmkComponent('cmk-dynamic-icon', DynamicIconApp, { pure: true })
defineCmkComponent('cmk-icon', IconApp, { pure: true })
defineCmkComponent('cmk-static-icon', IconApp, { pure: true })
defineCmkComponent('cmk-two-factor-authentication', TwoFactorAuthApp)
defineCmkComponent('cmk-webauthn-register-button', WebAuthnRegisterButtonApp)
defineCmkComponent('cmk-product-usage-analytics', ProductUsageAnalyticsApp)
defineCmkComponent('cmk-trial-mode-selection', TrialModeSelectionApp)
defineCmkComponent('cmk-date-time-picker', DateTimePickerApp)
defineCmkComponent('cmk-global-time-picker', GlobalTimePickerApp)
defineCmkComponent('cmk-graph-group', GraphGroup)
defineCmkComponent('cmk-custom-graph-designer', CustomGraphDesignerApp)
defineCmkComponent('cmk-profiling-flamegraph', ProfilingFlamegraphApp)
defineCmkComponent('cmk-profiling-profiles-list', ProfilingProfilesListApp)
