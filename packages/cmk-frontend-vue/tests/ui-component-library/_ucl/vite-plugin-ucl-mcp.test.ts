/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { serializePanelConfig } from '@ucl/_ucl/vite-plugin-ucl-mcp'
import { describe, expect, it } from 'vitest'

describe('vite-plugin-ucl-mcp', () => {
  it('serializes panel config', () => {
    const result = serializePanelConfig({
      label: {
        type: 'string',
        title: 'Label',
        initialState: 'Submit',
        help: 'Button label'
      },
      variant: {
        type: 'list',
        title: 'Variant',
        options: [
          { title: 'Primary', name: 'primary' },
          { title: 'Secondary', name: 'secondary' }
        ],
        initialState: 'primary'
      }
    })

    expect(result).toEqual([
      {
        name: 'label',
        type: 'string',
        uclInitialState: 'Submit',
        description: 'Button label'
      },
      {
        name: 'variant',
        type: 'list',
        uclInitialState: 'primary',
        options: ['primary', 'secondary']
      }
    ])
  })
})
