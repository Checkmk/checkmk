/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import PluginOutput from '@/monitoring/shared/components/PluginOutput.vue'

describe('PluginOutput', () => {
  it('shows a state badge in place of each marker', () => {
    render(PluginOutput, { props: { output: 'load: 3.1(!), temp: 90(!!)' } })

    expect(screen.getByText('WA')).toBeInTheDocument()
    expect(screen.getByText('CR')).toBeInTheDocument()
  })

  it('colors the badges by the state they mark', () => {
    const { container } = render(PluginOutput, { props: { output: 'a(!) b(!!) c(?) d(.)' } })

    expect(container.querySelector('.cmk-state-tag--warning')).toHaveTextContent('WA')
    expect(container.querySelector('.cmk-state-tag--critical')).toHaveTextContent('CR')
    expect(container.querySelector('.cmk-state-tag--unknown')).toHaveTextContent('UN')
    expect(container.querySelector('.cmk-state-tag--ok')).toHaveTextContent('OK')
  })

  it('keeps the text around the markers', () => {
    const { container } = render(PluginOutput, { props: { output: 'temp: 90(!!) too high' } })

    expect(container.textContent).toContain('temp: 90')
    expect(container.textContent).toContain(' too high')
  })

  it('shows output without a marker as it was written', () => {
    const { container } = render(PluginOutput, { props: { output: 'OK - nothing to report' } })

    expect(container.textContent).toBe('OK - nothing to report')
  })
})
