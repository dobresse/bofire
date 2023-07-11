from typing import Tuple

from pydantic import root_validator

from bofire.data_models.features.continuous import ContinuousInput


class ContinuousBinaryInput(ContinuousInput):
    """Base class for all binary input features. It behaves like a continuous inputs to allow for easy relaxation.
    It is not a true binary variable as it does not allow the variable to be either 0 or 1 while prohibiting all values
    in between.

    """

    def __init__(self, bounds=(0, 1), **kwargs):
        super().__init__(bounds=bounds, **kwargs)

    @root_validator(pre=False, skip_on_failure=True)
    def validate_lower_upper(cls, values):
        """Validates that lower bound is set to 0 and upper bound set to 1

        Args:
            values (Dict): Dictionary with attributes key, lower and upper bound

        Raises:
            ValueError: when the lower bound is higher than the upper bound

        Returns:
            Dict: The attributes as dictionary
        """

        if values["bounds"][0] != values["bounds"][1] and (
            values["bounds"][0] != 0 or values["bounds"][1] != 1
        ):
            raise ValueError(
                f'if variable is relaxed, lower bound must be 0 and upper bound 1, got {values["bounds"][0]}, {values["bounds"][1]}'
            )
        elif values["bounds"][0] == values["bounds"][1] and not (
            values["bounds"][0] == 0 or values["bounds"][0] == 1
        ):
            raise ValueError(
                f"if variable is fixed, lower and upper bound must be equal and both either 0 or 1,"
                f' got {values["bounds"][0]}, {values["bounds"][1]}'
            )

        return values

    def fix_to(self, value: int) -> Tuple[int, int]:
        """Fixes the binary variable to either 0 or 1
        Args:
            value: value to which the variable will be fixed to

        Returns: fixed bounds for the variable

        """
        if value != 0 and value != 1:
            raise ValueError(f"must be fixed to either 0 or 1, got {value}")
        self.bounds = (value, value)
        return self.bounds

    def relax(self) -> Tuple[int, int]:
        """Relaxes the bounds of the variable to the interval (0, 1)

        Returns: the new relaxed bounds

        """
        self.bounds = (0, 1)
        return self.bounds