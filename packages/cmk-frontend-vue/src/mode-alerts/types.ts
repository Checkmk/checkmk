/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type {
  BinaryConditionChoicesValue,
  ConditionChoicesValue
} from 'cmk-shared-typing/typescript/vue_formspec_components'

export type ServiceNameMatch = 'exact' | 'regex'

export interface HostConditions {
  folder_path: string
  host_tags?: ConditionChoicesValue[]
  host_label_groups?: BinaryConditionChoicesValue
  explicit_hosts?: { value: string[]; negate: boolean }
}

export type FolderPaths = Record<string, string>

export type AlertConditions = components['schemas']['AlertConditionsModel']
type TagCondition = NonNullable<AlertConditions['host_tags']>[number]

export type AlertThresholds = components['schemas']['AlertThresholdsModel']
type Levels = NonNullable<AlertThresholds['upper']>
type PredictionPeriod = components['schemas']['PredictiveLevelsModel']['period']
type DifferenceType = components['schemas']['PredictiveLevelsModel']['difference']['type']

export type PredictionPeriods = Record<string, PredictionPeriod>

type Level = number | ''
type LevelsPair = [Level, Level]

export type LevelsValue =
  | ['no_levels', null]
  | ['fixed', LevelsPair]
  | [
      'predictive',
      {
        period: string
        horizon: Level
        levels: [DifferenceType, LevelsPair]
        bound: LevelsPair | null
      }
    ]

export interface ThresholdsValue {
  upper_levels?: LevelsValue
  lower_levels?: LevelsValue
}

export interface AlertModel {
  name: string
  matchType: ServiceNameMatch
  servicePattern: string
  conditions: HostConditions
  thresholds: ThresholdsValue
}

export function emptyAlert(
  conditions: HostConditions = { folder_path: '' },
  thresholds: ThresholdsValue = {}
): AlertModel {
  return { name: '', matchType: 'exact', servicePattern: '', conditions, thresholds }
}

export function alertName(model: AlertModel): string {
  return model.name.trim()
}

export function servicePattern(model: AlertModel): string {
  return model.servicePattern.trim()
}

// The Livestatus and JavaScript dialects differ, so this only rules out patterns broken
// in both; Livestatus rejects the rest with a 400.
export function hasUnparsableRegex(model: AlertModel): boolean {
  const pattern = servicePattern(model)
  if (model.matchType !== 'regex' || pattern === '') {
    return false
  }
  try {
    new RegExp(pattern)
    return false
  } catch {
    return true
  }
}

function tagCondition({ group_name: key, value }: ConditionChoicesValue): TagCondition {
  if ('oper_eq' in value) {
    return { key, operator: 'is', value: value.oper_eq }
  }
  if ('oper_ne' in value) {
    return { key, operator: 'is_not', value: value.oper_ne }
  }
  if ('oper_or' in value) {
    return { key, operator: 'one_of', value: value.oper_or }
  }
  return { key, operator: 'none_of', value: value.oper_nor }
}

function folderPath(folderPaths: FolderPaths, optionId: string): string {
  const path = folderPaths[optionId]
  if (path === undefined) {
    // Falling back to the Main folder would silently widen the alert to every host.
    throw new Error(`Unknown folder option: ${optionId}`)
  }
  return path
}

// The rule editor drops a group without labels, too: the rule matcher counts it as
// matching, so with "or" or "not" it would select every host or none.
function hostLabelGroups(groups: BinaryConditionChoicesValue): BinaryConditionChoicesValue {
  const withLabels = groups.filter((group) => group.label_group.length > 0)
  // The new first group may be an "or", which would select every host as well.
  return withLabels.map((group, index) =>
    index === 0 && group.operator === 'or' ? { ...group, operator: 'and' } : group
  )
}

export function alertConditions(model: AlertModel, folderPaths: FolderPaths): AlertConditions {
  const conditions = model.conditions
  const explicitHosts = conditions.explicit_hosts
  return {
    folder: `/${folderPath(folderPaths, conditions.folder_path)}`,
    host_tags: (conditions.host_tags ?? []).map(tagCondition),
    host_label_groups: hostLabelGroups(conditions.host_label_groups ?? []),
    ...(explicitHosts && {
      host_name: {
        match_on: explicitHosts.value.filter((hostName) => hostName !== ''),
        operator: explicitHosts.negate ? 'none_of' : 'one_of'
      }
    })
  }
}

export function hasThresholds(model: AlertModel): boolean {
  const { upper_levels: upper, lower_levels: lower } = model.thresholds
  return upper !== undefined || lower !== undefined
}

function isComplete(pair: LevelsPair): boolean {
  return pair.every((level) => level !== '')
}

function hasCompleteLevels(value: LevelsValue | undefined): boolean {
  switch (value?.[0]) {
    case undefined:
    case 'no_levels':
      return true
    case 'fixed':
      return isComplete(value[1])
    case 'predictive': {
      const { horizon, levels, bound } = value[1]
      return horizon !== '' && isComplete(levels[1]) && (bound === null || isComplete(bound))
    }
  }
}

export function hasCompleteThresholds(model: AlertModel): boolean {
  return (
    hasCompleteLevels(model.thresholds.upper_levels) &&
    hasCompleteLevels(model.thresholds.lower_levels)
  )
}

function level(value: Level): number {
  if (value === '') {
    throw new Error('Incomplete levels cannot be sent')
  }
  return value
}

function predictionPeriod(periods: PredictionPeriods, optionId: string): PredictionPeriod {
  const period = periods[optionId]
  if (period === undefined) {
    throw new Error(`Unknown prediction period option: ${optionId}`)
  }
  return period
}

function levels(value: LevelsValue, periods: PredictionPeriods): Levels {
  switch (value[0]) {
    case 'no_levels':
      return { type: 'no_levels' }
    case 'fixed': {
      const [warn, crit] = value[1]
      return { type: 'fixed', warn: level(warn), crit: level(crit) }
    }
    case 'predictive': {
      const { period, horizon, levels: difference, bound } = value[1]
      const [type, [warn, crit]] = difference
      return {
        type: 'predictive',
        period: predictionPeriod(periods, period),
        horizon_days: level(horizon),
        difference: { type, warn: level(warn), crit: level(crit) },
        ...(bound && { fixed_limits: { warn: level(bound[0]), crit: level(bound[1]) } })
      }
    }
  }
}

export function alertThresholds(model: AlertModel, periods: PredictionPeriods): AlertThresholds {
  const { upper_levels: upper, lower_levels: lower } = model.thresholds
  return {
    ...(upper && { upper: levels(upper, periods) }),
    ...(lower && { lower: levels(lower, periods) })
  }
}
