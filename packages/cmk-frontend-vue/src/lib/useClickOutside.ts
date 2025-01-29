/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Directive } from 'vue'

const useClickOutside = () => {
  return {
    mounted: (el, binding) => {
      el.clickOutsideEvent = (event: MouseEvent) => {
        if (!(el === event.target || el.contains(event.target))) {
          binding.value(event)
        }
      }
      document.body.addEventListener('click', el.clickOutsideEvent)
    },
    unmounted: (el) => {
      document.body.removeEventListener('click', el.clickOutsideEvent)
    }
  } as Directive
}

export default useClickOutside
