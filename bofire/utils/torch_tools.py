import numpy as np
import torch

from bofire.domain import Domain
from bofire.domain.constraints import LinearConstraint
from bofire.domain.features import InputFeature

tkwargs = {
    "dtype": torch.double,
    "device": "cpu",
}


def get_linear_constraints(
    domain: Domain, constraint: LinearConstraint, unit_scaled: bool = False
):
    constraints = []
    for c in domain.constraints.get(constraint):
        indices = []
        coefficients = []
        lower = []
        upper = []
        rhs = 0.0
        for i, featkey in enumerate(c.features):
            idx = domain.get_feature_keys(InputFeature).index(featkey)
            feat = domain.get_feature(featkey)
            if feat.is_fixed():
                rhs -= feat.fixed_value() * c.coefficients[i]
            else:
                lower.append(feat.lower_bound)
                upper.append(feat.upper_bound)
                indices.append(idx)
                coefficients.append(
                    c.coefficients[i]
                )  # if unit_scaled == False else c_scaled.coefficients[i])
        if unit_scaled:
            lower = np.array(lower)
            upper = np.array(upper)
            s = upper - lower
            scaled_coefficients = s * np.array(coefficients)
            constraints.append(
                (
                    torch.tensor(indices),
                    -torch.tensor(scaled_coefficients).to(**tkwargs),
                    -(rhs + c.rhs - np.sum(np.array(coefficients) * lower)),
                )
            )
        else:
            constraints.append(
                (
                    torch.tensor(indices),
                    torch.tensor(coefficients).to(**tkwargs),
                    -(rhs + c.rhs),
                )
            )
    return constraints
