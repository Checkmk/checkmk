# encoding: utf-8
# pylint: disable=redefined-outer-name
import collections
import pytest  # type: ignore
from cmk.utils.rulesets.rule_matcher import RuleMatcher, MatchingError

HOST_PROD = {
    "name": "prod-host",
    "tags": {
        "crit": "prod",
        "location": "loft",
    },
    "service_level": 3000,
    "test_attr": "ding",
    "prod_attr": "gaaanz wichtig",
    "multiline_attr": "a\na\na",
    1: 2,
}

HOST_TEST = {
    "name": "test-host",
    "tags": {
        "crit": "test",
        "location": "datacenter",
    },
    "service_level": 10,
    "test_attr": "ding",
    "multiline_attr": "aab\nbbb\nccb",
    u"düng": u"däng",
}

HOSTS = [HOST_PROD, HOST_TEST]

Case = collections.namedtuple("Case", ["condition", "expected_result"])

SIMPLE_MATCHES = [
    Case({}, HOSTS),
    Case({"name": ""}, []),
    Case({"name": "prod-host"}, [HOST_PROD]),
    Case({"name": "ding-host"}, []),
    Case({"name": {
        "$in": ["prod-host", "test-host"]
    }}, [HOST_PROD, HOST_TEST]),
    Case({"name": {
        "$in": []
    }}, []),
    Case({
        "name": "prod-host",
        "tags": {
            "crit": "prod"
        }
    }, []),
    Case({
        "name": "prod-host",
        "tags": {
            "crit": "prod",
            "location": "loft",
        },
    }, [HOST_PROD]),
    Case({
        "name": "prod-host",
        "tags": {
            "crit": "prod",
            "location": "loft"
        }
    }, [HOST_PROD]),
    Case({
        "name": "prod-host",
        "tags": {
            "crit": "prod",
            "location": "garbage"
        }
    }, []),
    Case({u"düng": u"däng"}, [HOST_TEST]),
    Case({1: 2}, [HOST_PROD]),
    Case({"not_existing": "bla"}, []),
]

NESTED_FIELD_MATCHES = [
    Case({"tags.crit": "test"}, [HOST_TEST]),
    Case({"tags.crit": {
        "$eq": "test"
    }}, [HOST_TEST]),
    Case({"tags.crit": {
        "$ne": "test"
    }}, [HOST_PROD]),
    Case({"tags.not_existing": "test"}, []),
    Case({
        "tags.not_existing": {
            "$ne": "test"
        },
        "tags.not_existing2": {
            "$ne": "test"
        },
    }, [HOST_PROD, HOST_TEST]),
]

COMPARISON_MATCHES = [
    Case({"service_level": {
        "$eq": 10
    }}, [HOST_TEST]),
    Case({"service_level": {
        "$eq": 1337
    }}, []),
    Case({"service_level": {
        "$ne": 10
    }}, [HOST_PROD]),
    Case({"service_level": {
        "$ne": 5
    }}, [HOST_PROD, HOST_TEST]),
    Case({"service_level": {
        "$gt": 12
    }}, [HOST_PROD]),
    Case({"service_level": {
        "$gte": 10
    }}, [HOST_PROD, HOST_TEST]),
    Case({"service_level": {
        "$lt": 11
    }}, [HOST_TEST]),
    Case({"service_level": {
        "$lt": 10
    }}, []),
    Case({"service_level": {
        "$lte": 10
    }}, [HOST_TEST]),
    Case({"service_level": {
        "$lte": 9
    }}, []),
    Case({"service_level": {
        "$in": [2, 9]
    }}, []),
    Case({"service_level": {
        "$in": [10]
    }}, [HOST_TEST]),
    Case({"service_level": {
        "$nin": [11, 33]
    }}, [HOST_PROD, HOST_TEST]),
    Case({"service_level": {
        "$nin": [1, 2, 10]
    }}, [HOST_PROD]),
    Case({"service_level": {
        "$in": []
    }}, []),
]

LOGICAL_MATCHES = [
    Case({"$and": [{
        "test_attr": "ding"
    }, {
        "name": "prod-host"
    }]}, [HOST_PROD]),
    Case({"$or": [{
        "name": "prod-host"
    }, {
        "name": "test-host"
    }]}, [HOST_PROD, HOST_TEST]),
    Case({"$nor": [{
        "name": "test-host"
    }, {
        "service_level": 10,
    }]}, [HOST_PROD]),
    Case({"name": {
        "$not": {
            "$eq": "prod-host"
        }
    }}, [HOST_TEST]),
    Case({"name": {
        "$not": {
            "$not": {
                "$eq": "prod-host"
            }
        }
    }}, [HOST_PROD]),
    Case({"name": {
        "$not": {
            "$regex": "^prod"
        }
    }}, [HOST_TEST]),
    Case({
        '$and': [
            {
                '$or': [{
                    'name': {
                        '$regex': '^prod'
                    },
                }, {
                    'name': {
                        '$regex': '^test'
                    },
                }]
            },
            {
                '$or': [{
                    'multiline_attr': {
                        '$regex': '^aa'
                    }
                }, {
                    'multiline_attr': {
                        '$regex': '^xyz'
                    }
                }]
            },
        ]
    }, [HOST_TEST]),
]

EVALUATION_MATCHES = [
    # We only implement the { $regex: 'pattern'[, $options: '<options>'] } syntax
    Case({"name": {
        "$regex": "^PROD",
        "$options": "i",
    }}, [HOST_PROD]),
    Case({"name": {
        "$regex": "^PROD",
    }}, []),
    Case({"multiline_attr": {
        "$regex": "^a$",
        "$options": "m",
    }}, [HOST_PROD]),
    Case({"multiline_attr": {
        "$regex": "^a$",
        "$options": "",
    }}, []),
    Case({"multiline_attr": {
        "$regex": "a$",
    }}, [HOST_PROD]),
    Case({"multiline_attr": {
        "$regex": "b.c",
        "$options": "s",
    }}, [HOST_TEST]),
    Case({"multiline_attr": {
        "$regex": "^a   a\nb$",
        "$options": "mx",
    }}, [HOST_TEST]),
]


@pytest.mark.parametrize(
    "test_case",
    SIMPLE_MATCHES + NESTED_FIELD_MATCHES + COMPARISON_MATCHES + LOGICAL_MATCHES +
    EVALUATION_MATCHES,
)
def test_rule_condition_matcher(test_case):
    matched = [h for h in HOSTS if RuleMatcher().match(h, test_case.condition)]
    assert matched == test_case.expected_result


def test_rule_condition_matcher_invalid_expression():
    with pytest.raises(MatchingError):
        RuleMatcher().match({}, None)


def test_rule_condition_matcher_invalid_document():
    with pytest.raises(MatchingError):
        RuleMatcher().match(None, {})


def test_rule_condition_matcher_unknown_tree_operator():
    with pytest.raises(MatchingError):
        RuleMatcher().match({"a": "b"}, {"$zz": ""})


def test_rule_condition_matcher_unknown_value_operator():
    with pytest.raises(MatchingError):
        RuleMatcher().match({"a": "b"}, {"a": {"$zz": ""}})


def test_rule_condition_matcher_mixed_operator_object():
    with pytest.raises(MatchingError, match="Unknown value operator"):
        RuleMatcher().match({"a": "b"}, {"a": {"$eq": "b", "mix": "up"}})
