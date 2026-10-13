/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { StaticTextContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

describe('DashboardPreviewContent', () => {
  it('renders a linked title as plain text', () => {
    const props = makeContentProps<StaticTextContent>(
      { type: 'static_text', text: 'Hello' },
      {
        general_settings: {
          title: {
            text: 'Test',
            url: 'view.py?view_name=allhosts',
            render_mode: 'with_background'
          },
          render_background: true
        }
      }
    )
    const wrapper = defineComponent({
      setup() {
        useProvideMissingRuntimeFiltersAction(ref(true), () => {})
        return () => h(DashboardPreviewContent, props as never)
      }
    })

    render(wrapper)

    expect(screen.getByRole('heading', { name: 'Test' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Test' })).toBeNull()
  })
})
