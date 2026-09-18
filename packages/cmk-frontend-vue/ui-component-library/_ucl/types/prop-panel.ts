/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import { type Component, type Ref, ref } from 'vue'

import type {
  BoolPropDef,
  ListPropDef,
  MultiSelectPropDef,
  MultilineStringPropDef,
  NumberPropDef,
  PanelConfig,
  PanelConfigFor,
  PropDef,
  StringArrayPropDef,
  StringPropDef,
  UserProps
} from './prop-def'

export type {
  BoolPropDef,
  ListPropDef,
  MultilineStringPropDef,
  MultiSelectPropDef,
  NumberPropDef,
  PanelConfig,
  PanelConfigFor,
  PropDef,
  StringArrayPropDef,
  StringPropDef
}

export type Options<T> = { title: string; name: NonNullable<T> }

/**
 * Build the option list of a `list` prop from a record keyed by the variant name.
 *
 * The record type makes the type checker reject an option list that omits a variant
 * or names one that does not exist. Options are offered in key order.
 *
 * A list that deliberately offers only a sample of a large union keeps the plain
 * array form with `satisfies Options<T>[]`.
 */
export const listOptions = <T extends string | null | undefined>(
  titles: Record<NonNullable<T>, string>
): Options<T>[] => Object.entries(titles).map(([name, title]) => ({ name, title }) as Options<T>)

// Suggestion-typed alias kept for components that use CmkSuggestions as options source
export type SuggestionOptions = Suggestion[]

export type PanelState = Record<string, boolean | string | number | string[]>

type InferStateFromDef<T extends PropDef> = T extends BoolPropDef
  ? boolean
  : T extends StringPropDef
    ? string
    : T extends NumberPropDef
      ? number
      : T extends ListPropDef<infer U>
        ? NonNullable<U>
        : T extends MultilineStringPropDef
          ? string
          : T extends StringArrayPropDef
            ? string[]
            : T extends MultiSelectPropDef<infer U>
              ? NonNullable<U>[]
              : never

export type InferPanelState<T extends PanelConfig> = {
  [K in keyof T]: InferStateFromDef<T[K]>
}

export class PanelStateCreator<C extends Component, TOmit extends keyof UserProps<C> = never> {
  createRef<T extends PanelConfigFor<C, TOmit> & PanelConfig>(config: T): Ref<InferPanelState<T>> {
    return ref(
      Object.fromEntries(Object.entries(config).map(([key, def]) => [key, def.initialState]))
    ) as Ref<InferPanelState<T>>
  }
}
