#!/usr/bin/env python3
"""
量化交易信号生成器
基于7大技术指标生成综合交易信号，包含置信度评分和风险管理建议
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import os


class SignalType(Enum):
    """交易信号类型"""
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    NEUTRAL = "中性"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"


@dataclass
class SignalComponent:
    """单个指标的信号组件"""
    name: str
    signal: SignalType
    weight: float
    value: float
    threshold: str
    reasoning: str


@dataclass
class TradingSignal:
    """综合交易信号"""
    symbol: str
    timestamp: pd.Timestamp
    signal: SignalType
    confidence: float  # 0-100
    components: List[SignalComponent] = field(default_factory=list)
    price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'timestamp': str(self.timestamp),
            'signal': self.signal.value,
            'confidence': round(self.confidence, 1),
            'price': self.price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_reward': self.risk_reward,
            'components': [
                {
                    'name': c.name,
                    'signal': c.signal.value,
                    'value': round(c.value, 2),
                    'reasoning': c.reasoning
                }
                for c in self.components
            ]
        }


class TechnicalIndicatorCalculator:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """计算简单移动平均线"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """计算指数移动平均线"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        计算相对强弱指数(RSI)
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标
        
        Returns:
            macd_line: MACD线 (快EMA - 慢EMA)
            signal_line: 信号线 (MACD的EMA)
            histogram: MACD柱状图 (MACD - Signal)
        """
        ema_fast = TechnicalIndicatorCalculator.calculate_ema(data, fast)
        ema_slow = TechnicalIndicatorCalculator.calculate_ema(data, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicatorCalculator.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算布林带
        
        Returns:
            upper: 上轨
            middle: 中轨(SMA)
            lower: 下轨
        """
        middle = TechnicalIndicatorCalculator.calculate_sma(data, period)
        std = data.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """计算平均真实波幅(ATR)"""
        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        计算随机指标(Stochastic Oscillator)
        
        Returns:
            k: %K线
            d: %D线(%K的SMA)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        
        return k, d
    
    @staticmethod
    def calculate_adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算平均趋向指数(ADX)
        
        Returns:
            adx: ADX线
            plus_di: +DI线
            minus_di: -DI线
        """
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # 计算方向移动
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # 计算DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # 计算DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def calculate_all_indicators(
        df: pd.DataFrame,
        params: Dict[str, Any] = None
    ) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            df: DataFrame包含列: open, high, low, close, volume
            params: 可选的指标参数
            
        Returns:
            添加所有指标的DataFrame
        """
        params = params or {}
        result = df.copy()
        
        # 确保数据按时间升序排列（用于计算指标）
        result_sorted = result.sort_index(ascending=True)
        
        # 价格数据
        close = result_sorted['close']
        high = result_sorted['high']
        low = result_sorted['low']
        volume = result_sorted['volume']
        
        # 移动平均线
        result_sorted['sma_20'] = TechnicalIndicatorCalculator.calculate_sma(close, 20)
        result_sorted['sma_50'] = TechnicalIndicatorCalculator.calculate_sma(close, 50)
        result_sorted['sma_200'] = TechnicalIndicatorCalculator.calculate_sma(close, 200)
        
        # RSI
        rsi_period = params.get('rsi_period', 14)
        result_sorted['rsi'] = TechnicalIndicatorCalculator.calculate_rsi(close, rsi_period)
        
        # MACD
        macd_fast = params.get('macd_fast', 12)
        macd_slow = params.get('macd_slow', 26)
        macd_signal = params.get('macd_signal', 9)
        result_sorted['macd'], result_sorted['macd_signal'], result_sorted['macd_hist'] = \
            TechnicalIndicatorCalculator.calculate_macd(close, macd_fast, macd_slow, macd_signal)
        
        # 布林带
        bb_period = params.get('bb_period', 20)
        bb_std = params.get('bb_std', 2.0)
        result_sorted['bb_upper'], result_sorted['bb_middle'], result_sorted['bb_lower'] = \
            TechnicalIndicatorCalculator.calculate_bollinger_bands(close, bb_period, bb_std)
        result_sorted['bb_width'] = (result_sorted['bb_upper'] - result_sorted['bb_lower']) / result_sorted['bb_middle']
        result_sorted['bb_pct'] = (close - result_sorted['bb_lower']) / (result_sorted['bb_upper'] - result_sorted['bb_lower'])
        
        # ATR
        atr_period = params.get('atr_period', 14)
        result_sorted['atr'] = TechnicalIndicatorCalculator.calculate_atr(high, low, close, atr_period)
        result_sorted['atr_pct'] = result_sorted['atr'] / close * 100
        
        # 随机指标
        stoch_k = params.get('stoch_k', 14)
        stoch_d = params.get('stoch_d', 3)
        result_sorted['stoch_k'], result_sorted['stoch_d'] = \
            TechnicalIndicatorCalculator.calculate_stochastic(high, low, close, stoch_k, stoch_d)
        
        # 成交量指标
        result_sorted['volume_sma'] = TechnicalIndicatorCalculator.calculate_sma(volume, 20)
        result_sorted['volume_ratio'] = volume / result_sorted['volume_sma']
        
        # ADX
        adx_period = params.get('adx_period', 14)
        result_sorted['adx'], result_sorted['plus_di'], result_sorted['minus_di'] = \
            TechnicalIndicatorCalculator.calculate_adx(high, low, close, adx_period)
        
        # 价格变化
        result_sorted['change_1d'] = close.pct_change() * 100
        
        # 按时间降序排列返回（最新数据在前）
        return result_sorted.sort_index(ascending=False)


