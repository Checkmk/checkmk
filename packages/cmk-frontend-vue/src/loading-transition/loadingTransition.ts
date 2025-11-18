/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { LoadingTransition as _LoadingTransition } from 'cmk-shared-typing/typescript/loading_transition'

export type LoadingTransition = _LoadingTransition

/** KLUDGE: Share the implementation with the backend until we have a good
 * solution to slot in python html or we move all callsites into Vue.
 */
declare const cmk: {
  utils: {
    makeLoadingTransition: (template: string | null, delay: number, title?: string) => void
  }
}

export function showLoadingTransition(loadingTransition: LoadingTransition, title?: string): void {
  cmk.utils.makeLoadingTransition(loadingTransition, 1000, title)
}
