/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'

import TypeToFocusIndicator from '@/monitoring/shared/components/TypeToFocusIndicator.vue'

test('shows the buffer and the position among the matches', () => {
  render(TypeToFocusIndicator, { props: { buffer: 'cpu', index: 1, count: 5 } })

  const status = screen.getByRole('status')
  expect(status).toHaveTextContent('cpu')
  expect(status).toHaveTextContent('2/5')
})

test('says so when nothing matches', () => {
  render(TypeToFocusIndicator, { props: { buffer: 'xyz', index: -1, count: 0 } })

  expect(screen.getByRole('status')).toHaveTextContent('no match')
})

test('stays in the document, but empty, without a buffer', () => {
  render(TypeToFocusIndicator, { props: { buffer: '', index: -1, count: 0 } })

  expect(screen.getByRole('status')).toBeEmptyDOMElement()
})
