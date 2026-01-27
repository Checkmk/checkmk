<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { Oauth2Urls } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import { ref } from 'vue'
import { inject } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import { randomId } from '@/lib/randomId'
import { immediateWatch } from '@/lib/watch.ts'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import { getWizardContext } from '@/components/CmkWizard/utils.ts'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import { type OAuth2FormData, type Oauth2ConnectionApi } from '../lib/service/oauth2-connection-api'
import { submitKey } from '../lib/submitKey'
import { waitForRedirect } from '../lib/waitForRedirect'
import { buildRedirectUri } from './utils'

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

const submitted = inject(submitKey)

const TIMEOUT = 5 * 60000

const context = getWizardContext()

const loading = ref(true)
const saving = ref(false)
const loadingTitle = ref(_t('Verifying the authorization...'))
const errorTitle = ref(_t('Authorization failed.'))
const authSucceeded = ref(false)
const refId = randomId()
const countDownValue = ref<number>(TIMEOUT)

const dataRef = defineModel<OAuth2FormData>({ required: true })
const resultCode = ref<string | null>(null)

async function authorize(): Promise<string | null> {
  return new Promise((resolve) => {
    const authorityKey = dataRef.value.authority as keyof typeof props.authorityMapping
    const mappingValue = props.authorityMapping[authorityKey] ?? 'global_'
    const baseUrl =
      props.urls[props.connectorType][
        mappingValue as keyof (typeof props.urls)[typeof props.connectorType]
      ].base_url
    if (baseUrl) {
      const url = new URL(
        `${baseUrl.replace('###tenant_id###', dataRef.value.tenant_id as string)}/authorize`
      )

      url.searchParams.append('client_id', dataRef.value.client_id as string)
      url.searchParams.append('redirect_uri', buildRedirectUri(props.urls.redirect))
      url.searchParams.append('response_type', 'code')
      url.searchParams.append('response_mode', 'query')
      url.searchParams.append('scope', '.default')
      url.searchParams.append('state', refId)
      url.searchParams.append('prompt', 'select_account')

      const authWindow = open(url, '_blank')
      if (authWindow) {
        waitForRedirect<string | null>(
          authWindow,
          {
            host: location.host
          },
          resolve,
          verifyAuthorization,
          TIMEOUT
        )
      }
    }
  })
}

function verifyAuthorization(
  authWindow: WindowProxy,
  resolve: (value: string | null | PromiseLike<string | null>) => void,
  error?: string
) {
  if (error) {
    loading.value = false
    errorTitle.value = error as TranslatedString
    authWindow.close()
    return
  }

  const params = new URL(authWindow.location.href).searchParams

  if (params.get('state') === refId) {
    const code = params.get('code')
    if (code) {
      resolve(code)
    } else {
      loading.value = false
      resolve(null)
    }
  } else {
    loading.value = false
    resolve(null)
  }

  authWindow.close()
}

async function requestAccessToken(): Promise<boolean> {
  loadingTitle.value = _t('Requesting access token')
  try {
    if (props.connectorType === 'microsoft_entra_id' && resultCode.value) {
      const res = await props.api.requestAccessToken({
        type: 'ms_graph_api',
        id: props.ident,
        redirect_uri: buildRedirectUri(props.urls.redirect),
        data: dataRef.value,
        code: resultCode.value
      })
      if (res.status !== 'success') {
        errorTitle.value = _t(`${res.message}`)
        return false
      }
      if (res.data) {
        dataRef.value.access_token = res.data.access_token
        dataRef.value.refresh_token = res.data.refresh_token
      }
      return true
    }
  } catch (e) {
    errorTitle.value = _t(`Failed to request and save access token: ${e}`)
  }
  return false
}

function resetProcess() {
  loading.value = false
  saving.value = false
  countDownValue.value = TIMEOUT
}

async function saveConnection() {
  if (submitted !== undefined) {
    saving.value = true
    const error = await submitted(dataRef.value)
    if (error) {
      errorTitle.value = error
    }
    saving.value = false
  }
}

function countDown() {
  if (countDownValue.value > 0 && loading.value) {
    countDownValue.value -= 1000
    setTimeout(countDown, 1000)
  }
}

immediateWatch(
  () => context.isSelected(props.index),
  async (isSelected) => {
    if (isSelected) {
      authSucceeded.value = false
      loading.value = true
      try {
        countDown()
        const code = await authorize()

        if (code) {
          resultCode.value = code
          authSucceeded.value = await requestAccessToken()
          loading.value = false
        } else {
          loading.value = false
          errorTitle.value = _t('Authorization was not completed. Please try again.')
        }
      } catch (e) {
        loading.value = false
        errorTitle.value = (e as Error).message as TranslatedString
      }
    }
  }
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Authorize application') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph v-if="loading">
        {{ countDownValue / 1000 }}
        {{ _t('seconds remaining') }}
      </CmkParagraph>
      <span v-if="loading">
        <CmkIcon name="load-graph" />
        {{ loadingTitle }}
      </span>

      <template v-else-if="authSucceeded">
        <CmkAlertBox variant="success">
          {{ _t('OAuth2 connection parameters requested successfully!') }}
        </CmkAlertBox>
      </template>
      <CmkAlertBox v-else variant="error">
        {{ errorTitle }}
      </CmkAlertBox>

      <span v-if="saving">
        <CmkIcon name="load-graph" />
        {{ _t('Saving OAuth2 connection') }}
      </span>
    </template>

    <template #actions>
      <CmkWizardButton
        v-if="submitted"
        type="finish"
        :override-label="_t('Save')"
        :disabled="!authSucceeded"
        @click="saveConnection"
      />
      <CmkWizardButton
        type="previous"
        :override-label="_t('Go back to restart authorization process')"
        @click="resetProcess"
      />
    </template>
  </CmkWizardStep>
</template>
