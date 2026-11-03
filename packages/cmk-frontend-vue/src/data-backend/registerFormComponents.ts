/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { registerFormComponents } from '@/form'

import FormDataBackendSettings from './FormDataBackendSettings.vue'

export function registerDataBackendFormComponents(): void {
  registerFormComponents({
    data_backend_settings: FormDataBackendSettings
  })
}
