<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

const { _t } = usei18n()

interface CloneSuccessAlertProps {
  hasFilters?: boolean
}

interface CloneSuccessAlertEmit {
  editFilters: []
}

const props = defineProps<CloneSuccessAlertProps>()
const emits = defineEmits<CloneSuccessAlertEmit>()
</script>

<template>
  <div class="db-clone-success-alert">
    <CmkAlertBox variant="success">
      <template #heading>{{ _t('Dashboard cloned.') }}</template>
      <a v-if="props?.hasFilters" href="#" @click.prevent="emits('editFilters')">{{
        _t('Review applied filters.')
      }}</a>
    </CmkAlertBox>
  </div>
</template>

<style scoped>
.db-clone-success-alert {
  padding-left: var(--dimension-4);
  padding-right: var(--dimension-4);
}
</style>
