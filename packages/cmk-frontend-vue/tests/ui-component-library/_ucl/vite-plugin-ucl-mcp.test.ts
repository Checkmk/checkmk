/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { readCodeExample, serializePanelConfig } from '@ucl/_ucl/vite-plugin-ucl-mcp'
import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

describe('readCodeExample', () => {
  it('reads content from the co-located *CodeExample.vue file', () => {
    const compDir = path.resolve(
      __dirname,
      '../../../ui-component-library/components/basic-elements/CmkButton'
    )
    const expected = fs.readFileSync(path.join(compDir, 'UclCmkButtonCodeExample.vue'), 'utf-8')
    expect(readCodeExample(path.join(compDir, 'UclCmkButton.vue'))).toBe(expected)
  })
})

const componentsDir = path.resolve(__dirname, '../../../ui-component-library/components')

describe('UCL split script convention', () => {
  it('components using UclPropertiesPanel export panelConfig from the static <script> block', () => {
    const files = (fs.readdirSync(componentsDir, { recursive: true }) as string[])
      .filter((f) => {
        const name = path.basename(f)
        return (
          name.startsWith('Ucl') &&
          name.endsWith('.vue') &&
          !name.endsWith('Dev.vue') &&
          !name.endsWith('CodeExample.vue')
        )
      })
      .map((f) => path.join(componentsDir, f))

    const violations = files.filter((filePath) => {
      const content = fs.readFileSync(filePath, 'utf-8')
      if (!content.includes('UclPropertiesPanel')) {
        return false
      }
      const staticScript = content.match(/<script(?![^>]*\bsetup\b)[^>]*>([\s\S]*?)<\/script>/)?.[1]
      return !staticScript || !/export\s+const\s+\w*[Pp]anelConfig/.test(staticScript)
    })

    expect(
      violations.map((f) => path.relative(componentsDir, f)),
      'These components use <UclPropertiesPanel> but are missing `export const panelConfig` in the ' +
        'static <script lang="ts"> block (not <script setup>). ' +
        'Fix: add a separate <script lang="ts"> block and export panelConfig there. ' +
        'The vite-plugin-ucl-mcp resolves props via AST analysis of the static block only.'
    ).toEqual([])
  })
})

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
