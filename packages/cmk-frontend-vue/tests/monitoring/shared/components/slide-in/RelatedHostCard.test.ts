/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import RelatedHostCard from '@/monitoring/shared/components/slide-in/RelatedHostCard.vue'

const TITLE = 'web-1' as TranslatedString
const SUBTITLE = 'Relation type: parent' as TranslatedString

test('is no link itself', () => {
  render(RelatedHostCard, { props: { title: TITLE, subtitle: SUBTITLE } })

  expect(screen.getByRole('heading', { name: TITLE })).toBeInTheDocument()
  expect(screen.getByText(SUBTITLE)).toBeInTheDocument()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})

test('shows what it is given in place of its title', () => {
  render(RelatedHostCard, {
    props: { title: TITLE, subtitle: SUBTITLE },
    slots: { title: '<a href="host.py?host=web-1">web-1 details</a>' }
  })

  expect(screen.getByRole('heading', { name: 'web-1 details' })).toBeInTheDocument()
  expect(screen.queryByText(TITLE)).not.toBeInTheDocument()
})
