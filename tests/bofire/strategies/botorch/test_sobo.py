import random

import numpy as np
import pytest
from botorch.acquisition.monte_carlo import (
    qExpectedImprovement,
    qNoisyExpectedImprovement,
    qProbabilityOfImprovement,
    qUpperConfidenceBound,
)

from bofire.strategies.botorch.sobo import (
    BoTorchSoboAdditiveStrategy,
    BoTorchSoboMultiplicativeStrategy,
    BoTorchSoboStrategy,
)
from bofire.utils.enum import (
    AcquisitionFunctionEnum,
    CategoricalEncodingEnum,
    CategoricalMethodEnum,
    DescriptorEncodingEnum,
    DescriptorMethodEnum,
)
from tests.bofire.domain.test_domain_validators import (
    generate_candidates,
    generate_experiments,
)
from tests.bofire.domain.utils import get_invalids
from tests.bofire.strategies.botorch.test_base import data, domains
from tests.bofire.strategies.botorch.test_model_spec import VALID_MODEL_SPEC_LIST

VALID_BOTORCH_SOBO_STRATEGY_SPEC = {
    "acquisition_function": random.choice(list(AcquisitionFunctionEnum)),
    # "num_sobol_samples": 1024,
    # "num_restarts": 8,
    # "num_raw_samples": 1024,
    "descriptor_encoding": random.choice(list(DescriptorEncodingEnum)),
    "descriptor_method": random.choice(list(DescriptorMethodEnum)),
    "categorical_encoding": random.choice(list(CategoricalEncodingEnum)),
    "categorical_method": "EXHAUSTIVE",
}

BOTORCH_SOBO_STRATEGY_SPECS = {
    "valids": [
        VALID_BOTORCH_SOBO_STRATEGY_SPEC,
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "seed": 1},
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "model_specs": VALID_MODEL_SPEC_LIST},
    ],
    "invalids": [
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "acquisition_function": None},
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "descriptor_encoding": None},
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "categorical_encoding": None},
        {
            **VALID_BOTORCH_SOBO_STRATEGY_SPEC,
            "categorical_encoding": "ORDINAL",
            "categorical_method": "FREE",
        },
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "seed": -1},
    ],
}


@pytest.mark.parametrize(
    "domain, acqf",
    [(domains[0], VALID_BOTORCH_SOBO_STRATEGY_SPEC["acquisition_function"])],
)
def test_SOBO_not_fitted(domain, acqf):
    strategy = BoTorchSoboStrategy(domain=domain, acquisition_function=acqf)
    msg = "Model not trained."
    with pytest.raises(AssertionError, match=msg):
        strategy._init_acqf()


@pytest.mark.parametrize(
    "domain, acqf, expected, num_test_candidates",
    [
        (domains[0], acqf_inp[0], acqf_inp[1], num_test_candidates)
        for acqf_inp in [
            ("QEI", qExpectedImprovement),
            ("QNEI", qNoisyExpectedImprovement),
            ("QPI", qProbabilityOfImprovement),
            ("QUCB", qUpperConfidenceBound),
        ]
        for num_test_candidates in range(1, 3)
    ],
)
def test_SOBO_init_acqf(domain, acqf, expected, num_test_candidates):
    strategy = BoTorchSoboStrategy(domain=domain, acquisition_function=acqf)
    experiments = generate_experiments(domain, 20)
    experiments_test = generate_experiments(domain, num_test_candidates)

    strategy.tell(experiments)
    assert isinstance(strategy.acqf, expected)
    # test acqf calc
    acqf_vals = strategy._choose_from_pool(experiments_test, num_test_candidates)
    assert acqf_vals.shape[0] == num_test_candidates


@pytest.mark.parametrize(
    "domain, experiments, Strategy, expected",
    [
        (domains[0], data[0], BoTorchSoboStrategy, 12.0),
        (domains[1], data[1], BoTorchSoboStrategy, 12.0),
        (domains[3], data[3], BoTorchSoboStrategy, 12.0),
        (domains[2], data[2], BoTorchSoboAdditiveStrategy, 12.0 + 105.0),
        (domains[4], data[4], BoTorchSoboAdditiveStrategy, 12.0 + 105.0),
        (domains[2], data[2], BoTorchSoboMultiplicativeStrategy, 12.0 * 105.0),
        (domains[4], data[4], BoTorchSoboMultiplicativeStrategy, 12.0 * 105.0),
    ],
)
def test_SOBO_get_fbest(domain, experiments, Strategy, expected):
    my_strategy = Strategy(
        domain=domain, acquisition_function=random.choice(list(AcquisitionFunctionEnum))
    )
    my_strategy.domain.set_experiments(experiments)
    fbest = my_strategy.get_fbest()
    assert np.allclose(fbest, expected)
