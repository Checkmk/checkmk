<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'

interface SpecificFilterProps {
  globalFiltersLabel: TranslatedString
  globalFilterTooltip: TranslatedString

  widgetFilterLabel: TranslatedString
  widgetFilterTooltip: TranslatedString
}

defineProps<SpecificFilterProps>()
const displayAppliedFilters = ref<boolean>(false)
const displayWidgetFilters = ref<boolean>(true)
</script>

<template>
  <CmkCollapsibleTitle
    :title="globalFiltersLabel"
    :help_text="globalFilterTooltip"
    :open="displayAppliedFilters"
    @toggle-open="displayAppliedFilters = !displayAppliedFilters"
  />
  <CmkCollapsible :open="displayAppliedFilters">
    <slot name="global-filters" />
  </CmkCollapsible>

  <CmkCollapsibleTitle
    :title="widgetFilterLabel"
    :help_text="widgetFilterTooltip"
    :open="displayWidgetFilters"
    @toggle-open="displayWidgetFilters = !displayWidgetFilters"
  />
  <CmkCollapsible :open="displayWidgetFilters">
    <slot name="widget-filters" />
  </CmkCollapsible>
</template>
