<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { Oauth2Urls } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import { randomId } from '@/lib/randomId.ts'

import CmkButton from '@/components/CmkButton.vue'
import CmkCopy from '@/components/CmkCopy.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkLabel from '@/components/CmkLabel.vue'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import type { ValidationMessages } from '@/form'

import type {
  OAuth2FormData,
  Oauth2ConnectionApi
} from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'
import { buildAuthorizationUrl } from '@/mode-oauth2-connection/steps/utils.ts'

const { _t } = usei18n()

const props = defineProps<
  CmkWizardStepProps & {
    urls: Oauth2Urls
    authorityMapping: Record<string, string>
    connectorType: 'microsoft_entra_id'
    ident: string
    api: Oauth2ConnectionApi
  }
>()

const canProceed = computed(() => {
  if (!model.value.data.override_site) {
    return true
  }
  return model.value.overrideCode.trim().length > 0
})

async function validateCanProceed(): Promise<boolean> {
  return canProceed.value
}
const refId = randomId()

const model = defineModel<{
  data: OAuth2FormData
  validation: ValidationMessages
  overrideCode: string
}>({
  required: true
})

const authorizationUrl = computed(() =>
  buildAuthorizationUrl(
    props.urls,
    props.connectorType,
    props.authorityMapping,
    model.value.data,
    refId
  )
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Authorize the connection') }}</CmkHeading>
    </template>

    <template #content>
      <template v-if="!model.data.override_site">
        {{
          _t(
            'A new tab will be opened and you will need to log in to Microsoft Azure to authorize the application. The process has to be completed within 5 minutes.'
          )
        }}
      </template>
      <template v-else>
        <p>
          {{
            _t(
              'Since you have configured a distributed site for the redirect, the authorization process cannot be started automatically. Open the following URL in your browser to start the authorization:'
            )
          }}
        </p>
        <CmkCopy :text="authorizationUrl">
          <CmkButton>
            <CmkIcon name="copied" variant="inline" size="medium" />
            {{ _t('Copy authorization URL to clipboard') }}
          </CmkButton>
        </CmkCopy>
        <div class="mode-oauth2-connection-authorize-connection">
          <CmkLabel>{{ _t('Authorization code') }}</CmkLabel>
          <CmkInput
            v-model="model.overrideCode"
            field-size="FILL"
            :placeholder="_t('Paste the code from the redirect page here')"
          />
        </div>
      </template>
    </template>

    <template #actions>
      <CmkWizardButton
        type="next"
        :override-label="_t('Start authorization')"
        :validation-cb="validateCanProceed"
      />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-oauth2-connection-authorize-connection {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  margin-top: var(--spacing);
}
</style>
