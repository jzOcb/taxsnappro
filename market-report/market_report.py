#!/usr/bin/env python3
"""
US Stock Market Report Generator

Generates comprehensive market reports covering:
- Major indices (S&P 500, Nasdaq, Dow, Russell 2000)
- Sector performance (XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLRE, XLB, XLC)
- Top movers in major stocks
- Market breadth indicators
- Key macro signals (VIX, DXY, Gold, Oil, 10Y yield)

Usage:
    python3 market_report.py                    # Full report to stdout
    python3 market_report.py --output /tmp/report.txt  # Save to file
    python3 market_report.py --alert-only       # Only output if significant moves detected
    python3 market_report.py --json             # JSON output for programmatic use
"""

import yfinance as yf
import json
import sys
import os
from datetime import datetime, timedelta, timezone
import argparse

# === Configuration ===

INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
    "^RUT": "Russell 2000",
}

SECTORS = {
    "XLK": "科技",
    "XLF": "金融",
    "XLE": "能源",
    "XLV": "医疗",
    "XLY": "消费可选",
    "XLP": "消费必需",
    "XLI": "工业",
    "XLU": "公用事业",
    "XLRE": "房地产",
    "XLB": "材料",
    "XLC": "通信",
}

MACRO = {
    "^VIX": "VIX恐慌指数",
    "GC=F": "黄金",
    "CL=F": "原油WTI",
    "^TNX": "10Y国债",
    "DX-Y.NYB": "美元指数",
    "BTC-USD": "比特币",
}

# Mag7 + key stocks to track
WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",  # Mag7
    "TSM", "AMD", "LMND", "RKLB", "VOO",  # Jason's portfolio
    "PLTR", "CRM", "NOW", "WDAY",  # Software/AI
    "JPM", "GS", "WFC",  # Banks
    "WMT", "COST",  # Retail
    "NVO", "LLY", "MRK",  # Pharma
    "COIN", "MSTR",  # Crypto-adjacent
    "OXY", "OPEN",  # Jason's smaller positions
]

# Alert thresholds
ALERT_THRESHOLDS = {
    "index_move_pct": 1.5,      # Index moves > 1.5%
    "vix_level": 25,            # VIX above 25
    "vix_spike_pct": 15,        # VIX daily spike > 15%
    "stock_move_pct": 8,        # Individual stock > 8%
    "sector_move_pct": 3,       # Sector ETF > 3%
}


def get_quote_data(tickers_list):
    """Fetch current quotes for a list of tickers."""
    results = {}
    try:
        tickers_str = " ".join(tickers_list)
        tickers = yf.Tickers(tickers_str)
        for symbol in tickers_list:
            try:
                t = tickers.tickers[symbol]
                info = t.fast_info
                price = getattr(info, 'last_price', None)
                prev_close = getattr(info, 'previous_close', None)
                
                if price and prev_close and prev_close > 0:
                    change_pct = ((price - prev_close) / prev_close) * 100
                else:
                    # Fallback to history
                    hist = t.history(period="2d")
                    if len(hist) >= 2:
                        price = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2]
                        change_pct = ((price - prev_close) / prev_close) * 100
                    elif len(hist) == 1:
                        price = hist['Close'].iloc[-1]
                        change_pct = 0
                    else:
                        continue
                
                results[symbol] = {
                    "price": round(float(price), 2),
                    "prev_close": round(float(prev_close), 2) if prev_close else None,
                    "change_pct": round(float(change_pct), 2),
                }
            except Exception as e:
                pass  # Skip failed tickers silently
    except Exception as e:
        print(f"Error fetching batch: {e}", file=sys.stderr)
    
    return results


