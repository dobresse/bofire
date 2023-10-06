from typing import Literal

from pydantic import Field

from bofire.data_models.kernels.api import (
    PolynomialKernel,
)
from bofire.data_models.priors.api import BOTORCH_NOISE_PRIOR, AnyPrior

# from bofire.data_models.strategies.api import FactorialStrategy
from bofire.data_models.surrogates.botorch import BotorchSurrogate
from bofire.data_models.surrogates.scaler import ScalerEnum
from bofire.data_models.surrogates.trainable import TrainableSurrogate


class PolynomialSurrogate(BotorchSurrogate, TrainableSurrogate):
    type: Literal["PolynomialSurrogate"] = "PolynomialSurrogate"
    noise_prior: AnyPrior = Field(default_factory=lambda: BOTORCH_NOISE_PRIOR())
    scaler: ScalerEnum = ScalerEnum.NORMALIZE

    def __init__(self, power=2):
        self.kernel: PolynomialKernel = Field(
            default_factory=lambda: PolynomialKernel(power=power)
        )
