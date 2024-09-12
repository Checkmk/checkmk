/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { App } from 'vue'

export function mixinUniqueId(app: App<Element>) {
  let uniqueId = 0
  app.mixin({
    beforeCreate: function () {
      this.$componentId = `comp_${uniqueId}`
      uniqueId += 1
    }
  })
}