def check_alerts(indices_data, sectors_data, macro_data, watchlist_data):
    """Check for significant market events that warrant an alert."""
    alerts = []
    
    # Check index moves
    for symbol, data in indices_data.items():
        name = INDICES.get(symbol, symbol)
        if abs(data["change_pct"]) >= ALERT_THRESHOLDS["index_move_pct"]:
            direction = "暴涨" if data["change_pct"] > 0 else "暴跌"
            alerts.append(f"🚨 {name} {direction} {data['change_pct']:+.1f}%")
    
    # Check VIX
    if "^VIX" in macro_data:
        vix = macro_data["^VIX"]
        if vix["price"] >= ALERT_THRESHOLDS["vix_level"]:
            alerts.append(f"🚨 VIX 恐慌指数飙升至 {vix['price']:.1f}")
        if abs(vix["change_pct"]) >= ALERT_THRESHOLDS["vix_spike_pct"]:
            alerts.append(f"🚨 VIX 日内变动 {vix['change_pct']:+.1f}%")
    
    # Check sector moves
    for symbol, data in sectors_data.items():
        name = SECTORS.get(symbol, symbol)
        if abs(data["change_pct"]) >= ALERT_THRESHOLDS["sector_move_pct"]:
            direction = "大涨" if data["change_pct"] > 0 else "大跌"
            alerts.append(f"⚠️ {name}板块 {direction} {data['change_pct']:+.1f}%")
    
    # Check individual stock moves
    for symbol, data in watchlist_data.items():
        if abs(data["change_pct"]) >= ALERT_THRESHOLDS["stock_move_pct"]:
            direction = "飙升" if data["change_pct"] > 0 else "暴跌"
            alerts.append(f"⚠️ {symbol} {direction} {data['change_pct']:+.1f}% (${data['price']})")
    
    return alerts


def compute_technicals(symbol, name, period="3mo"):
    """Compute technical analysis: support, resistance, trend, RSI, moving averages."""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period=period)
        if hist.empty or len(hist) < 20:
            return None

        closes = hist['Close'].values
        highs = hist['High'].values
        lows = hist['Low'].values
        volumes = hist['Volume'].values
        current = closes[-1]

        # --- Moving Averages ---
        sma20 = float(closes[-20:].mean()) if len(closes) >= 20 else None
        sma50 = float(closes[-50:].mean()) if len(closes) >= 50 else None
        sma200 = float(closes[-200:].mean()) if len(closes) >= 200 else None
        ema9 = None
        if len(closes) >= 9:
            ema = [float(closes[0])]
            mult = 2.0 / (9 + 1)
            for c in closes[1:]:
                ema.append(float(c) * mult + ema[-1] * (1 - mult))
            ema9 = ema[-1]

        # --- RSI (14-day) ---
        rsi = None
        if len(closes) >= 15:
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            gains = [d if d > 0 else 0 for d in deltas[-14:]]
            losses = [-d if d < 0 else 0 for d in deltas[-14:]]
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100

        # --- Support & Resistance (pivot-based + recent swing highs/lows) ---
        # Find recent swing highs and lows (last 20 bars)
        window = min(20, len(closes))
        recent_closes = closes[-window:]
        recent_highs = highs[-window:]
        recent_lows = lows[-window:]

        # Swing highs: local maxima
        swing_highs = []
        for i in range(1, len(recent_highs) - 1):
            if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i+1]:
                swing_highs.append(float(recent_highs[i]))

        # Swing lows: local minima
        swing_lows = []
        for i in range(1, len(recent_lows) - 1):
            if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i+1]:
                swing_lows.append(float(recent_lows[i]))

        # Key levels: 52-week high/low, recent swing levels
        high_52w = float(max(highs)) if len(highs) >= 50 else float(max(recent_highs))
        low_52w = float(min(lows)) if len(lows) >= 50 else float(min(recent_lows))

        # Resistance = nearest swing highs above current price
        resistance_levels = sorted([h for h in swing_highs if h > current])
        resistance = resistance_levels[0] if resistance_levels else high_52w

        # Support = nearest swing lows below current price
        support_levels = sorted([l for l in swing_lows if l < current], reverse=True)
        support = support_levels[0] if support_levels else low_52w

        # Also add MA levels as support/resistance
        ma_support = []
        ma_resistance = []
        for ma_val, ma_name in [(sma20, 'SMA20'), (sma50, 'SMA50'), (sma200, 'SMA200')]:
            if ma_val:
                if ma_val < current:
                    ma_support.append((ma_val, ma_name))
                else:
                    ma_resistance.append((ma_val, ma_name))

        # --- Trend determination ---
        trend = "neutral"
        trend_signals = 0
        if sma20 and current > sma20:
            trend_signals += 1
        elif sma20:
            trend_signals -= 1
        if sma50 and current > sma50:
            trend_signals += 1
        elif sma50:
            trend_signals -= 1
        if sma20 and sma50 and sma20 > sma50:
            trend_signals += 1  # golden cross tendency
        elif sma20 and sma50:
            trend_signals -= 1  # death cross tendency

        if trend_signals >= 2:
            trend = "bullish"
        elif trend_signals <= -2:
            trend = "bearish"

        # --- Distance from key levels ---
        dist_support_pct = ((current - support) / current * 100) if support else None
        dist_resistance_pct = ((resistance - current) / current * 100) if resistance else None

        return {
            'symbol': symbol,
            'name': name,
            'price': round(float(current), 2),
            'sma20': round(sma20, 2) if sma20 else None,
            'sma50': round(sma50, 2) if sma50 else None,
            'sma200': round(sma200, 2) if sma200 else None,
            'ema9': round(ema9, 2) if ema9 else None,
            'rsi': round(rsi, 1) if rsi else None,
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'dist_support_pct': round(dist_support_pct, 1) if dist_support_pct else None,
            'dist_resistance_pct': round(dist_resistance_pct, 1) if dist_resistance_pct else None,
            'high_52w': round(high_52w, 2),
            'low_52w': round(low_52w, 2),
            'trend': trend,
            'ma_support': [(round(v, 2), n) for v, n in ma_support],
            'ma_resistance': [(round(v, 2), n) for v, n in ma_resistance],
        }
    except Exception as e:
        return None


