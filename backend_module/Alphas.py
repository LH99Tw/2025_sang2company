import numpy as np
import pandas as pd
from numpy import abs, log, sign
from scipy.stats import rankdata

# =========================
# region Auxiliary functions
# =========================
def ts_sum(df, window=10):
    """Rolling sum."""
    return df.rolling(int(window)).sum()

def sma(df, window=10):
    """Simple moving average."""
    return df.rolling(int(window)).mean()

def stddev(df, window=10):
    """Rolling standard deviation."""
    return df.rolling(int(window)).std()

def correlation(x, y, window=10):
    """Rolling correlation."""
    return x.rolling(int(window)).corr(y)

def covariance(x, y, window=10):
    """Rolling covariance."""
    return x.rolling(int(window)).cov(y)

def rolling_rank(na):
    """Helper for ts_rank: last element's rank in the window."""
    return rankdata(na)[-1]

def ts_rank(df, window=10):
    """Rolling rank (percentile-like, via rankdata on each window)."""
    return df.rolling(int(window)).apply(rolling_rank)

def rolling_prod(na):
    """Helper for rolling product."""
    return np.prod(na)

def product(df, window=10):
    """Rolling product."""
    return df.rolling(int(window)).apply(rolling_prod)

def ts_min(df, window=10):
    """Rolling min."""
    return df.rolling(int(window)).min()

def ts_max(df, window=10):
    """Rolling max."""
    return df.rolling(int(window)).max()

def delta(df, period=1):
    """Difference."""
    return df.diff(int(period))

def delay(df, period=1):
    """Lag."""
    return df.shift(int(period))

def rank(df):
    """Cross-sectional rank (per-date pct rank 기대 시, 외부에서 groupby(date) 사용)."""
    if isinstance(df, pd.DataFrame):
        # rank each row (date-wise) so cross-sectional percentiles per timestamp
        return df.rank(axis=1, pct=True)
    return df.rank(pct=True)

def scale(df, k=1):
    """
    WorldQuant식 scale: |x|의 합이 k가 되도록 스케일.
    - Series: 전체 합으로 나눔
    - DataFrame: 각 행(단면) 합으로 나눔
    - 0/NaN 분모 안전 처리
    """
    if isinstance(df, pd.DataFrame):
        denom = np.abs(df).sum(axis=1)
        denom = denom.replace(0, np.nan)
        out = df.div(denom, axis=0) * k
        return out.fillna(0)  # <<< CHANGED
    else:
        denom = np.abs(df).sum()
        if pd.isna(denom) or denom == 0:
            return df * 0      # <<< CHANGED
        return df * (k / denom)

def ts_argmax(df, window=10):
    """Index (1-based) of argmax within the rolling window."""
    return df.rolling(int(window)).apply(np.argmax) + 1

def ts_argmin(df, window=10):
    """Index (1-based) of argmin within the rolling window."""
    return df.rolling(int(window)).apply(np.argmin) + 1

def decay_linear(df, period=10):
    """Linear weighted moving average implementation (per-column)."""
    period = int(period)
    if isinstance(df, pd.Series):
        df = df.to_frame()
    elif not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    if df.isnull().values.any():
        df = df.copy()
        df.fillna(method='ffill', inplace=True)
        df.fillna(method='bfill', inplace=True)
        df.fillna(value=0, inplace=True)

    na_lwma = np.zeros_like(df)
    na_lwma[:period, :] = df.iloc[:period, :]
    na_series = df.values

    divisor = period * (period + 1) / 2
    y = (np.arange(period) + 1) * 1.0 / divisor

    for row in range(period - 1, df.shape[0]):
        x = na_series[row - period + 1: row + 1, :]
        na_lwma[row, :] = (np.dot(x.T, y))

    return pd.DataFrame(na_lwma, index=df.index, columns=df.columns)

# --- NEW: helpers for ADV and floor window ---
def safe_clean(x):
    """Series/DataFrame이면 inf/NaN→0으로 정리, 스칼라면 그대로."""
    if isinstance(x, (pd.Series, pd.DataFrame)):
        return x.replace([-np.inf, np.inf], 0).fillna(0)  # <<< CHANGED
    return x

