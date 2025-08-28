/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Plugin, type Ref, computed, ref } from 'vue'
import { type Translations, createGettext, useGettext } from 'vue3-gettext'

import type { TranslatedString } from '@/lib/i18nString'

import { dummyT, dummyTn, dummyTnp, dummyTp } from './i18nDummy'

const AVAILABLE_LANGUAGES: Record<string, string> = {
  en: 'English',
  de: 'German',
  fr: 'French'
}

export type SupportedLanguage = keyof typeof AVAILABLE_LANGUAGES

type InterpolationValues = Record<string, string | number>

// Lazy loaded translation handling
async function loadTranslations(language: SupportedLanguage): Promise<Translations> {
  return (await import(`@/assets/locale/${language}.json`)).default
}

type GettextInstance = ReturnType<typeof createGettext>

interface I18nState {
  translationLoading: Ref<boolean>
  currentLanguage: Ref<SupportedLanguage>
  instance: GettextInstance | null
}

const globalState: I18nState = {
  translationLoading: ref<boolean>(false),
  currentLanguage: ref<SupportedLanguage>('en'),
  instance: null
}

async function switchLanguage(language: SupportedLanguage): Promise<void> {
  if (!globalState.instance) {
    throw new Error('Gettext instance is not initialized. Call createi18n() first.')
  }

  if (language === 'en' || language in globalState.instance.translations) {
    // No lazy loading required, just switch
    globalState.translationLoading.value = false
    globalState.instance.current = language
    globalState.currentLanguage.value = language
    return
  }

  if (globalState.translationLoading.value) {
    // Waiting on lazy load, keep current language
    return
  }
  globalState.translationLoading.value = true

  try {
    const data = await loadTranslations(language)
    globalState.instance.translations = {
      ...globalState.instance.translations,
      ...data
    }
    globalState.instance.current = language
    globalState.currentLanguage.value = language
  } catch (error) {
    throw new Error(`Failed to load translations for ${language}: ${error}`)
  } finally {
    globalState.translationLoading.value = false
  }
}

/**
 * Marks a string as already translated.
 *
 * This is useful for strings that are not to be translated (e.g., product names or technical terms.)
 * or come translated from the backend.
 *
 * Example usage:
 * ```ts
 * untranslated('Checkmk')
 * untranslated('CPU')
 * ```
 */
export function untranslated(alreadyTranslatedString: string): TranslatedString {
  return alreadyTranslatedString as TranslatedString
}

interface I18nFunctions {
  /**
   * Defines a string to be translated.
   *
   * @param msg
   *    This will be used in the parsing process to define the english translation.
   *
   *    You can specify named placeholder values with `%{<name>}` which will be replaced by the values
   *    in the `interpolation` object.
   *
   * @param interpolation
   *    Used to replace placeholders in the translation string.
   *
   * Example usage:
   * ```ts
   * _t('Enter your name')
   * _t('Hello %{name}!', { name: 'Alice' })
   * ```
   */
  _t(msg: string): TranslatedString
  _t(msg: string, interpolation: InterpolationValues): TranslatedString

  /**
   * Defines a string to be translated with pluralization.
   *
   * @param singular
   *    This will be used in the parsing process to define the singular english translation.
   *
   *    You can specify named placeholder values with `%{<name>}` which will be replaced by the values
   *    in the `interpolation` object.
   *
   * @param plural
   *    This will be used in the parsing process to define the plural english translation.
   *
   *    You can specify named placeholder values with `%{<name>}` which will be replaced by the values
   *    in the `interpolation` object.
   *
   * @param count
   *    Specifies the number of items for pluralization.
   *
   * @param interpolation
   *    Used to replace placeholders in the translation string.
   *
   * Example usage:
   * ```ts
   * _tn('apple', 'apples', appleArray.length)
   * _tn('We found 1 item', 'We found {n} items', items.length, { n: items.length })
   * ```
   */
  _tn(singular: string, plural: string, count: number): TranslatedString
  _tn(
    singular: string,
    plural: string,
    count: number,
    interpolation: InterpolationValues
  ): TranslatedString