def format_technicals(tech_results):
    """Format technical analysis section."""
    lines = []
    lines.append("📐 技术面分析")
    lines.append("")

    for t in tech_results:
        if not t:
            continue

        trend_emoji = {"bullish": "🟢↗", "bearish": "🔴↘", "neutral": "⚪→"}
        te = trend_emoji.get(t['trend'], "⚪→")
        trend_cn = {"bullish": "多头趋势", "bearish": "空头趋势", "neutral": "震荡"}
        tc = trend_cn.get(t['trend'], "震荡")

        lines.append(f"  {te} **{t['name']}** ({t['symbol']}) — {tc}")
        lines.append(f"    价格: ${t['price']:,.2f} | RSI: {t['rsi'] if t['rsi'] else 'N/A'}")

        # Support/Resistance
        sup_str = f"${t['support']:,.2f}"
        if t['dist_support_pct'] is not None:
            sup_str += f" (-{t['dist_support_pct']:.1f}%)"
        res_str = f"${t['resistance']:,.2f}"
        if t['dist_resistance_pct'] is not None:
            res_str += f" (+{t['dist_resistance_pct']:.1f}%)"
        lines.append(f"    支撑: {sup_str} | 阻力: {res_str}")

        # Moving averages
        ma_parts = []
        if t['ema9']:
            pos = "上方" if t['price'] > t['ema9'] else "下方"
            ma_parts.append(f"EMA9={t['ema9']:,.2f}({pos})")
        if t['sma20']:
            pos = "上方" if t['price'] > t['sma20'] else "下方"
            ma_parts.append(f"SMA20={t['sma20']:,.2f}({pos})")
        if t['sma50']:
            pos = "上方" if t['price'] > t['sma50'] else "下方"
            ma_parts.append(f"SMA50={t['sma50']:,.2f}({pos})")
        if ma_parts:
            lines.append(f"    均线: {' | '.join(ma_parts)}")

        # RSI interpretation
        if t['rsi']:
            if t['rsi'] >= 70:
                lines.append(f"    ⚠️ RSI {t['rsi']} — 超买区域，回调风险增加")
            elif t['rsi'] <= 30:
                lines.append(f"    💡 RSI {t['rsi']} — 超卖区域，反弹概率增加")

        lines.append("")

    return lines


# Tickers for technical analysis
TECH_ANALYSIS_TICKERS = {
    # Indices
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "QQQ": "QQQ",
    # Jason's large positions (>4% of portfolio)
    "TSLA": "Tesla",           # 33.9% of portfolio
    "NVDA": "NVIDIA",          # 8.5%
    "AAPL": "Apple",           # 7.1%
    "TSM": "TSM (台积电)",      # 6.3%
    "LMND": "Lemonade",        # 4.5%
    "AMZN": "Amazon",          # 4.2%
    "VOO": "VOO (S&P ETF)",    # 4.0%
    "AMD": "AMD",              # 3.8%
    # Crypto exposure
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "COIN": "Coinbase",
    "MSTR": "MicroStrategy",
    # Other watchlist
    "PLTR": "Palantir",
    "GOOGL": "Google",         # 2.1% of portfolio
    "RKLB": "Rocket Lab",
}


