#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

import datetime

import pytest

from cmk.werks.meisterwerk import (
    evaluate_werk,
    rewrite_werk,
    user_understanding_of_werk,
)
from cmk.werks.schemas.requests import Werk as WerkRequest
from cmk.werks.schemas.responses import (
    EvaluationResponse,
    RewritingResponse,
    UserUnderstandingResponse,
)


@pytest.mark.vcr
def test_evaluate_werk_simple_feature() -> None:
    """Test evaluation of a simple feature werk using real API call."""
    werk_request = WerkRequest(
        title="Simple Feature Implementation",
        date=datetime.datetime.fromisoformat("2024-01-15T10:30:00Z"),
        level=2,
        version="1.0.0",
        werk_class="feature",
        component="core",
        compatible=True,
        werk_text="Added new feature for better user experience. The feature improves workflow efficiency.",
    )

    result = evaluate_werk(werk_request)

    scores = result.evaluation.aggregated_scores
    assert scores.grammar_score in [1, 2, 3]
    assert scores.user_impact_clarity_score in [1, 2, 3]
    assert scores.paragraph_division_score in [1, 2, 3]
    assert scores.english_style_score in [1, 2, 3]


@pytest.mark.vcr
def test_evaluate_werk_breaking_change() -> None:
    """Test evaluation of a breaking change werk using real API call."""
    werk_request = WerkRequest(
        title="Breaking API Change",
        date=datetime.datetime.fromisoformat("2024-06-01T00:00:00Z"),
        level=1,
        version="2.0.0",
        werk_class="breaking",
        component="api",
        compatible=False,
        werk_text="Removed deprecated API endpoints. This change requires user migration. Please update your API calls to use the new endpoints. The old endpoints will return 404 errors after the upgrade.",
    )

    result = evaluate_werk(werk_request)

    assert isinstance(result, EvaluationResponse)
    assert result.evaluation is not None
    scores = result.evaluation.aggregated_scores

    # Breaking change should have non_compatible_werk_score
    assert scores.non_compatible_werk_score is not None
    assert scores.non_compatible_werk_score in [1, 2, 3]

    suggestions = result.evaluation.aggregated_suggestions
    assert suggestions.non_compatible_werk_suggestions_to_improve_text is not None
    assert isinstance(suggestions.non_compatible_werk_suggestions_to_improve_text, str)


@pytest.mark.vcr
def test_evaluate_werk_security_fix() -> None:
    """Test evaluation of a security fix werk using real API call."""
    werk_request = WerkRequest(
        title="Security Fix: Authentication Bypass",
        date=datetime.datetime.fromisoformat("2024-04-15T00:00:00Z"),
        level=1,
        version="1.3.2",
        werk_class="security",
        component="authentication",
        compatible=True,
        werk_text="Fixed critical security vulnerability in authentication system. Users should update immediately. No configuration changes required. The vulnerability allowed unauthorized access under specific conditions.",
    )

    result = evaluate_werk(werk_request)

    assert isinstance(result, EvaluationResponse)
    assert result.evaluation is not None
    assert result.evaluation.aggregated_scores is not None


@pytest.mark.vcr
def test_evaluate_werk_with_poor_grammar() -> None:
    """Test evaluation of werk with intentionally poor grammar using real API call."""
    werk_request = WerkRequest(
        title="Feature with bad grammer",
        date=datetime.datetime.fromisoformat("2024-02-01T00:00:00Z"),
        level=2,
        version="1.1.0",
        werk_class="feature",
        component="ui",
        compatible=True,
        werk_text="This feature are implemented for users. It have many benefit and provide good experience. User can now do thing they couldn't did before. The feature work very good.",
    )

    result = evaluate_werk(werk_request)

    assert isinstance(result, EvaluationResponse)
    scores = result.evaluation.aggregated_scores
    suggestions = result.evaluation.aggregated_suggestions

    assert scores.grammar_score in [1, 2, 3]
    assert len(suggestions.grammar_suggestions_to_improve_text) > 0


@pytest.mark.vcr
def test_user_understanding_simple_feature() -> None:
    """Test user understanding generation for simple feature using real API call."""
    werk_request = WerkRequest(
        title="Dashboard Enhancement",
        date=datetime.datetime.fromisoformat("2024-04-15T00:00:00Z"),
        level=2,
        version="1.3.0",
        werk_class="feature",
        component="dashboard",
        compatible=True,
        werk_text="Enhanced dashboard with new visualization options. Users can now create custom charts and export data in multiple formats. The enhancement improves data analysis capabilities.",
    )

    result = user_understanding_of_werk(werk_request)

    assert isinstance(result, UserUnderstandingResponse)
    assert result.user_understanding is not None
    assert isinstance(result.user_understanding, str)
    assert len(result.user_understanding) > 20


@pytest.mark.vcr
def test_user_understanding_breaking_change() -> None:
    """Test user understanding for breaking change using real API call."""
    werk_request = WerkRequest(
        title="Database Schema Migration",
        date=datetime.datetime.fromisoformat("2024-05-15T00:00:00Z"),
        level=1,
        version="3.0.0",
        werk_class="breaking",
        component="database",
        compatible=False,
        werk_text="Changed database schema for improved performance. This requires manual migration. Please backup your database before upgrading and run the migration script. The process may take several hours for large databases.",
    )

    result = user_understanding_of_werk(werk_request)

    assert isinstance(result, UserUnderstandingResponse)
    assert result.user_understanding is not None
    assert isinstance(result.user_understanding, str)
    assert len(result.user_understanding) > 20