  /**
   * Defines a string to be translated with context.
   *
   * You can give some additional context to help with translation, this context also separates
   * translation instances of the same english target string.
   *
   * @param context
   *    Context to aid with translation and to separate translation instances of the same english target string.
   *
   * @param msg
   *    This will be used in the parsing process to define the english translation.
   *
   *    You can specify named placeholder values with `%{<name>}` which will be replaced by the values
   *    in the `interpolation` object.
   *
   * @param interpolation
   *    Used to replace placeholders in the translation string.
   *
   * Example usage:
   * ```ts
   * _tp('a compliment, not a fruit', 'peachy')
   * _tp('a bank for money, not for sitting', 'A bank in %{location}', { location })
   * ```
   */
  _tp(context: string, msg: string): TranslatedString
  _tp(context: string, msg: string, interpolation: InterpolationValues): TranslatedString

  /**
   * Defines a string to be translated with pluralization and context.
   *
   * You can give some additional context to help with translation, this context also separates
   * translation instances of the same english target string.
   *
   * @param context
   *    Context to aid with translation and to separate translation instances of the same english target string.
   *
   * @param singular
   *    This will be used in the parsing process to define the singular english translation.
   *
   *    You can specify named placeholder values with `%{<name>}` which will be replaced by the values
   *    in the `interpolation` object.
   *
   * @param plural
   *    This will be used in the parsing process to define the plural english translation.
   *
   *    You can specify named placeholder values with `%{<name>}` which will be replaced by the values
   *    in the `interpolation` object.
   *
   * @param count
   *    Specifies the number of items for pluralization.
   *
   * @param interpolation
   *    Used to replace placeholders in the translation string.
   *
   * Example usage:
   * ```ts
   * _tnp('Poker hands not limbs', 'hand', 'hands', hands.length)
   * _tnp('Body part, not unit of measurement', '{n_feet} foot', '{n_feet} feet', n_feet, { n_feet })
   * ```
   */
  _tnp(context: string, singular: string, plural: string, count: number): TranslatedString
  _tnp(
    context: string,
    singular: string,
    plural: string,
    count: number,
    interpolation: InterpolationValues
  ): TranslatedString
}

/**
 * Hook to offer i18n functionality in Vue components.
 *
 * Callsites must not be renamed, they are parsed in the build process to extract all strings to be translated.
 */
export default function usei18n() {
  const { $gettext, $ngettext, $npgettext, $pgettext } = useGettext()
  const showEnglish = computed(() => globalState.currentLanguage.value === 'en')

  function _t(msg: string, interpolation?: InterpolationValues): string {
    if (showEnglish.value) {
      return dummyT(msg, interpolation)
    }
    return interpolation === undefined ? $gettext(msg) : $gettext(msg, interpolation)
  }

  function _tn(
    singular: string,
    plural: string,
    count: number,
    interpolation?: InterpolationValues
  ): string {
    if (showEnglish.value) {
      return dummyTn(singular, plural, count, interpolation)
    }
    return interpolation === undefined
      ? $ngettext(singular, plural, count)
      : $ngettext(singular, plural, count, interpolation)
  }

  function _tp(context: string, msg: string, interpolation?: InterpolationValues): string {
    if (showEnglish.value) {
      return dummyTp(context, msg, interpolation)
    }
    return interpolation === undefined
      ? $pgettext(context, msg)
      : $pgettext(context, msg, interpolation)
  }

  function _tnp(
    context: string,
    singular: string,
    plural: string,
    count: number,
    interpolation?: InterpolationValues
  ): string {
    if (showEnglish.value) {
      return dummyTnp(context, singular, plural, count, interpolation)
    }
    return interpolation === undefined
      ? $npgettext(context, singular, plural, count)
      : $npgettext(context, singular, plural, count, interpolation)
  }

  return {
    _t: _t as I18nFunctions['_t'],
    _tn: _tn as I18nFunctions['_tn'],
    _tp: _tp as I18nFunctions['_tp'],
    _tnp: _tnp as I18nFunctions['_tnp'],
    switchLanguage,
    translationLoading: globalState.translationLoading
  }
}

export function createi18n(): Plugin {
  if (!globalState.instance) {
    globalState.instance = createGettext({
      availableLanguages: AVAILABLE_LANGUAGES,
      defaultLanguage: 'en',
      translations: {}
    })
  }

  return globalState.instance
}