def adv(df_close, df_volume, window):
    """Average Daily *Dollar* Volume = SMA(close*volume, N)"""
    return sma(df_close * df_volume, int(window))         # <<< CHANGED

def floor_window(x):
    """WorldQuant 101 규칙: 비정수 창은 내림."""
    return int(np.floor(x))                               # <<< CHANGED
# endregion
# =========================


class Alphas(object):
    def __init__(self, df_data):
        self.open = pd.DataFrame(df_data['S_DQ_OPEN'])
        self.high = pd.DataFrame(df_data['S_DQ_HIGH'])
        self.low = pd.DataFrame(df_data['S_DQ_LOW'])
        self.close = pd.DataFrame(df_data['S_DQ_CLOSE'])
        self.volume = pd.DataFrame(df_data['S_DQ_VOLUME']) * 100
        self.returns = pd.DataFrame(df_data['S_DQ_PCTCHANGE'])
        self.vwap = (pd.DataFrame(df_data['S_DQ_AMOUNT']) * 1000) / (pd.DataFrame(df_data['S_DQ_VOLUME']) * 100 + 1)

    # Alpha#1
    def alpha001(self):
        base = self.close.copy()
        m = (self.returns < 0)
        base[m] = stddev(self.returns, 20)[m]
        return rank(ts_argmax(base ** 2, 5)) - 0.5

    # Alpha#2
    def alpha002(self):
        df = -1 * correlation(rank(delta(log(self.volume), 2)), rank((self.close - self.open) / self.open), 6)
        return df.replace([-np.inf, np.inf], 0).fillna(value=0)

    # Alpha#3
    def alpha003(self):
        df = -1 * correlation(rank(self.open), rank(self.volume), 10)
        return df.replace([-np.inf, np.inf], 0).fillna(value=0)

    # Alpha#4
    def alpha004(self):
        return -1 * ts_rank(rank(self.low), 9)

    # Alpha#5
    def alpha005(self):
        return (rank((self.open - (ts_sum(self.vwap, 10) / 10))) * (-1 * abs(rank((self.close - self.vwap)))))

    # Alpha#6
    def alpha006(self):
        df = -1 * correlation(self.open, self.volume, 10)
        return df.replace([-np.inf, np.inf], 0).fillna(value=0)

    # Alpha#7  <<< CHANGED (ADV 정의 고정)
    def alpha007(self):
        adv20 = adv(self.close, self.volume, 20)  # 달러 ADV
        mom7 = delta(self.close, 7)
        core = -1 * ts_rank(abs(mom7), 60) * sign(mom7)
        out = pd.Series(-1.0, index=self.close.index)
        out[adv20 < self.volume] = core[adv20 < self.volume]
        # out = out.shift(1)  # 옵션: 익일 체결
        return out.fillna(-1)

    # Alpha#8
    def alpha008(self):
        return -1 * (rank(((ts_sum(self.open, 5) * ts_sum(self.returns, 5)) -
                           delay((ts_sum(self.open, 5) * ts_sum(self.returns, 5)), 10))))

    # Alpha#9
    def alpha009(self):
        delta_close = delta(self.close, 1)
        cond_1 = ts_min(delta_close, 5) > 0
        cond_2 = ts_max(delta_close, 5) < 0
        alpha = -1 * delta_close
        alpha[cond_1 | cond_2] = delta_close
        return alpha

    # Alpha#10
    def alpha010(self):
        delta_close = delta(self.close, 1)
        cond_1 = ts_min(delta_close, 4) > 0
        cond_2 = ts_max(delta_close, 4) < 0
        alpha = -1 * delta_close
        alpha[cond_1 | cond_2] = delta_close
        return alpha

    # Alpha#11
    def alpha011(self):
        return ((rank(ts_max((self.vwap - self.close), 3)) + rank(ts_min((self.vwap - self.close), 3))) *
                rank(delta(self.volume, 3)))

    # Alpha#12
    def alpha012(self):
        return sign(delta(self.volume, 1)) * (-1 * delta(self.close, 1))

    # Alpha#13
    def alpha013(self):
        return -1 * rank(covariance(rank(self.close), rank(self.volume), 5))

    # Alpha#14
    def alpha014(self):
        df = correlation(self.open, self.volume, 10)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * rank(delta(self.returns, 3)) * df

    # Alpha#15
    def alpha015(self):
        df = correlation(rank(self.high), rank(self.volume), 3)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * ts_sum(rank(df), 3)

    # Alpha#16
    def alpha016(self):
        return -1 * rank(covariance(rank(self.high), rank(self.volume), 5))

    # Alpha#17
    def alpha017(self):
        adv20 = adv(self.close, self.volume, 20)
        return -1 * (rank(ts_rank(self.close, 10)) *
                     rank(delta(delta(self.close, 1), 1)) *
                     rank(ts_rank((self.volume / adv20), 5)))

    # Alpha#18
    def alpha018(self):
        df = correlation(self.close, self.open, 10)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * (rank((stddev(abs((self.close - self.open)), 5) + (self.close - self.open)) + df))

    # Alpha#19
    def alpha019(self):
        return ((-1 * sign((self.close - delay(self.close, 7)) + delta(self.close, 7))) *
                (1 + rank(1 + ts_sum(self.returns, 250))))

    # Alpha#20
    def alpha020(self):
        return -1 * (rank(self.open - delay(self.high, 1)) *
                     rank(self.open - delay(self.close, 1)) *
                     rank(self.open - delay(self.low, 1)))

    # Alpha#21
    def alpha021(self):
        cond_1 = sma(self.close, 8) + stddev(self.close, 8) < sma(self.close, 2)
        adv20 = adv(self.close, self.volume, 20)
        cond_2 = sma(self.volume, 20) / self.volume < 1  # 원문 유지
        alpha = pd.Series(np.ones_like(self.close), index=self.close.index)
        alpha[cond_1 | cond_2] = -1
        return alpha

    # Alpha#22
    def alpha022(self):
        df = correlation(self.high, self.volume, 5)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * delta(df, 5) * rank(stddev(self.close, 20))

    # Alpha#23
    def alpha023(self):
        cond = sma(self.high, 20) < self.high
        alpha = pd.Series(np.zeros_like(self.close), index=self.close.index)
        alpha[cond] = -1 * delta(self.high, 2).fillna(value=0)
        return alpha

    # Alpha#24
    def alpha024(self):
        cond = delta(sma(self.close, 100), 100) / delay(self.close, 100) <= 0.05
        alpha = -1 * delta(self.close, 3)
        alpha[cond] = -1 * (self.close - ts_min(self.close, 100))
        return alpha

    # Alpha#25
    def alpha025(self):
        adv20 = adv(self.close, self.volume, 20)
        return rank(((((-1 * self.returns) * adv20) * self.vwap) * (self.high - self.close)))

    # Alpha#26
    def alpha026(self):
        df = correlation(ts_rank(self.volume, 5), ts_rank(self.high, 5), 5)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * ts_max(df, 3)

    # Alpha#27
    def alpha027(self):
        alpha = rank((sma(correlation(rank(self.volume), rank(self.vwap), 6), 2) / 2.0))
        alpha[alpha > 0.5] = -1
        alpha[alpha <= 0.5] = 1
        return alpha

    # Alpha#28
    def alpha028(self):
        adv20 = adv(self.close, self.volume, 20)
        df = correlation(adv20, self.low, 5)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return scale(((df + ((self.high + self.low) / 2)) - self.close))

    # Alpha#29
    def alpha029(self):
        return (ts_min(rank(rank(scale(log(ts_sum(rank(rank(-1 * rank(delta((self.close - 1), 5)))), 2))))), 5) +
                ts_rank(delay((-1 * self.returns), 6), 5))

    # Alpha#30
    def alpha030(self):
        delta_close = delta(self.close, 1)
        inner = sign(delta_close) + sign(delay(delta_close, 1)) + sign(delay(delta_close, 2))
        return ((1.0 - rank(inner)) * ts_sum(self.volume, 5)) / ts_sum(self.volume, 20)

    # Alpha#31
    def alpha031(self):
        adv20 = adv(self.close, self.volume, 20)
        df = correlation(adv20, self.low, 12).replace([-np.inf, np.inf], 0).fillna(value=0)
        p1 = rank(rank(rank(decay_linear((-1 * rank(rank(delta(self.close, 10)))).to_frame(), 10))))
        p2 = rank((-1 * delta(self.close, 3)))
        p3 = sign(scale(df))
        return p1.iloc[:, 0] + p2 + p3

    # Alpha#32
    def alpha032(self):
        return scale(((sma(self.close, 7) / 7) - self.close)) + (20 * scale(correlation(self.vwap, delay(self.close, 5), 230)))

    # Alpha#33
    def alpha033(self):
        return rank(-1 + (self.open / self.close))

    # Alpha#34
    def alpha034(self):
        inner = stddev(self.returns, 2) / stddev(self.returns, 5)
        inner = inner.replace([-np.inf, np.inf], 1).fillna(value=1)
        return rank(2 - rank(inner) - rank(delta(self.close, 1)))

    # Alpha#35
    def alpha035(self):
        return ((ts_rank(self.volume, 32) *
                 (1 - ts_rank(self.close + self.high - self.low, 16))) *
                (1 - ts_rank(self.returns, 32)))

    # Alpha#36
    def alpha036(self):
        adv20 = adv(self.close, self.volume, 20)
        return (((((2.21 * rank(correlation((self.close - self.open), delay(self.volume, 1), 15))) +
                    (0.7 * rank((self.open - self.close)))) +
                   (0.73 * rank(ts_rank(delay((-1 * self.returns), 6), 5)))) +
                  rank(abs(correlation(self.vwap, adv20, 6)))) +
                (0.6 * rank((((sma(self.close, 200) / 200) - self.open) * (self.close - self.open)))))

    # Alpha#37
    def alpha037(self):
        return rank(correlation(delay(self.open - self.close, 1), self.close, 200)) + rank(self.open - self.close)

    # Alpha#38
    def alpha038(self):
        ratio = (self.close / self.open).replace([-np.inf, np.inf], 1).fillna(value=1)
        return -1 * rank(ts_rank(self.close, 10)) * rank(ratio)

    # Alpha#39
    def alpha039(self):
        adv20 = adv(self.close, self.volume, 20)
        return ((-1 * rank(delta(self.close, 7) *
                (1 - rank(decay_linear((self.volume / adv20).to_frame(), 9).iloc[:, 0])))) *
                (1 + rank(sma(self.returns, 250))))

    # Alpha#40
    def alpha040(self):
        return -1 * rank(stddev(self.high, 10)) * correlation(self.high, self.volume, 10)

    # Alpha#41
    def alpha041(self):
        return pow((self.high * self.low), 0.5) - self.vwap

    # Alpha#42
    def alpha042(self):
        return rank((self.vwap - self.close)) / rank((self.vwap + self.close))

    # Alpha#43
    def alpha043(self):
        adv20 = adv(self.close, self.volume, 20)
        return ts_rank(self.volume / adv20, 20) * ts_rank((-1 * delta(self.close, 7)), 8)

    # Alpha#44
    def alpha044(self):
        df = correlation(self.high, rank(self.volume), 5)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * df

    # Alpha#45
    def alpha045(self):
        df = correlation(self.close, self.volume, 2)
        df = df.replace([-np.inf, np.inf], 0).fillna(value=0)
        return -1 * (rank(sma(delay(self.close, 5), 20)) * df *
                     rank(correlation(ts_sum(self.close, 5), ts_sum(self.close, 20), 2)))

    # Alpha#46
    def alpha046(self):
        inner = ((delay(self.close, 20) - delay(self.close, 10)) / 10) - ((delay(self.close, 10) - self.close) / 10)
        alpha = (-1 * delta(self.close))
        alpha[inner < 0] = 1
        alpha[inner > 0.25] = -1
        return alpha

    # Alpha#47
    def alpha047(self):
        adv20 = adv(self.close, self.volume, 20)
        return ((((rank((1 / self.close)) * self.volume) / adv20) *
                 ((self.high * rank((self.high - self.close))) / (sma(self.high, 5) / 5))) -
                rank((self.vwap - delay(self.vwap, 5))))

    # Alpha#49
    def alpha049(self):
        inner = (((delay(self.close, 20) - delay(self.close, 10)) / 10) - ((delay(self.close, 10) - self.close) / 10))
        alpha = (-1 * delta(self.close))
        alpha[inner < -0.1] = 1
        return alpha

    # Alpha#50
    def alpha050(self):
        return (-1 * ts_max(rank(correlation(rank(self.volume), rank(self.vwap), 5)), 5))

    # Alpha#51
    def alpha051(self):
        inner = (((delay(self.close, 20) - delay(self.close, 10)) / 10) - ((delay(self.close, 10) - self.close) / 10))
        alpha = (-1 * delta(self.close))
        alpha[inner < -0.05] = 1
        return alpha

    # Alpha#52
    def alpha052(self):
        return (((-1 * delta(ts_min(self.low, 5), 5)) *
                 rank(((ts_sum(self.returns, 240) - ts_sum(self.returns, 20)) / 220))) *
                ts_rank(self.volume, 5))

    # Alpha#53
    def alpha053(self):
        inner = (self.close - self.low).replace(0, 0.0001)
        return -1 * delta((((self.close - self.low) - (self.high - self.close)) / inner), 9)

    # Alpha#54
    def alpha054(self):
        inner = (self.low - self.high).replace(0, -0.0001)
        return -1 * (self.low - self.close) * (self.open ** 5) / (inner * (self.close ** 5))

    # Alpha#55
    def alpha055(self):
        divisor = (ts_max(self.high, 12) - ts_min(self.low, 12)).replace(0, 0.0001)
        inner = (self.close - ts_min(self.low, 12)) / (divisor)
        df = correlation(rank(inner), rank(self.volume), 6)
        return -1 * df.replace([-np.inf, np.inf], 0).fillna(value=0)

    # Alpha#57
    def alpha057(self):
        return (0 - (1 * ((self.close - self.vwap) / decay_linear(rank(ts_argmax(self.close, 30)).to_frame(), 2).iloc[:, 0])))

    # Alpha#60
    def alpha060(self):
        divisor = (self.high - self.low).replace(0, 0.0001)
        inner = ((self.close - self.low) - (self.high - self.close)) * self.volume / divisor
        return - ((2 * scale(rank(inner))) - scale(rank(ts_argmax(self.close, 10))))

    # Alpha#61 (windows floored)
    def alpha061(self):
        adv180 = adv(self.close, self.volume, 180)
        return (rank((self.vwap - ts_min(self.vwap, floor_window(11.5783)))) <
                rank(correlation(self.vwap, adv180, floor_window(17.9282))))

    # Alpha#62 (sum(adv20,k) 사용)
    def alpha062(self):
        adv20 = adv(self.close, self.volume, 20)
        k = floor_window(22.4101)
        w = floor_window(9.91009)
        left = rank(correlation(self.vwap, ts_sum(adv20, k), w))  # <<< CHANGED
        right = rank(((rank(self.open) + rank(self.open)) <
                      (rank(((self.high + self.low) / 2)) + rank(self.high))))
        return ((left < right) * -1)

    # Alpha#64 (windows floored)
    def alpha064(self):
        adv120 = adv(self.close, self.volume, 120)
        return ((rank(correlation(sma(((self.open * 0.178404) + (self.low * (1 - 0.178404))),
                                      floor_window(12.7054)+1),
                                   sma(adv120, floor_window(12.7054)+1),
                                   floor_window(16.6208))) <
                 rank(delta(((((self.high + self.low) / 2) * 0.178404) +
                             (self.vwap * (1 - 0.178404))),
                            floor_window(3.69741)))) * -1)

    # Alpha#65 (sum(adv60,k) 사용)
    def alpha065(self):
        adv60 = adv(self.close, self.volume, 60)
        k = floor_window(8.6911)
        w = floor_window(6.40374)
        left = rank(correlation(((self.open * 0.00817205) + (self.vwap * (1 - 0.00817205))),
                                ts_sum(adv60, k), w))          # <<< CHANGED
        right = rank((self.open - ts_min(self.open, floor_window(13.635))))
        return ((left < right) * -1)

    # Alpha#66
    def alpha066(self):
        return ((rank(decay_linear(delta(self.vwap, floor_window(3.51013)+1).to_frame(),
                                   floor_window(7.23052)).iloc[:, 0]) +
                 ts_rank(decay_linear(((((self.low * 0.96633) +
                                          (self.low * (1 - 0.96633))) - self.vwap) /
                                        (self.open - ((self.high + self.low) / 2))).to_frame(),
                                      floor_window(11.4157)).iloc[:, 0],
                          floor_window(6.72611))) * -1)

    # Alpha#68
    def alpha068(self):
        adv15 = adv(self.close, self.volume, 15)
        left = ts_rank(correlation(rank(self.high), rank(adv15), floor_window(8.91644)),
                       floor_window(13.9333))
        right = rank(delta(((self.close * 0.518371) + (self.low * (1 - 0.518371))),
                           floor_window(1.06157)))
        return ((left < right) * -1)

    # Alpha#71
    def alpha071(self):
        adv180 = adv(self.close, self.volume, 180)
        p1 = ts_rank(decay_linear(correlation(ts_rank(self.close, floor_window(3.43976)),
                                              ts_rank(adv180, floor_window(12.0647)),
                                              floor_window(18.0175)).to_frame(),
                                  floor_window(4.20501)).iloc[:, 0],
                     floor_window(15.6948))
        p2 = ts_rank(decay_linear((rank(((self.low + self.open) - (self.vwap + self.vwap))).pow(2)).to_frame(),
                                  floor_window(16.4662)).iloc[:, 0],
                     floor_window(4.4388))
        result = pd.Series(index=self.close.index)
        result[p1 >= p2] = p1[p1 >= p2]
        result[p2 > p1] = p2[p2 > p1]
        return result

    # Alpha#72
    def alpha072(self):
        adv40 = adv(self.close, self.volume, 40)
        num = rank(decay_linear(correlation(((self.high + self.low) / 2),
                                            adv40,
                                            floor_window(8.93345)).to_frame(),
                                floor_window(10.1519)).iloc[:, 0])
        den = rank(decay_linear(correlation(ts_rank(self.vwap, floor_window(3.72469)),
                                            ts_rank(self.volume, floor_window(18.5188)),
                                            floor_window(6.86671)).to_frame(),
                                floor_window(2.95011)).iloc[:, 0])
        return num / den

    # Alpha#73
    def alpha073(self):
        p1 = rank(decay_linear(delta(self.vwap, floor_window(4.72775)+1).to_frame(),
                               floor_window(2.91864)).iloc[:, 0])
        p2 = ts_rank(decay_linear(((delta(((self.open * 0.147155) +
                                           (self.low * (1 - 0.147155))),
                                          floor_window(2.03608)) /
                                    ((self.open * 0.147155) +
                                     (self.low * (1 - 0.147155)))) * -1).to_frame(),
                                  floor_window(3.33829)).iloc[:, 0],
                         floor_window(16.7411))
        result = pd.Series(index=self.close.index)
        result[p1 >= p2] = p1[p1 >= p2]
        result[p2 > p1] = p2[p2 > p1]
        return -1 * result

    # Alpha#74  <<< CHANGED (sum(adv30,k), 불리언 캐스팅)
    def alpha074(self):
        adv30 = adv(self.close, self.volume, 30)
        k  = floor_window(37.4843)
        w1 = floor_window(15.1365)
        w2 = floor_window(11.4791)
        mix = (self.high * 0.0261661) + (self.vwap * (1 - 0.0261661))
        left  = correlation(self.close, ts_sum(adv30, k), w1)
        right = correlation(rank(mix), rank(self.volume), w2)
        left  = safe_clean(left)
        right = safe_clean(right)
        signal = (rank(left) < rank(right)).astype(int) * -1
        # signal = signal.shift(1)
        return signal.fillna(0)

    # Alpha#75  <<< CHANGED (ADV 달러, 불리언 캐스팅)
    def alpha075(self):
        adv50 = adv(self.close, self.volume, 50)
        w_left  = floor_window(4.24304)
        w_right = floor_window(12.4413)
        left  = correlation(self.vwap, self.volume, w_left)
        right = correlation(rank(self.low), rank(adv50), w_right)
        left  = safe_clean(left)
        right = safe_clean(right)
        signal = (rank(left) < rank(right)).astype(int) * -1
        # signal = signal.shift(1)
        return signal.fillna(0)

    # Alpha#77
    def alpha077(self):
        adv40 = adv(self.close, self.volume, 40)
        p1 = rank(decay_linear(((((self.high + self.low) / 2) + self.high) -
                                 (self.vwap + self.high)).to_frame(),
                               floor_window(20.0451)).iloc[:, 0])
        p2 = rank(decay_linear(correlation(((self.high + self.low) / 2),
                                           adv40,
                                           floor_window(3.1614)).to_frame(),
                               floor_window(5.64125)).iloc[:, 0])
        result = pd.Series(index=self.close.index)
        result[p1 <= p2] = p1[p1 <= p2]
        result[p2 < p1] = p2[p2 < p1]
        return result

    # Alpha#78
    def alpha078(self):
        adv40 = adv(self.close, self.volume, 40)
        return (rank(correlation(ts_sum(((self.low * 0.352233) + (self.vwap * (1 - 0.352233))),
                                        floor_window(19.7428)),
                                 ts_sum(adv40, floor_window(19.7428)),
                                 floor_window(6.83313))).pow(
                    rank(correlation(rank(self.vwap), rank(self.volume), floor_window(5.77492)))))

    # Alpha#81
    def alpha081(self):
        adv10 = adv(self.close, self.volume, 10)
        return ((rank(log(product(rank((rank(correlation(self.vwap,
                                                         ts_sum(adv10, floor_window(49.6054)),
                                                         floor_window(8.47743))).pow(4))),
                                     floor_window(14.9655)))) <
                 rank(correlation(rank(self.vwap), rank(self.volume), floor_window(5.07914)))) * -1)

    # Alpha#83
    def alpha083(self):
        return ((rank(delay(((self.high - self.low) / (ts_sum(self.close, 5) / 5)), 2)) *
                 rank(rank(self.volume))) /
                (((self.high - self.low) / (ts_sum(self.close, 5) / 5)) / (self.vwap - self.close)))

    # Alpha#84
    def alpha084(self):
        return pow(ts_rank((self.vwap - ts_max(self.vwap, floor_window(15.3217))),
                           floor_window(20.7127)),
                   delta(self.close, floor_window(4.96796)))

    # Alpha#85
    def alpha085(self):
        adv30 = adv(self.close, self.volume, 30)
        return (rank(correlation(((self.high * 0.876703) + (self.close * (1 - 0.876703))),
                                 adv30,
                                 floor_window(9.61331))).pow(
                rank(correlation(ts_rank(((self.high + self.low) / 2), floor_window(3.70596)),
                                 ts_rank(self.volume, floor_window(10.1595)),
                                 floor_window(7.11408)))))

    # Alpha#86
    def alpha086(self):
        adv20 = adv(self.close, self.volume, 20)
        return ((ts_rank(correlation(self.close,
                                     sma(adv20, floor_window(14.7444)+1),
                                     floor_window(6.00049)),
                         floor_window(20.4195)) <
                 rank(((self.open + self.close) - (self.vwap + self.open)))) * -1)

    # Alpha#88
    def alpha088(self):
        adv60 = adv(self.close, self.volume, 60)
        p1 = rank(decay_linear(((rank(self.open) + rank(self.low)) - (rank(self.high) + rank(self.close))).to_frame(),
                               floor_window(8.06882)).iloc[:, 0])
        p2 = ts_rank(decay_linear(correlation(ts_rank(self.close, floor_window(8.44728)),
                                              ts_rank(adv60, floor_window(20.6966)),
                                              floor_window(8.01266)).to_frame(),
                                  floor_window(6.65053)).iloc[:, 0],
                     floor_window(2.61957))
        result = pd.Series(index=self.close.index)
        result[p1 <= p2] = p1[p1 <= p2]
        result[p2 < p1] = p2[p2 < p1]
        return result

    # Alpha#92
    def alpha092(self):
        adv30 = adv(self.close, self.volume, 30)
        p1 = ts_rank(decay_linear(((((self.high + self.low) / 2) + self.close) < (self.low + self.open)).to_frame(),
                                  floor_window(14.7221)).iloc[:, 0],
                     floor_window(18.8683))
        p2 = ts_rank(decay_linear(correlation(rank(self.low), rank(adv30), floor_window(7.58555)).to_frame(),
                                  floor_window(6.94024)).iloc[:, 0],
                     floor_window(6.80584))
        result = pd.Series(index=self.close.index)
        result[p1 <= p2] = p1[p1 <= p2]
        result[p2 < p1] = p2[p2 < p1]
        return result

    # Alpha#94
    def alpha094(self):
        adv60 = adv(self.close, self.volume, 60)
        return (rank((self.vwap - ts_min(self.vwap, floor_window(11.5783)))).pow(
                    ts_rank(correlation(ts_rank(self.vwap, floor_window(19.6462)),
                                        ts_rank(adv60, floor_window(4.02992)),
                                        floor_window(18.0926)),
                            floor_window(2.70756))) * -1)

    # Alpha#95
    def alpha095(self):
        adv40 = adv(self.close, self.volume, 40)
        return (rank((self.open - ts_min(self.open, floor_window(12.4105)))) <
                ts_rank((rank(correlation(sma(((self.high + self.low) / 2),
                                              floor_window(19.1351)),
                                             sma(adv40, floor_window(19.1351)),
                                             floor_window(12.8742))).pow(5)),
                        floor_window(11.7584)))

    # Alpha#96
    def alpha096(self):
        adv60 = adv(self.close, self.volume, 60)
        p1 = ts_rank(decay_linear(correlation(rank(self.vwap), rank(self.volume), floor_window(3.83878)).to_frame(),
                                  floor_window(4.16783)).iloc[:, 0],
                     floor_window(8.38151))
        p2 = ts_rank(decay_linear(ts_argmax(correlation(ts_rank(self.close, floor_window(7.45404)),
                                                        ts_rank(adv60, floor_window(4.13242)),
                                                        floor_window(3.65459)),
                                            floor_window(12.6556)).to_frame(),
                                  floor_window(14.0365)).iloc[:, 0],
                     floor_window(13.4143))
        result = pd.Series(index=self.close.index)
        result[p1 >= p2] = p1[p1 >= p2]
        result[p2 > p1] = p2[p2 > p1]
        return -1 * result

    # Alpha#98
    def alpha098(self):
        adv5 = adv(self.close, self.volume, 5)
        adv15 = adv(self.close, self.volume, 15)
        return (rank(decay_linear(correlation(self.vwap,
                                              sma(adv5, floor_window(26.4719)+1),
                                              floor_window(4.58418)).to_frame(),
                                  floor_window(7.18088)).iloc[:, 0])) - \
               (rank(decay_linear(ts_rank(ts_argmin(correlation(rank(self.open),
                                                                 rank(adv15),
                                                                 floor_window(20.8187)),
                                                     floor_window(8.62571)),
                                           floor_window(6.95668)).to_frame(),
                                  floor_window(8.07206)).iloc[:, 0]))

    # Alpha#99  <<< CHANGED (ADV 달러, sum(adv60,k), 불리언 캐스팅)
    def alpha099(self):
        adv60 = adv(self.close, self.volume, 60)
        p  = floor_window(19.8975)
        w1 = floor_window(8.8136)
        w2 = floor_window(6.28259)
        avg_price = (self.high + self.low) / 2
        A = correlation(ts_sum(avg_price, p), ts_sum(adv60, p), w1)
        B = correlation(self.low, self.volume, w2)
        A = safe_clean(A)
        B = safe_clean(B)
        signal = (rank(A) < rank(B)).astype(int) * -1
        # signal = signal.shift(1)
        return signal.fillna(0)

    # Alpha#101
    def alpha101(self):
        return (self.close - self.open) / ((self.high - self.low) + 0.001)
