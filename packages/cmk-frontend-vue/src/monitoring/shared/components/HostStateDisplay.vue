<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import StateTag, { type StateTagSize, type StateTone } from 'cmk-ui-library/components/StateTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { HostState } from '@/monitoring/shared/api/types'

const props = defineProps<{
  state: HostState
  stale?: boolean | undefined
  /** Two-letter labels, for a state column too tight to spell the state out. */
  abbreviated?: boolean | undefined
}>()

const { _t } = usei18n()

const assertNever = (value: never): never => {
  throw new Error(`Unhandled host state: ${String(value)}`)
}

const stateLabel = computed<TranslatedString>(() => {
  const state = props.state
  switch (state) {
    case 'UP':
      return _t('UP')
    case 'DOWN':
      return props.abbreviated ? _t('DO') : _t('DOWN')
    case 'UNREACHABLE':
      return props.abbreviated ? _t('UN') : _t('UNREACH')
    case 'PENDING':
      return props.abbreviated ? _t('PD') : _t('PENDING')
    default:
      return assertNever(state)
  }
})

const stateTitle = computed<TranslatedString | undefined>(() => {
  if (!props.abbreviated) {
    return undefined
  }
  const state = props.state
  switch (state) {
    case 'UP':
      return undefined
    case 'DOWN':
      return _t('Down')
    case 'UNREACHABLE':
      return _t('Unreachable')
    case 'PENDING':
      return _t('Pending')
    default:
      return assertNever(state)
  }
})

const stateTone = computed<StateTone>(() => {
  const state = props.state
  switch (state) {
    case 'UP':
      return 'ok'
    case 'DOWN':
      return 'critical'
    case 'UNREACHABLE':
      return 'unknown'
    case 'PENDING':
      return 'pending'
    default:
      return assertNever(state)
  }
})

const tagSize = computed<StateTagSize>(() => (props.abbreviated ? 'compact' : 'default'))
</script>

<template>
  <StateTag
    kind="host"
    :label="stateLabel"
    :title="stateTitle"
    :tone="stateTone"
    :size="tagSize"
    :stale="stale"
  />
</template>
