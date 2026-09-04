<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkTag, { type Colors } from '@/components/CmkTag.vue'

import type { HostState } from '@/monitoring/shared/api/types'

const props = defineProps<{ state: HostState }>()

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
      return _t('DOWN')
    case 'UNREACHABLE':
      return _t('UNREACH')
    case 'PENDING':
      return _t('PEND')
    default:
      return assertNever(state)
  }
})

const stateColor = computed<Colors>(() => {
  const state = props.state
  switch (state) {
    case 'UP':
      return 'success'
    case 'DOWN':
      return 'danger'
    case 'UNREACHABLE':
      return 'unknown'
    case 'PENDING':
      return 'default'
    default:
      return assertNever(state)
  }
})
</script>

<template>
  <CmkTag
    class="monitoring-host-state-display"
    :color="stateColor"
    variant="weighted"
    :content="stateLabel"
    size="small"
  />
</template>

<style scoped>
.monitoring-host-state-display {
  --host-state-display-height: 21px;
  --host-state-display-min-width: 60px;

  margin: 0;
  display: flex;
  box-sizing: border-box;
  height: var(--host-state-display-height);
  min-width: var(--host-state-display-min-width);
  align-items: center;
  justify-content: center;
}
</style>
