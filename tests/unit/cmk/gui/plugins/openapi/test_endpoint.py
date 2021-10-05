def test_openapi_accept_header_missing(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    resp = wsgi_app.call_method(
        'get',
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        status=200,
    )
    assert resp.json['value'] == []


def test_openapi_accept_header_matches(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    resp = wsgi_app.call_method(
        'get',
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        {},  # params
        {'Accept': 'application/json'},  # headers
        status=200,
    )
    assert resp.json['value'] == []


def test_openapi_accept_header_invalid(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    resp = wsgi_app.call_method(
        'get',
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        {},  # params
        {'Accept': 'asd-asd-asd'},  # headers
        status=406,
    )
    assert resp.json == {
        'detail': 'Can not send a response with the content type specified in the '
                  "'Accept' Header. Accept Header: asd-asd-asd. Supported content "
                  'types: [application/json]',
        'status': 406,
        'title': 'Not Acceptable',
    }
