/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export const MARKETING_EMAIL = 'marketing@checkmk.com'

/**
 * Targets for the consent links on the email step.
 */
export const LEGAL_LINKS = {
  terms: 'https://checkmk.com/legal/terms-and-conditions',
  eula: 'https://checkmk.com/eula',
  privacy: 'https://checkmk.com/privacy-policy',
  checkmk_group: 'https://checkmk.com/contact',
  marketing_email: `mailto:${MARKETING_EMAIL}`
} as const
