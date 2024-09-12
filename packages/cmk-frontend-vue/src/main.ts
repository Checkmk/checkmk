/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// see https://github.com/vuejs/eslint-plugin-vue/issues/2201
/* eslint-disable vue/one-component-per-file */

import 'core-js/stable'

import { createApp } from 'vue'

import { mixinUniqueId } from './plugins'

import D3Table from './views/D3Table.vue'
import Table from './views/CmkTable.vue'
import QuickSetup from './quick-setup/QuickSetupApp.vue'
import NotificationOverview from './notification/NotificationOverviewApp.vue'
import { FormApp } from '@/form'

function setupVue() {
  document.querySelectorAll<HTMLFormElement>('div[data-cmk_vue_app_name]').forEach((div) => {
    const dataset = div.dataset
    if (dataset === undefined) {
      return
    }

    const appName = dataset['cmk_vue_app_name']
    const appDataRaw = dataset['cmk_vue_app_data']
    if (appName === undefined || appDataRaw === undefined) {
      return
    }
    const appData = JSON.parse(appDataRaw)

    let app

    switch (appName) {
      case 'form_spec': {
        app = createApp(FormApp, {
          id: appData.id,
          spec: appData.spec,
          // eslint has a false positive: assuming `data` is part of a vue component
          // eslint-disable-next-line vue/no-deprecated-data-object-declaration, vue/no-shared-component-data
          data: appData.data,
          backendValidation: appData.validation,
          renderMode: appData.render_mode
        })
        // Assign a unique id to each component, useful for label for=..
        // until https://github.com/vuejs/rfcs/discussions/557 is resolved
        app.use(mixinUniqueId)
        break
      }
      case 'd3_table': {
        console.log('vue create table')
        app = createApp(D3Table, {
          table_spec: appData.component
        })
        console.log('vue fully mounted table')
        break
      }
      case 'vue_table': {
        console.log('vue create table')
        app = createApp(Table, {
          table_spec: appData.component
        })
        console.log('vue fully mounted table')
        break
      }
      case 'quick_setup': {
        app = createApp(QuickSetup, { quick_setup_id: appData.quick_setup_id })
        app.use(mixinUniqueId)
        break
      }
      case 'notification_overview': {
        app = createApp(NotificationOverview, {
          fallback_warning: appData.fallback_warning,
          notification_stats: appData.notification_stats,
          core_stats: appData.core_stats,
          rule_sections: appData.rule_sections
        })
        break
      }
      default:
        throw `can not load vue app "${appName}"`
    }

    app.mount(div)
  })
}

addEventListener('load', () => {
  setupVue()
})

/* eslint-disable-next-line @typescript-eslint/naming-convention */
export const cmk_export = {}
