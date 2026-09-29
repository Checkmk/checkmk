/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'

import defineCmkComponent from './defineCmkComponent'

export function registerNonFreeComponent(
  name: string,
  modules: Record<string, { default: Component }>,
  options?: Parameters<typeof defineCmkComponent>[2]
): void {
  const [module] = Object.values(modules)
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
