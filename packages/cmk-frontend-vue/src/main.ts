/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// see https://github.com/vuejs/eslint-plugin-vue/issues/2201
/* eslint-disable vue/one-component-per-file */

import 'core-js/stable'

import { createApp } from 'vue'

import D3Table from './views/D3Table.vue'
import { CmkRuleset } from './components/cmk-form/'
import Table from './views/CmkTable.vue'

function setup_vue() {
  document.querySelectorAll<HTMLFormElement>('div[data-cmk_vue_app]').forEach((div) => {
    const dataset = div.dataset
    if (dataset == undefined) {
      return
    }

    const vue_app_data = dataset.cmk_vue_app
    if (vue_app_data == undefined) {
      return
    }
    const vueApp = JSON.parse(vue_app_data)

    if (vueApp.app_name == 'form_spec') {
      const app = createApp(CmkRuleset, {
        id: vueApp.id,
        spec: vueApp.form_spec,
        // eslint has a false positive: assuming `data` is part of a vue component
        // eslint-disable-next-line vue/no-deprecated-data-object-declaration, vue/no-shared-component-data
        data: vueApp.model_value,
        validation: vueApp.validation_messages
      })
      app.mount(div)
    } else if (vueApp.app_name == 'd3_table') {
      console.log('vue create table')
      const app = createApp(D3Table, {
        table_spec: vueApp.component
      })
      app.mount(div)
      console.log('vue fully mounted table')
    } else if (vueApp.app_name == 'vue_table') {
      console.log('vue create table')
      const app = createApp(Table, {
        table_spec: vueApp.component
      })
      app.mount(div)
      console.log('vue fully mounted table')
    } else {
      throw `can not load vue app "${vueApp.app_name}"`
    }
  })
}

addEventListener('load', () => {
  setup_vue()
})

export const cmk_export = {}
