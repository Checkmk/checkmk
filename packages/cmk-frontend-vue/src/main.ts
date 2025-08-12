/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import defineCmkComponent from '@/lib/defineCmkComponent'
import AgentDownload from './setup/AgentDownloadApp.vue'
import QuickSetup from './quick-setup/QuickSetupApp.vue'
import NotificationOverview from './notification/NotificationOverviewApp.vue'
import { FormApp } from '@/form'
import NotificationParametersOverviewApp from '@/notification/NotificationParametersOverviewApp.vue'
import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'
import ModeHostApp from '@/mode-host/ModeHostApp.vue'
import WelcomeApp from './welcome/WelcomeApp.vue'
import ChangesApp from './main-menu/ChangesApp.vue'

import '@/assets/variables.css'
import UnifiedSearchApp from './unified-search/UnifiedSearchApp.vue'
import WelcomeSnapin from './welcome/components/snapin/WelcomeSnapin.vue'
import WelcomeSnapinSlideout from '@/welcome/components/snapin/WelcomeSnapinSlideout.vue'

defineCmkComponent('cmk-form-spec', FormApp)
defineCmkComponent('cmk-quick-setup', QuickSetup)
defineCmkComponent('cmk-notification-overview', NotificationOverview)
defineCmkComponent('cmk-agent-download', AgentDownload)
defineCmkComponent('cmk-notification-parameters-overview', NotificationParametersOverviewApp)
defineCmkComponent('cmk-graph-designer', GraphDesignerApp)
defineCmkComponent('cmk-mode-host', ModeHostApp)
defineCmkComponent('cmk-unified-search', UnifiedSearchApp)
defineCmkComponent('cmk-welcome', WelcomeApp)
defineCmkComponent('cmk-welcome-snapin', WelcomeSnapin)
defineCmkComponent('cmk-welcome-snapin-slideout', WelcomeSnapinSlideout)
defineCmkComponent('cmk-main-menu-changes', ChangesApp)
