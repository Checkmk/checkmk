/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Dedicated entry point for the page chrome that is present on (nearly) every
// page: the main navigation, the sidebar and the loading transition. Keeping
// these in their own small bundle decouples them from the large `main.ts`
// bundle, so they can be registered and become interactive without waiting for
// the heavy content apps (dashboard, forms, ...) to download and execute.
import defineCmkComponent from '@/lib/web-component/defineCmkComponent'

import '@/assets/variables.css'

import LoadingTransition from './loading-transition/LoadingTransition.vue'
import MainMenuApp from './main-menu/MainMenuApp.vue'
import SidebarApp from './sidebar/SidebarApp.vue'

defineCmkComponent('cmk-main-menu', MainMenuApp)
defineCmkComponent('cmk-sidebar', SidebarApp)
defineCmkComponent('cmk-loading-transition', LoadingTransition, { appprops: { fullPage: true } })
