<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
/**
 * A cell of icons, each hyperlinked when it carries a link and read-only otherwise.
 *
 * Not to be confused with StateCell: this cell says what happened, or which modes are active,
 * rather than showing the current state of a host or service. The mode columns render linked
 * icons here; the History tab renders the event icon of a log entry, which links nowhere.
 */
import IconList from '@/monitoring/shared/components/IconList.vue'

import type { MonitoringIcon } from '../../api/types'
import BaseCell from './BaseCell.vue'

defineProps<{
  icons: MonitoringIcon[]
  columnId?: string | undefined
}>()
</script>

<template>
  <BaseCell :column-id="columnId">
    <template #default>
      <IconList :icons="icons" />
    </template>
  </BaseCell>
</template>
