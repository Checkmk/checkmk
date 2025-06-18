<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, computed, type Ref } from 'vue'
import usei18n from '@/lib/i18n'
import { formatError } from '@/lib/error.ts'
import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkHtml from '@/components/CmkHtml.vue'

const { t } = usei18n('cmk-error-boundary')

const showDetails = ref<boolean>(false)

const detailMessage = computed<string>(() => {
  const error = props.error.value
  if (error === null) {
    return ''
  }
  return formatError(error)
})

const props = defineProps<{ error: Ref<Error | null> }>()
</script>

<template>
  <CmkAlertBox v-if="props.error.value !== null" variant="error">
    <p>{{ t('unexpected-error', 'An unexpected error occurred') }}:</p>
    <CmkIndent>
      <CmkHtml :html="props.error.value.message" />
    </CmkIndent>
    <p>
      {{
        t(
          'refresh-page',
          'Refresh the page to try again. If the problem persists, reach out to the Checkmk support.'
        )
      }}
    </p>
    <CmkCollapsibleTitle
      :title="'Details'"
      :open="showDetails"
      @toggle-open="() => (showDetails = !showDetails)"
    />
    <CmkCollapsible :open="showDetails">
      <CmkIndent>
        <pre>{{ detailMessage }}</pre>
      </CmkIndent>
    </CmkCollapsible>
  </CmkAlertBox>
  <template v-else>
    <slot> </slot>
  </template>
</template>

<style scoped>
pre {
  white-space: pre-wrap;
  padding: 0;
  margin: 0;
  line-height: 1.4;
}
</style>