def generate_analysis(indices_data, sectors_data, macro_data, watchlist_data):
    """Generate market analysis and short-term outlook."""
    analysis = []
    outlook = []

    # --- Derive key metrics ---
    sp = indices_data.get("^GSPC", {})
    nq = indices_data.get("^IXIC", {})
    rut = indices_data.get("^RUT", {})
    vix = macro_data.get("^VIX", {})
    tnx = macro_data.get("^TNX", {})
    gold = macro_data.get("GC=F", {})
    oil = macro_data.get("CL=F", {})
    dxy = macro_data.get("DX-Y.NYB", {})
    btc = macro_data.get("BTC-USD", {})

    sp_chg = sp.get("change_pct", 0)
    nq_chg = nq.get("change_pct", 0)
    rut_chg = rut.get("change_pct", 0)
    vix_val = vix.get("price", 0)
    vix_chg = vix.get("change_pct", 0)
    tnx_val = tnx.get("price", 0)
    gold_chg = gold.get("change_pct", 0)
    btc_chg = btc.get("change_pct", 0)

    # Sorted sectors
    sorted_sectors = sorted(
        [(s, SECTORS[s], sectors_data[s]) for s in SECTORS if s in sectors_data],
        key=lambda x: x[2]["change_pct"],
        reverse=True,
    )
    best_sector = sorted_sectors[0] if sorted_sectors else None
    worst_sector = sorted_sectors[-1] if sorted_sectors else None

    # --- 市况分析 ---
    # 1) Broad risk-off / risk-on
    if sp_chg < -1.0 and vix_chg > 10:
        analysis.append("市场进入risk-off模式，大盘普跌+VIX飙升，机构正在减仓或对冲。")
    elif sp_chg > 1.0 and vix_chg < -5:
        analysis.append("risk-on情绪主导，指数上攻同时恐慌指数回落，资金积极入场。")

    # 2) Tech vs defensives rotation
    tech_chg = sectors_data.get("XLK", {}).get("change_pct", 0)
    staples_chg = sectors_data.get("XLP", {}).get("change_pct", 0)
    utils_chg = sectors_data.get("XLU", {}).get("change_pct", 0)
    defensive_avg = (staples_chg + utils_chg) / 2 if (staples_chg or utils_chg) else 0
    if tech_chg < -1.5 and defensive_avg > -0.5:
        analysis.append(f"科技板块({tech_chg:+.1f}%)跌幅远超防御性板块({defensive_avg:+.1f}%)，典型的growth→value轮动信号。")
    elif tech_chg > 1.0 and defensive_avg < 0:
        analysis.append("资金从防御板块流向科技成长，市场偏好高beta。")

    # 3) Small vs large cap divergence
    if abs(sp_chg - rut_chg) > 1.0:
        if rut_chg > sp_chg:
            analysis.append(f"小盘股（Russell {rut_chg:+.1f}%）表现强于大盘（S&P {sp_chg:+.1f}%），risk appetite偏乐观。")
        else:
            analysis.append(f"大盘抗跌（S&P {sp_chg:+.1f}%）优于小盘（Russell {rut_chg:+.1f}%），资金避险偏好大票。")

    # 4) Bond-equity signal
    if tnx_val:
        if tnx_val > 4.5 and sp_chg < -0.5:
            analysis.append(f"10Y收益率{tnx_val:.2f}%持续高位压制估值，debt rollover成本上升对高负债公司不利。")
        elif tnx_val < 4.0 and sp_chg > 0:
            analysis.append(f"10Y收益率降至{tnx_val:.2f}%，利率环境趋宽松，利好成长股估值修复。")

    # 5) VIX level interpretation
    if vix_val >= 30:
        analysis.append(f"VIX {vix_val:.0f} — 极度恐慌区域（>30），历史上是超卖反弹的前置信号，但要等确认。")
    elif vix_val >= 25:
        analysis.append(f"VIX {vix_val:.0f} — 高恐慌区域，期权隐含波动率显著偏高，short vol策略需谨慎。")
    elif vix_val >= 20 and vix_chg > 10:
        analysis.append(f"VIX从低位快速拉升至{vix_val:.0f}（+{vix_chg:.0f}%），市场情绪急转，short-term仍有惯性下行风险。")

    # 6) Crypto correlation
    if btc_chg < -5 and sp_chg < -1:
        analysis.append(f"BTC（{btc_chg:+.1f}%）和美股同步大跌，宏观risk-off主导，加密市场非独立行情。")

    # 7) Gold as safe haven
    if gold_chg > 1 and sp_chg < -1:
        analysis.append("黄金逆势上涨，典型避险买盘，市场对尾部风险定价上升。")
    elif gold_chg < -0.5 and sp_chg < -1:
        analysis.append("股金齐跌，可能是流动性紧缩（margin call被迫卖出一切）而非单纯避险。")

    # 8) Notable stock moves
    for sym in WATCHLIST:
        d = watchlist_data.get(sym, {})
        chg = d.get("change_pct", 0)
        if abs(chg) >= 5:
            if sym in ("COIN", "MSTR") and btc_chg < -5:
                analysis.append(f"{sym}({chg:+.1f}%)随BTC({btc_chg:+.1f}%)联动下跌，crypto beta放大效应。")
                break
            elif sym in ("LLY", "NVO") and abs(chg) > 5:
                analysis.append(f"减肥药龙头{sym}({chg:+.1f}%)大幅异动，关注是否有trial/guidance催化剂。")
                break

    # Fallback if no analysis generated
    if not analysis:
        if abs(sp_chg) < 0.3:
            analysis.append("市场窄幅震荡，缺乏明确方向，等待催化剂。")
        else:
            direction = "偏多" if sp_chg > 0 else "偏空"
            analysis.append(f"整体{direction}，S&P {sp_chg:+.1f}%，无明显异常信号。")

    # --- 短期展望 ---
    bearish_signals = 0
    bullish_signals = 0

    if sp_chg < -1.0:
        bearish_signals += 1
    elif sp_chg > 1.0:
        bullish_signals += 1
    if vix_chg > 15:
        bearish_signals += 1
    elif vix_chg < -10:
        bullish_signals += 1
    if vix_val >= 25:
        bearish_signals += 1
        # Contrarian: extreme VIX is also a bounce signal
        bullish_signals += 0.5
    if tech_chg < -2:
        bearish_signals += 1
    if btc_chg < -5:
        bearish_signals += 0.5
    if gold_chg > 1 and sp_chg < 0:
        bearish_signals += 0.5

    if bearish_signals >= 3:
        outlook.append("⚠️ 短期偏空 — 多重risk-off信号共振，明日大概率低开或延续弱势。")
        outlook.append("但VIX急升后1-3天常有技术反弹，不建议在恐慌高点追空。")
        outlook.append("关注支撑位和成交量变化，放量下跌=趋势，缩量下跌=洗盘。")
    elif bearish_signals >= 2:
        outlook.append("⚠️ 短期谨慎 — 空头信号偏多，但未到极端，可能横盘消化。")
        outlook.append("关注明日开盘前30分钟方向确认。")
    elif bullish_signals >= 2:
        outlook.append("📈 短期偏多 — 多头信号占优，有望延续反弹。")
    else:
        outlook.append("📊 短期中性 — 多空信号混杂，方向不明，建议观望。")

    return analysis, outlook


