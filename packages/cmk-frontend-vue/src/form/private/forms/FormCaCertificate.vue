<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkInlineButton from 'cmk-ui-library/components/user-input/CmkInlineButton.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { AjaxResponseError, cmkAjax } from 'cmk-ui-library/lib/ajax'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { ref, shallowRef } from 'vue'

import { type ValidationMessages } from '@/form/private/validation'

import FormMultilineText from './FormMultilineText.vue'

// eslint-disable-next-line @typescript-eslint/naming-convention
declare let global_csrf_token: string

interface FetchedCertificate {
  details: {
    issued_to: string
    issued_by: string
    valid_from: string
    valid_till: string
    digest_sha256: string
  }
  cert_pem: string
}

class Idle {}

class Fetching {}

class FetchFailed {
  constructor(public readonly message: string) {}
}

class Fetched {
  constructor(public readonly certificate: FetchedCertificate) {}
}

type FetchState = Idle | Fetching | FetchFailed | Fetched

const { _t } = usei18n()

defineProps<{
  spec: FormSpec.CaCertificate
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })

const hostId = useId()
const portId = useId()

const fileInput = ref<HTMLInputElement | null>(null)

const slideInOpen = ref(false)
const host = ref('')
const port = ref('443')
const fetchState = shallowRef<FetchState>(new Idle())

const onFileSelected = async (event: Event): Promise<void> => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    data.value = await file.text()
  }
  // allow selecting the same file again
  input.value = ''
}

const closeSlideIn = (): void => {
  fetchState.value = new Idle()
  slideInOpen.value = false
}

const fetchFromServer = async (): Promise<void> => {
  fetchState.value = new Fetching()
  // The endpoint reads its parameters as request variables, so they go into the query string.
  const params = new URLSearchParams({
    address: host.value,
    port: port.value,
    _csrf_token: global_csrf_token
  })
  try {
    fetchState.value = new Fetched(
      await cmkAjax<FetchedCertificate>(`ajax_fetch_ca.py?${params.toString()}`, {})
    )
  } catch (e: unknown) {
    fetchState.value = new FetchFailed(
      e instanceof AjaxResponseError ? String(e.response.result) : String(e)
    )
  }
}

const useCertificate = (): void => {
  if (!(fetchState.value instanceof Fetched)) {
    return
  }
  data.value = fetchState.value.certificate.cert_pem
  closeSlideIn()
}
</script>

<template>
  <div class="form-ca-certificate__stack">
    <FormMultilineText
      v-model:data="data"
      :backend-validation="backendValidation"
      :spec="{ ...spec, type: 'multiline_text', monospaced: true, macro_support: false }"
    />
    <div class="form-ca-certificate__row">
      <CmkInlineButton icon="upload" @click="fileInput?.click()">
        {{ _t('Upload file') }}
      </CmkInlineButton>
      <CmkInlineButton v-if="spec.allow_fetch" icon="host" @click="slideInOpen = true">
        {{ _t('Fetch from server') }}
      </CmkInlineButton>
      <input ref="fileInput" hidden type="file" accept=".pem,.crt" @change="onFileSelected" />
    </div>
  </div>
  <CmkSlideInDialog
    :open="slideInOpen"
    size="small"
    :header="{ title: _t('Fetch certificate from server'), closeButton: true }"
    @close="closeSlideIn"
  >
    <div class="form-ca-certificate__stack">
      <div class="form-ca-certificate__row">
        <CmkButton
          variant="secondary"
          :icon="{ name: 'save' }"
          :disabled="!(fetchState instanceof Fetched)"
          :title="fetchState instanceof Fetched ? '' : _t('Fetch a certificate first')"
          @click="useCertificate"
        >
          {{ _t('Use this certificate') }}
        </CmkButton>
        <CmkButton :icon="{ name: 'cancel' }" @click="closeSlideIn">
          {{ _t('Cancel') }}
        </CmkButton>
      </div>
      <div class="form-ca-certificate__row">
        <div class="form-ca-certificate__stack form-ca-certificate__stack--grow">
          <CmkLabel :for="hostId">{{ _t('Host') }}</CmkLabel>
          <CmkInput
            :id="hostId"
            v-model="host"
            type="text"
            field-size="fill"
            @keydown.enter.prevent="fetchFromServer"
          />
        </div>
        <div class="form-ca-certificate__stack">
          <CmkLabel :for="portId">{{ _t('Port') }}</CmkLabel>
          <CmkInput
            :id="portId"
            v-model="port"
            type="text"
            field-size="small"
            @keydown.enter.prevent="fetchFromServer"
          />
        </div>
        <CmkButton
          variant="secondary"
          :running="fetchState instanceof Fetching"
          @click="fetchFromServer"
        >
          {{ _t('Fetch') }}
        </CmkButton>
      </div>
      <CmkAlertBox v-if="fetchState instanceof FetchFailed" variant="error">
        {{ fetchState.message }}
      </CmkAlertBox>
      <CmkHeading type="h4">{{ _t('Certificate') }}</CmkHeading>
      <template v-if="fetchState instanceof Fetched">
        <dl class="form-ca-certificate__details">
          <dt>{{ _t('Issued to') }}</dt>
          <dd>{{ fetchState.certificate.details.issued_to }}</dd>
          <dt>{{ _t('Issued by') }}</dt>
          <dd>{{ fetchState.certificate.details.issued_by }}</dd>
          <dt>{{ _t('Valid from') }}</dt>
          <dd>{{ fetchState.certificate.details.valid_from }}</dd>
          <dt>{{ _t('Valid until') }}</dt>
          <dd>{{ fetchState.certificate.details.valid_till }}</dd>
          <dt>{{ _t('Fingerprint') }}</dt>
          <dd>{{ fetchState.certificate.details.digest_sha256 }}</dd>
        </dl>
        <CmkCode :code-text="fetchState.certificate.cert_pem" width="fill" />
      </template>
      <CmkParagraph v-else class="form-ca-certificate__placeholder">
        {{ _t('No certificate fetched yet.') }}
      </CmkParagraph>
    </div>
  </CmkSlideInDialog>
</template>

<style scoped>
.form-ca-certificate__stack {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.form-ca-certificate__stack--grow {
  flex: 1;
}

.form-ca-certificate__row {
  display: flex;
  align-items: flex-end;
  gap: var(--dimension-4);
}

.form-ca-certificate__placeholder {
  font-style: italic;
}

.form-ca-certificate__details {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--dimension-4);
  margin: 0;
  overflow-wrap: anywhere;

  dt {
    font-weight: var(--font-weight-bold);
  }

  dd {
    margin: 0;
  }
}
</style>
