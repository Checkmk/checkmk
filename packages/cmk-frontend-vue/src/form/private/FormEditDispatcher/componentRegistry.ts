/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Components } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type Component } from 'vue'

export type FormComponents = Partial<Record<Components['type'], Component>>

const _componentRegistry: Record<string, Component> = {}

export function registerFormComponents(components: FormComponents) {
  Object.assign(_componentRegistry, components)
}

export function getComponent(type: string): Component {
  const result = _componentRegistry[type as Components['type']]
  if (result !== undefined) {
    return result
  }
  throw new Error(`Could not find Component for type=${type}`)
}
