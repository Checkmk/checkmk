/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { storageHandler } from './utils'
import { ref, watch } from 'vue'
import type { Ref } from 'vue'

const usePersistentRef = <T>(key: string, defaultValue: T, storageOpt?: 'session' | 'local') => {
  const storage = storageOpt === 'session' ? sessionStorage : localStorage
  const currentValue = storageHandler.get(storage, key, defaultValue) as T
  const value = ref(currentValue) as Ref<T>
  watch(value, (newValue) => {
    storageHandler.set(storage, key, newValue)
  })

  return value
}

export default usePersistentRef
