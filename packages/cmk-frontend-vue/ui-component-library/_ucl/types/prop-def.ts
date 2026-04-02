/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface BoolPropDef {
  type: 'boolean'
  title: string
  initialState: boolean
  help?: string
}

export interface StringPropDef {
  type: 'string'
  title: string
  initialState: string
  help?: string
}

export interface ListPropDef<T extends string = string> {
  type: 'list'
  title: string
  options: Array<{ title: string; name: NonNullable<T> }>
  initialState: T
  help?: string
}

export interface NumberPropDef {
  type: 'number'
  title: string
  initialState: number
  help?: string
}

export interface MultilineStringPropDef {
  type: 'multiline-string'
  title: string
  initialState: string
  help?: string
}

export interface StringArrayPropDef {
  type: 'string-array'
  title: string
  initialState: string[]
  help?: string
}

export type PropDef =
  | BoolPropDef
  | StringPropDef
  | NumberPropDef
  | ListPropDef<string>
  | MultilineStringPropDef
  | StringArrayPropDef

export type PanelConfig = Record<string, PropDef>
