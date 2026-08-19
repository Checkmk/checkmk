/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type TranslationLoader, setTranslationLoader } from 'cmk-ui-library/lib/i18n'
import CmkApp, { type CmkAppProps } from 'cmk-ui-library/lib/web-component/CmkApp.vue'
import { type Component, computed, defineCustomElement, h } from 'vue'

let appCount = 0

function defineCmkComponent(
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
        const appData = computed(() => JSON.parse(props.data))
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

export interface CmkUiConfig {
  /**
   * cmk-ui-library ships no translation catalogs: its strings are extracted into the
   * embedding application's catalog, so the application owns loading the
   * compiled locale files (typically a lazy import of its locale JSON).
   */
  translationLoader: TranslationLoader
}

export default function initCmkUi(config: CmkUiConfig): {
  defineCmkComponent: typeof defineCmkComponent
} {
  setTranslationLoader(config.translationLoader)
  return { defineCmkComponent }
}
