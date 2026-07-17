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

const props = defineProps<{ state: HostState; pending?: boolean | undefined }>()

const { _t } = usei18n()

const stateLabel = computed<TranslatedString>(() => {
  if (props.pending) {
    return _t('PEND')
  }
  switch (props.state) {
    case 'UP':
      return _t('UP')
    case 'DOWN':
      return _t('DOWN')
    case 'UNREACHABLE':
    default:
      return _t('UNREACH')
  }
})

const stateColor = computed<Colors>(() => {
  if (props.pending) {
    return 'default'
  }
  switch (props.state) {
    case 'UP':
      return 'success'
    case 'DOWN':
      return 'danger'
    default:
      return 'unknown'
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
