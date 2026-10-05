/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import ItemIdChip from '@/graphing/designer/calculation/components/ItemIdChip.vue'

const DARK_TEXT = 'rgb(30, 38, 46)'
const LIGHT_TEXT = 'rgb(255, 255, 255)'

function renderChip(props: Record<string, unknown> = {}) {
  const rendered = render(ItemIdChip, { props: { id: 'A', ...props } })
  return {
    ...rendered,
    chip: rendered.container.querySelector('.graphing-item-id-chip') as HTMLElement
  }
}

test.each([
  ['#ffe000', 'rgb(255, 224, 0)', DARK_TEXT],
  ['#0667c1', 'rgb(6, 103, 193)', LIGHT_TEXT]
])('contrasts the text with the item color %s', (color, expectedBackground, expectedContrast) => {
  const { chip } = renderChip({ color })
  expect(chip.style.backgroundColor).toBe(expectedBackground)
  expect(chip.style.color).toBe(expectedContrast)
})

test('falls back to the grey placeholder without an item color', () => {
  const { chip } = renderChip()
  expect(chip.style.backgroundColor).toBe('var(--background-neutral)')
  expect(chip.style.color).toBe('var(--tag-font-color-dark)')
})
