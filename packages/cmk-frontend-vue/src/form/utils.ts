/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useId as vueUseId } from 'vue'

export function useId(): string {
  const id = vueUseId()
  if (id === undefined) {
    // the original useId implementation should not throw an error:
    // https://github.com/vuejs/core/pull/11404#pullrequestreview-2303630461
    throw Error('Can not generate unique id, missing active currentInstance.')
  }
  return id
}
