/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import './assets/main.css'
import '@/assets/variables.css'

import { createApp } from 'vue'
import DemoApp from './DemoApp.vue'
import router from './router'

const app = createApp(DemoApp)
app.use(router)
app.mount('#app')
