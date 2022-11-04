import uuid

import pytest

# from bofire.domain.desirability_functions import (
#    CloseToTargetDesirabilityFunction,
#    ConstantDesirabilityFunction,
#    DeltaIdentityDesirabilityFunction,
#    DesirabilityFunction,
#    IdentityDesirabilityFunction,
#    MaxIdentityDesirabilityFunction,
#    MaxSigmoidDesirabilityFunction,
#    MinIdentityDesirabilityFunction,
#    MinSigmoidDesirabilityFunction,
#    TargetDesirabilityFunction,
# )
from bofire.domain.features import (
    CloseToTargetOutputFeature,
    ConstantOutputFeature,
    DeltaIdentityOutputFeature,
    Feature,
    MaxIdentityOutputFeature,
    MaxSigmoidOutputFeature,
    MinIdentityOutputFeature,
    MinSigmoidOutputFeature,
    TargetOutputFeature,
)
from pydantic.error_wrappers import ValidationError
from tests.bofire.domain.utils import INVALID_SPECS, get_invalids

VALID_CONSTANT_OUTPUT_FEATURE_SPEC = {
    "key": str(uuid.uuid4()),
    "w": 100.0,
}

INVALID_CONSTANT_OUTPUT_FEATURE_SPEC = {
    "key": str(uuid.uuid4()),
    "w": "s",
}

VALID_IDENTITY_OUTPUT_FEATURE_SPEC = {"key": str(uuid.uuid4()), "w": 0.5}

VALID_DELTA_IDENTITY_OUTPUT_FEATURE_SPEC = {
    "key": str(uuid.uuid4()),
    "w": 0.5,
    "ref_point": 5,
    "scale": 1,
}

VALID_SIGMOID_OUTPUT_FEATURE_SPEC = {
    "key": str(uuid.uuid4()),
    "steepness": 5,
    "tp": -44.1,
    "w": 0.5,
}

VALID_TARGET_OUTPUT_FEATURE_SPEC = {
    "key": str(uuid.uuid4()),
    "target_value": -42,
    "steepness": 5,
    "tolerance": 100,
    "w": 0.5,
}

VALID_CLOSE_TO_TARGET_OUTPUT_FEATURE_SPEC = {
    "key": str(uuid.uuid4()),
    "target_value": 42,
    "exponent": 2,
    "tolerance": 1.5,
    "w": 1.0,
}

INVALID_W = [
    {"w": 0},
    {"w": -100},
    {"w": 1.0000001},
    {"w": 100},
]

INVALID_BOUNDS = [
    {"lower_bound": 5, "upper_bound": 3},
    {"lower_bound": None, "upper_bound": None},
]
INVALID_STEEPNESS = [
    {"steepness": 0},
    {"steepness": -100},
]
INVALID_TOLERANCE = [
    {"tolerance": -0.1},
    {"tolerance": -100},
]

INVALID_REFPOINT = [{"ref_point": None}, {"ref_point": "s"}]

