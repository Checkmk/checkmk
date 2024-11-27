<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import ConditionalNotificationStageWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationStageWidget.vue'
import type { CompositeWidgetProps } from '@/quick-setup/components/quick-setup/widgets/widget_types'
import { inject } from 'vue'
import { formDataKey } from '@/quick-setup/keys.ts'
import { showConditionalNotificationStageWidget } from '@/quick-setup/components/quick-setup/widgets/conditional_widget_utils.ts'

const props = defineProps<CompositeWidgetProps>()

const formData = inject(formDataKey)
</script>

<template>
  <ConditionalNotificationStageWidget
    :condition="showConditionalNotificationStageWidget(formData, 'ec_alerts')"
    :items="props.items"
    :data="props?.data || {}"
    :errors="props.errors || {}"
  />
</template>
