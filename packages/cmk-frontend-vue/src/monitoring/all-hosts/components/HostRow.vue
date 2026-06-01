<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkTag, { type Colors as TagColor } from '@/components/CmkTag.vue'

import type { HostEntry, HostState } from '@/monitoring/shared/api/types'
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'

const { _t } = usei18n()

const props = defineProps<{
  row: HostEntry
}>()

const STATE_COLOR: Record<HostState, TagColor> = {
  UP: 'success',
  DOWN: 'danger',
  UNREACHABLE: 'warning'
}

const stateLabel: Record<HostState, TranslatedString> = {
  UP: _t('UP'),
  DOWN: _t('DOWN'),
  UNREACHABLE: _t('UNREACH')
}

const count = (n: number): TranslatedString => untranslated(String(n))

const serviceCounts = computed(() => ({
  ok: count(props.row.num_services_ok),
  warn: count(props.row.num_services_warn),
  crit: count(props.row.num_services_crit),
  unknown: count(props.row.num_services_unknown),
  pending: count(props.row.num_services_pending)
}))
</script>

<template>
  <BaseCell>
    <CmkTag variant="fill" :color="STATE_COLOR[row.state]" :content="stateLabel[row.state]" />
  </BaseCell>
  <BaseCell>{{ row.name }}</BaseCell>
  <BaseCell hide-below="l">{{ row.alias }}</BaseCell>
  <BaseCell hide-below="m">{{ row.ip }}</BaseCell>
  <BaseCell>
    <CmkTag variant="fill" color="success" :content="serviceCounts.ok" />
  </BaseCell>
  <BaseCell>
    <CmkTag variant="fill" color="warning" :content="serviceCounts.warn" />
  </BaseCell>
  <BaseCell>
    <CmkTag variant="fill" color="danger" :content="serviceCounts.crit" />
  </BaseCell>
  <BaseCell>
    <CmkTag variant="fill" color="default" :content="serviceCounts.unknown" />
  </BaseCell>
  <BaseCell>
    <CmkTag variant="outline" color="default" :content="serviceCounts.pending" />
  </BaseCell>
</template>
