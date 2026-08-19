<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkCollapsible, { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkHtml from 'cmk-ui-library/components/CmkHtml.vue'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import { formatError } from 'cmk-ui-library/lib/error.ts'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { CrashReportState } from './JavascriptCrashReportApi'

const { _t } = usei18n()

const showDetails = ref<boolean>(false)

const props = defineProps<{ error: Error; crashReport?: CrashReportState | undefined }>()

const detailMessage = computed<string>(() => {
  return formatError(props.error)
})

const crashReportStatus = computed<CrashReportState['status']>(
  () => props.crashReport?.status ?? 'none'
)

const crashReportUrl = computed<string | null>(() =>
  props.crashReport?.status === 'stored' ? props.crashReport.url : null
)
</script>

<template>
  <CmkAlertBox variant="error">
    <div class="cmk-error-alert">
      <div class="cmk-error-alert__paragraph">
        <p>{{ _t('An unexpected error occurred') }}:</p>
        <CmkIndent>
          <CmkHtml :html="props.error.message" class="cmk-error-alert__short" />
        </CmkIndent>
      </div>
      <p>
        {{
          _t(
            'Refresh the page to try again. If the problem persists, reach out to the Checkmk support.'
          )
        }}
      </p>
      <p v-if="crashReportStatus === 'storing'">{{ _t('Storing a crash report…') }}</p>
      <div v-else-if="crashReportUrl !== null" class="cmk-error-alert__paragraph">
        <p>
          {{
            _t(
              'A crash report has been created. You can review it and send it to the Checkmk team:'
            )
          }}
        </p>
        <CmkIndent>
          <CmkLink :href="crashReportUrl">{{ _t('Open crash report') }}</CmkLink>
        </CmkIndent>
      </div>
      <p v-else-if="crashReportStatus === 'failed'">
        {{ _t('No crash report could be stored for this error.') }}
      </p>
      <div class="cmk-error-alert__paragraph">
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
      </div>
    </div>
  </CmkAlertBox>
</template>

<style scoped>
.cmk-error-alert {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}

.cmk-error-alert__paragraph {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

p {
  margin: 0;
}

pre,
.cmk-error-alert__short {
  overflow-wrap: break-word;
  word-break: break-all;
}

pre {
  white-space: pre-wrap;
  padding: 0;
  margin: 0;
  line-height: 1.4;
}
</style>
