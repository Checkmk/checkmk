/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { evaluateNode, readCodeExample, serializePanelConfig } from '@ucl/_ucl/vite-plugin-ucl-mcp'
import type { Expression } from 'acorn'
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

  it('throws when no co-located *CodeExample.vue exists', () => {
    const compDir = path.resolve(
      __dirname,
      '../../../ui-component-library/components/basic-elements/CmkButton'
    )
    // A component that has no sibling *CodeExample.vue: the plugin treats this as
    // a hard error, so readCodeExample must throw rather than return "".
    expect(() => readCodeExample(path.join(compDir, 'NoSuchComponent.vue'))).toThrow()
  })
})

// evaluateNode walks the small subset of ESTree node shapes the plugin relies
// on. We build those nodes as plain literals (the same shape acorn produces)
// rather than parsing source, keeping the test free of a parser dependency.
function asExpression(node: unknown): Expression {
  return node as Expression
}

describe('evaluateNode', () => {
  it('evaluates a Literal to its value', () => {
    expect(evaluateNode(asExpression({ type: 'Literal', value: 'primary' }))).toBe('primary')
    expect(evaluateNode(asExpression({ type: 'Literal', value: 42 }))).toBe(42)
    expect(evaluateNode(asExpression({ type: 'Literal', value: true }))).toBe(true)
  })

  it('evaluates an ArrayExpression element-wise, skipping null and spread', () => {
    const node = {
      type: 'ArrayExpression',
      elements: [
        { type: 'Literal', value: 'a' },
        null,
        { type: 'SpreadElement' },
        { type: 'Literal', value: 'b' }
      ]
    }
    expect(evaluateNode(asExpression(node))).toEqual(['a', 'b'])
  })

  it('evaluates an ObjectExpression with Identifier and string-literal keys', () => {
    const node = {
      type: 'ObjectExpression',
      properties: [
        {
          type: 'Property',
          key: { type: 'Identifier', name: 'name' },
          value: { type: 'Literal', value: 'primary' }
        },
        {
          type: 'Property',
          key: { type: 'Literal', value: 'is-default' },
          value: { type: 'Literal', value: true }
        }
      ]
    }
    expect(evaluateNode(asExpression(node))).toEqual({ name: 'primary', 'is-default': true })
  })

  it('evaluates a TemplateLiteral, interpolating its expressions', () => {
    const node = {
      type: 'TemplateLiteral',
      quasis: [{ value: { cooked: 'count: ' } }, { value: { cooked: ' items' } }],
      expressions: [{ type: 'Literal', value: 3 }]
    }
    expect(evaluateNode(asExpression(node))).toBe('count: 3 items')
  })

  it('throws on a node type it cannot evaluate', () => {
    expect(() =>
      evaluateNode(asExpression({ type: 'CallExpression', callee: {}, arguments: [] }))
    ).toThrow('Cannot evaluate: CallExpression')
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
