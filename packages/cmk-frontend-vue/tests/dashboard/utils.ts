/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Suspense, defineComponent, h } from 'vue'

const scheduler = typeof setImmediate === 'function' ? setImmediate : setTimeout

// Rendering async components inside <Suspense /> does not work as expected
// flushPromises and wrapInSuspense functions are needed in order to make
// it work.
// How to use:
//     render(wrapInSuspense(MyAsyncComponent, { props: { ... } }))
//     await flushPromises()
//
// https://github.com/testing-library/vue-testing-library/issues/230
export function flushPromises(): Promise<void> {
  return new Promise((resolve) => {
    scheduler(resolve, 0)
  })
}

export function wrapInSuspense(
  component: ReturnType<typeof defineComponent>,
  { props }: { props: object }
): ReturnType<typeof defineComponent> {
  return defineComponent({
    render() {
      return h(
        'div',
        { id: 'root' },
        h(Suspense, null, {
          default() {
            return h(component, props)
          },
          fallback: h('div', 'fallback')
        })
      )
    }
  })
}
