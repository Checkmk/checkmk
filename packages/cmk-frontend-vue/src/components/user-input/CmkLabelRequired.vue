<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkSpace from '@/components/CmkSpace.vue'

const { _t } = usei18n()

const { show = true, space = null } = defineProps<{
  show?: boolean
  space?: ('before' | 'after' | 'both') | null
}>()
</script>

<template>
  <span v-if="show" class="cmk-label-required">
    <CmkSpace v-if="space === 'before' || space === 'both'" :size="'small'" />({{
      _t('required')
    }})<CmkSpace v-if="space === 'after' || space === 'both'" :size="'small'" />
  </span>
</template>

<style scoped>
span.cmk-label-required {
  color: var(--form-element-required-color);
}
</style>
