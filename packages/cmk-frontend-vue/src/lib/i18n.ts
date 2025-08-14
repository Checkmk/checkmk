/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Plugin } from 'vue'
import { createGettext, useGettext } from 'vue3-gettext'

// Generated during build process
import de from '@/assets/locale/de.json'
import en from '@/assets/locale/en.json'

type InterpolationValues = Record<string, string | number>

/**
 * Hook to offer i18n functionality in Vue components.
 *
 * Callsites must not be renamed, they are parsed in the build process to extract all strings to be translated.
 */
export default function usei18n() {
  const { $gettext, $ngettext, $npgettext, $pgettext } = useGettext()

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
  function _t(msg: string): string
  function _t(msg: string, interpolation: InterpolationValues): string
  function _t(msg: string, interpolation?: InterpolationValues): string {
    return interpolation === undefined ? $gettext(msg) : $gettext(msg, interpolation)
  }

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
  function _tn(singular: string, plural: string, count: number): string
  function _tn(
    singular: string,
    plural: string,
    count: number,
    interpolation: InterpolationValues
  ): string
  function _tn(
    singular: string,
    plural: string,
    count: number,
    interpolation?: InterpolationValues
  ): string {
    return interpolation === undefined
      ? $ngettext(singular, plural, count)
      : $ngettext(singular, plural, count, interpolation)
  }

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
  function _tp(context: string, msg: string): string
  function _tp(context: string, msg: string, interpolation: InterpolationValues): string
  function _tp(context: string, msg: string, interpolation?: InterpolationValues): string {
    return interpolation === undefined
      ? $pgettext(context, msg)
      : $pgettext(context, msg, interpolation)
  }

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
  function _tnp(context: string, singular: string, plural: string, count: number): string
  function _tnp(
    context: string,
    singular: string,
    plural: string,
    count: number,
    interpolation: InterpolationValues
  ): string
  function _tnp(
    context: string,
    singular: string,
    plural: string,
    count: number,
    interpolation?: InterpolationValues
  ): string {
    return interpolation === undefined
      ? $npgettext(context, singular, plural, count)
      : $npgettext(context, singular, plural, count, interpolation)
  }

  return {
    _t,
    _tn,
    _tp,
    _tnp
  }
}

export function createi18n(): Plugin {
  return createGettext({
    availableLanguages: {
      en: 'English',
      de: 'German'
    },
    defaultLanguage: 'en',
    translations: { ...en, ...de }
  })
}
