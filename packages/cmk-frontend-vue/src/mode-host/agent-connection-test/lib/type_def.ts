/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'

export type PackageOption = {
  label: 'RPM' | 'DEB' | 'TGZ'
  value: 'rpm' | 'deb' | 'tgz'
}
export type PackageOptions = PackageOption[]

export interface AgentSlideOutTabs {
  id: string
  title: string
  installMsg?: TranslatedString
  installCmd?: string | undefined
  installDebCmd?: string
  installRpmCmd?: string
  installTgzCmd?: string | undefined
  registrationMsg?: TranslatedString
  registrationCmd?: string
  installUrl?: InstallUrl | undefined
  toggleButtonOptions?: PackageOptions
}

export interface InstallUrl {
  title: TranslatedString
  url: string
  msg: TranslatedString
  icon?: SimpleIcons
}
