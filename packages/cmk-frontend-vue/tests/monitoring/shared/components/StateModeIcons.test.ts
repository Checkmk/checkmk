/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import StateModeIcons from '@/monitoring/shared/components/StateModeIcons.vue'

test('renders neither icon by default', () => {
  render(StateModeIcons, { props: {} })

  expect(screen.queryByTitle('Flapping')).not.toBeInTheDocument()
  expect(screen.queryByTitle('Stale')).not.toBeInTheDocument()
})

test('renders the flapping icon when flapping', () => {
  render(StateModeIcons, { props: { flapping: true } })

  expect(screen.getByTitle('Flapping')).toBeInTheDocument()
})

test('renders the stale icon when stale', () => {
  render(StateModeIcons, { props: { stale: true } })

  expect(screen.getByTitle('Stale')).toBeInTheDocument()
})

test('renders both icons together', () => {
  render(StateModeIcons, { props: { flapping: true, stale: true } })

  expect(screen.getByTitle('Flapping')).toBeInTheDocument()
  expect(screen.getByTitle('Stale')).toBeInTheDocument()
})
