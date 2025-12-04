/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import TwoFactorAuth from '@/two-factor-auth/TwoFactorAuthApp.vue'

const createComponent = (methods = {}) => {
  return {
    components: { TwoFactorAuth },
    setup() {
      return {
        availableMethods: {
          totp_credentials: false,
          webauthn_credentials: false,
          backup_codes: false,
          ...methods
        }
      }
    },
    template: `
      <TwoFactorAuth :available-methods="availableMethods" />
    `
  }
}
test('TwoFactorAuth component shows header', async () => {
  render(
    createComponent({
      totp_credentials: true,
      webauthn_credentials: true,
      backup_codes: true
    })
  )

  const header = screen.getByText('Two-factor authentication')
  expect(header).toBeInTheDocument()
})

test('TwoFactorAuth component renders with all methods available', async () => {
  render(
    createComponent({
      totp_credentials: true,
      webauthn_credentials: true,
      backup_codes: true
    })
  )

  const otp = await screen.findByText('Use Authenticator app')
  const token = screen.getByText('Use Security token')
  const backup = screen.getByText('Use Backup Codes')

  expect(otp).toBeInTheDocument()
  expect(token).toBeInTheDocument()
  expect(backup).toBeInTheDocument()
})

test('TwoFactorAuth component renders with backup code input', async () => {
  render(
    createComponent({
      backup_codes: true
    })
  )

  const backup = await screen.findByText('Backup code:')
  const submit = screen.getByText('Submit')
  const otp = screen.queryByText('Use authenticator app')
  const token = screen.queryByText('Use security token')

  expect(backup).toBeInTheDocument()
  expect(submit).toBeInTheDocument()
  expect(otp).not.toBeInTheDocument()
  expect(token).not.toBeInTheDocument()
})

test('TwoFactorAuth component renders with otp code input', async () => {
  render(
    createComponent({
      totp_credentials: true
    })
  )

  const otp = await screen.findByText(
    'Enter the six-digit code from your authenticator app to log in.'
  )
  const submit = screen.getByText('Submit')
  const backup = screen.queryByText('Use Backup Codes')
  const token = screen.queryByText('Use security token')

  expect(otp).toBeInTheDocument()
  expect(submit).toBeInTheDocument()
  expect(backup).not.toBeInTheDocument()
  expect(token).not.toBeInTheDocument()
})

test('TwoFactorAuth component renders with webauth enabled', async () => {
  render(
    createComponent({
      webauthn_credentials: true
    })
  )

  const web = await screen.findByText(
    "Please follow your browser's instructions for authentication."
  )
  const submit = screen.queryByText('Submit')
  const backup = screen.queryByText('Use Backup Codes')
  const token = screen.queryByText('Use security token')
  const otp = screen.queryByText('Use Authenticator app')

  expect(web).toBeInTheDocument()
  expect(submit).not.toBeInTheDocument()
  expect(backup).not.toBeInTheDocument()
  expect(token).not.toBeInTheDocument()
  expect(otp).not.toBeInTheDocument()
})

test('TwoFactorAuth component renders with webauth and back up enabled', async () => {
  render(
    createComponent({
      webauthn_credentials: true,
      backup_codes: true
    })
  )

  const multi = await screen.findByText(
    'You have multiple methods enabled. Please select the security method you want to use to log in.'
  )
  const backup = screen.queryByText('Use Backup Codes')
  const token = screen.queryByText('Use Security token')
  const otp = screen.queryByText('Use Authenticator app')

  expect(multi).toBeInTheDocument()
  expect(backup).toBeInTheDocument()
  expect(token).toBeInTheDocument()
  expect(otp).not.toBeInTheDocument()
})

test('TwoFactorAuth component renders with authenticator code and back up enabled', async () => {
  render(
    createComponent({
      totp_credentials: true,
      backup_codes: true
    })
  )

  const multi = await screen.findByText(
    'You have multiple methods enabled. Please select the security method you want to use to log in.'
  )
  const backup = screen.queryByText('Use Backup Codes')
  const token = screen.queryByText('Use Security token')
  const otp = screen.queryByText('Use Authenticator app')

  expect(multi).toBeInTheDocument()
  expect(backup).toBeInTheDocument()
  expect(otp).toBeInTheDocument()
  expect(token).not.toBeInTheDocument()
})

test('TwoFactorAuth component renders with authenticator code and web auth enabled', async () => {
  render(
    createComponent({
      totp_credentials: true,
      webauthn_credentials: true
    })
  )

  const multi = await screen.findByText(
    'You have multiple methods enabled. Please select the security method you want to use to log in.'
  )
  const backup = screen.queryByText('Use Backup Codes')
  const token = screen.queryByText('Use Security token')
  const otp = screen.queryByText('Use Authenticator app')

  expect(multi).toBeInTheDocument()
  expect(token).toBeInTheDocument()
  expect(otp).toBeInTheDocument()
  expect(backup).not.toBeInTheDocument()
})
