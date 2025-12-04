/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

export interface WebAuthnMessage {
  title: string
  lines: string[]
  type: 'success' | 'error'
}

function urlSafeBase64Decode(base64str: string): string {
  return window.atob(base64str.replace(/_/g, '/').replace(/-/g, '+'))
}

interface JsonEncodedCredential {
  type: string
  id: string
}
const { _t } = usei18n()

function parseCreationOptionsFromJSON(
  credentialcreationoptions: Record<string, unknown>
): CredentialCreationOptions {
  /* The data comes from the server now as JSON, but the browser API likes
   * native types like Uint8Arrays... There is a draft for the 3rd spec to
   * include a function like this wo the API. Once we're there we can remove
   * this...*/
  const options = credentialcreationoptions['publicKey'] as Record<string, unknown>
  const userObj = options['user'] as Record<string, string>
  const authenticatorSelection = options['authenticatorSelection'] as
    | AuthenticatorSelectionCriteria
    | undefined

  const publicKeyOptions: PublicKeyCredentialCreationOptions = {
    challenge: Uint8Array.from(urlSafeBase64Decode(options['challenge'] as string), (c) =>
      c.charCodeAt(0)
    ),
    rp: options['rp'] as PublicKeyCredentialRpEntity,
    user: {
      id: Uint8Array.from(urlSafeBase64Decode(userObj['id']!), (c) => c.charCodeAt(0)),
      name: userObj['name']!,
      displayName: userObj['displayName']!
    },
    pubKeyCredParams: options['pubKeyCredParams'] as PublicKeyCredentialParameters[],
    excludeCredentials: (options['excludeCredentials'] as JsonEncodedCredential[]).map(
      (e: JsonEncodedCredential) => ({
        type: e['type'] as PublicKeyCredentialType,
        id: Uint8Array.from(urlSafeBase64Decode(e['id']), (c) => c.charCodeAt(0))
      })
    )
  }

  if (authenticatorSelection !== undefined) {
    publicKeyOptions.authenticatorSelection = authenticatorSelection
  }

  return { publicKey: publicKeyOptions }
}

function parseRequestOptionsFromJSON(data: Record<string, unknown>): CredentialRequestOptions {
  const options = data['publicKey'] as Record<string, unknown>
  return {
    publicKey: {
      challenge: Uint8Array.from(urlSafeBase64Decode(options['challenge'] as string), (c) =>
        c.charCodeAt(0)
      ),
      allowCredentials: (options['allowCredentials'] as JsonEncodedCredential[]).map(
        (e: JsonEncodedCredential) => ({
          type: e['type'] as PublicKeyCredentialType,
          id: Uint8Array.from(urlSafeBase64Decode(e['id']), (c) => c.charCodeAt(0))
        })
      )
    }
  }
}

