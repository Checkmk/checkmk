/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'

import PresentationGadgetMetricField from '@/maps/map/presentation/components/PresentationGadgetMetricField.vue'
import { clearDataBindingCache } from '@/maps/map/presentation/composables/useDataBinding'
import { createElement } from '@/maps/map/presentation/elements'
import type { DataElement } from '@/maps/types/api'

import { fakeMapsServices, mapsGlobal } from '../../../support/services'

function aServiceElement(mode: DataElement['display']['mode']): DataElement {
  const element = createElement('data', 0, 0) as DataElement
  return {
    ...element,
    host_name: 'heute',
    service_description: 'CPU load',
    display: { ...element.display, mode }
  }
}

describe('PresentationGadgetMetricField', () => {
  beforeEach(() => {
    clearDataBindingCache()
    const app = document.createElement('div')
    app.id = 'app'
    document.body.appendChild(app)
  })

  afterEach(() => {
    document.getElementById('app')?.remove()
  })

  it('offers the metrics once an icon element is switched to a gadget', async () => {
    const user = userEvent.setup()
    const services = fakeMapsServices()
    vi.mocked(services.apis.objects.fetchPerfMetrics).mockResolvedValue({
      perf_data: 'load1=5.94;;;0;12',
      check_command: 'check_mk-cpu_loads',
      metrics: ['load1']
    })
    const element = reactive(aServiceElement('icon'))
    render(PresentationGadgetMetricField, {
      props: { element, connectionId: 'live_1' },
      global: mapsGlobal({}, services)
    })

    // The editor patches the element in place, as the inspector's Display
    // dropdown does -- a new element object would re-run every watcher anyway.
    Object.assign(element, { display: { ...element.display, mode: 'gadget' } })
    await user.click(await screen.findByRole('combobox', { name: 'Metric' }))

    expect(await screen.findByRole('option', { name: 'load1' })).toBeInTheDocument()
  })
})
