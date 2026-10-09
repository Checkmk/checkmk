/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'

import EditField from '@/maps/map/edit/components/EditField.vue'

describe('EditField', () => {
  it('names the control it labels', () => {
    render(
      defineComponent({
        components: { EditField, CmkInput },
        template: `
          <EditField v-slot="{ id }" label="Latitude" labels-control>
            <CmkInput :id="id" type="number" />
          </EditField>`
      })
    )

    expect(screen.getByLabelText('Latitude')).toHaveAttribute('type', 'number')
  })

  it('leaves a control that names itself unlabelled', () => {
    render(
      defineComponent({
        components: { EditField },
        template: `
          <EditField label="Object type">
            <button type="button" aria-label="Host">Host</button>
          </EditField>`
      })
    )

    expect(screen.getByText('Object type').closest('label')).not.toHaveAttribute('for')
  })
})