def format_report(indices_data, sectors_data, macro_data, watchlist_data, alerts):
    """Format the market report as a readable text."""
    now = datetime.now(timezone.utc)
    lines = []

    # Header
    if alerts:
        lines.append("🚨 美股市场警报 🚨")
        for a in alerts:
            lines.append(a)
        lines.append("")

    lines.append(f"📊 美股市场报告 — {now.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")

    # Indices
    lines.append("📈 主要指数")
    for symbol, name in INDICES.items():
        if symbol in indices_data:
            d = indices_data[symbol]
            emoji = "🟢" if d["change_pct"] >= 0 else "🔴"
            lines.append(f"  {emoji} {name}: {d['price']:,.1f} ({d['change_pct']:+.1f}%)")
    lines.append("")

    # Macro — VIX uses inverted emoji (up = bad), no $ prefix for VIX/TNX
    lines.append("🌍 宏观信号")
    for symbol, name in MACRO.items():
        if symbol in macro_data:
            d = macro_data[symbol]
            if symbol == "^VIX":
                # VIX up = bearish → 🔴, VIX down = bullish → 🟢
                emoji = "🔴" if d["change_pct"] >= 0 else "🟢"
                lines.append(f"  {emoji} {name}: {d['price']:.1f} ({d['change_pct']:+.1f}%)")
            elif symbol == "^TNX":
                emoji = "🟢" if d["change_pct"] >= 0 else "🔴"
                lines.append(f"  {emoji} {name}: {d['price']:.2f}% ({d['change_pct']:+.1f}%)")
            else:
                emoji = "🟢" if d["change_pct"] >= 0 else "🔴"
                lines.append(f"  {emoji} {name}: ${d['price']:,.1f} ({d['change_pct']:+.1f}%)")
    lines.append("")
    
    # Sectors - sorted by change
    lines.append("🏭 板块表现（涨跌排序）")
    sorted_sectors = sorted(
        [(s, SECTORS[s], sectors_data[s]) for s in SECTORS if s in sectors_data],
        key=lambda x: x[2]["change_pct"],
        reverse=True
    )
    for symbol, name, d in sorted_sectors:
        emoji = "🟢" if d["change_pct"] >= 0 else "🔴"
        bar_len = min(int(abs(d["change_pct"]) * 5), 20)
        bar = "█" * bar_len if bar_len > 0 else "▏"
        lines.append(f"  {emoji} {name:6s} {d['change_pct']:+5.1f}% {bar}")
    lines.append("")
    
    # Top movers in watchlist
    if watchlist_data:
        sorted_watch = sorted(
            [(s, watchlist_data[s]) for s in watchlist_data],
            key=lambda x: x[1]["change_pct"],
            reverse=True
        )
        
        # Top gainers
        gainers = [(s, d) for s, d in sorted_watch if d["change_pct"] > 0][:5]
        losers = [(s, d) for s, d in sorted_watch if d["change_pct"] < 0][-5:]
        losers.reverse()
        
        if gainers:
            lines.append("🚀 今日领涨")
            for s, d in gainers:
                lines.append(f"  🟢 {s:6s} ${d['price']:>8.1f}  {d['change_pct']:+.1f}%")
        
        if losers:
            lines.append("💀 今日领跌")
            for s, d in losers:
                lines.append(f"  🔴 {s:6s} ${d['price']:>8.1f}  {d['change_pct']:+.1f}%")
    lines.append("")

    # Technical Analysis
    tech_results = []
    for sym, name in TECH_ANALYSIS_TICKERS.items():
        tech = compute_technicals(sym, name)
        if tech:
            tech_results.append(tech)
    if tech_results:
        lines.extend(format_technicals(tech_results))

    # Analysis & Outlook
    analysis, outlook = generate_analysis(indices_data, sectors_data, macro_data, watchlist_data)

    if analysis:
        lines.append("🧠 市况分析")
        for a in analysis:
            lines.append(f"  • {a}")
        lines.append("")

    if outlook:
        lines.append("🔮 短期展望")
        for o in outlook:
            lines.append(f"  {o}")

    return "\n".join(lines)


