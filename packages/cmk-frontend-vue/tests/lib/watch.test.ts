/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// eslint-disable-next-line no-restricted-imports -- TODO: migrate to @testing-library/vue, see https://wiki.lan.checkmk.net/spaces/DEV/pages/149528812/All+things+Vue
import { mount } from '@vue/test-utils'
import { type Component, defineComponent, h, onErrorCaptured } from 'vue'

import { immediateWatch } from '@/lib/watch'

function wrapWithErrorCapture(component: Component) {
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
  // eslint-disable-next-line @typescript-eslint/naming-convention
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
