/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useId as vueUseId } from 'vue'

export default function useId(): string {
  const id = vueUseId()
  if (id === undefined || id === '') {
    // the original useId implementation should not throw an error:
    // https://github.com/vuejs/core/pull/11404#pullrequestreview-2303630461
    // but then they just made it return an empty string:
    // https://github.com/vuejs/core/commit/a177092754642af2f98c33a4feffe8f198c3c950
    throw Error('Can not generate unique id, missing active currentInstance.')
  }
  return id
}
