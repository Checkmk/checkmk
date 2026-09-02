/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Turning a rejected command into something the operator can act on.
 *
 * Checkmk's own message is usually the right one to show. The exception is a
 * bulk command on a group that only exists implicitly, through livestatus
 * group membership: the REST API rejects it by naming the offending field,
 * which reads like a bug in Maps rather than like a configuration gap.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { TranslateFn } from '@/maps/utils/dropdownOptions'

/** How Checkmk rejects a group it does not have a Setup entry for. */
const IMPLICIT_GROUP_REJECTION = /hostgroup_name|servicegroup_name|Group missing|not monitored/i

export function messageOf(caught: unknown, fallback: TranslatedString): TranslatedString {
  // What Checkmk said is shown as it came: it is the site's own message, in the
  // site's own language, and there is nothing to translate it against.
  if (caught instanceof Error) {
    return caught.message ? untranslated(caught.message) : fallback
  }
  return typeof caught === 'string' && caught ? untranslated(caught) : fallback
}

/**
 * The message, plus the reason behind it where the object is a group and the
 * rejection is the implicit-group one.
 */
export function describeGroupCommandError(
  message: TranslatedString,
  isGroup: boolean,
  groupTypeLabel: string,
  _t: TranslateFn
): TranslatedString {
  if (!isGroup || !IMPLICIT_GROUP_REJECTION.test(message)) {
    return message
  }
  return untranslated(
    `${message}\n\n${_t('Tip: Checkmk only accepts bulk actions on %{type}s that are configured in Setup → Host groups (or Service groups). Implicit / livestatus-only groups are rejected by the REST API.', { type: groupTypeLabel })}`
  )
}
