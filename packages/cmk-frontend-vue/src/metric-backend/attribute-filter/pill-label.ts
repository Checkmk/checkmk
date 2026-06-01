/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { AttributeCondition, AttributeType, Operator } from './types'

export const ATTRIBUTE_TYPE_LABELS: Record<Exclude<AttributeType, null>, string> = {
  resource: 'Resource',
  scope: 'Scope',
  datapoint: 'Data point'
}

function attributeTypePrefixes(): Record<Exclude<AttributeType, null>, TranslatedString> {
  const { _t } = usei18n()
  return {
    resource: _t('[Resource]'),
    scope: _t('[Scope]'),
    datapoint: _t('[Data point]')
  }
}

function operatorPhrases(): Record<Operator, TranslatedString> {
  const { _t } = usei18n()
  return {
    eq: _t('is'),
    neq: _t('is not'),
    contains: _t('contains'),
    not_contains: _t('does not contain'),
    starts_with: _t('starts with'),
    not_starts_with: _t('does not start with'),
    ends_with: _t('ends with'),
    not_ends_with: _t('does not end with'),
    regex: _t('matches regex'),
    not_regex: _t('does not match regex'),
    exists: _t('exists'),
    not_exists: _t('does not exist')
  }
}

export function attributeTypePrefix(attributeType: AttributeType): string {
  return attributeType === null ? '' : `${attributeTypePrefixes()[attributeType]} `
}

export function operatorPhrase(operator: Operator): string {
  return operatorPhrases()[operator]
}

export function pillLabel(condition: AttributeCondition): string {
  const prefix = attributeTypePrefix(condition.attributeType)
  const phrase = operatorPhrase(condition.operator)
  const key = condition.key ?? ''
  const isExistence = condition.operator === 'exists' || condition.operator === 'not_exists'
  if (isExistence) {
    return `${prefix}${key} ${phrase}`
  }
  return `${prefix}${key} ${phrase} ${condition.value}`
}
