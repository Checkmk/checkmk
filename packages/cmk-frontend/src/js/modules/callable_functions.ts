/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { confirm_on_form_leave } from '@/modules/forms'
import { insert_before } from '@/modules/layout'
import { render_qr_code } from '@/modules/qrcode_rendering'
import { lock_and_redirect } from '@/modules/sites'
import { render_stats_table } from '@/modules/tracking_display'

import { type CallableFunction, register_callable_functions } from './ts_function_dispatcher'

// See cmk.gui.htmllib.generator:KnownTSFunction
// The type on the Python side and the available keys in this dictionary MUST MATCH.
const callable_functions: { [name: string]: CallableFunction } = {
  render_stats_table: render_stats_table,
  render_qr_code: render_qr_code,
  insert_before: insert_before,
  lock_and_redirect: lock_and_redirect,
  confirm_on_form_leave: confirm_on_form_leave
}

register_callable_functions(callable_functions)
