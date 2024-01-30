import math
import warnings
from copy import deepcopy
from typing import Dict

import numpy as np
import pandas as pd
import torch
from botorch.optim.initializers import sample_q_batches_from_polytope
from botorch.optim.parameter_constraints import _generate_unfixed_lin_constraints

from bofire.data_models.constraints.api import (
    LinearEqualityConstraint,
    LinearInequalityConstraint,
    NChooseKConstraint,
)
from bofire.data_models.domain.api import Domain
from bofire.data_models.features.api import (
    CategoricalInput,
    ContinuousInput,
    DiscreteInput,
)
from bofire.data_models.strategies.api import PolytopeSampler as DataModel
from bofire.strategies.strategy import Strategy
from bofire.utils.torch_tools import (
    get_interpoint_constraints,
    get_linear_constraints,
    tkwargs,
)


class PolytopeSampler(Strategy):
    """Base class for sampling methods in BoFire for sampling from constrained input spaces.

    Attributes
        domain (Domain): Domain defining the constrained input space
    """

    def __init__(
        self,
        data_model: DataModel,
        **kwargs,
    ):
        super().__init__(data_model=data_model, **kwargs)
        self.n_burnin = data_model.n_burnin
        self.n_thinning = data_model.n_thinning
        self.fallback_sampling_method = data_model.fallback_sampling_method

    def _ask(
        self,
        candidate_count: int,
    ) -> pd.DataFrame:
        """Generates the samples. In the case that `NChooseK` constraints are
        present, per combination `n` samples are generated.

        Args:
            candidate_count (int): number of samples to generate.
        Returns:
            Dataframe with samples.
        """
        if len(self.domain.constraints.get(NChooseKConstraint)) > 0:
            _, unused = self.domain.get_nchoosek_combinations()

            if candidate_count <= len(unused):
                sampled_combinations = [
                    unused[i]
                    for i in self.rng.choice(
                        len(unused), size=candidate_count, replace=False
                    )
                ]
                num_samples_per_it = 1
            else:
                sampled_combinations = unused
                num_samples_per_it = math.ceil(candidate_count / len(unused))

            samples = []
            for u in sampled_combinations:
                # create new domain without the nchoosekconstraints
                domain = deepcopy(self.domain)
                domain.constraints = domain.constraints.get(excludes=NChooseKConstraint)
                # fix the unused features
                for key in u:
                    feat = domain.inputs.get_by_key(key=key)
                    assert isinstance(feat, ContinuousInput)
                    feat.bounds = (0, 0)
                # setup then sampler for this situation
                sampler: PolytopeSampler = self.duplicate(domain=domain)
                samples.append(sampler.ask(num_samples_per_it))
            samples = pd.concat(samples, axis=0, ignore_index=True)
            return samples.sample(
                n=candidate_count,
                replace=False,
                ignore_index=True,
                random_state=self._get_seed(),
            )

        return self._sample_from_polytope(candidate_count)

    def _sample_from_polytope(self, n: int) -> pd.DataFrame:
        if len(self.domain.constraints) == 0:
            return self.domain.inputs.sample(
                n, self.fallback_sampling_method, seed=self._get_seed()
            )

        # check if we have pseudo fixed features in the linear equality constraints
        # a pseudo fixed is a linear euquality constraint with only one feature included
        # this can happen when fixing features when sampling with NChooseK constraints
        eqs = get_linear_constraints(
            domain=self.domain,
            constraint=LinearEqualityConstraint,  # type: ignore
            unit_scaled=False,
        )
        cleaned_eqs = []
        fixed_features: Dict[str, float] = {
            feat.key: feat.fixed_value()[0]  # type: ignore
            for feat in self.domain.inputs.get(ContinuousInput)
            if feat.is_fixed()  # type: ignore
        }

        for eq in eqs:
            if (
                len(eq[0]) == 1
            ):  # only one coefficient, so this is a pseudo fixed feature
                fixed_features[
                    self.domain.inputs.get_keys(ContinuousInput)[eq[0][0]]
                ] = float(eq[2] / eq[1][0])
            else:
                cleaned_eqs.append(eq)

        fixed_features_indices: Dict[int, float] = {
            self.domain.inputs.get_keys(ContinuousInput).index(key): value
            for key, value in fixed_features.items()
        }

        ineqs = get_linear_constraints(
            domain=self.domain,
            constraint=LinearInequalityConstraint,  # type: ignore
            unit_scaled=False,
        )

        interpoints = get_interpoint_constraints(domain=self.domain, n_candidates=n)

        lower = [
            feat.lower_bound  # type: ignore
            for feat in self.domain.get_features(ContinuousInput)
            if feat.key not in fixed_features.keys()  # type: ignore
        ]

        upper = [
            feat.upper_bound  # type: ignore
            for feat in self.domain.get_features(ContinuousInput)
            if feat.key not in fixed_features.keys()  # type: ignore
        ]

        if len(lower) == 0:
            warnings.warn(
                "Nothing to sample, all is fixed. Just the fixed set is returned.",
                UserWarning,
            )
            samples = pd.DataFrame(
                data=np.nan, index=range(n), columns=self.domain.inputs.get_keys()
            )
        else:
            bounds = torch.tensor([lower, upper]).to(**tkwargs)

            unfixed_ineqs = _generate_unfixed_lin_constraints(
                constraints=ineqs,
                eq=False,
                fixed_features=fixed_features_indices,
                dimension=len(self.domain.inputs.get(ContinuousInput)),
            )
            unfixed_eqs = _generate_unfixed_lin_constraints(
                constraints=cleaned_eqs,
                eq=True,
                fixed_features=fixed_features_indices,
                dimension=len(self.domain.inputs.get(ContinuousInput)),
            )
            unfixed_interpoints = _generate_unfixed_lin_constraints(
                constraints=interpoints,
                eq=True,
                fixed_features=fixed_features_indices,
                dimension=len(self.domain.inputs.get(ContinuousInput)),
            )

            combined_eqs = unfixed_eqs + unfixed_interpoints  # type: ignore

            # now use the hit and run sampler
            candidates = sample_q_batches_from_polytope(
                n=1,
                q=n,
                bounds=bounds.to(**tkwargs),
                inequality_constraints=unfixed_ineqs
                if len(unfixed_ineqs) > 0  # type: ignore
                else None,
                equality_constraints=combined_eqs if len(combined_eqs) > 0 else None,
                n_burnin=self.n_burnin,
                thinning=self.n_thinning,
                seed=self._get_seed(),
            ).squeeze(dim=0)

            # check that the random generated candidates are not always the same
            if (candidates.unique(dim=0).shape[0] != n) and (n > 1):
                warnings.warn("Generated candidates are not unique!")

            free_continuals = [
                feat.key
                for feat in self.domain.get_features(ContinuousInput)
                if feat.key not in fixed_features.keys()  # type: ignore
            ]
            # setup the output
            samples = pd.DataFrame(
                data=candidates.detach().numpy(),
                index=range(n),
                columns=free_continuals,
            )

        # setup the categoricals and discrete ones as uniform sampled vals
        for feat in self.domain.get_features([CategoricalInput, DiscreteInput]):
            samples[feat.key] = feat.sample(n, seed=self._get_seed())  # type: ignore

        # setup the fixed continuous ones
        for key, value in fixed_features.items():
            samples[key] = value

        return samples

    def has_sufficient_experiments(self) -> bool:
        return True

    def duplicate(self, domain: Domain) -> "PolytopeSampler":
        data_model = DataModel(
            domain=domain,
            fallback_sampling_method=self.fallback_sampling_method,
            n_burnin=self.n_burnin,
            n_thinning=self.n_thinning,
        )
        return self.__class__(data_model=data_model)