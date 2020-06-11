#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pprint import pformat


def dump_environ_app(environ, start_response):
    dumped_env = "\n".join(["{0}: {1}".format(k, environ[k]) for k in environ.keys()])
    return serve_string(dumped_env)(environ, start_response)


def serve_string(_str):
    def _server(environ, start_response):
        status = '200 OK'
        response_headers = [('Content-Type', 'text/plain'), ('Content-Length', str(len(_str)))]
        start_response(status, response_headers)

        return [_str]

    return _server


def test_formdata(environ, start_response):
    # show the environment:
    output = [
        '<pre>',
        pformat(environ),
        '</pre>',
        '<form method="post">',
        '<input type="text" name="test">',
        '<input type="submit">',
        '</form>',
    ]

    if environ['REQUEST_METHOD'] == 'POST':
        # show form data as received by POST:
        output.append('<h1>FORM DATA</h1>')
        output.append(pformat(environ['wsgi.input'].read()))

    # send results
    output_len = sum(len(line) for line in output)
    start_response('200 OK', [('Content-type', 'text/html'), ('Content-Length', str(output_len))])
    return output
