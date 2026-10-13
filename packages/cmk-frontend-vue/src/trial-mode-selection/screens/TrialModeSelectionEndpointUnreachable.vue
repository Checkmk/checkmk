<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import TrialModeSelectionDialogFooter from '../components/TrialModeSelectionDialogFooter.vue'
import TrialModeSelectionScreenHeading from '../components/TrialModeSelectionScreenHeading.vue'

const { domain, saving } = defineProps<{
  /** Domain the site must reach to verify a trial. */
  domain: string
  saving: boolean
}>()

const emit = defineEmits<{
  back: []
  retry: []
  continueOffline: []
}>()

const { _t } = usei18n()
</script>

<template>
  <div class="trial-mode-selection-endpoint-unreachable">
    <TrialModeSelectionScreenHeading>
      <CmkBadge
        class="trial-mode-selection-endpoint-unreachable__badge"
        color="warning"
        type="outline"
      >
        {{ _t('Connection blocked') }}
      </CmkBadge>
      {{ _t("This site can't reach %{domain}", { domain }) }}
    </TrialModeSelectionScreenHeading>
    <CmkParagraph class="trial-mode-selection-endpoint-unreachable__dimmed">
      {{
        _t(
          'Email verification needs an outbound HTTPS connection to that domain. A firewall or proxy rule is the most common cause — if this site has no internet access at all, continue as an offline trial instead.'
        )
      }}
    </CmkParagraph>

    <div class="trial-mode-selection-endpoint-unreachable__allowlist">
      <CmkParagraph class="trial-mode-selection-endpoint-unreachable__allowlist-title">
        {{ _t('Allow outbound access to') }}
      </CmkParagraph>
      <CmkParagraph>
        <code class="trial-mode-selection-endpoint-unreachable__domain">{{ domain }}</code>
        <span class="trial-mode-selection-endpoint-unreachable__dimmed">
          · {{ _t('TCP 443 (HTTPS)') }}
        </span>
      </CmkParagraph>
      <CmkParagraph class="trial-mode-selection-endpoint-unreachable__dimmed">
        {{
          _t(
            'Add the domain to your firewall or proxy allowlist, then retry. The same endpoint is used for product analytics, so allowlisting it once covers both.'
          )
        }}
      </CmkParagraph>
    </div>

    <TrialModeSelectionDialogFooter :back-disabled="saving" @back="emit('back')">
      <CmkButton variant="secondary" :running="saving" @click="emit('continueOffline')">
        {{ _t('Continue as offline trial') }}
      </CmkButton>
      <CmkButton variant="success" :disabled="saving" @click="emit('retry')">
        {{ _t('Retry') }}
      </CmkButton>
    </TrialModeSelectionDialogFooter>
  </div>
</template>

<style scoped>
.trial-mode-selection-endpoint-unreachable__badge {
  width: fit-content;
  margin: 0 0 var(--dimension-5);
}

.trial-mode-selection-endpoint-unreachable__dimmed {
  color: var(--font-color-dimmed);
}

.trial-mode-selection-endpoint-unreachable__allowlist {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-6);
  padding: var(--dimension-6);
  border: 1px solid var(--ux-theme-6);
  border-radius: var(--border-radius);
}

.trial-mode-selection-endpoint-unreachable__allowlist-title {
  color: var(--font-color-dimmed);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
}

.trial-mode-selection-endpoint-unreachable__domain {
  color: var(--success);
  font-family: monospace;
}
</style>
