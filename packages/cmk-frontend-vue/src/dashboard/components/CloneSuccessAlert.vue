<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

const { _t } = usei18n()

interface CloneSuccessAlertProps {
  hasFilters?: boolean
  clonedAsResponsive?: boolean
}

interface CloneSuccessAlertEmit {
  editFilters: []
}

const props = defineProps<CloneSuccessAlertProps>()
const emits = defineEmits<CloneSuccessAlertEmit>()

const open = defineModel<boolean>('open', { required: true })

const heading = computed(() =>
  props.clonedAsResponsive ? _t('Dashboard cloned as responsive') : _t('Dashboard cloned.')
)

const asksForReview = computed(() => props.hasFilters || props.clonedAsResponsive)

watch(asksForReview, (stillAsksForReview) => {
  if (!stillAsksForReview) {
    open.value = false
  }
})
</script>

<template>
  <div v-if="open" class="db-clone-success-alert">
    <CmkAlertBoxDeprecated
      v-model:open="open"
      variant="success"
      :dismissible="true"
      :auto-dismiss="!asksForReview"
      :heading="heading"
    >
      <div v-if="props.clonedAsResponsive">
        {{ _t('Review the layout and adjust any shifted or resized widgets if needed.') }}
      </div>
      <a v-if="props.hasFilters" href="#" @click.prevent="emits('editFilters')">{{
        _t('Review applied filters.')
      }}</a>
    </CmkAlertBoxDeprecated>
  </div>
</template>

<style scoped>
.db-clone-success-alert {
  padding-left: var(--dimension-4);
  padding-right: var(--dimension-4);
}
</style>
