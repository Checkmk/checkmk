import pytest
from pydantic import BaseModel, ValidationError

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD


class DummyModel(BaseModel):
    field: int | None | Omitted = OMITTED_FIELD


def test_omitted_valid_type_works():
    model = DummyModel.model_validate({"field": 123})
    assert model.field == 123


def test_omitted_none_stays_none():
    model = DummyModel.model_validate({"field": None})
    assert model.field is None


def test_omitted_omitted_stays_omitted():
    model = DummyModel.model_validate({"field": Omitted()})
    assert isinstance(model.field, Omitted)


def test_omitted_invalid_type_raises():
    with pytest.raises(ValidationError):
        DummyModel.model_validate({"field": "string"})
