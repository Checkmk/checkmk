/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ComponentProps } from 'vue-component-type-helpers'

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

type InternalVueProps = 'key' | 'ref' | 'ref_for' | 'ref_key' | 'class' | 'style' | `on${string}`

export type UserProps<T> = Omit<ComponentProps<T>, InternalVueProps>

export type PanelConfigFor<T, TOmit extends keyof UserProps<T> = never> = {
  [K in keyof UserProps<T> as K extends TOmit ? never : K]-?: PropDef
}
