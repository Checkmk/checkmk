/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type initCmkUi from 'cmk-ui-library/lib/initCmkUi'
import type { Component } from 'vue'

type DefineCmkComponent = ReturnType<typeof initCmkUi>['defineCmkComponent']

export function registerNonFreeComponent(
  defineCmkComponent: DefineCmkComponent,
  name: string,
  modules: Record<string, { default: Component }>,
  options?: Parameters<DefineCmkComponent>[2]
): void {
  const found = Object.values(modules)
  if (found.length > 1) {
    throw new Error(`Expected at most one module for "${name}", got ${found.length}`)
  }
  const [module] = found
  if (module) {
    defineCmkComponent(name, module.default, options)
    return
  }
  customElements.define(
    name,
    class extends HTMLElement {
      public connectedCallback(): void {
        throw new Error(`The web component "${name}" is not part of this edition.`)
      }
    }
  )
}
