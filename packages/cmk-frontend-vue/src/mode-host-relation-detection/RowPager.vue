<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  total: number
  pageSize: number
}>()

const offset = defineModel<number>('offset', { required: true })
</script>

<template>
  <div v-if="props.total > props.pageSize" class="mode-host-relation-detection-row-pager">
    <CmkButton
      variant="optional"
      :disabled="offset === 0"
      @click="offset = Math.max(0, offset - props.pageSize)"
    >
      {{ _t('Previous') }}
    </CmkButton>
    <CmkParagraph>
      {{
        _t('%{first}-%{last} of %{total}', {
          first: offset + 1,
          last: Math.min(offset + props.pageSize, props.total),
          total: props.total
        })
      }}
    </CmkParagraph>
    <CmkButton
      variant="optional"
      :disabled="offset + props.pageSize >= props.total"
      @click="offset = offset + props.pageSize"
    >
      {{ _t('Next') }}
    </CmkButton>
  </div>
</template>

<style scoped>
.mode-host-relation-detection-row-pager {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}
</style>
