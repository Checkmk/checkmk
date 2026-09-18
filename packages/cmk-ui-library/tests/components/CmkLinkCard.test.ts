/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

const TITLE = 'Checkmk website' as TranslatedString

test('takes the reader along when a url is given', () => {
  render(CmkLinkCard, { props: { title: TITLE, url: 'https://checkmk.com', openInNewTab: true } })

  expect(screen.getByRole('link', { name: TITLE })).toHaveAttribute('href', 'https://checkmk.com')
})

test('stays a link for a card that only runs a callback', () => {
  render(CmkLinkCard, { props: { title: TITLE, callback: () => {}, openInNewTab: false } })

  expect(screen.getByRole('link', { name: TITLE })).toBeInTheDocument()
})

test('is a plain container when there is nowhere to go', () => {
  const { container } = render(CmkLinkCard, { props: { title: TITLE, openInNewTab: false } })

  expect(screen.queryByRole('link')).not.toBeInTheDocument()
  expect(container.querySelector('.cmk-link-card')?.tagName).toBe('DIV')
})

test('carries what it is given below its subtitle', () => {
  render(CmkLinkCard, {
    props: { title: TITLE, openInNewTab: false },
    slots: { default: '<p>counted services</p>' }
  })

  expect(screen.getByText('counted services')).toBeInTheDocument()
})
