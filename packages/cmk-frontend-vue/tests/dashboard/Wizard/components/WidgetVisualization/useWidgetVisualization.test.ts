/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { useWidgetVisualizationProps } from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'

vi.mock('@/dashboard/composables/useProvideDashboardConstants', () => ({
  useInjectDashboardConstants: () => ({ widgets: {} })
}))

describe('useWidgetVisualizationProps validate', () => {
  it('passes and clears errors when titleUrlEnabled is false', () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = false
    props.titleUrl.value = 'not-a-url <script>'
    expect(props.validate()).toBe(true)
    expect(props.titleUrlValidationErrors.value).toEqual([])
  })

  it('passes for a valid http(s) URL when enabled', () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = true
    props.titleUrl.value = 'https://example.com/path'
    expect(props.validate()).toBe(true)
    expect(props.titleUrlValidationErrors.value).toEqual([])
  })

  it('passes for an internal URL when enabled', () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = true
    props.titleUrl.value = 'view.py?label=cmk/os:linux'
    expect(props.validate()).toBe(true)
    expect(props.titleUrlValidationErrors.value).toEqual([])
  })

  it('fails and pushes the error when the URL is invalid', () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = true
    props.titleUrl.value = 'javascript:alert(1)'
    expect(props.validate()).toBe(false)
    expect(props.titleUrlValidationErrors.value).toEqual(['Value must be a valid URL'])
  })

  it('clears previous errors on re-validation', () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = true
    props.titleUrl.value = 'javascript:alert(1)'
    props.validate()
    expect(props.titleUrlValidationErrors.value).toHaveLength(1)

    props.titleUrl.value = 'https://example.com'
    expect(props.validate()).toBe(true)
    expect(props.titleUrlValidationErrors.value).toEqual([])
  })
})

describe('useWidgetVisualizationProps live validation', () => {
  it('shows the error as soon as an invalid URL is typed', async () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = true
    await nextTick()
    props.titleUrl.value = 'javascript:alert(1)'
    await nextTick()
    expect(props.titleUrlValidationErrors.value).toEqual(['Value must be a valid URL'])
  })

  it('clears the error once the URL becomes valid', async () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = true
    await nextTick()
    props.titleUrl.value = 'javascript:alert(1)'
    await nextTick()
    expect(props.titleUrlValidationErrors.value).toHaveLength(1)

    props.titleUrl.value = 'https://example.com'
    await nextTick()
    expect(props.titleUrlValidationErrors.value).toEqual([])
  })

  it('does not show an error while the URL is empty', async () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = true
    await nextTick()
    props.titleUrl.value = 'javascript:alert(1)'
    await nextTick()
    expect(props.titleUrlValidationErrors.value).toHaveLength(1)

    props.titleUrl.value = ''
    await nextTick()
    expect(props.titleUrlValidationErrors.value).toEqual([])
  })

  it('clears the error when titleUrlEnabled is toggled off', async () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrlEnabled.value = true
    await nextTick()
    props.titleUrl.value = 'javascript:alert(1)'
    await nextTick()
    expect(props.titleUrlValidationErrors.value).toHaveLength(1)

    props.titleUrlEnabled.value = false
    await nextTick()
    expect(props.titleUrlValidationErrors.value).toEqual([])
  })

  it('does not validate while titleUrlEnabled is false', async () => {
    const props = useWidgetVisualizationProps('Title')
    props.titleUrl.value = 'javascript:alert(1)'
    await nextTick()
    expect(props.titleUrlValidationErrors.value).toEqual([])
  })
})
