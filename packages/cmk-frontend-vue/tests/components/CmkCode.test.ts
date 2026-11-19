/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import CmkCode from '@/components/CmkCode.vue'

const codeText = `${'first: line\n'.repeat(10)}last: line`

test('copies the code to the clipboard', async () => {
  const user = userEvent.setup()
  render(CmkCode, { props: { code_txt: codeText } })

  await user.click(screen.getByRole('button', { name: 'Copy to clipboard' }))

  expect(await navigator.clipboard.readText()).toBe(codeText)
})
