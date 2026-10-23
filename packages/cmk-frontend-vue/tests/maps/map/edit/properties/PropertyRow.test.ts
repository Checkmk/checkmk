/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'

import PropertyRow from '@/maps/map/edit/properties/PropertyRow.vue'

describe('PropertyRow', () => {
  it('names the control it labels', () => {
    render(
      defineComponent({
        components: { PropertyRow, CmkInput },
        template: `
          <PropertyRow v-slot="{ id }" label="Lat" labels-control>
            <CmkInput :id="id" type="number" />
          </PropertyRow>`
      })
    )

    expect(screen.getByLabelText('Lat')).toHaveAttribute('type', 'number')
    expect(screen.queryByRole('group')).not.toBeInTheDocument()
  })

  it('names a control it cannot point at by the group around it', () => {
    render(
      defineComponent({
        components: { PropertyRow },
        template: `
          <PropertyRow label="Custom icon">
            <button type="button">Pick</button>
          </PropertyRow>`
      })
    )

    expect(screen.getByRole('group', { name: 'Custom icon' })).toContainElement(
      screen.getByRole('button', { name: 'Pick' })
    )
  })
})
