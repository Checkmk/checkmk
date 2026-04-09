/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'

export interface AgentSlideOutSubTab {
  id: string
  label: string
  installMsg: TranslatedString
  downloadCmd?: string
  installCmd: string
  installWarning?: TranslatedString
}

export interface AgentSlideOutTabs {
  id: string
  title: string
  installMsg?: TranslatedString
  installWarning?: TranslatedString
  installCmd?: string | undefined
  installDownloadCmd?: string
  registrationMsg?: TranslatedString
  registrationCmd?: string
  installUrl?: InstallUrl | undefined
  subTabs?: AgentSlideOutSubTab[]
}

export interface InstallUrl {
  title: TranslatedString
  url: string
  msg: TranslatedString
  icon?: SimpleIcons
}
