/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import type { TranslatedString } from '@/lib/i18nString'

import CmkVisuallyHidden from '@/components/CmkVisuallyHidden.vue'

describe('CmkVisuallyHidden', () => {
  test('exposes its text to assistive tech', () => {
    const { getByText } = render(CmkVisuallyHidden, {
      props: { text: 'hidden label' as TranslatedString }
    })
    expect(getByText('hidden label')).toBeInTheDocument()
  })

  test.each([{ props: {} }, { props: { live: 'off' as const } }])(
    'is a silent (off) region with no announcing role by default ($props)',
    ({ props }) => {
      const { container } = render(CmkVisuallyHidden, {
        props: { text: 'x' as TranslatedString, ...props }
      })
      const el = container.firstElementChild!
      expect(el).not.toHaveAttribute('role')
      expect(el).toHaveAttribute('aria-live', 'off')
    }
  )

  test('live="polite" renders a polite status region', () => {
    const { container } = render(CmkVisuallyHidden, {
      props: { text: 'June 2026' as TranslatedString, live: 'polite' }
    })
    const el = container.firstElementChild!
    expect(el).toHaveAttribute('role', 'status')
    expect(el).toHaveAttribute('aria-live', 'polite')
  })

  test('live="assertive" renders an assertive alert region', () => {
    const { container } = render(CmkVisuallyHidden, {
      props: { text: 'x' as TranslatedString, live: 'assertive' }
    })
    const el = container.firstElementChild!
    expect(el).toHaveAttribute('role', 'alert')
    expect(el).toHaveAttribute('aria-live', 'assertive')
  })
})
