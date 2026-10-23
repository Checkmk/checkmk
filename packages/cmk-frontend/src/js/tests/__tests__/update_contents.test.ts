/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from '@jest/globals'

import { update_contents } from '@/modules/utils'

test('update_contents does not execute inline scripts of the inserted HTML', () => {
  document.body.innerHTML = '<div id="container"></div>'

  update_contents(
    'container',
    '<script>document.body.dataset.evaluated = "yes"</script><span>content</span>'
  )

  expect(document.body.dataset.evaluated).toBeUndefined()
})
