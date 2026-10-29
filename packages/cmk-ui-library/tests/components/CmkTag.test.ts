/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'

test('an interactive tag is a button named by its content', () => {
  render(CmkTag, { props: { content: untranslated('os'), value: 'linux', interactive: true } })

  screen.getByRole('button', { name: 'os: linux' })
})

test('a plain tag is no button', () => {
  render(CmkTag, { props: { content: untranslated('os'), value: 'linux' } })

  expect(screen.queryByRole('button')).toBeNull()
})
