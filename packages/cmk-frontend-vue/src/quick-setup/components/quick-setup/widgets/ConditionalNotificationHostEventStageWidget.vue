<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import ConditionalNotificationStageWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationStageWidget.vue'
import type { CompositeWidgetProps } from '@/quick-setup/components/quick-setup/widgets/widget_types'

const props = defineProps<CompositeWidgetProps>()
</script>

<template>
  <ConditionalNotificationStageWidget
    condition-key="host_events"
    :items="props.items"
    :data="props?.data || {}"
    :errors="props.errors || {}"
  />
</template>
