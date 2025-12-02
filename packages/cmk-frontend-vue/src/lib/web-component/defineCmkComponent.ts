/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Component, defineCustomElement, h } from 'vue'

import CmkApp, { type CmkAppProps } from './CmkApp.vue'

let appCount = 0

export default function defineCmkComponent(
  componentName: string,
  component: Component,
  options?: {
    appprops?: CmkAppProps
    pure?: boolean
  }
) {
  if (componentName.startsWith('cmk-') === false) {
    throw new Error(`Element name "${componentName}" must start with "cmk-"`)
  }

  if (options === undefined) {
    options = {}
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
        if (options.pure === undefined || options.pure === false) {
          return h(CmkApp, options.appprops, () => h(component, this.appData))
        } else {
          return h(component, { ...this.appData, ...this.$attrs })
        }
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
