/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { createApp } from 'vue'
import 'vue-router'

import '@/assets/variables.css'

import DemoApp from './_demo/DemoApp.vue'
import './_demo/assets/main.css'
import router from './_demo/router'

const app = createApp(DemoApp)
app.use(router)
app.mount('#app')

export {}

declare module 'vue-router' {
  interface RouteMeta {
    name: string
  }
}
