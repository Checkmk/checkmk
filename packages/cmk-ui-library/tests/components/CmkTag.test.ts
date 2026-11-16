/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'

test('a tag with a button action is a button named by its content', () => {
  render(CmkTag, {
    props: { content: untranslated('os'), value: 'linux', action: { type: 'button' } }
  })

  screen.getByRole('button', { name: 'os: linux' })
})

test('a tag without an action is neither a button nor a link', () => {
  render(CmkTag, { props: { content: untranslated('os'), value: 'linux' } })

  expect(screen.queryByRole('button')).toBeNull()
  expect(screen.queryByRole('link')).toBeNull()
})

test('a tag with a link action is a link to its address', () => {
  render(CmkTag, {
    props: {
      content: untranslated('os'),
      value: 'linux',
      action: { type: 'link', href: 'hosts.py', target: '_top' }
    }
  })

  const link = screen.getByRole('link', { name: 'os: linux' })
  expect(link).toHaveAttribute('href', 'hosts.py')
  expect(link).toHaveAttribute('target', '_top')
})