export function register(): Promise<WebAuthnMessage> {
  return new Promise((resolve, reject) => {
    fetch('user_webauthn_register_begin.py', {
      method: 'POST'
    })
      .then(function (response) {
        if (response.ok) {
          return response.json()
        }
        throw new Error('Error getting registration data!')
      })
      .then(function (options) {
        if (!('credentials' in navigator)) {
          throw new DOMException(
            'navigator does not have credentials property, probably no https?',
            'SecurityError'
          )
        }
        return navigator.credentials.create(parseCreationOptionsFromJSON(options))
      })
      .then(function (attestation) {
        const attestationPkc = attestation as PublicKeyCredential
        const attestationPkcResponse = attestationPkc.response as AuthenticatorAttestationResponse
        return fetch('user_webauthn_register_complete.py', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            credentialId: btoa(String.fromCharCode(...new Uint8Array(attestationPkc.rawId))),
            attestationObject: btoa(
              String.fromCharCode(...new Uint8Array(attestationPkcResponse.attestationObject))
            ),
            clientDataJSON: btoa(
              String.fromCharCode(...new Uint8Array(attestationPkcResponse.clientDataJSON))
            )
          })
        })
      })
      .then(function (response) {
        if (response.ok) {
          resolve({
            title: _t('Registration successful'),
            lines: [_t('Your authenticator has been registered successfully.')],
            type: 'success'
          })
          // eslint-disable-next-line @typescript-eslint/no-floating-promises
          response.text().then(function (text) {
            if (JSON.parse(text).replicate) {
              if (JSON.parse(text).redirect) {
                window.location.href = 'user_profile_replicate.py?back=index.py'
              } else {
                window.location.href = 'user_profile_replicate.py?back=user_two_factor_overview.py'
              }
              window.location.href = 'user_profile_replicate.py?back=user_two_factor_overview.py'
            } else if (JSON.parse(text).redirect) {
              window.location.href = 'index.py'
            } else {
              window.location.href = 'user_two_factor_overview.py'
            }
          })
        } else {
          // eslint-disable-next-line @typescript-eslint/no-floating-promises
          response.text().then(function (text) {
            reject({
              title: _t('Registration failed'),
              lines: [
                _t(
                  `${text}. A Checkmk administrator may have a look at var/log/web.log to get additional information.`
                )
              ],
              type: 'error'
            })
          })
        }
      })
      .catch(function (e) {
        if (e.name === 'SecurityError') {
          reject({
            title: _t('Security Error'),
            lines: [
              _t(
                'Can not enable two-factor authentication. You have to use HTTPS and access the GUI through a valid domain name (See #13325 for further information).'
              )
            ],
            type: 'error'
          })
        } else if (e.name === 'AbortError') {
          reject({
            title: _t('Registration failed'),
            lines: [
              _t('Possible reasons are:'),
              _t('- You have aborted the registration'),
              _t('- Your browser does not support the WebAuthn standard'),
              _t('- The browser configuration has disabled WebAuthn')
            ],
            type: 'error'
          })
        } else if (e.name === 'InvalidStateError') {
          reject({
            title: _t('Registration failed'),
            lines: [
              _t(
                'The given authenticator is not usable. This may be due to the repeated use of an already registered authenticator.'
              )
            ],
            type: 'error'
          })
        } else {
          reject({
            title: _t('Registration failed'),
            lines: [e.message || _t('An unknown error occurred')],
            type: 'error'
          })
        }
      })
  })
}
export function login(): Promise<WebAuthnMessage> {
  return new Promise((resolve, reject) => {
    fetch('user_webauthn_login_begin.py', {
      method: 'POST'
    })
      .then(function (response) {
        if (response.ok) {
          return response.json()
        }
        throw new Error('No credential available to authenticate!')
      })
      .then(function (options) {
        if (!('credentials' in navigator)) {
          throw new DOMException(
            'navigator does not have credentials property, probably no https?',
            'SecurityError'
          )
        }
        return navigator.credentials.get(parseRequestOptionsFromJSON(options))
      })
      .then(function (assertion) {
        const assertionPkc = assertion as PublicKeyCredential
        const assertionResponse = assertionPkc.response as AuthenticatorAssertionResponse
        return fetch('user_webauthn_login_complete.py', {
          method: 'POST',
          body: JSON.stringify({
            credentialId: btoa(String.fromCharCode(...new Uint8Array(assertionPkc.rawId))),
            authenticatorData: btoa(
              String.fromCharCode(...new Uint8Array(assertionResponse.authenticatorData))
            ),
            clientDataJSON: btoa(
              String.fromCharCode(...new Uint8Array(assertionResponse.clientDataJSON))
            ),
            signature: btoa(String.fromCharCode(...new Uint8Array(assertionResponse.signature)))
          })
        })
      })
      .then(function (response) {
        if (response.ok) {
          resolve({
            title: _t('Login successful'),
            lines: [_t('You have been authenticated successfully.')],
            type: 'success'
          })
          window.location.href = 'index.py'
        } else {
          reject({
            title: _t('Login failed'),
            lines: [_t('Your WebAuthn authentication could not be verified.')],
            type: 'error'
          })
        }
      })
      .catch(function (e) {
        if (e.name === 'SecurityError') {
          reject({
            title: _t('Security Error'),
            lines: [_t('2FA not possible (See #13325 for details)')],
            type: 'error'
          })
        } else {
          reject({
            title: _t('WebAuthn login failed'),
            lines: [e.message || _t('An unknown error occurred')],
            type: 'error'
          })
        }
      })
  })
}
