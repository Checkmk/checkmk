/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Dedicated entry point for the page chrome that is present on (nearly) every
// page: the main navigation, the sidebar, the AI assistant panel and the loading
// transition. Keeping these in their own small bundle decouples them from the
// large `main.ts` bundle, so they can be registered and become interactive
// without waiting for the heavy content apps (dashboard, forms, ...) to download
// and execute.
import initCmkUi from 'cmk-ui-library/lib/initCmkUi'

import { registerNonFreeComponent } from '@/lib/web-component/registerNonFreeComponent'

import '@/assets/variables.css'
import { translationLoader } from '@/translationLoader'

import LoadingTransition from './loading-transition/LoadingTransition.vue'
import MainMenuApp from './main-menu/MainMenuApp.vue'
import SidebarApp from './sidebar/SidebarApp.vue'

// Inject monolithic translation catalog from cmk-frontend-vue.
const { defineCmkComponent } = initCmkUi({ translationLoader })

defineCmkComponent('cmk-main-menu', MainMenuApp)
defineCmkComponent('cmk-sidebar', SidebarApp)
defineCmkComponent('cmk-loading-transition', LoadingTransition, { appprops: { fullPage: true } })

registerNonFreeComponent(
  defineCmkComponent,
  'cmk-ai-assistant-panel',
  import.meta.glob('./nonfree/ai/AiAssistantPanelApp.vue', { eager: true })
)
