/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * vite-plugin-ucl-mcp.ts
 *
 * Vite plugin that emits a combined component JSON for dev docs on each production build.
 * Skipped during `vite dev` (serve mode).
 */
import type {
  ExportNamedDeclaration,
  Expression,
  Identifier,
  Literal,
  Program,
  Property,
  VariableDeclaration
} from 'acorn'
import path from 'node:path'
import { type Plugin } from 'vite'

import { type PropDef } from './types/prop-def'

export function evaluateNode(node: Expression): unknown {
  switch (node.type) {
    case 'Literal':
      return node.value
    case 'ArrayExpression':
      return node.elements
        .filter((e): e is Expression => e !== null && e.type !== 'SpreadElement')
        .map(evaluateNode)
    case 'ObjectExpression':
      return Object.fromEntries(
        node.properties
          .filter((p): p is Property => p.type === 'Property')
          .map((p) => {
            const key = p.key.type === 'Identifier' ? p.key.name : String((p.key as Literal).value)
            return [key, evaluateNode(p.value)]
          })
      )
    case 'TemplateLiteral': {
      let result = node.quasis[0]!.value.cooked ?? ''
      for (let i = 0; i < node.expressions.length; i++) {
        result += String(evaluateNode(node.expressions[i]!))
        result += node.quasis[i + 1]!.value.cooked ?? ''
      }
      return result
    }
    default:
      throw new Error(`Cannot evaluate: ${node.type}`)
  }
}

export type ApiPropDef = {
  name: string
  type: string
  options?: string[]
  uclInitialState?: unknown
  description?: string
}

export type AccessibilityItem = {
  keys: (string | string[])[]
  description: string
}

export type CatalogEntry = {
  name: string
  slug: string
  category: string
  publicUrl: string
}

export type ComponentDetail = CatalogEntry & {
  description: string
  props: ApiPropDef[]
  codeExample: string
  accessibility: AccessibilityItem[]
}

/**
 * Converts a plain panelConfig object to ApiPropDef[] for the API.
 *
 * The UCL source format: { type, title, initialState, options?, help? }
 * is mapped to the AI-readable API format: { name, type, uclInitialState?, options?, description? }
 *
 */
export function serializePanelConfig(config: Record<string, PropDef>): ApiPropDef[] {
  return Object.entries(config).map(([name, def]) => {
    const prop: ApiPropDef = { name, type: def.type }
    if (def.initialState !== undefined) {
      prop.uclInitialState = def.initialState
    }
    if (def.help) {
      prop.description = def.help
    }
    if (def.type === 'list') {
      prop.options = def.options.map((o) => o.name)
    }
    return prop
  })
}

export function generateUclApiPlugin(): Plugin {
  const componentDetails: ComponentDetail[] = []

  return {
    name: 'vite-plugin-ucl-mcp',
    apply: 'build',
    enforce: 'post',

    transform(code, id) {
      if (!id.includes('?vue&type=script')) {
        return
      }
      const filePath = id.split('?')[0]!

      if (!filePath.includes('/components/')) {
        return
      }
      const base = path.basename(filePath)
      if (!base.startsWith('Ucl') || base.endsWith('Dev.vue')) {
        return
      }

      const compIdx = filePath.lastIndexOf('/components/')
      if (compIdx === -1) {
        this.warn(`UCL plugin: could not resolve components dir for ${filePath}`)
        return
      }
      const componentsDir = filePath.slice(0, compIdx + '/components'.length)
      const category = path.relative(componentsDir, path.dirname(filePath)).split(path.sep)[0]!
      if (!category || category.startsWith('..')) {
        this.warn(`UCL plugin: could not determine category for ${filePath}`)
        return
      }

      const name = base.replace(/^Ucl/, '').replace(/\.vue$/, '')

      let program: Program
      try {
        program = this.parse(code) as Program
      } catch {
        this.warn(`UCL plugin: failed to parse ${filePath}`)
        return
      }

      let props: ApiPropDef[] = []
      let codeExample = ''
      let accessibility: AccessibilityItem[] = []
      let description = ''

      for (const node of program.body) {
        if (node.type !== 'ExportNamedDeclaration') {
          continue
        }
        const decl = node as ExportNamedDeclaration
        if (decl.declaration?.type !== 'VariableDeclaration') {
          continue
        }
        const varDecl = decl.declaration as VariableDeclaration

        for (const d of varDecl.declarations) {
          if (!d.init) {
            continue
          }
          try {
            const value = evaluateNode(d.init)
            const varName = d.id.type === 'Identifier' ? (d.id as Identifier).name : ''
            if (varName.includes('panelConfig')) {
              props = serializePanelConfig(value as Record<string, PropDef>)
            } else if (varName === 'codeExample') {
              codeExample = value as string
            } else if (varName === 'a11yData') {
              accessibility = value as AccessibilityItem[]
            } else if (varName === 'description') {
              description = value as string
            }
          } catch {
            // skip non-evaluable declarations
          }
        }
      }

      if (codeExample === '') {
        this.warn(
          `UCL plugin: no exported data found in ${filePath} — does it use the split <script>/<script setup> pattern?`
        )
      }

      const slug = name.toLowerCase()
      componentDetails.push({
        name,
        slug,
        category,
        publicUrl: `/${category}/${slug}`,
        description,
        props,
        codeExample,
        accessibility
      })
    },

    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'api/ucl-components.json',
        source: JSON.stringify(componentDetails, null, 2)
      })
    }
  }
}
