"""
Incremental regression
"""

# Author: Michael Schindler <michael.schindler@maschindler.de>
# License: BSD 3 clause

import numpy as np
import scipy
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils import check_X_y
from sklearn.utils.extmath import safe_sparse_dot
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import NotFittedError


class IncrementalRegression(BaseEstimator, RegressorMixin):
    """Linear regression.

    This linear regression algorithm is able to perform a linear regression
    with the L2 regularization and iterative fit. [1]_

    .. [1] https://ieeexplore.ieee.org/document/4012031

    References
    ----------

    N. Liang, G. Huang, P. Saratchandran and N. Sundararajan,
    "A Fast and Accurate Online Sequential Learning Algorithm for Feedforward Networks,"
    in IEEE Transactions on Neural Networks, vol. 17, no. 6, pp. 1411-1423, Nov. 2006, doi: 10.1109/TNN.2006.880583.

    Parameters
    ----------
    alpha : float, default=1.0
        L2 regularization parameter
    fit_intercept : bool, default=True
        Fits a constant offset if True. Use this if input values are not average free.
    normalize : bool, default=False
        Performs a preprocessing normalization if True.
    """
    def __init__(self, alpha=1.0, fit_intercept=True, normalize=False):
        self.alpha = alpha
        self.fit_intercept = fit_intercept
        self.normalize = normalize
        self.scaler = StandardScaler(copy=False)

        self._K = None
        self._P = None
        self._output_weights = None

    def partial_fit(self, X, y, partial_normalize=True, reset=False):
        """Fits the regressor partially.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
        y : {ndarray, sparse matrix} of shape (n_samples,) or (n_samples, n_targets)
        partial_normalize : bool, default=True
            Partial fits the normalization transformer on this sample if True.
        reset : bool, default=False
            Begin a new fit, drop prior fits.

        Returns
        -------
        self
        """
        X_preprocessed = self._preprocessing(X, partial_normalize=partial_normalize)

        if reset:
            self._K = None
            self._P = None

        if self._K is None:
            self._K = safe_sparse_dot(X_preprocessed.T, X_preprocessed)
        else:
            self._K += safe_sparse_dot(X_preprocessed.T, X_preprocessed)

        self._P = np.linalg.inv(self._K + self.alpha**2 * np.identity(X_preprocessed.shape[1]))

        if self._output_weights is None:
            self._output_weights = np.matmul(self._P, safe_sparse_dot(X_preprocessed.T, y))
        else:
            self._output_weights += np.matmul(
                self._P, safe_sparse_dot(X_preprocessed.T, (y - safe_sparse_dot(X_preprocessed, self._output_weights))))

        return self

    def fit(self, X, y):
        """Fits the regressor.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
        y : {ndarray, sparse matrix} of shape (n_samples,) or (n_samples, n_targets)

        Returns
        -------
        self
        """
        X, y = check_X_y(X, y)

        self.partial_fit(X, y, partial_normalize=False, reset=True)
        return self

    def predict(self, X):
        """Predicts output y according to input X.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)

        Returns
        -------
        Y : ndarray of shape (n_samples,) or (n_samples, n_targets)
        """
        if self._output_weights is None:
            raise NotFittedError(self)

        return safe_sparse_dot(self._preprocessing(X, partial_normalize=False), self._output_weights)

    def _preprocessing(self, X, partial_normalize=True):
        """Applies preprocessing on the input data X.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
        partial_normalize : bool, default=True
            Partial fits the normalization transformer on this sample if True.

        Returns
        -------
        X_preprocessed : {ndarray, sparse matrix} of shape (n_samples, n_features) or (n_samples, n_features+1)
        """
        X_preprocessed = X

        if self.fit_intercept:
            X_preprocessed = np.hstack((X_preprocessed, np.ones(shape=(X.shape[0], 1))))

        if self.normalize:
            if partial_normalize:
                self.scaler.partial_fit(X_preprocessed).transform(X_preprocessed)
            else:
                self.scaler.fit_transform(X_preprocessed)

        return X_preprocessed
