/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import './_demo/assets/main.css'
import '@/assets/variables.css'

import { createApp } from 'vue'
import DemoApp from './_demo/DemoApp.vue'
import router from './_demo/router'

const app = createApp(DemoApp)
app.use(router)
app.mount('#app')

import 'vue-router'
export {}

declare module 'vue-router' {
  interface RouteMeta {
    name: string
  }
}
