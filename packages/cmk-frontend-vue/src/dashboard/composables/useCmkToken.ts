/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject, provide } from 'vue'

export const cmkTokenKey: InjectionKey<string | undefined> = Symbol('cmkToken')

export function useProvideCmkToken(value: string): void {
  provide(cmkTokenKey, value)
}

export function useInjectCmkToken(): string | undefined {
  return inject(cmkTokenKey, undefined)
}
