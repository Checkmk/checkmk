/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { localStorageHandler } from './utils'
import { ref, watch } from 'vue'

const usePersistentRef = <T>(key: string, defaultValue: T) => {
  const currentValue: T = localStorageHandler.get(key, defaultValue) as T
  const value = ref(currentValue as T)
  watch(value, (newValue) => {
    localStorageHandler.set(key, newValue)
  })

  return value
}

export default usePersistentRef
