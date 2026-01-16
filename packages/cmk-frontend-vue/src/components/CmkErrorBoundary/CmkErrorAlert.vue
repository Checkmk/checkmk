<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import { formatError } from '@/lib/error.ts'
import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
import CmkHtml from '@/components/CmkHtml.vue'
import CmkIndent from '@/components/CmkIndent.vue'

const { _t } = usei18n()

const showDetails = ref<boolean>(false)

const props = defineProps<{ error: Error }>()

const detailMessage = computed<string>(() => {
  return formatError(props.error)
})
</script>

<template>
  <CmkAlertBox variant="error">
    <p>{{ _t('An unexpected error occurred') }}:</p>
    <CmkIndent>
      <CmkHtml :html="props.error.message" />
    </CmkIndent>
    <p>
      {{
        _t(
          'Refresh the page to try again. If the problem persists, reach out to the Checkmk support.'
        )
      }}
    </p>
    <CmkCollapsibleTitle
      :title="_t('Details')"
      :open="showDetails"
      @toggle-open="() => (showDetails = !showDetails)"
    />
    <CmkCollapsible :open="showDetails">
      <CmkIndent>
        <pre>{{ detailMessage }}</pre>
      </CmkIndent>
    </CmkCollapsible>
  </CmkAlertBox>
</template>

<style scoped>
pre {
  white-space: pre-wrap;
  padding: 0;
  margin: 0;
  line-height: 1.4;
}
</style>
