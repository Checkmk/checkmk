/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export function buildRedirectUri(redirectUrl: string): string {
  const baseUri = (
    location.origin +
    location.pathname.replace('wato.py', '') +
    redirectUrl
  ).replace('index.py', 'wato.py')

  const url = new URL(baseUri)
  url.searchParams.delete('connector_type')
  url.searchParams.delete('clone')
  url.searchParams.delete('ident')
  url.searchParams.delete('entity_type_specifier')
  return url.toString()
}
