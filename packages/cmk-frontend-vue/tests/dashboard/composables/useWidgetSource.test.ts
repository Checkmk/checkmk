/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import { useProvideCmkToken } from '@/dashboard/composables/useCmkToken'
import { type WidgetRequestSource, useWidgetSource } from '@/dashboard/composables/useWidgetSource'

const PROPS = {
  widget_id: 'w1',
  content: { type: 'host_stats' },
  effective_filter_context: {
    uses_infos: [],
    filters: { host: { host: 'my-host' } },
    restricted_to_single: []
  }
}

function sourceOf(cmkToken?: string): WidgetRequestSource<{ type: string }> {
  let result: WidgetRequestSource<{ type: string }> | undefined
  const consumer = defineComponent({
    setup() {
      result = useWidgetSource(PROPS)
      return () => null
    }
  })
  render(
    defineComponent({
      setup() {
        if (cmkToken !== undefined) {
          useProvideCmkToken(cmkToken)
        }
        return () => h(consumer)
      }
    })
  )
  return result!
}

describe('useWidgetSource', () => {
  it('builds an explicit source without a token', () => {
    const { source, headers } = sourceOf()

    expect(source.value).toEqual({
      type: 'explicit',
      content: { type: 'host_stats' },
      context: { host: { host: 'my-host' } }
    })
    expect(headers).toEqual({})
  })

  it('builds a saved source with the token header', () => {
    const { source, headers } = sourceOf('0:the-token')

    expect(source.value).toEqual({ type: 'saved', widget_id: 'w1' })
    expect(headers).toEqual({ Authorization: 'CMK-TOKEN 0:the-token' })
  })
})
