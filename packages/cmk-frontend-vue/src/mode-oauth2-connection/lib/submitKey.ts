/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { InjectionKey } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

export const submitKey: InjectionKey<(data: OAuth2FormData) => Promise<TranslatedString | null>> =
  Symbol('submit')
