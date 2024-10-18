/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { InjectionKey, Ref } from 'vue'
import type { StageData } from '@/quick-setup/components/quick-setup/widgets/widget_types'

export const formDataKey: InjectionKey<Ref<{ [key: number]: StageData }>> = Symbol('formData')
