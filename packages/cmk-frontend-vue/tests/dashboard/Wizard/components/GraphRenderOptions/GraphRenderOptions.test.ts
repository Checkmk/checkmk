/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import GraphRenderOptions from '@/dashboard/components/Wizard/components/GraphRenderOptions/GraphRenderOptions.vue'

const requiredProps = {
  horizontalAxis: true,
  verticalAxis: true,
  verticalAxisWidthMode: 'fixed' as const,
  fixedVerticalAxisWidth: 8,
  fontSize: 8,
  timestamp: false,
  roundMargin: false,
  graphLegend: false,
  clickToPlacePin: true,
  showBurgerMenu: false,
  dontFollowTimerange: false
}

describe('GraphRenderOptions', () => {
  describe('presentation dropdown', () => {
    it('is hidden when no presentation model is bound', () => {
      render(GraphRenderOptions, { props: { ...requiredProps } })
      expect(screen.queryByText('Presentation')).not.toBeInTheDocument()
    })

    it('is shown with the current value marked as selected', async () => {
      const user = userEvent.setup()
      render(GraphRenderOptions, { props: { ...requiredProps, presentation: 'stacked' } })

      expect(screen.getByText('Presentation')).toBeInTheDocument()

      await user.click(screen.getByRole('combobox', { name: 'Select presentation' }))
      // 'stacked' is the second option (index 1) in the suggestions list.
      expect((await screen.findAllByRole('option'))[1]).toHaveClass('selected')
    })

    it('emits update:presentation when a new option is selected', async () => {
      const user = userEvent.setup()
      const { emitted } = render(GraphRenderOptions, {
        props: { ...requiredProps, presentation: 'lines' }
      })

      await user.click(screen.getByRole('combobox', { name: 'Select presentation' }))
      await user.click(await screen.findByText('Sum'))

      expect(emitted('update:presentation')).toEqual([['sum']])
    })
  })
})
