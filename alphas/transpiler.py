from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .base import AlphaDataset, AlphaExecutionError

TRANSPILER_VERSION = "2025.01"


class AlphaTranspilerError(ValueError):
    """알파 표현식이 트랜스파일될 수 없을 때 발생합니다."""


def _build_allowed_globals() -> Dict[str, Any]:
    """알파 표현식에서 사용할 수 있는 헬퍼 함수들을 노출합니다."""
    from backend_module.Alphas import (
        adv,
        correlation,
        covariance,
        decay_linear,
        delta,
        delay,
        floor_window,
        product,
        rank,
        safe_clean,
        scale,
        sma,
        stddev,
        ts_argmax,
        ts_argmin,
        ts_max,
        ts_min,
        ts_rank,
        ts_sum,
    )

    def _to_column_index(source: Any) -> Optional[pd.Index]:
        cols = getattr(source, 'columns', None)
        if cols is not None and len(cols) > 0:
            return pd.Index(cols)
        name = getattr(source, 'name', None)
        if name:
            return pd.Index([name])
        return None

    def _propagate_columns(result: Any, args: Tuple[Any, ...]) -> Any:
        if isinstance(result, pd.Series):
            existing = getattr(result, 'columns', None)
            if existing is None or (hasattr(existing, '__len__') and len(existing) == 0):
                copied = None
                for arg in args:
                    copied = _to_column_index(arg)
                    if copied is not None:
                        break
                if copied is None:
                    copied = pd.Index([getattr(result, 'name', None) or 'value'])
                try:
                    result.columns = copied
                except Exception:
                    setattr(result, 'columns', copied)
        elif isinstance(result, pd.DataFrame):
            if result.empty or result.shape[1] == 0:
                result.columns = pd.Index(['value'])
        elif isinstance(result, (list, tuple)):
            return type(result)(_propagate_columns(item, args) for item in result)
        return result

    def _ensure_column_vector(array: Any) -> np.ndarray:
        arr = np.asarray(array)
        if arr.ndim == 0:
            return arr.reshape(1, 1)
        if arr.ndim == 1:
            return arr.reshape(-1, 1)
        if arr.ndim == 2:
            if arr.shape[1] == 0:
                return arr.reshape(arr.shape[0], 1)
            return arr
        return arr.reshape(arr.shape[0], -1)

    class _SafeNumpy:
        def __init__(self, module):
            self._module = module

        def minimum(self, a, b):
            return np.minimum(_ensure_column_vector(a), _ensure_column_vector(b))

        def maximum(self, a, b):
            return np.maximum(_ensure_column_vector(a), _ensure_column_vector(b))

        def __getattr__(self, item):
            return getattr(self._module, item)

    def _wrap_series_output(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return _propagate_columns(result, args)
        wrapper.__name__ = getattr(func, '__name__', 'wrapped_function')
        wrapper.__doc__ = getattr(func, '__doc__')
        return wrapper

    def ts_mean(df: Any, window: int = 10):
        """Rolling mean; Series 또는 DataFrame 지원."""
        window = int(window)
        return df.rolling(window, min_periods=window).mean()

    def ts_stddev(df: Any, window: int = 10):
        """Rolling stddev with population ddof=0."""
        window = int(window)
        return df.rolling(window, min_periods=window).std(ddof=0)

    def ts_var(df: Any, window: int = 10):
        """Rolling variance (population)."""
        window = int(window)
        return df.rolling(window, min_periods=window).var(ddof=0)

    def ts_zscore(df: Any, window: int = 20):
        """Rolling z-score: (x - rolling_mean) / rolling_std."""
        window = int(window)
        rolling_mean = df.rolling(window, min_periods=window).mean()
        rolling_std = df.rolling(window, min_periods=window).std(ddof=0)
        normalized = (df - rolling_mean) / (rolling_std.replace(0, np.nan))
        return normalized.fillna(0)

    def zscore(df: Any, window: int = 20):
        """Alias for rolling z-score; defaults to 20."""
        return ts_zscore(df, window)

    def ts_mean_abs(df: Any, window: int = 10):
        """Rolling mean of absolute values."""
        return df.abs().rolling(int(window), min_periods=int(window)).mean()

    safe_builtins = {
        "abs": abs,
        "min": min,
        "max": max,
        "pow": pow,
        "round": round,
    }

    globals_map: Dict[str, Any] = {
        "__builtins__": safe_builtins,
        "np": _SafeNumpy(np),
        "pd": pd,
        "adv": _wrap_series_output(adv),
        "correlation": _wrap_series_output(correlation),
        "covariance": _wrap_series_output(covariance),
        "decay_linear": _wrap_series_output(decay_linear),
        "delta": _wrap_series_output(delta),
        "delay": _wrap_series_output(delay),
        "floor_window": floor_window,
        "product": _wrap_series_output(product),
        "rank": _wrap_series_output(rank),
        "safe_clean": _wrap_series_output(safe_clean),
        "scale": _wrap_series_output(scale),
        "sma": _wrap_series_output(sma),
        "stddev": _wrap_series_output(stddev),
        "ts_argmax": _wrap_series_output(ts_argmax),
        "ts_argmin": _wrap_series_output(ts_argmin),
        "ts_max": _wrap_series_output(ts_max),
        "ts_min": _wrap_series_output(ts_min),
        "ts_rank": _wrap_series_output(ts_rank),
        "ts_sum": _wrap_series_output(ts_sum),
        "ts_mean": ts_mean,
        "ts_stddev": ts_stddev,
        "ts_std": ts_stddev,
        "ts_var": ts_var,
        "ts_variance": ts_var,
        "ts_zscore": ts_zscore,
        "zscore": zscore,
        "ts_avg": ts_mean,
        "ts_mean_abs": ts_mean_abs,
        # 표현식에서 자주 사용되는 편리한 넘파이 약어들
        "sign": np.sign,
        "log": np.log,
        "exp": np.exp,
        "sqrt": np.sqrt,
    }
    return globals_map


ALPHA_GLOBALS = _build_allowed_globals()


@dataclass
class TranspiledAlpha:
    """컴파일된 호출 가능 객체와 메타데이터를 위한 컨테이너."""

    name: Optional[str]
    expression: str
    callable: Callable[[AlphaDataset], pd.Series]
    python_source: str
    globals_hash: int
    version: str = TRANSPILER_VERSION


def _coerce_to_series(result: Any, dataset: AlphaDataset) -> pd.Series:
    """트랜스파일된 표현식 출력이 판다스 시리즈인지 확인합니다."""
    if isinstance(result, pd.Series):
        return result

    if isinstance(result, pd.DataFrame):
        if result.shape[1] == 1:
            return result.iloc[:, 0]

        # 2차원 행렬을 단일 시계열로 축소합니다.
        try:
            if result.shape[0] == result.shape[1] and list(result.columns) == list(result.index):
                diagonal = result.to_numpy().diagonal()
                return pd.Series(diagonal, index=result.index)
        except Exception:
            pass

        reduced = result.mean(axis=1, numeric_only=True)
        if isinstance(reduced, pd.Series) and len(reduced) == len(dataset.frame.index):
            return reduced

        raise AlphaExecutionError("Expression returned DataFrame with incompatible shape")

    if isinstance(result, (np.ndarray, list, tuple)):
        if len(result) == len(dataset.frame.index):
            return pd.Series(result, index=dataset.frame.index)
        raise AlphaExecutionError("Expression output length does not match dataset index")

    # Broadcast scalars across the index
    if np.isscalar(result):
        return pd.Series(result, index=dataset.frame.index)

    raise AlphaExecutionError(f"Unsupported expression output type: {type(result).__name__}")


def compile_expression(expression: str, *, name: Optional[str] = None) -> TranspiledAlpha:
    """
    알파 표현식 문자열을 실행 가능한 호출 가능 객체로 컴파일합니다.

    매개변수
    ----------
    expression:
        별칭 네임스페이스를 사용하는 문자열 공식 (`close`, `volume`, ...).
    name:
        디버깅이나 소스 렌더링을 위한 선택적 이름.
    """
    if not expression or not expression.strip():
        raise AlphaTranspilerError("Alpha expression cannot be empty")

    expression = expression.strip()
    if "self." in expression:
        expression = expression.replace("self.", "")
    filename = f"<alpha:{name or 'expression'}>"

    try:
        code_object = compile(expression, filename, "eval")
    except SyntaxError as exc:
        raise AlphaTranspilerError(f"Expression syntax error: {exc}") from exc

    globals_hash = hash(tuple(sorted(ALPHA_GLOBALS.keys())))

    def _call(dataset: AlphaDataset) -> pd.Series:
        locals_env = dataset.build_eval_locals()
        try:
            result = eval(code_object, ALPHA_GLOBALS, locals_env)  # noqa: S307 - controlled globals
        except Exception as exc:  # pragma: no cover - surface as runtime error
            raise AlphaExecutionError(f"Alpha evaluation failed: {exc}") from exc
        return _coerce_to_series(result, dataset)

    python_source = render_function_source(name or "alpha_formula", expression)

    return TranspiledAlpha(
        name=name,
        expression=expression,
        callable=_call,
        python_source=python_source,
        globals_hash=globals_hash,
    )


def render_function_source(function_name: str, expression: str) -> str:
    """
    표현식을 재사용 가능한 파이썬 함수 정의로 렌더링합니다.
    """
    safe_name = function_name or "alpha_formula"
    body = textwrap.dedent(
        f"""
        def {safe_name}(dataset):
            \"\"\"Auto-generated alpha formula (v{TRANSPILER_VERSION}).\"\"\"
            env = dataset.build_eval_locals()
            return eval({expression!r}, ALPHA_GLOBALS, env)
        """
    ).strip()
    return body
