/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// see https://github.com/vuejs/eslint-plugin-vue/issues/2201
/* eslint-disable vue/one-component-per-file */

import { createApp } from 'vue'

import QuickSetup from './quick-setup/QuickSetupApp.vue'
import NotificationOverview from './notification/NotificationOverviewApp.vue'
import { FormApp } from '@/form'
import NotificationParametersOverviewApp from '@/notification/NotificationParametersOverviewApp.vue'
import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'

import '@/assets/variables.css'

function setupVue() {
  document
    .querySelectorAll<HTMLFormElement>('div[data-cmk_vue_app_name]')
    .forEach((div, divIndex) => {
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
            displayMode: appData.display_mode
          })
          break
        }
        case 'quick_setup': {
          app = createApp(QuickSetup, {
            quick_setup_id: appData.quick_setup_id,
            mode: appData.mode,
            toggleEnabled: appData.toggle_enabled,
            objectId: appData.object_id || null
          })
          break
        }
        case 'notification_overview': {
          app = createApp(NotificationOverview, {
            overview_title_i18n: appData.overview_title_i18n,
            fallback_warning: appData.fallback_warning,
            notification_stats: appData.notification_stats,
            core_stats: appData.core_stats,
            rule_sections: appData.rule_sections,
            user_id: appData.user_id
          })
          break
        }
        case 'notification_parameters_overview': {
          app = createApp(NotificationParametersOverviewApp, {
            parameters: appData.parameters,
            i18n: appData.i18n
          })
          break
        }
        case 'graph_designer': {
          app = createApp(GraphDesignerApp, {
            graph_lines: appData.graph_lines,
            graph_options: appData.graph_options,
            i18n: appData.i18n
          })
          break
        }
        default:
          throw `can not load vue app "${appName}"`
      }
      app.config.idPrefix = `app${divIndex}` // useId for multiple vue apps
      app.mount(div)

      div.classList.add('cmk-vue-app')
    })
}

addEventListener('load', () => {
  setupVue()
})
