/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import Stage2 from '@/dashboard/components/Wizard/wizards/view/stage2/StageContents.vue'
import type { DataConfiguration } from '@/dashboard/components/Wizard/wizards/view/useDataConfiguration'

const duplicateConfiguration: DataConfiguration = {
  mode: 'duplicate',
  embeddedId: 'the-copy',
  sourceEmbeddedId: 'the-original'
}

describe('view wizard data configuration', () => {
  it('sends the editor to a new embedded view when it duplicates', () => {
    const { container } = render(Stage2, {
      props: {
        dashboardKey: { name: 'my_dashboard', owner: 'admin' },
        dataConfiguration: duplicateConfiguration
      }
    })

    const source = container.querySelector('iframe')!.getAttribute('src')!
    const { searchParams } = new URL(source, window.location.origin)

    expect(searchParams.get('mode')).toBe('duplicate')
    expect(searchParams.get('embedded_id')).toBe('the-copy')
    expect(searchParams.get('source_embedded_id')).toBe('the-original')
  })
})