def generate_report(alert_only=False, output_json=False):
    """Main report generation function."""
    # Fetch all data
    all_tickers = list(INDICES.keys()) + list(SECTORS.keys()) + list(MACRO.keys()) + WATCHLIST
    all_data = get_quote_data(all_tickers)
    
    # Split into categories
    indices_data = {k: all_data[k] for k in INDICES if k in all_data}
    sectors_data = {k: all_data[k] for k in SECTORS if k in all_data}
    macro_data = {k: all_data[k] for k in MACRO if k in all_data}
    watchlist_data = {k: all_data[k] for k in WATCHLIST if k in all_data}
    
    # Check alerts
    alerts = check_alerts(indices_data, sectors_data, macro_data, watchlist_data)
    
    if alert_only and not alerts:
        return None
    
    if output_json:
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alerts": alerts,
            "indices": indices_data,
            "sectors": sectors_data,
            "macro": macro_data,
            "watchlist": watchlist_data,
        }, indent=2, ensure_ascii=False)
    
    return format_report(indices_data, sectors_data, macro_data, watchlist_data, alerts)


def main():
    parser = argparse.ArgumentParser(description="US Stock Market Report Generator")
    parser.add_argument("--output", help="Save report to file")
    parser.add_argument("--alert-only", action="store_true", help="Only output if alerts triggered")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    report = generate_report(alert_only=args.alert_only, output_json=args.json)
    
    if report is None:
        sys.exit(0)  # No alerts, silent exit
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
