/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { mount } from '@vue/test-utils'

import { h, onErrorCaptured, defineComponent, type Component } from 'vue'
import { immediateWatch } from '@/lib/watch'

function wrapWithErrorCapture(component: Component) {
  // eslint-disable-next-line vue/one-component-per-file
  return defineComponent({
    setup() {
      onErrorCaptured(() => {
        // do nothing, just ignore it
        return false
      })
    },
    render() {
      return h(component, {})
    }
  })
}

test('support async callback function in immediateWatch', async () => {
  // eslint-disable-next-line vue/one-component-per-file,@typescript-eslint/naming-convention
  const InnerComponent = defineComponent({
    props: {},
    setup() {
      immediateWatch(
        () => 1,
        async (_int: number) => {
          // don't worry, it will be captured by the onErrorCaptured method in the TestComponent
          throw new Error('this is an async error')
        }
      )
      return {}
    },
    render() {
      return h('div')
    }
  })

  // just make sure no error leaks
  mount(wrapWithErrorCapture(InnerComponent), {})
})
