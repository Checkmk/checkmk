/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import ResponsiveGridWidget from '@/dashboard/components/ResponsiveGrid/ResponsiveGridWidget.vue'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'

import { makeContentProps } from './testHelpers'

function renderWidget(props: { spec: ContentProps; isEditing: boolean }) {
  const wrapperComponent = defineComponent({
    components: { ResponsiveGridWidget },
    setup() {
      useProvideMissingRuntimeFiltersAction(ref(true), () => {})
      return { spec: props.spec, isEditing: props.isEditing }
    },
    template: '<ResponsiveGridWidget :spec="spec" :is-editing="isEditing" />'
  })
  return render(wrapperComponent)
}

describe('ResponsiveGridWidget', () => {
  it('shows three edit control buttons when isEditing is true', () => {
    renderWidget({ spec: makeContentProps(), isEditing: true })

    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(3)
  })

  it('hides edit controls when isEditing is false', () => {
    renderWidget({ spec: makeContentProps(), isEditing: false })

    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })

  it('has aria-label "Widget"', () => {
    renderWidget({ spec: makeContentProps(), isEditing: false })

    expect(screen.getByLabelText('Widget')).toBeInTheDocument()
  })

  it('allows clicking all edit buttons without errors', async () => {
    renderWidget({ spec: makeContentProps(), isEditing: true })

    const buttons = screen.getAllByRole('button')
    for (const button of buttons) {
      await fireEvent.click(button)
    }

    // all 3 buttons are still present after clicking
    expect(screen.getAllByRole('button')).toHaveLength(3)
  })
})