@pytest.mark.vcr
def test_user_understanding_complex_technical_werk() -> None:
    """Test user understanding for complex technical werk using real API call."""
    werk_request = WerkRequest(
        title="Advanced Monitoring System with Machine Learning",
        date=datetime.datetime.fromisoformat("2024-06-01T00:00:00Z"),
        level=3,
        version="2.5.0",
        werk_class="feature",
        component="monitoring",
        compatible=True,
        werk_text="Implemented advanced monitoring system with machine learning algorithms for anomaly detection. The system uses neural networks to analyze patterns and predict potential issues. It integrates with existing monitoring infrastructure and provides real-time alerts. Configuration options include sensitivity thresholds, notification channels, and data retention policies. The system requires additional memory and CPU resources for optimal performance.",
    )

    result = user_understanding_of_werk(werk_request)

    assert isinstance(result, UserUnderstandingResponse)
    assert result.user_understanding is not None
    assert isinstance(result.user_understanding, str)
    assert len(result.user_understanding) > 50


@pytest.mark.vcr
def test_rewrite_werk_simple_case() -> None:
    """Test werk rewriting for simple case using real API call."""
    werk_request = WerkRequest(
        title="Bug Fix in Parser",
        date=datetime.datetime.fromisoformat("2024-02-01T00:00:00Z"),
        level=2,
        version="1.1.0",
        werk_class="fix",
        component="parser",
        compatible=True,
        werk_text="Fixed bug in parser that caused issues. The parser now work better and handle edge cases. User should see improved performance.",
    )

    # First get evaluation
    evaluation_result = evaluate_werk(werk_request)

    # Then rewrite based on evaluation
    result = rewrite_werk(werk_request, evaluation_result)

    assert isinstance(result, RewritingResponse)
    assert result.rewritten_text is not None
    assert isinstance(result.rewritten_text, str)
    assert len(result.rewritten_text) > 20


@pytest.mark.vcr
def test_rewrite_werk_breaking_change() -> None:
    """Test rewriting breaking change werk using real API call."""
    werk_request = WerkRequest(
        title="Configuration File Format Change",
        date=datetime.datetime.fromisoformat("2024-05-15T00:00:00Z"),
        level=1,
        version="2.0.0",
        werk_class="breaking",
        component="configuration",
        compatible=False,
        werk_text="Changed configuration file format from INI to YAML for better structure. Users need to migrate their configuration files. Old format will not work after upgrade.",
    )

    # First get evaluation
    evaluation_result = evaluate_werk(werk_request)

    # Then rewrite based on evaluation
    result = rewrite_werk(werk_request, evaluation_result)

    assert isinstance(result, RewritingResponse)
    assert result.rewritten_text is not None
    assert isinstance(result.rewritten_text, str)
    assert len(result.rewritten_text) > 20


@pytest.mark.vcr
def test_rewrite_werk_with_technical_details() -> None:
    """Test rewriting werk with complex technical details using real API call."""
    werk_request = WerkRequest(
        title="Performance Optimization in Data Processing Pipeline",
        date=datetime.datetime.fromisoformat("2024-03-01T00:00:00Z"),
        level=3,
        version="1.4.0",
        werk_class="feature",
        component="processing",
        compatible=True,
        werk_text="Optimized data processing pipeline using advanced algorithms and caching mechanisms. The implementation uses thread pooling, memory mapping, and vectorized operations. Performance improvements range from 200% to 500% depending on data size. Memory usage reduced by 30%. Configuration parameters include thread count, cache size, and batch processing thresholds.",
    )

    # First get evaluation
    evaluation_result = evaluate_werk(werk_request)

    # Then rewrite based on evaluation
    result = rewrite_werk(werk_request, evaluation_result)

    assert isinstance(result, RewritingResponse)
    assert result.rewritten_text is not None
    assert isinstance(result.rewritten_text, str)
    assert len(result.rewritten_text) > 50


@pytest.mark.vcr
def test_evaluate_werk_unicode_content() -> None:
    """Test evaluation with unicode content using real API call."""
    werk_request = WerkRequest(
        title="Unicode Support: émojis 🚀 and spëcial chars",
        date=datetime.datetime.fromisoformat("2024-12-01T15:45:30Z"),
        level=2,
        version="2.4.0",
        werk_class="feature",
        component="internationalization",
        compatible=True,
        werk_text="Added support for unicode characters including émojis 🚀, accented chars like café, "
        "and symbols like ©️™️. The feature enables proper display and processing of international content. "
        "Users can now input text in multiple languages without encoding issues.",
    )

    result = evaluate_werk(werk_request)

    assert isinstance(result, EvaluationResponse)
    assert result.evaluation is not None


@pytest.mark.vcr
def test_end_to_end_workflow() -> None:
    """Test complete workflow: evaluate -> rewrite using real API calls."""
    werk_request = WerkRequest(
        title="Feature that need improvement",
        date=datetime.datetime.fromisoformat("2024-01-01T00:00:00Z"),
        level=2,
        version="1.0.0",
        werk_class="feature",
        component="core",
        compatible=True,
        werk_text="This feature was implemented for users. It have some benefits and provide experience. "
        "The feature work good but could be describe better for user understanding.",
    )

    # Step 1: Evaluate the werk
    evaluation_result = evaluate_werk(werk_request)
    assert isinstance(evaluation_result, EvaluationResponse)

    # Step 2: Get user understanding
    understanding_result = user_understanding_of_werk(werk_request)
    assert isinstance(understanding_result, UserUnderstandingResponse)

    # Step 3: Rewrite based on evaluation
    rewrite_result = rewrite_werk(werk_request, evaluation_result)
    assert isinstance(rewrite_result, RewritingResponse)

    # Verify all steps completed successfully
    assert evaluation_result.evaluation is not None
    assert len(understanding_result.user_understanding) > 0
    assert len(rewrite_result.rewritten_text) > 0
