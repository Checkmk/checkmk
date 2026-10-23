/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { defineComponent, h, nextTick, ref } from 'vue'

async function renderOpenTooltip(props: Record<string, unknown>, content: string): Promise<void> {
  const open = ref(false)
  render(
    defineComponent({
      setup: () => () =>
        h(CmkTooltipProvider, () =>
          h(CmkTooltip, { open: open.value }, () => [
            h(CmkTooltipTrigger, () => 'Trigger'),
            h(CmkTooltipContent, props, () => content)
          ])
        )
    })
  )
  await nextTick()
  open.value = true
  await screen.findByRole('tooltip', { hidden: true })
}

describe('CmkTooltipContent', () => {
  test.each(['unstyled', 'text', 'content'])(
    'renders the slot of the %s variant',
    async (variant) => {
      await renderOpenTooltip({ variant }, '2026-03-20 - 2026-03-28')

      expect(screen.getByRole('tooltip', { hidden: true })).toHaveTextContent(
        '2026-03-20 - 2026-03-28'
      )
    }
  )

  test('renders the title and aside of the content variant', async () => {
    await renderOpenTooltip(
      {
        variant: 'content',
        title: untranslated('Graph title'),
        titleAside: untranslated('13:27:59')
      },
      'Legend'
    )

    expect(screen.getByText('Graph title')).toBeInTheDocument()
    expect(screen.getByText('13:27:59')).toBeInTheDocument()
  })
})
