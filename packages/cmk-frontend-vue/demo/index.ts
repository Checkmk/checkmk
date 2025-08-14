/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import './_demo/assets/main.css'
import '@/assets/variables.css'

import { createApp } from 'vue'
import { createi18n } from '@/lib/i18n'
import DemoApp from './_demo/DemoApp.vue'
import router from './_demo/router'

const i18n = createi18n()

const app = createApp(DemoApp)
app.use(i18n)
app.use(router)
app.mount('#app')

import 'vue-router'
export {}

declare module 'vue-router' {
  interface RouteMeta {
    name: string
  }
}
