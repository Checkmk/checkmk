/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n, {
  type SupportedLanguage,
  type TranslationLoader,
  setTranslationLoader,
  untranslated
} from './i18n.ts'

export { setTranslationLoader, untranslated, type SupportedLanguage, type TranslationLoader }
export default usei18n