class TradingSignalGenerator:
    """交易信号生成器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化信号生成器
        
        Args:
            config_path: 配置文件路径（可选）
        """
        self.params = self._load_config(config_path)
        self.weights = self._get_weights()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'rsi': {'period': 14, 'oversold': 30, 'overbought': 70},
            'macd': {'fast': 12, 'slow': 26, 'signal': 9},
            'bollinger': {'period': 20, 'std_dev': 2.0},
            'stochastic': {'k_period': 14, 'd_period': 3, 'overbought': 80, 'oversold': 20},
            'atr': {'period': 14, 'multiplier': 2.0},
            'adx': {'period': 14, 'trend_threshold': 25},
            'signals': {
                'weights': {
                    'rsi': 1.0,
                    'macd': 1.0,
                    'bollinger': 1.0,
                    'trend': 1.0,
                    'volume': 0.5,
                    'stochastic': 0.5,
                    'adx': 0.5
                },
                'risk': {
                    'atr_multiplier': 2.0,
                    'risk_reward_target': 2.0
                }
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    custom_config = yaml.safe_load(f)
                    # 合并配置
                    for key, value in custom_config.items():
                        if key in default_config:
                            if isinstance(default_config[key], dict) and isinstance(value, dict):
                                default_config[key].update(value)
                            else:
                                default_config[key] = value
                        else:
                            default_config[key] = value
            except Exception as e:
                print(f"[WARN] 配置文件加载失败，使用默认配置: {e}")
        
        return default_config
    
    def _get_weights(self) -> Dict[str, float]:
        """获取指标权重"""
        return self.params.get('signals', {}).get('weights', {
            'rsi': 1.0,
            'macd': 1.0,
            'bollinger': 1.0,
            'trend': 1.0,
            'volume': 0.5,
            'stochastic': 0.5,
            'adx': 0.5
        })
    
    def _signal_to_score(self, signal: SignalType) -> float:
        """将信号转换为数值分数（-2到+2）"""
        mapping = {
            SignalType.STRONG_BUY: 2,
            SignalType.BUY: 1,
            SignalType.NEUTRAL: 0,
            SignalType.SELL: -1,
            SignalType.STRONG_SELL: -2,
        }
        return mapping[signal]
    
    def _score_to_signal(self, score: float) -> SignalType:
        """将数值分数转换为信号"""
        if score >= 1.5:
            return SignalType.STRONG_BUY
        elif score >= 0.5:
            return SignalType.BUY
        elif score <= -1.5:
            return SignalType.STRONG_SELL
        elif score <= -0.5:
            return SignalType.SELL
        else:
            return SignalType.NEUTRAL
    
    def analyze_rsi(self, row: pd.Series) -> SignalComponent:
        """分析RSI指标"""
        rsi = row.get('rsi', np.nan)
        rsi_config = self.params.get('rsi', {})
        oversold = rsi_config.get('oversold', 30)
        overbought = rsi_config.get('overbought', 70)
        
        if pd.isna(rsi):
            return SignalComponent(
                name='RSI',
                signal=SignalType.NEUTRAL,
                weight=self.weights['rsi'],
                value=50,
                threshold=f'{oversold}/{overbought}',
                reasoning='数据不足'
            )
        
        if rsi < oversold:
            signal = SignalType.STRONG_BUY
            reasoning = f'超卖区域({rsi:.1f} < {oversold})'
        elif rsi < 40:
            signal = SignalType.BUY
            reasoning = f'接近超卖({rsi:.1f})'
        elif rsi > overbought:
            signal = SignalType.STRONG_SELL
            reasoning = f'超买区域({rsi:.1f} > {overbought})'
        elif rsi > 60:
            signal = SignalType.SELL
            reasoning = f'接近超买({rsi:.1f})'
        else:
            signal = SignalType.NEUTRAL
            reasoning = f'中性区域({rsi:.1f})'
        
        return SignalComponent(
            name='RSI',
            signal=signal,
            weight=self.weights['rsi'],
            value=rsi,
            threshold=f'{oversold}/{overbought}',
            reasoning=reasoning
        )
    
    def analyze_macd(self, row: pd.Series, prev_row: pd.Series = None) -> SignalComponent:
        """分析MACD指标"""
        macd = row.get('macd', np.nan)
        signal_line = row.get('macd_signal', np.nan)
        histogram = row.get('macd_hist', np.nan)
        
        if pd.isna(macd) or pd.isna(signal_line):
            return SignalComponent(
                name='MACD',
                signal=SignalType.NEUTRAL,
                weight=self.weights['macd'],
                value=0,
                threshold='交叉',
                reasoning='数据不足'
            )
        
        # 检查交叉
        crossover = False
        if prev_row is not None and not pd.isna(prev_row.get('macd', np.nan)):
            prev_above = prev_row['macd'] > prev_row['macd_signal']
            curr_above = macd > signal_line
            crossover = prev_above != curr_above
        
        if macd > signal_line and histogram > 0:
            if crossover:
                signal = SignalType.STRONG_BUY
                reasoning = '金叉，正向动能'
            else:
                signal = SignalType.BUY
                reasoning = 'MACD在信号线上方，正向动能'
        elif macd < signal_line and histogram < 0:
            if crossover:
                signal = SignalType.STRONG_SELL
                reasoning = '死叉，负向动能'
            else:
                signal = SignalType.SELL
                reasoning = 'MACD在信号线下方，负向动能'
        else:
            signal = SignalType.NEUTRAL
            reasoning = 'MACD信号不明确'
        
        return SignalComponent(
            name='MACD',
            signal=signal,
            weight=self.weights['macd'],
            value=histogram,
            threshold='交叉',
            reasoning=reasoning
        )
    
    def analyze_bollinger(self, row: pd.Series) -> SignalComponent:
        """分析布林带指标"""
        bb_pct = row.get('bb_pct', np.nan)
        close = row['close']
        bb_upper = row.get('bb_upper', close)
        bb_lower = row.get('bb_lower', close)
        
        if pd.isna(bb_pct):
            return SignalComponent(
                name='布林带',
                signal=SignalType.NEUTRAL,
                weight=self.weights['bollinger'],
                value=0.5,
                threshold='0.0/1.0',
                reasoning='数据不足'
            )
        
        if bb_pct < 0:
            signal = SignalType.STRONG_BUY
            reasoning = f'价格低于下轨({close:.2f} < {bb_lower:.2f})'
        elif bb_pct < 0.2:
            signal = SignalType.BUY
            reasoning = f'接近下轨(%B = {bb_pct:.2f})'
        elif bb_pct > 1:
            signal = SignalType.STRONG_SELL
            reasoning = f'价格高于上轨({close:.2f} > {bb_upper:.2f})'
        elif bb_pct > 0.8:
            signal = SignalType.SELL
            reasoning = f'接近上轨(%B = {bb_pct:.2f})'
        else:
            signal = SignalType.NEUTRAL
            reasoning = f'在布林带中间(%B = {bb_pct:.2f})'
        
        return SignalComponent(
            name='布林带',
            signal=signal,
            weight=self.weights['bollinger'],
            value=bb_pct,
            threshold='0.0/1.0',
            reasoning=reasoning
        )
    
    def analyze_trend(self, row: pd.Series) -> SignalComponent:
        """分析趋势指标"""
        close = row['close']
        sma_20 = row.get('sma_20', np.nan)
        sma_50 = row.get('sma_50', np.nan)
        sma_200 = row.get('sma_200', np.nan)
        
        if pd.isna(sma_20) or pd.isna(sma_50):
            return SignalComponent(
                name='趋势',
                signal=SignalType.NEUTRAL,
                weight=self.weights['trend'],
                value=0,
                threshold='均线交叉',
                reasoning='数据不足'
            )
        
        # 统计看涨条件
        bullish = 0
        bearish = 0
        
        if close > sma_20:
            bullish += 1
        else:
            bearish += 1
        
        if close > sma_50:
            bullish += 1
        else:
            bearish += 1
        
        if not pd.isna(sma_200):
            if close > sma_200:
                bullish += 1
            else:
                bearish += 1
            
            if sma_50 > sma_200:
                bullish += 1
            else:
                bearish += 1
        
        score = bullish - bearish
        
        if score >= 3:
            signal = SignalType.STRONG_BUY
            reasoning = '强势上涨：价格在所有均线上方，金叉形态'
        elif score >= 1:
            signal = SignalType.BUY
            reasoning = '上涨趋势：价格在关键均线上方'
        elif score <= -3:
            signal = SignalType.STRONG_SELL
            reasoning = '强势下跌：价格在所有均线下方，死叉形态'
        elif score <= -1:
            signal = SignalType.SELL
            reasoning = '下跌趋势：价格在关键均线下方'
        else:
            signal = SignalType.NEUTRAL
            reasoning = '趋势信号混合'
        
        return SignalComponent(
            name='趋势',
            signal=signal,
            weight=self.weights['trend'],
            value=score,
            threshold='均线交叉',
            reasoning=reasoning
        )
    
    def analyze_volume(self, row: pd.Series) -> SignalComponent:
        """分析成交量指标"""
        volume_ratio = row.get('volume_ratio', np.nan)
        
        if pd.isna(volume_ratio):
            return SignalComponent(
                name='成交量',
                signal=SignalType.NEUTRAL,
                weight=self.weights['volume'],
                value=1.0,
                threshold='1.5x平均',
                reasoning='数据不足'
            )
        
        change = row.get('change_1d', 0)
        
        if volume_ratio > 2.0:
            if change > 0:
                signal = SignalType.STRONG_BUY
                reasoning = f'放量上涨({volume_ratio:.1f}x)'
            else:
                signal = SignalType.STRONG_SELL
                reasoning = f'放量下跌({volume_ratio:.1f}x)'
        elif volume_ratio > 1.5:
            if change > 0:
                signal = SignalType.BUY
                reasoning = f'成交量放大({volume_ratio:.1f}x)配合上涨'
            else:
                signal = SignalType.SELL
                reasoning = f'成交量放大({volume_ratio:.1f}x)配合下跌'
        else:
            signal = SignalType.NEUTRAL
            reasoning = f'成交量正常({volume_ratio:.1f}x平均)'
        
        return SignalComponent(
            name='成交量',
            signal=signal,
            weight=self.weights['volume'],
            value=volume_ratio,
            threshold='1.5x平均',
            reasoning=reasoning
        )
    
    def analyze_stochastic(self, row: pd.Series) -> SignalComponent:
        """分析随机指标"""
        k = row.get('stoch_k', np.nan)
        d = row.get('stoch_d', np.nan)
        stoch_config = self.params.get('stochastic', {})
        oversold = stoch_config.get('oversold', 20)
        overbought = stoch_config.get('overbought', 80)
        
        if pd.isna(k) or pd.isna(d):
            return SignalComponent(
                name='随机指标',
                signal=SignalType.NEUTRAL,
                weight=self.weights['stochastic'],
                value=50,
                threshold=f'{oversold}/{overbought}',
                reasoning='数据不足'
            )
        
        if k < oversold and d < oversold:
            signal = SignalType.STRONG_BUY
            reasoning = f'超卖(%K={k:.1f}, %D={d:.1f})'
        elif k < 30:
            signal = SignalType.BUY
            reasoning = f'接近超卖(%K={k:.1f})'
        elif k > overbought and d > overbought:
            signal = SignalType.STRONG_SELL
            reasoning = f'超买(%K={k:.1f}, %D={d:.1f})'
        elif k > 70:
            signal = SignalType.SELL
            reasoning = f'接近超买(%K={k:.1f})'
        else:
            signal = SignalType.NEUTRAL
            reasoning = f'中性区域(%K={k:.1f})'
        
        return SignalComponent(
            name='随机指标',
            signal=signal,
            weight=self.weights['stochastic'],
            value=k,
            threshold=f'{oversold}/{overbought}',
            reasoning=reasoning
        )
    
    def analyze_adx(self, row: pd.Series) -> SignalComponent:
        """分析ADX指标"""
        adx = row.get('adx', np.nan)
        plus_di = row.get('plus_di', np.nan)
        minus_di = row.get('minus_di', np.nan)
        adx_config = self.params.get('adx', {})
        trend_threshold = adx_config.get('trend_threshold', 25)
        
        if pd.isna(adx):
            return SignalComponent(
                name='ADX',
                signal=SignalType.NEUTRAL,
                weight=self.weights['adx'],
                value=20,
                threshold=f'{trend_threshold}趋势阈值',
                reasoning='数据不足'
            )
        
        if adx < 20:
            signal = SignalType.NEUTRAL
            reasoning = f'无明确趋势(ADX={adx:.1f})'
        elif adx < trend_threshold:
            if plus_di > minus_di:
                signal = SignalType.BUY
                reasoning = f'上涨趋势形成中(ADX={adx:.1f}, +DI>-DI)'
            else:
                signal = SignalType.SELL
                reasoning = f'下跌趋势形成中(ADX={adx:.1f}, -DI>+DI)'
        else:
            if plus_di > minus_di:
                signal = SignalType.STRONG_BUY if adx > 40 else SignalType.BUY
                reasoning = f'强势上涨(ADX={adx:.1f}, +DI={plus_di:.1f})'
            else:
                signal = SignalType.STRONG_SELL if adx > 40 else SignalType.SELL
                reasoning = f'强势下跌(ADX={adx:.1f}, -DI={minus_di:.1f})'
        
        return SignalComponent(
            name='ADX',
            signal=signal,
            weight=self.weights['adx'],
            value=adx,
            threshold=f'{trend_threshold}趋势阈值',
            reasoning=reasoning
        )
    
    def calculate_risk_levels(
        self,
        price: float,
        signal: SignalType,
        atr: float
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算止损和止盈价位
        
        Args:
            price: 当前价格
            signal: 交易信号
            atr: 平均真实波幅
            
        Returns:
            (止损价, 止盈价, 风险回报比)
        """
        risk_config = self.params.get('signals', {}).get('risk', {})
        atr_multiplier = risk_config.get('atr_multiplier', 2.0)
        risk_reward_target = risk_config.get('risk_reward_target', 2.0)
        
        if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
            stop_loss = price - (atr * atr_multiplier)
            take_profit = price + (atr * atr_multiplier * risk_reward_target)
        elif signal in [SignalType.STRONG_SELL, SignalType.SELL]:
            stop_loss = price + (atr * atr_multiplier)
            take_profit = price - (atr * atr_multiplier * risk_reward_target)
        else:
            stop_loss = None
            take_profit = None
        
        risk_reward = risk_reward_target if stop_loss else None
        
        return stop_loss, take_profit, risk_reward
    
    def generate_signal(
        self,
        kline_data: pd.DataFrame,
        stock_code: str,
        stock_name: str
    ) -> TradingSignal:
        """
        生成综合交易信号
        
        Args:
            kline_data: K线数据DataFrame（降序排列，最新在前）
            stock_code: 股票代码
            stock_name: 股票名称
            
        Returns:
            综合交易信号
        """
        # 计算所有技术指标
        df_with_indicators = TechnicalIndicatorCalculator.calculate_all_indicators(kline_data, self.params)
        
        row = df_with_indicators.iloc[0]  # 最新数据
        prev_row = df_with_indicators.iloc[1] if len(df_with_indicators) > 1 else None
        
        # 分析每个指标
        components = [
            self.analyze_rsi(row),
            self.analyze_macd(row, prev_row),
            self.analyze_bollinger(row),
            self.analyze_trend(row),
            self.analyze_volume(row),
            self.analyze_stochastic(row),
            self.analyze_adx(row),
        ]
        
        # 计算加权得分
        total_weight = sum(c.weight for c in components)
        weighted_score = sum(
            self._signal_to_score(c.signal) * c.weight
            for c in components
        ) / total_weight
        
        # 转换为综合信号
        composite_signal = self._score_to_signal(weighted_score)
        
        # 计算置信度（0-100）
        scores = [self._signal_to_score(c.signal) for c in components]
        agreement = 1 - (np.std(scores) / 2)  # 0到1
        strength = abs(weighted_score) / 2  # 0到1
        confidence = min(100, (agreement * 0.5 + strength * 0.5) * 100)
        
        # 计算风险水平
        atr = row.get('atr', 0)
        stop_loss, take_profit, risk_reward = self.calculate_risk_levels(
            row['close'], composite_signal, atr
        )
        
        symbol = f"{stock_name}({stock_code})"
        
        return TradingSignal(
            symbol=symbol,
            timestamp=df_with_indicators.index[0],
            signal=composite_signal,
            confidence=confidence,
            components=components,
            price=row['close'],
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward
        )
    
    def format_signal_for_analysis(self, signal: TradingSignal) -> str:
        """
        格式化交易信号用于AI分析
        
        Args:
            signal: 交易信号
            
        Returns:
            格式化的信号文本
        """
        lines = [
            "## 量化交易信号分析",
            "",
            f"**综合信号**：{signal.signal.value}",
            f"**置信度**：{signal.confidence:.1f}%",
            f"**当前价格**：{signal.price:.2f}元",
            ""
        ]
        
        # 风险管理
        if signal.stop_loss and signal.take_profit:
            lines.extend([
                "### 风险管理建议",
                f"- **止损位**：{signal.stop_loss:.2f}元 ({abs(signal.stop_loss/signal.price-1)*100:.2f}%)",
                f"- **止盈位**：{signal.take_profit:.2f}元 ({abs(signal.take_profit/signal.price-1)*100:.2f}%)",
                f"- **风险回报比**：1:{signal.risk_reward:.1f}",
                ""
            ])
        
        # 信号组成
        lines.append("### 各指标信号组成")
        for comp in signal.components:
            lines.append(f"- **{comp.name}**：{comp.signal.value} ({comp.value:.2f})")
            lines.append(f"  - 推理：{comp.reasoning}")
        
        lines.append("")
        
        # 信号解读
        confidence_level = "高" if signal.confidence >= 70 else "中" if signal.confidence >= 50 else "低"
        
        lines.extend([
            "### 信号解读",
            f"**置信度评级**：{confidence_level}({signal.confidence:.1f}%)",
            ""
        ])
        
        if signal.signal in [SignalType.STRONG_BUY, SignalType.BUY]:
            lines.extend([
                f"当前{signal.signal.value}信号来自多个技术指标的共振：",
                "- 看涨指标数量较多，形成买入合力",
                "- 建议关注回调后的买入机会",
                "- 严格执行止损纪律，控制下行风险"
            ])
        elif signal.signal in [SignalType.STRONG_SELL, SignalType.SELL]:
            lines.extend([
                f"当前{signal.signal.value}信号来自多个技术指标的共振：",
                "- 看跌指标数量较多，形成卖出合力",
                "- 建议减仓或空仓观望",
                "- 严格风控，避免逆势操作"
            ])
        else:
            lines.extend([
                "当前中性信号，技术指标方向不明确：",
                "- 多空指标相互抵消，缺乏明确方向",
                "- 建议观望，等待更明确的信号",
                "- 可结合基本面分析做出投资决策"
            ])
        
        lines.append("")
        lines.extend([
            "**风险提示**：",
            "- 技术信号仅供参考，不构成投资建议",
            "- 实际操作需结合市场环境和风险偏好",
            "- 建议做好仓位管理和止损纪律",
            "- 投资有风险，入市需谨慎"
        ])
        
        return "\n".join(lines)
