/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkTruncateText from 'cmk-ui-library/components/CmkTruncateText.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, test } from 'vitest'
import { computed } from 'vue'

describe('CmkTruncateText', () => {
  test('keeps the full text available as title and label', () => {
    const title = 'CPU utilization of host'
    render(CmkTruncateText, { props: { text: untranslated(title) } })

    const element = screen.getByTitle(title)
    expect(element).toHaveAttribute('aria-label', 'CPU utilization of host')
    expect(element).toHaveTextContent('CPU utilization of host')
  })

  test('keeps the last six characters out of the truncatable start by default', () => {
    const { container } = render(CmkTruncateText, {
      props: { text: untranslated('Filesystem /var/log') }
    })

    expect(container.querySelector('.cmk-truncate-text__start')?.textContent).toBe('Filesystem /v')
    expect(container.querySelector('.cmk-truncate-text__end')?.textContent).toBe('ar/log')
  })

  test('keeps the given number of characters out of the truncatable start', () => {
    const { container } = render(CmkTruncateText, {
      props: { text: computed(() => untranslated('Disk IO read')), suffixCount: 4 }
    })

    expect(container.querySelector('.cmk-truncate-text__start')?.textContent).toBe('Disk IO ')
    expect(container.querySelector('.cmk-truncate-text__end')?.textContent).toBe('read')
  })
})
