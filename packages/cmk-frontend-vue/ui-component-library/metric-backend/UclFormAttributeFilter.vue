<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

export const panelConfig = {} satisfies PanelConfigFor<
  typeof FormAttributeFilter,
  'modelValue' | 'ariaLabel'
>
</script>

<script setup lang="ts">
import {
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import FormAttributeFilter from '@/metric-backend/attribute-filter/FormAttributeFilter.vue'
import type { AttributeFilterModel } from '@/metric-backend/attribute-filter/types'

defineProps<{ screenshotMode: boolean }>()

const filters = ref<AttributeFilterModel>([
  {
    id: crypto.randomUUID(),
    attributeType: 'resource',
    key: 'service.name',
    operator: 'eq',
    value: 'frontend',
    connector: 'AND'
  }
])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>FormAttributeFilter</UclDetailPageHeader>

    <UclDetailPageComponent>
      <FormAttributeFilter v-model="filters" />
    </UclDetailPageComponent>
  </UclDetailPageLayout>
</template>
