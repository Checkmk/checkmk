<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import HostModeIcons from '@/monitoring/shared/components/HostModeIcons.vue'

import type { HostMode } from '../../api/types'
import BaseCell from './BaseCell.vue'

defineProps<{
  modes: HostMode[]
  columnId?: string | undefined
}>()
</script>

<template>
  <BaseCell :column-id="columnId">
    <template #default>
      <HostModeIcons :modes="modes" />
    </template>
  </BaseCell>
</template>
