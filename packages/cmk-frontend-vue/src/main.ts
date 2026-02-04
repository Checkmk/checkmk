/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import defineCmkComponent from '@/lib/web-component/defineCmkComponent'

import { FormApp } from '@/form'

import '@/assets/variables.css'
import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'
import ModeHostApp from '@/mode-host/ModeHostApp.vue'
import NotificationParametersOverviewApp from '@/notification/NotificationParametersOverviewApp.vue'

import AiExplainThisIssueApp from './ai/AiExplainButtonApp.vue'
import DynamicIconApp from './components/CmkIcon/CmkDynamicIcon/DynamicIconApp.vue'
import IconApp from './components/CmkIcon/IconApp.vue'
import RnbwApp from './components/graphics/RnbwApp.vue'
import Dashboard from './dashboard/DashboardApp.vue'
import SharedDashboard from './dashboard/DashboardSharedApp.vue'
import DialogApp from './dialog/DialogApp.vue'
import LoadingTransition from './loading-transition/LoadingTransition.vue'
import MainMenuApp from './main-menu/MainMenuApp.vue'
import ChangesApp from './main-menu/changes/ChangesApp.vue'
import ModeCreateOAuth2ConnectionApp from './mode-oauth2-connection/ModeCreateOAuth2ConnectionApp.vue'
import ModeRedirectOAuth2ConnectionAppCopy from './mode-oauth2-connection/ModeRedirectOAuth2ConnectionApp.vue'
import ModeCreateOTelConfApp from './mode-otel/ModeCreateOTelConfApp.vue'
import ModeCreateRelayApp from './mode-relay/ModeCreateRelayApp.vue'
import NotificationOverview from './notification/NotificationOverviewApp.vue'
import ProductUsageAnalyticsApp from './product-usage-analytics/ProductUsageAnalyticsApp.vue'
import QuickSetup from './quick-setup/QuickSetupApp.vue'
import AgentDownload from './setup/AgentDownloadApp.vue'
import SidebarApp from './sidebar/SidebarApp.vue'
import TwoFactorAuthApp from './two-factor-auth/TwoFactorAuthApp.vue'
import WebAuthnRegisterButtonApp from './two-factor-auth/WebAuthnRegisterButtonApp.vue'
import UnifiedSearchApp from './unified-search/UnifiedSearchApp.vue'
import WelcomeApp from './welcome/WelcomeApp.vue'
import WelcomeSnapin from './welcome/components/snapin/WelcomeSnapin.vue'

defineCmkComponent('cmk-form-spec', FormApp)
defineCmkComponent('cmk-quick-setup', QuickSetup)
defineCmkComponent('cmk-dashboard', Dashboard)
defineCmkComponent('cmk-shared-dashboard', SharedDashboard)
defineCmkComponent('cmk-notification-overview', NotificationOverview)
defineCmkComponent('cmk-agent-download', AgentDownload)
defineCmkComponent('cmk-notification-parameters-overview', NotificationParametersOverviewApp)
defineCmkComponent('cmk-graph-designer', GraphDesignerApp)
defineCmkComponent('cmk-mode-host', ModeHostApp)
defineCmkComponent('cmk-mode-create-otel-conf', ModeCreateOTelConfApp)
defineCmkComponent('cmk-mode-create-relay', ModeCreateRelayApp)
defineCmkComponent('cmk-mode-create-oauth2-connection', ModeCreateOAuth2ConnectionApp)
defineCmkComponent('cmk-mode-redirect-oauth2-connection', ModeRedirectOAuth2ConnectionAppCopy)
defineCmkComponent('cmk-sidebar', SidebarApp)
defineCmkComponent('cmk-unified-search', UnifiedSearchApp)
defineCmkComponent('cmk-welcome', WelcomeApp)
defineCmkComponent('cmk-welcome-snapin', WelcomeSnapin)
defineCmkComponent('cmk-rnbw', RnbwApp, { pure: true })
defineCmkComponent('cmk-main-menu', MainMenuApp)
defineCmkComponent('cmk-main-menu-changes', ChangesApp)
defineCmkComponent('cmk-loading-transition', LoadingTransition, { appprops: { fullPage: true } })
defineCmkComponent('cmk-ai-explain-button', AiExplainThisIssueApp)
defineCmkComponent('cmk-dialog', DialogApp)
defineCmkComponent('cmk-dynamic-icon', DynamicIconApp, { pure: true })
defineCmkComponent('cmk-icon', IconApp, { pure: true })
defineCmkComponent('cmk-static-icon', IconApp, { pure: true })
defineCmkComponent('cmk-two-factor-authentication', TwoFactorAuthApp)
defineCmkComponent('cmk-webauthn-register-button', WebAuthnRegisterButtonApp)
defineCmkComponent('cmk-product-usage-analytics', ProductUsageAnalyticsApp)
