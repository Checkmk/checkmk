/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { iconSearchLabels } from '@ucl/foundations/Icons/iconSearchLabels'
import { describe, expect, it } from 'vitest'

import {
  oneColorIcons,
  themedIcons,
  twoColorIcons,
  unthemedIcons
} from '@/components/CmkIcon/icons.constants'

// Every icon name the UclIcons foundation page can render, derived from the
// same registry sources the page reads. <CmkIcon> shows the union of the
// unthemed and per-theme maps; <CmkMultitoneIcon> shows the one- and two-color
// lists.
const displayedIconNames = new Set<string>([
  ...Object.keys(unthemedIcons),
  ...Object.keys(themedIcons.light),
  ...Object.keys(themedIcons.dark),
  ...oneColorIcons,
  ...twoColorIcons
])

describe('iconSearchLabels', () => {
  // Guards against a new icon being added to the registry without curated
  // search keywords: the UclIcons page can only match such an icon by its raw
  // name, so this test fails until the icon gets an iconSearchLabels entry.
  it('has a keyword entry for every displayed icon', () => {
    const missing = [...displayedIconNames].filter((name) => !(name in iconSearchLabels)).sort()
    expect(
      missing,
      `Icons missing an iconSearchLabels entry. Add curated synonyms for each in ` +
        `ui-component-library/foundations/Icons/iconSearchLabels.ts:\n${missing.join('\n')}`
    ).toEqual([])
  })

  // Keeps the curated list honest: a label keyed to a name that no longer
  // exists in the registry is dead weight (e.g. after an icon is renamed).
  it('has no keyword entry for a non-existent icon', () => {
    const stale = Object.keys(iconSearchLabels)
      .filter((name) => !displayedIconNames.has(name))
      .sort()
    expect(
      stale,
      `iconSearchLabels entries that match no icon in the registry (rename or remove them):\n` +
        `${stale.join('\n')}`
    ).toEqual([])
  })

  it('only maps to non-empty lowercase keyword lists', () => {
    for (const [name, keywords] of Object.entries(iconSearchLabels)) {
      expect(keywords.length, `${name} has an empty keyword list`).toBeGreaterThan(0)
      for (const keyword of keywords) {
        expect(keyword, `${name} keyword "${keyword}" must be lowercase and trimmed`).toBe(
          keyword.toLowerCase().trim()
        )
      }
    }
  })
})
