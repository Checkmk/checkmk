/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Component, defineCustomElement, h } from 'vue'

import CmkApp from './CmkApp.vue'

let appCount = 0

export default function defineCmkComponent(componentName: string, component: Component) {
  if (componentName.startsWith('cmk-') === false) {
    throw new Error(`Element name "${componentName}" must start with "cmk-"`)
  }

  // eslint-disable-next-line @typescript-eslint/naming-convention
  const CustomElement = defineCustomElement(
    {
      props: {
        data: String
      },
      setup(props: { data: string }) {
        const appData = JSON.parse(props.data)
        return { appData }
      },
      render() {
        return h(CmkApp, () => h(component, this.appData))
      }
    },
    {
      shadowRoot: false,
      configureApp: (app) => {
        app.config.idPrefix = `cmk-vue-app-${appCount++}`
      }
    }
  )

  customElements.define(componentName, CustomElement)
}
