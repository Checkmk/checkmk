<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type ProductUsageAnalyticsConfig } from 'cmk-shared-typing/typescript/product_usage_analytics'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkPopupDialog from 'cmk-ui-library/components/CmkPopupDialog.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import { createGlobalSettingsService } from '@/global-settings/api'

const { _t, _tp } = usei18n()

const props = defineProps<ProductUsageAnalyticsConfig>()

const VARNAME = 'product_usage_analytics'

const popupOpen = ref(true)
const state = ref<'asking' | 'saving' | 'failed' | 'enabled'>('asking')

// One msgid per sentence, so translations can move the link.
const shareNoteParts = _tp(
  '%{link} is a link to the product usage analytics manifest with the text "manifest"',
  'We believe in only receiving data you explicitly choose to share (see %{link}).'
).split('%{link}')
const changeNoteParts = _tp(
  '%{link} is a link to the global setting with the text "global settings"',
  'You can change your decision at any time in %{link}.'
).split('%{link}')

/**
 * Ask again after the reminder interval. Without this, the pop-up comes back on the next page load.
 */
function deferDecision(): void {
  const { name, path, max_age_seconds: maxAge } = props.reminder_cookie
  const secure = window.location.protocol === 'https:' ? '; secure' : ''
  document.cookie = `${name}=${Date.now() / 1000}; path=${path}; max-age=${maxAge}${secure}`
  popupOpen.value = false
}

async function enable(): Promise<void> {
  state.value = 'saving'
  // The pop-up is only shown on standalone and central sites.
  const service = createGlobalSettingsService({ type: 'global', managed_by_central_site: false })
  try {
    const current = await service.load(VARNAME)
    // Keep the other parts of the setting, like the proxy, as they are.
    const value = {
      ...(current.value as Record<string, unknown>),
      enabled: props.enabled_choice_id
    }
    const result = await service.save(VARNAME, value, current.etag)
    state.value = result.type === 'saved' ? 'enabled' : 'failed'
  } catch {
    state.value = 'failed'
  }
}

function goToActivateChanges(): void {
  window.location.href = props.activate_changes_link
}
</script>

<template>
  <CmkPopupDialog
    :open="popupOpen"
    :title="_t('Help us improve Checkmk with product usage analytics')"
    :stay-open-overlay-click="true"
    @close="popupOpen = false"
  >
    <div class="product-usage-analytics-app__content">
      <p>
        <b>{{ _t('We want to understand how you use Checkmk.') }}</b>
        {{
          _t(
            'Product usage analytics allows us to make data-driven decisions and focus development on what parts of Checkmk you regularly use. \
            The data you share will help us prioritize the features that matter most to you.'
          )
        }}
      </p>

      <CmkSpace direction="horizontal" size="small" />

      <CmkHeading type="h4">{{ _t('What data are we collecting?') }}</CmkHeading>
      <ul>
        <li>
          <b>{{ _t('We collect: ') }}</b
          >{{
            _t(
              'data about the general usage of features and configuration options (e.g., counts of hosts, folders, plug-ins, MKPs, and services).'
            )
          }}
        </li>
        <li>
          <b>{{ _t('We do NOT collect: ') }}</b
          >{{
            _t(
              'any data about users or their behavior (e.g., PII) or possibly sensitive identifiers about your environment (e.g., hostnames, file paths, service names).'
            )
          }}
        </li>
      </ul>

      <CmkSpace direction="horizontal" size="small" />

      <p>
        <b>{{ _t('Important: ') }}</b>
        {{
          _t(
            'The names of custom check plug-ins (either developed internally or installed as an MKP from the Checkmk Exchange) will be collected as part of the product usage data. \
            If you use MKPs, we recommend you inspect the data carefully via the data download option to verify the content before opting in, to ensure no sensitive data is included. \
            Do not enable product usage analytics if you do not wish to share this information.'
          )
        }}
      </p>

      <CmkSpace direction="horizontal" size="small" />

      <p>
        <b>{{ _t('Product usage analytics is turned off by default. ') }}</b>
        {{ shareNoteParts[0]
        }}<CmkLink :href="props.manifest_link" target="_blank" inline>{{ _t('manifest') }}</CmkLink
        >{{ shareNoteParts[1] }} {{ changeNoteParts[0]
        }}<CmkLink :href="props.global_settings_link" inline @click="deferDecision">{{
          _t('global settings')
        }}</CmkLink
        >{{ changeNoteParts[1] }}
      </p>

      <CmkAlert
        v-if="state === 'enabled'"
        variant="success"
        :heading="_t('Thank you! Product usage analytics is enabled.')"
        :text="_t('Activate the pending changes to start the collection.')"
        :main-button="{ title: _t('Activate changes'), onclick: goToActivateChanges }"
      />
      <CmkAlert
        v-if="state === 'failed'"
        variant="error"
        :text="
          _t(
            'Product usage analytics could not be enabled. Please try again or enable it in global settings.'
          )
        "
      />
    </div>

    <div class="product-usage-analytics-app__buttons">
      <CmkButton v-if="state === 'enabled'" variant="primary" @click="popupOpen = false">{{
        _t('Close')
      }}</CmkButton>
      <template v-else>
        <CmkButton variant="secondary" @click="deferDecision">{{
          _t('Remind me again in 30 days')
        }}</CmkButton>
        <CmkButton
          variant="primary"
          :running="state === 'saving'"
          :disabled="state === 'saving'"
          @click="enable"
          >{{ _t('Enable product usage analytics') }}</CmkButton
        >
      </template>
    </div>
  </CmkPopupDialog>
</template>

<style scoped>
.product-usage-analytics-app__content {
  padding: var(--dimension-4) var(--dimension-11) var(--dimension-10) var(--dimension-11);
}

.product-usage-analytics-app__buttons {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-8);
}
</style>
