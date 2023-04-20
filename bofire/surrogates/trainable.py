from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Tuple

import pandas as pd
from sklearn.model_selection import KFold

from bofire.data_models.enum import OutputFilteringEnum
from bofire.surrogates.diagnostics import CvResult, CvResults
from bofire.surrogates.surrogate import Surrogate


class TrainableSurrogate(ABC):
    _output_filtering: OutputFilteringEnum = OutputFilteringEnum.ALL

    def fit(self, experiments: pd.DataFrame):
        # preprocess
        experiments = self._preprocess_experiments(experiments)
        # validate
        experiments = self.input_features.validate_experiments(  # type: ignore
            experiments, strict=False
        )
        X = experiments[self.input_features.get_keys()]  # type: ignore
        # TODO: output feature validation
        Y = experiments[self.output_features.get_keys()]  # type: ignore
        # fit
        self._fit(X=X, Y=Y)  # type: ignore

    def _preprocess_experiments(self, experiments: pd.DataFrame) -> pd.DataFrame:
        if self._output_filtering is None:
            return experiments
        elif self._output_filtering == OutputFilteringEnum.ALL:
            return self.output_features.preprocess_experiments_all_valid_outputs(  # type: ignore
                experiments=experiments,
                output_feature_keys=self.output_features.get_keys(),  # type: ignore
            )
        elif self._output_filtering == OutputFilteringEnum.ANY:
            return self.output_features.preprocess_experiments_any_valid_outputs(  # type: ignore
                experiments=experiments,
                output_feature_keys=self.output_features.get_keys(),  # type: ignore
            )
        else:
            raise ValueError("Unknown output filtering option requested.")

    @abstractmethod
    def _fit(self, X: pd.DataFrame, Y: pd.DataFrame):
        pass

    def cross_validate(
        self,
        experiments: pd.DataFrame,
        folds: int = -1,
        include_X: bool = False,
        include_labcodes: bool = False,
        hooks: Dict[
            str,
            Callable[
                [
                    Surrogate,
                    pd.DataFrame,
                    pd.DataFrame,
                    pd.DataFrame,
                    pd.DataFrame,
                ],
                Any,
            ],
        ] = {},
        hook_kwargs: Dict[str, Dict[str, Any]] = {},
    ) -> Tuple[CvResults, CvResults, Dict[str, List[Any]]]:
        """Perform a cross validation for the provided training data.

        Args:
            experiments (pd.DataFrame): Data on which the cross validation should be performed.
            folds (int, optional): Number of folds. -1 is equal to LOO CV. Defaults to -1.
            include_X (bool, optional): If true the X values of the fold are written to respective CvResult objects for
                later analysis. Defaults ot False.
            hooks (Dict[str, Callable[[Model, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame], Any]], optional):
                Dictionary of callable hooks that are called within the CV loop. The callable retrieves the current trained
                modeld and the current CV folds in the following order: X_train, y_train, X_test, y_test. Defaults to {}.
            hook_kwargs (Dict[str, Dict[str, Any]], optional): Dictionary holding hook specefic keyword arguments.
                Defaults to {}.

        Returns:
            Tuple[CvResults, CvResults, Dict[str, List[Any]]]: First CvResults object reflects the training data,
                second CvResults object the test data, dictionary object holds the return values of the applied hooks.
        """
        if include_labcodes and "labcode" not in experiments.columns:
            raise ValueError("No labcodes available for the provided experiments.")

        if len(self.output_features) > 1:  # type: ignore
            raise NotImplementedError(
                "Cross validation not implemented for multi-output models"
            )
        n = len(experiments)
        if folds > n:
            raise ValueError(
                f"Training data only has {n} experiments, which is less than folds"
            )
        elif n == 0:
            raise ValueError("Experiments is empty.")
        elif folds < 2 and folds != -1:
            raise ValueError("Folds must be -1 for LOO, or > 1.")
        elif folds == -1:
            folds = n
        # preprocess hooks
        hook_results = {key: [] for key in hooks.keys()}
        # instantiate kfold object
        cv = KFold(n_splits=folds, shuffle=True)
        key = self.output_features.get_keys()[0]  # type: ignore
        # first filter the experiments based on the model setting
        experiments = self._preprocess_experiments(experiments)
        train_results = []
        test_results = []
        # now get the indices for the split
        for train_index, test_index in cv.split(experiments):
            X_train = experiments.iloc[train_index][self.input_features.get_keys()]  # type: ignore
            X_test = experiments.iloc[test_index][self.input_features.get_keys()]  # type: ignore
            y_train = experiments.iloc[train_index][self.output_features.get_keys()]  # type: ignore
            y_test = experiments.iloc[test_index][self.output_features.get_keys()]  # type: ignore
            train_labcodes = (
                experiments.iloc[train_index]["labcode"] if include_labcodes else None
            )
            test_labcodes = (
                experiments.iloc[test_index]["labcode"] if include_labcodes else None
            )
            # now fit the model
            self._fit(X_train, y_train)
            # now do the scoring
            y_test_pred = self.predict(X_test)  # type: ignore
            y_train_pred = self.predict(X_train)  # type: ignore
            # now store the results
            train_results.append(
                CvResult(  # type: ignore
                    key=key,
                    observed=y_train[key],
                    predicted=y_train_pred[key + "_pred"],
                    standard_deviation=y_train_pred[key + "_sd"],
                    X=X_train if include_X else None,
                    labcodes=train_labcodes,
                )
            )
            test_results.append(
                CvResult(  # type: ignore
                    key=key,
                    observed=y_test[key],
                    predicted=y_test_pred[key + "_pred"],
                    standard_deviation=y_test_pred[key + "_sd"],
                    X=X_test if include_X else None,
                    labcodes=test_labcodes,
                )
            )
            # now call the hooks if available
            for hookname, hook in hooks.items():
                hook_results[hookname].append(
                    hook(
                        model=self,  # type: ignore
                        X_train=X_train,
                        y_train=y_train,
                        X_test=X_test,
                        y_test=y_test,
                        **hook_kwargs.get(hookname, {}),
                    )
                )
        return (
            CvResults(results=train_results),
            CvResults(results=test_results),
            hook_results,
        )