OUTPUT_FEATURE_SPECS = {
    MinIdentityOutputFeature: {
        "valids": [VALID_IDENTITY_OUTPUT_FEATURE_SPEC],
        "invalids": INVALID_SPECS
        + get_invalids(VALID_IDENTITY_OUTPUT_FEATURE_SPEC)
        + [
            {
                **VALID_IDENTITY_OUTPUT_FEATURE_SPEC,
                **invalid,
            }
            for invalid in [
                *INVALID_W,
                *INVALID_BOUNDS,
            ]
        ],
    },
    MaxIdentityOutputFeature: {
        "valids": [VALID_IDENTITY_OUTPUT_FEATURE_SPEC],
        "invalids": INVALID_SPECS
        + get_invalids(VALID_IDENTITY_OUTPUT_FEATURE_SPEC)
        + [
            {
                **VALID_IDENTITY_OUTPUT_FEATURE_SPEC,
                **invalid,
            }
            for invalid in [*INVALID_W, *INVALID_BOUNDS]
        ],
    },
    DeltaIdentityOutputFeature: {
        "valids": [VALID_DELTA_IDENTITY_OUTPUT_FEATURE_SPEC],
        "invalids": INVALID_SPECS
        + get_invalids(VALID_DELTA_IDENTITY_OUTPUT_FEATURE_SPEC)
        + [
            {
                **VALID_DELTA_IDENTITY_OUTPUT_FEATURE_SPEC,
                **invalid,
            }
            for invalid in [*INVALID_W, *INVALID_REFPOINT]
        ],
    },
    MinSigmoidOutputFeature: {
        "valids": [VALID_SIGMOID_OUTPUT_FEATURE_SPEC],
        "invalids": INVALID_SPECS
        + get_invalids(VALID_SIGMOID_OUTPUT_FEATURE_SPEC)
        + [
            {**VALID_SIGMOID_OUTPUT_FEATURE_SPEC, **invalid}
            for invalid in [
                *INVALID_W,
                *INVALID_STEEPNESS,
            ]
        ],
    },
    MaxSigmoidOutputFeature: {
        "valids": [VALID_SIGMOID_OUTPUT_FEATURE_SPEC],
        "invalids": INVALID_SPECS
        + get_invalids(VALID_SIGMOID_OUTPUT_FEATURE_SPEC)
        + [
            {**VALID_SIGMOID_OUTPUT_FEATURE_SPEC, **invalid}
            for invalid in [
                *INVALID_W,
                *INVALID_STEEPNESS,
            ]
        ],
    },
    TargetOutputFeature: {
        "valids": [VALID_TARGET_OUTPUT_FEATURE_SPEC],
        "invalids": INVALID_SPECS
        + get_invalids(VALID_TARGET_OUTPUT_FEATURE_SPEC)
        + [
            {**VALID_TARGET_OUTPUT_FEATURE_SPEC, **invalid}
            for invalid in [
                *INVALID_STEEPNESS,
                *INVALID_TOLERANCE,
                *INVALID_W,
            ]
        ],
    },
    CloseToTargetOutputFeature: {
        "valids": [VALID_CLOSE_TO_TARGET_OUTPUT_FEATURE_SPEC],
        "invalids": INVALID_SPECS
        + get_invalids(VALID_CLOSE_TO_TARGET_OUTPUT_FEATURE_SPEC)
        + [
            {**VALID_CLOSE_TO_TARGET_OUTPUT_FEATURE_SPEC, **invalid}
            for invalid in [
                # *INVALID_STEEPNESS,
                *INVALID_TOLERANCE,
                *INVALID_W,
            ]
        ],
    },
    ConstantOutputFeature: {
        "valids": [VALID_CONSTANT_OUTPUT_FEATURE_SPEC],
        "invalids": [INVALID_CONSTANT_OUTPUT_FEATURE_SPEC],
    },
}


@pytest.mark.parametrize(
    "cls, spec",
    [
        (cls, valid)
        for cls, data in OUTPUT_FEATURE_SPECS.items()
        for valid in data["valids"]
    ],
)
def test_valid_output_feature_specs(cls, spec):
    res = cls(**spec)
    assert isinstance(res, cls)


@pytest.mark.parametrize(
    "cls, spec",
    [
        (cls, valid)
        for cls, data in OUTPUT_FEATURE_SPECS.items()
        for valid in data["valids"]
    ],
)
def test_output_feature_serialize(cls, spec):
    res = cls(**spec)
    config = res.to_config()
    res2 = Feature.from_config(config)
    assert res == res2


@pytest.mark.parametrize(
    "cls, spec",
    [
        (cls, invalid)
        for cls, data in OUTPUT_FEATURE_SPECS.items()
        for invalid in data["invalids"]
    ],
)
def test_invalid_output_feature_specs(cls, spec):
    print(spec)
    with pytest.raises((ValueError, TypeError, KeyError, ValidationError)):
        res = cls(**spec)
