/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import 'core-js/stable'

import $ from 'jquery'
import { createApp } from 'vue'

import D3Table from './views/D3Table.vue'
import Form from './views/Form.vue'
import Table from './views/Table.vue'

function setup_vue() {
  document.querySelectorAll<HTMLFormElement>('div[data-cmk_vue_app]').forEach((div, _) => {
    const dataset = div.dataset
    if (dataset == undefined) return

    const vue_app_data = dataset.cmk_vue_app
    if (vue_app_data == undefined) return
    const vueApp = JSON.parse(vue_app_data)

    if (vueApp.app_name == 'demo') {
      const app = createApp(Form, {
        form_spec: {
          id: vueApp.id,
          component: vueApp.component
        }
      })
      app.use(Form)
      app.mount(div)
    } else if (vueApp.app_name == 'd3_table') {
      console.log('vue create table')
      const app = createApp(D3Table, {
        table_spec: vueApp.component
      })
      app.use(Form)
      app.mount(div)
      console.log('vue fully mounted table')
    } else if (vueApp.app_name == 'vue_table') {
      console.log('vue create table')
      const app = createApp(Table, {
        table_spec: vueApp.component
      })
      app.use(Form)
      app.mount(div)
      console.log('vue fully mounted table')
    } else {
      throw `can not load vue app "${vueApp.app_name}"`
    }
  })
}

$(() => {
  // -> change to X.onload?
  setup_vue()
})

export const cmk_export = {}
