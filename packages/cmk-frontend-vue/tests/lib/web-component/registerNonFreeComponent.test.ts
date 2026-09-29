/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { defineComponent, h } from 'vue'

import { registerNonFreeComponent } from '@/lib/web-component/registerNonFreeComponent'

type Connectable = HTMLElement & { connectedCallback(): void }

test('registers the component the edition ships', () => {
  const shipped = defineComponent(() => () => h('p', 'shipped'))

  registerNonFreeComponent('cmk-test-shipped', { './Shipped.vue': { default: shipped } })

  const element = document.createElement('cmk-test-shipped') as Connectable
  expect(() => element.connectedCallback()).not.toThrow()
})

test('makes using the element throw when the edition does not ship the component', () => {
  registerNonFreeComponent('cmk-test-missing', {})

  const element = document.createElement('cmk-test-missing') as Connectable
  expect(() => element.connectedCallback()).toThrow('cmk-test-missing')
})
