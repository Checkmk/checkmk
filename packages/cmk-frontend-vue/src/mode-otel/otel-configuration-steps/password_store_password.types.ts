/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface PasswordConfig {
  general_props: {
    id: string
    title: string
    comment: string
    docu_url: string
  }
  password_props: {
    password: string
    owned_by: ['admins', null] | ['contact_group', string]
    share_with: string[]
  }
}
