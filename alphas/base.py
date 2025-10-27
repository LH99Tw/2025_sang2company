from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


class AlphaExecutionError(RuntimeError):
    """알파 공식이 평가될 수 없을 때 발생합니다."""


@dataclass
class AlphaDataset:
    """
    원시 팩터 입력 프레임의 래퍼.

    입력 프레임은 표준 WorldQuant 스타일의
    컬럼 명명 규칙(`S_DQ_*`)을 포함해야 합니다. `open`, `high`, `close`와 같은
    별칭이 표현식 평가 및 트랜스파일링을 단순화하기 위해 노출됩니다.
    """

    frame: pd.DataFrame
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 표현식 내부에서 사용되는 표준 컬럼 별칭들
    column_aliases: Dict[str, str] = field(
        default_factory=lambda: {
            "open": "S_DQ_OPEN",
            "high": "S_DQ_HIGH",
            "low": "S_DQ_LOW",
            "close": "S_DQ_CLOSE",
            "volume": "S_DQ_VOLUME",
            "amount": "S_DQ_AMOUNT",
            "returns": "S_DQ_PCTCHANGE",
            "vwap": "S_DQ_VWAP",
        }
    )

    def __post_init__(self):
        if self.frame is None:
            raise ValueError("AlphaDataset frame cannot be None")
        if not isinstance(self.frame, pd.DataFrame):
            raise TypeError("AlphaDataset expects a pandas DataFrame input")
        # 호출자에게 다시 누출되지 않도록 복사본에서 작업합니다.
        writable_flag = getattr(self.frame.flags, "writable", None)
        if writable_flag is None:
            writable_flag = getattr(self.frame.flags, "writeable", None)

        if writable_flag is False:
            self.frame = self.frame.copy()
        else:
            self.frame = self.frame.copy()

        # 명시적으로 제공되지 않은 경우 VWAP를 파생시킵니다.
        if (
            "S_DQ_VWAP" not in self.frame.columns
            and "S_DQ_AMOUNT" in self.frame.columns
            and "S_DQ_VOLUME" in self.frame.columns
        ):
            volume = self.frame["S_DQ_VOLUME"].replace(0, pd.NA)
            vwap = self.frame["S_DQ_AMOUNT"] / volume
            self.frame["S_DQ_VWAP"] = vwap.fillna(method="ffill").fillna(method="bfill").fillna(0)

    def ensure_columns(self, required: Optional[List[str]] = None):
        """알파에서 요구하는 컬럼이 프레임에 포함되어 있는지 검증합니다."""
        required = required or list(set(self.column_aliases.values()))
        missing = [c for c in required if c not in self.frame.columns]
        if missing:
            raise ValueError(f"AlphaDataset is missing required columns: {missing}")

    def get_series(self, alias: str) -> pd.Series:
        """별칭 이름(`close`, `volume`, ...)으로 시리즈를 반환합니다."""
        column = self.column_aliases.get(alias)
        if not column:
            raise KeyError(f"Unknown alpha alias: {alias}")
        if column not in self.frame.columns:
            raise KeyError(f"Column '{column}' not found in AlphaDataset frame")
        return self.frame[column]

    def build_eval_locals(self) -> Dict[str, Any]:
        """
        동적 표현식을 평가할 때 사용되는 지역 변수 사전을 구축합니다.

        각 별칭을 판다스 시리즈로 노출시키며, `data`(전체 프레임)와
        `meta`(호출자가 제공한 추가 메타데이터)를 포함합니다.
        """
        locals_env: Dict[str, Any] = {}
        for alias, column in self.column_aliases.items():
            if column not in self.frame.columns:
                continue
            data = self.frame[column].copy()
            if isinstance(data, pd.Series):
                df = data.to_frame(name=alias)
            else:
                df = pd.DataFrame(data)
                df.columns = [alias] * df.shape[1]
            locals_env[alias] = df
        locals_env["data"] = self.frame
        locals_env["meta"] = self.metadata
        return locals_env

    def worldquant_engine(self):
        """
        기존 구현을 중복하지 않고 재사용할 수 있도록 레거시
        `backend_module.Alphas.Alphas` 엔진을 지연 구축합니다.
        """
        if "_worldquant_engine" not in self.__dict__:
            from backend_module.Alphas import Alphas as WorldQuantAlphas

            self.__dict__["_worldquant_engine"] = WorldQuantAlphas(self.frame)
        return self.__dict__["_worldquant_engine"]


@dataclass
class AlphaDefinition:
    """
    단일 알파 공식을 나타내는 메타데이터 및 호출 가능 번들.
    """

    name: str
    compute: Callable[[AlphaDataset], pd.Series]
    source: str = "shared"
    provider: str = "core"
    owner: Optional[str] = None
    description: str = ""
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        """API를 위한 직렬화 가능한 표현."""
        payload = {
            "name": self.name,
            "source": self.source,
            "provider": self.provider,
            "owner": self.owner,
            "description": self.description,
            "version": self.version,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }
        return payload
