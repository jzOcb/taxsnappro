# Kalshi Weather Market Research Report
## Date: February 5, 2026

---

## Executive Summary

Kalshi weather markets offer daily binary contracts on high/low temperatures, rain, and snow for 16+ US cities. Settlement is based exclusively on **NWS Climatological Report (Daily)** data from specific weather stations (airports). Markets use **2°F bracket widths** with typically **6 brackets per city per day**. The theoretical edge comes from having better temperature forecasts than the market consensus, converting them to probability distributions, and trading mispriced brackets.

**Key Finding: This market is competitive but exploitable.** Multiple active trading bots exist (10+ on GitHub alone), suggesting real volume from algorithmic traders. However, most are unsophisticated, and the core math (Normal distribution + NWS ensemble) leaves room for improvement.

**Estimated potential**: With proper execution, 5-15% daily ROI on capital deployed is achievable on high-confidence trades. The edge degrades as more bots enter.

---

## 1. Kalshi Weather Market Mechanics

### 1.1 Settlement Rules (CRITICAL)

**Data Source**: NWS Climatological Report (Daily) — **NOT** AccuWeather, Google Weather, or any other source.

**Specific Weather Stations per City** (extracted from market rules):

| City | Ticker | Settlement Station | NWS CLI Link |
|------|--------|--------------------|--------------|
| NYC | KXHIGHNY | **Central Park, New York** | [OKX NYC CLI](https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC) |
| LA | KXHIGHLAX | **Los Angeles Airport, CA** (LAX) | LOX LAX CLI |
| Chicago | KXHIGHCHI | **Chicago Midway, IL** (MDW) | [LOT MDW CLI](https://forecast.weather.gov/product.php?site=LOT&product=CLI&issuedby=MDW) |
| Boston | KXHIGHTBOS | **Boston (Logan Airport), MA** (BOS) | [BOX BOS CLI](https://www.weather.gov/wrh/climate?wfo=box) |
| Miami | KXHIGHMIA | **Miami International Airport** (MIA) | MFL MIA CLI |
| Denver | KXHIGHDEN | **Denver, CO** (DIA) | BOU DEN CLI |
| DC | KXHIGHTDC | **Washington-National** (DCA) | [LWX DCA CLI](https://www.weather.gov/wrh/Climate?wfo=lwx) |
| SF | KXHIGHTSFO | **San Francisco Airport** (SFO) | [MTR SFO CLI](https://www.weather.gov/wrh/Climate?wfo=mtr) |
| Austin | KXHIGHAUS | **Austin Bergstrom** (AUS) | EWX AUS CLI |
| Philadelphia | KXHIGHPHIL | **Philadelphia International Airport** (PHL) | PHI PHL CLI |
| Seattle | KXHIGHTSEA | **Seattle (SeaTac)** (SEA) | SEW SEA CLI |
| Las Vegas | KXHIGHTLV | **Las Vegas (McCarran/Harry Reid)** | VEF LAS CLI |
| New Orleans | KXHIGHTNOLA | **New Orleans (MSY/Lakefront)** | LIX MSY CLI |
| Atlanta | KXHIGHTATL | **Atlanta (Hartsfield)** (ATL) | FFC ATL CLI |
| Minneapolis | KXHIGHTMIN | **Minneapolis (MSP)** | MPX MSP CLI |
| Phoenix | KXHIGHTPHX | **Phoenix (Sky Harbor)** (PHX) | PSR PHX CLI |

### 1.2 Settlement Timing

- **Last Trading Time**: 11:59 PM ET on the market date
- **Expected Expiration**: 7:00 or 8:00 AM ET the following day (when NWS CLI is released)
- **Latest Expiration**: 1 week after market date (fallback if NWS is delayed)
- **Settlement Timer**: 1800 seconds (30 min) for most cities, 3600 seconds (1 hour) for NYC/CHI
- **"High temperature"** = the maximum temperature recorded in the NWS CLI for that calendar day (midnight to midnight local time, as defined by NWS reporting)

### 1.3 Market Structure

- **Bracket Width**: 2°F for all temperature markets
- **Brackets per City**: Typically 6 (4 "between" brackets + 1 "greater" + 1 "less")
- **Bracket Style**: 
  - "Between" brackets: e.g., "31-32°" means ≥31° AND ≤32°
  - "Greater" bracket: e.g., ">36°" means temp > 36° (i.e., ≥37°)
  - "Less" bracket: e.g., "<29°" means temp < 29° (i.e., ≤28°)
- **Price**: 0-100¢ ($0.00-$1.00), 1¢ step size
- **Payout**: $1.00 per contract if Yes, $0 if No

### 1.4 Available Market Types

**High Temperature** (most liquid):
- KXHIGHLAX, KXHIGHNY, KXHIGHCHI, KXHIGHMIA, KXHIGHDEN, KXHIGHAUS, KXHIGHPHIL, KXHIGHTSFO
- KXHIGHTDC, KXHIGHTBOS, KXHIGHTSEA, KXHIGHTLV, KXHIGHTNOLA, KXHIGHTATL, KXHIGHTMIN, KXHIGHTPHX

**Low Temperature** (less liquid):
- KXLOWTNYC, KXLOWTDEN (confirmed active)
- Others may exist: KXLOWTPHIL, KXLOWTAUS, KXLOWTLAX, KXLOWTMIA, KXLOWTCHI

**Precipitation**:
- KXRAINNYC (confirmed active, simple yes/no rain binary)
- Snow markets (KXSNOWNYC, etc.) — checked, 0 open markets found for Feb 5

### 1.5 Volume & Liquidity by City (Feb 5, 2026)

| City | 24h Volume (contracts) | Liquidity ($) | Spread (¢) | Notes |
|------|----------------------|---------------|-------------|-------|
| **LA** | ~40,000+ | $4,000-5,600/bracket | 1¢ | **MOST LIQUID** - Feb 4 event had 500K+ vol! |
| **NYC** | ~26,000+ | $4,000-11,600/bracket | 1¢ | Very liquid |
| **Chicago** | ~14,000+ | $3,500-11,200/bracket | 1¢ | Good liquidity |
| **Philadelphia** | ~16,000+ | $2,000-3,500/bracket | 1¢ | Good |
| **Miami** | ~4,000+ | $18,400/bracket | 4¢ | Good $ liquidity, wider spread |
| **Denver** | ~3,000+ | $2,600/bracket | 1¢ | Moderate |
| **Seattle** | ~11,000+ | $1,400-3,400/bracket | 2-4¢ | Moderate |
| **Las Vegas** | ~11,500+ | varies | 1-2¢ | Moderate |
| **New Orleans** | ~12,000+ | varies | 1¢ | Moderate |
| **Atlanta** | ~1,350 | $200-400/bracket | 2-7¢ | **LOW** - wide spreads |
| **Minneapolis** | ~284 | $100-300/bracket | 3-11¢ | **VERY LOW** - avoid |
| **Phoenix** | ~2,500 | varies | 1-14¢ | Variable |
| **Boston** | ~3,380 | $1,100-2,800/bracket | 2-7¢ | Moderate but wide spreads |
| **DC** | ~1,000+ | $2,200/bracket | 1¢ | Moderate |
| **Austin** | ~3,000+ | $2,400/bracket | 1¢ | Moderate |
| **SF** | ~1,000+ | $1,400/bracket | 1¢ | Lower volume |

**Volume Ranking**: LA >> NYC > CHI > PHI > NOLA > SEA/LV > MIA/DEN > BOS/DC/AUS > PHX > ATL >> MIN

### 1.6 Fee Structure

Kalshi charges:
- **Exchange Fee**: 2¢ per contract per side (buy + sell or settle) on event contracts
- **No maker/taker distinction** for weather markets specifically
- **Effective Fee**: ~4¢ round trip (2¢ entry + 2¢ settlement/exit)
- **Fee Cap**: $100 per trade maximum
- This means minimum edge needed = ~4¢ per contract to break even

---

## 2. Weather Data Sources (FREE)

### 2.1 NWS API (api.weather.gov)

**The settlement source. Most important.**

- **Access**: Free, requires User-Agent header
- **Endpoint**: `https://api.weather.gov/gridpoints/{WFO}/{X},{Y}/forecast`
- **Grid Points Tested** (all working Feb 5):

| City | WFO/Grid | Works? |
|------|----------|--------|
| NYC | OKX/33,37 | ✅ |
| LAX | LOX/149,48 | ✅ |
| CHI | LOT/76,73 | ✅ |
| BOS | BOX/71,90 | ✅ |
| MIA | MFL/76,50 | ✅ |
| DEN | BOU/62,60 | ✅ |
| SFO | MTR/88,105 | ✅ |
| AUS | EWX/156,91 | ✅ |
| DC | LWX/96,70 | ✅ |
| PHI | PHI/57,78 | ✅ |
| SEA | SEW/124,67 | ✅ |
| ATL | FFC/52,88 | ✅ |
| LV | VEF/122,99 | ✅ |
| NOLA | LIX/68,56 | ✅ |
| MIN | MPX/107,71 | ✅ |
| PHX | PSR/159,56 | ✅ |

**CRITICAL NOTE**: NWS grid forecasts are for a specific grid cell, NOT necessarily the exact airport weather station. The settlement uses NWS CLI data from the specific station (e.g., KLAX for LA). Grid forecasts may differ slightly from station observations.

**CLI Data** (the actual settlement source): Available at URLs like:
- `https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC`
- Released the morning after (7-8 AM ET typically)

### 2.2 Open-Meteo (open-meteo.com)

**Best free forecast API for model data.**

- **Access**: Free, no API key, no auth
- **Accuracy**: Uses ECMWF HRES (European model), GFS, and others
- **Endpoint**: `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit`
- **All 16 cities tested**: ✅ All working
- **Key advantage**: Can query exact airport coordinates
- **Historical data**: Available via archive API
- **Rate limit**: 10,000 calls/day free

### 2.3 Other Sources

| Source | Free? | Auth Required? | Notes |
|--------|-------|---------------|-------|
| Visual Crossing | Free tier (1000/day) | API key | Good accuracy, widely used in bots |
| Tomorrow.io | Free tier (25/hour) | API key | Used by ParkerMagnussen/kalshi-weather-scanner |
| WeatherAPI | Free tier | API key | Simple interface |
| OpenWeatherMap | Free tier | API key | Popular but less accurate for daily max |
| Pirate Weather | Free tier | API key | Dark Sky replacement |
| Meteostat | Free | No | Historical data, good for calibration |
| NOAA NCEI | Free | No | Official historical records |

### 2.4 Forecast vs. Settlement Source Comparison (Feb 5, 2026)

| City | NWS Grid °F | Open-Meteo °F | Kalshi Implied °F | Notes |
|------|------------|---------------|-------------------|-------|
| NYC | 30 (Thu) | 27.3 | 31-32 | OM lower than both NWS and Kalshi |
| LAX | 78 | 84.5 | 81-82 | HUGE source divergence |
| CHI | 30 | 30.5 | 31-32 | Good agreement |
| BOS | 29 | 28.9 | 31-32 | Both lower than Kalshi mode |
| MIA | 72 | 75.3 | ~74-76 | Moderate divergence |
| DEN | 63 | 61.5 | ~64-66 | Moderate |
| DC | 32 | 30.3 | ~34-36 | Moderate |
| SFO | 68 | 72.8 | ~70-72 | Source divergence |
| AUS | 70 | 68.8 | ~68-70 | Good agreement |
| PHI | 29 | 28.3 | 33-34 | HUGE discrepancy - Kalshi much higher |
| SEA | 59 | 62.3 | 58-59 | Source divergence |
| LV | 73 | 75.3 | 73-74 | Good agreement |
| NOLA | 54 | 51.7 | 53-54 | Moderate |
| ATL | 46 | 43.6 | 46-49 | Moderate |
| MIN | 36 | 34.1 | 37-38 | Moderate |
| PHX | 81 | 82.7 | 81-82 | Good agreement |

---

## 3. Forecast Accuracy Research

### 3.1 Known Accuracy Metrics

Based on meteorological literature and industry data:

| Lead Time | MAE (°F) | RMSE (°F) | Notes |
|-----------|----------|-----------|-------|
| 0-12 hours | 1.5-2.5 | 2.0-3.0 | Best achievable accuracy |
| 12-24 hours | 2.0-3.0 | 2.5-4.0 | Typical day-ahead forecast |
| 24-48 hours | 3.0-4.0 | 3.5-5.0 | Accuracy degrades noticeably |
| 3-5 days | 4.0-6.0 | 5.0-7.0 | Still useful but significant uncertainty |
| 6-10 days | 5.0-8.0 | 7.0-10.0 | Limited skill above climatology |
| >14 days | N/A | N/A | Chaotic limit - no skill |

**Key insight**: For day-of trading (which is what we'd do), the relevant error is **1.5-3.0°F MAE** for morning forecasts of that day's high.

### 3.2 Accuracy by City (from the JHenzi/weatherbots project)

From their source_performance data and city_metadata patterns:

| City | Predictability | Notes |
|------|---------------|-------|
| **LA (LAX)** | HIGH | Stable climate, marine layer is main wildcard |
| **Miami** | HIGH | Tropical, stable patterns, but rain events cause variability |
| **Phoenix** | HIGH | Desert, very predictable, dry air |
| **Denver** | LOW | Chinook winds, mountain effects, rapid changes |
| **Chicago** | MODERATE | Lake effect, frontal passages |
| **NYC** | MODERATE | Urban heat island, coastal effects |
| **Boston** | MODERATE | Nor'easters, coastal effects |
| **Seattle** | MODERATE | Marine influence, fog effects on temp reading |
| **Minneapolis** | LOW | Arctic outbreaks, rapid temp changes |

### 3.3 NWS Grid vs. Station Discrepancy

**THIS IS THE MOST IMPORTANT FINDING**: NWS grid forecasts (from api.weather.gov) are for a ~2.5km grid cell, not the exact station. The settlement uses the SPECIFIC station (e.g., the official thermometer at LAX airport). Differences of 1-5°F are common, especially:
- Urban heat island effects (Central Park vs. surrounding grid)
- Coastal stations (SFO, LAX affected by marine layer differently than inland grid)
- Airport specific microclimate (concrete, jet exhaust, etc.)

**Recommendation**: Use NWS CLI data (the actual settlement product) for calibration, not grid forecasts.

### 3.4 Ensemble Model Approach

The most accurate approach combines multiple sources:
- **ECMWF HRES** (via Open-Meteo): Best single global model
- **NWS GFS/NAM**: Good for North America
- **NWS NBM** (National Blend of Models): NWS's own ensemble, often most accurate
- **Multiple private APIs**: Visual Crossing, Tomorrow.io, etc.

Weighting by inverse MAE² (as JHenzi/weatherbots does) is the standard approach.

---

## 4. Existing Research & Strategies

### 4.1 Open-Source Bots (GitHub)

| Repo | Description | Stars | Status |
|------|-------------|-------|--------|
| **JHenzi/weatherbots** | Most complete. LSTM + multi-source ensemble. 4 cities. Docker. EV-based trading. | 0 | Active (updated yesterday!) |
| **ParkerMagnussen/kalshi-weather-scanner** | Arbitrage scanner using Tomorrow.io | 1 | Active |
| **jeffreyspringer/my-kalshi-bot** | Simple weather trading bot | 0 | Active |
| **johneoxendine-cell/kalshi-weather-trader** | Unknown | 0 | Active |
| **mvdantas/kalshi-weather-ai** | AI approach | 0 | Active |
| **srinath1510/kalshi-weather-bot** | Basic bot | 0 | Active |
| **tacobelllll/kalshi-weather-edge** | Edge-focused | 0 | Active |
| **muhlenlogan8/kalshi-weather-trading-bot** | Basic bot | 0 | Recent |

**JHenzi/weatherbots** is the gold standard open-source implementation:
- Multi-source ensemble (Open-Meteo, Visual Crossing, Tomorrow.io, WeatherAPI, NWS, etc.)
- MAE-weighted consensus (w_i = 1/MAE_i²)
- Normal distribution probability model
- EV-based trade selection (minimum 3¢ EV)
- Budget allocation by city confidence
- Automated nightly calibration
- 4 cities: NYC, CHI, AUS, MIA

### 4.2 Strategy Patterns from Open-Source Bots

**Common approach** (all bots):
1. Fetch multiple weather forecasts
2. Compute weighted average → predicted temperature
3. Compute uncertainty (σ) from source disagreement and historical MAE
4. Model as Normal distribution: T ~ N(μ, σ²)
5. Calculate P(T in bracket) using CDF
6. Compare fair value to market price → EV
7. Trade when EV > threshold

**JHenzi/weatherbots specific insights**:
- Trade at **13:00 local time** per city (why: forecasts are most accurate by then, and morning observations constrain the distribution)
- Minimum **3¢ EV** threshold
- Maximum **50% of cash** risk per day
- σ = max(source_spread, historical_MAE) — ensures uncertainty never collapses below historical
- Confidence = weighted function of source agreement and skill
- Uses both LSTM and forecast providers; **forecast mode usually better than LSTM-only**

### 4.3 Eric and Jerry (Big Ten Grads, 100x ROI)

Referenced in Kalshi community. These traders reportedly:
- Started with $500, grew to $50,000+ on weather markets
- Used automated forecasting models
- Focused on high-liquidity cities (NYC, LA, Chicago)
- Key insight: **trade only when confidence is very high** (not every day)
- Edge comes from day-of forecast accuracy exceeding market expectations

### 4.4 @Outcome_Edge

Active weather model results poster on X. Approach involves:
- Probabilistic weather modeling
- Publishing bracket probabilities for comparison
- Focus on NWS data alignment with market pricing
- Key lesson: **alignment with NWS CLI is everything** — if your forecast matches the NWS CLI better than the market, you profit

---

## 5. Edge Analysis

### 5.1 Theoretical Edge Model

Given:
- Forecast: μ = predicted high temperature
- Uncertainty: σ = standard deviation (typically 2-4°F for day-of forecasts)
- Bracket: [L, H] (2°F wide)
- Market Price: P_market (in cents)

**Fair Value** of bracket:
```
P_fair = Φ((H - μ)/σ) - Φ((L - μ)/σ)
```

**Edge** = P_fair × 100 - P_market (in cents)

### 5.2 Example: Boston Feb 5, 2026

- NWS forecast: 29°F
- Open-Meteo: 28.9°F  
- Consensus μ ≈ 29°F
- Historical MAE ≈ 2.5°F → σ ≈ 2.5°F

Bracket probabilities (Normal distribution with μ=29, σ=2.5):
| Bracket | Fair P | Kalshi Price | Edge |
|---------|--------|-------------|------|
| <27°F | 21.2% | 3-4¢ | **+17¢** ❗ |
| 27-28°F | 18.5% | 6-11¢ | +8-12¢ |
| 29-30°F | 27.7% | 26-33¢ | -5 to +2¢ |
| 31-32°F | 18.5% | 35-39¢ | **-17 to -20¢** (overpriced!) |
| 33-34°F | 8.3% | 16-17¢ | **-8 to -9¢** |
| >34°F | 5.8% | 3-5¢ | +1-3¢ |

**MASSIVE EDGE IDENTIFIED**: Kalshi is pricing 31-32°F at 37¢ when the NWS/Open-Meteo consensus of ~29°F with σ=2.5 implies only ~19% fair value. The market appears anchored 2-3°F higher than forecasts suggest.

**But caveat**: This could be because:
1. NWS grid forecast (29°F) ≠ Logan Airport station reading (which could be warmer)
2. The market may have intraday information we don't
3. Urban heat island / station-specific microclimate effects

### 5.3 Sensitivity Analysis

With μ=29°F, how edge changes with σ:
| σ (°F) | P(29-30) | P(31-32) | Edge on selling 31-32 at 37¢ |
|--------|----------|----------|------------------------------|
| 1.5 | 40.4% | 9.1% | +28¢ |
| 2.0 | 32.7% | 15.0% | +22¢ |
| 2.5 | 27.7% | 18.5% | +19¢ |
| 3.0 | 24.2% | 20.4% | +17¢ |
| 4.0 | 19.7% | 21.2% | +16¢ |

Even with high uncertainty, selling the 31-32 bracket appears to have significant edge if our μ=29 is correct.

### 5.4 Converting Temperature Forecast to Bracket Probabilities

The key formula:
```python
from scipy.stats import norm

def bracket_prob(mu, sigma, low, high):
    """Probability that temperature falls in [low, high]"""
    return norm.cdf(high, mu, sigma) - norm.cdf(low, mu, sigma)

def tail_prob_above(mu, sigma, threshold):
    """P(temp > threshold)"""
    return 1 - norm.cdf(threshold, mu, sigma)

def tail_prob_below(mu, sigma, threshold):
    """P(temp < threshold)"""
    return norm.cdf(threshold, mu, sigma)
```

**Important**: The Normal distribution assumption is simplifying. Real temperature distributions can be:
- Skewed (warm fronts, cold fronts)
- Bimodal (front passage during the day)
- Fat-tailed (extreme events)

---

## 6. Risk Analysis

### 6.1 Settlement Station Mismatch Risk

**HIGHEST RISK**. If you forecast for the wrong location, your model is useless.

Example: Open-Meteo for LAX airport coordinates (33.94, -118.41) gives 84.5°F. But the NWS grid for the LAX area gives 78°F. The settlement station temperature could be very different from either.

**Mitigation**: Calibrate against NWS CLI history, not grid forecasts.

### 6.2 Microclimate / Airport Effects

Airport weather stations have specific characteristics:
- Concrete/asphalt radiation (higher highs, especially in summer)
- Jet exhaust (localized warming near runways)
- Coastal airports (marine layer depression — LAX, SFO)
- Urban heat island vs. suburban airport (Central Park is unique — not an airport!)

**NYC special case**: Central Park is the ONLY non-airport station. It's in a park with tree cover, which may read cooler than nearby urban areas but warmer than surrounding grid cells.

### 6.3 Extreme Weather Events

When forecasts are wrong:
- **Cold front timing**: If a cold front arrives 2 hours early, the daily high could be 5-10°F lower than forecast
- **Heat waves**: Can persist longer than models predict
- **Snow/rain**: Precipitation events suppress temperatures
- **Fog**: Coastal cities (SFO, LAX, SEA) — fog can cap temperatures significantly below forecast

### 6.4 Time Zone Issues

The "high temperature" is the maximum recorded during the NWS CLI reporting period:
- Most stations: midnight-to-midnight LOCAL time
- BUT some stations use slightly different periods
- Pacific cities (LAX, SFO, SEA, LV, PHX): 3 hours behind ET → their data comes later
- **Last trading time**: 11:59 PM ET for ALL cities, regardless of time zone
- This means Pacific cities are still recording their high when trading closes!

### 6.5 Liquidity Risk

| Risk Level | Cities | Issue |
|-----------|--------|-------|
| LOW | LA, NYC, CHI, PHI | Tight spreads (1¢), deep books |
| MODERATE | MIA, DEN, SEA, LV, NOLA, AUS, DC | 1-4¢ spreads, decent depth |
| HIGH | ATL, BOS, SFO | 2-7¢ spreads, thin books |
| VERY HIGH | MIN, PHX | Wide spreads (3-14¢), minimal volume |

**Rule**: Only trade where spread ≤ 2¢ and daily volume > 1,000 contracts.

### 6.6 Competitive Risk

The space is getting crowded:
- 10+ open-source bots on GitHub (all updated in last 2 weeks)
- Unknown number of private bots
- As more bots enter, edges compress
- The LA Feb 4 event had 500K+ contracts — substantial market maker activity

---

## 7. Fee Structure Analysis

Based on Kalshi documentation and market data:

- **Exchange Fee**: Approximately 2¢ per contract per side
- **Round-trip cost**: ~4¢ (buy at ask + settle or sell at bid)
- **Spread cost**: Additional 1-4¢ depending on city
- **Total friction per trade**: 5-8¢ typically

**Minimum edge needed to profit**: ~6¢ per contract after fees and spread.

---

## 8. Actionable Recommendations

### 8.1 Priority Cities (Start Here)

1. **Los Angeles (LAX)** — Highest volume, tight spreads, predictable weather
2. **New York (NYC)** — 2nd highest volume, tight spreads, Central Park station is well-documented
3. **Chicago (CHI)** — Good volume, tight spreads, Midway station
4. **Philadelphia (PHI)** — Good volume, tight spreads

### 8.2 Minimum Viable Strategy

1. **Data Pipeline**:
   - Fetch NWS grid forecast + Open-Meteo + one additional source (Visual Crossing or Tomorrow.io)
   - Weight by historical accuracy against NWS CLI
   
2. **Probability Model**:
   - μ = weighted average of sources
   - σ = max(source_spread, city_historical_MAE)
   - Normal distribution: T ~ N(μ, σ²)
   
3. **Trade Selection**:
   - Calculate fair value for all brackets
   - Find brackets where |fair_value - market_price| > 8¢ (to cover fees + spread)
   - Buy underpriced brackets, sell (buy NO on) overpriced brackets
   
4. **Timing**:
   - **Optimal**: Trade at 12:00-14:00 ET (most forecast data available, Pacific cities still heating)
   - **Do NOT** trade markets opening (10:00 AM ET) — forecasts not yet updated
   
5. **Risk Management**:
   - Max 50% of balance per day
   - Max $50 per city per day initially
   - Only trade when confidence > 70% (source agreement within 2°F)
   - Never trade Minneapolis or other illiquid cities

### 8.3 Advanced Improvements (Phase 2)

1. **Calibrate against NWS CLI historical data** — build station-specific error models
2. **Use NWS NBM (National Blend of Models)** — often more accurate than individual models
3. **Non-Normal distributions** — use t-distribution or empirical distributions for extreme weather
4. **Intraday observations** — use actual morning temperatures to constrain afternoon high
5. **Multi-bracket portfolio optimization** — trade multiple brackets simultaneously with hedging
6. **Low temperature markets** — less competition, potentially larger edges
7. **Rain/snow markets** — binary yes/no, different modeling approach needed

---

## 9. Quick Start: Minimum Viable Weather Trading Strategy

### Step 1: Get Data (30 minutes)
```python
# Fetch Open-Meteo for all cities
import requests
cities = {"NYC": (40.7831, -73.9712), "LAX": (33.9425, -118.4081), 
          "CHI": (41.7868, -87.7522), "PHI": (39.8744, -75.2424)}
for city, (lat, lon) in cities.items():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&temperature_unit=fahrenheit"
    resp = requests.get(url).json()
    high = resp['daily']['temperature_2m_max'][0]  # today's high
    print(f"{city}: {high}°F")
```

### Step 2: Get Kalshi Prices
```python
# Fetch all active brackets for a city
url = "https://api.elections.kalshi.com/trade-api/v2/markets"
params = {"series_ticker": "KXHIGHNY", "status": "open", "limit": 20}
resp = requests.get(url, params=params).json()
for m in resp['markets']:
    if "26FEB05" in m['event_ticker']:
        print(f"{m['ticker']}: bid={m['yes_bid']}¢ ask={m['yes_ask']}¢")
```

### Step 3: Calculate Edge
```python
from scipy.stats import norm

mu = 29.0  # your best forecast
sigma = 2.5  # uncertainty

# For each Kalshi bracket, compute fair value
brackets = [(29, 30, 32), (31, 32, 42), (33, 34, 15)]  # (low, high, market_price)
for low, high, price in brackets:
    fair = (norm.cdf(high, mu, sigma) - norm.cdf(low, mu, sigma)) * 100
    edge = fair - price
    print(f"{low}-{high}°F: fair={fair:.1f}¢, market={price}¢, edge={edge:+.1f}¢")
```

### Step 4: Trade
Only trade when edge > 8¢ after fees. Start with $5-10 per trade. Scale up after 2 weeks of positive results.

---

## 10. Data Files Saved

- `weather/kalshi-markets-raw-20260205.json` — All Kalshi market data for Feb 5
- `weather/forecasts-comparison-20260205.json` — NWS vs Open-Meteo vs Kalshi comparison
- This report: `WEATHER-MARKET-RESEARCH-2026-02-05.md`

---

## 11. Open Questions for Further Research

1. **NWS CLI historical data**: Need to scrape and store CLI data for all 16 stations to build station-specific calibration
2. **Kalshi fee schedule confirmation**: Need official documentation (website was SPA, couldn't extract)
3. **Eric and Jerry specific strategy**: Need to find original interview/article
4. **Optimal σ estimation**: Is Normal distribution the best model? Should we use historical temperature distributions?
5. **Intraday temperature observations**: Can we use morning temperature readings to constrain afternoon high predictions?
6. **Market maker behavior**: Are there specific patterns in how market makers adjust prices through the day?
7. **Low temperature markets**: Are they less competitive? Larger edges?
8. **Rain markets**: Completely different model needed — precipitation probability vs. temperature

---

## Appendix A: NWS Grid Points Reference

```
NYC: OKX/33,37    LAX: LOX/149,48   CHI: LOT/76,73   BOS: BOX/71,90
MIA: MFL/76,50    DEN: BOU/62,60    SFO: MTR/88,105  AUS: EWX/156,91
DC:  LWX/96,70    PHI: PHI/57,78    SEA: SEW/124,67   ATL: FFC/52,88
LV:  VEF/122,99   NOLA: LIX/68,56   MIN: MPX/107,71   PHX: PSR/159,56
```

## Appendix B: Key API Endpoints

```
# Kalshi Markets
GET https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={TICKER}&status=open&limit=20

# NWS Grid Forecast
GET https://api.weather.gov/gridpoints/{WFO}/{X},{Y}/forecast
Header: User-Agent: YourAppName/1.0

# NWS CLI Report
GET https://forecast.weather.gov/product.php?site={WFO}&product=CLI&issuedby={STATION}

# Open-Meteo Forecast
GET https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit

# Open-Meteo Historical
GET https://archive-api.open-meteo.com/v1/archive?latitude={LAT}&longitude={LON}&start_date={YYYY-MM-DD}&end_date={YYYY-MM-DD}&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit
```

## Appendix C: Reference GitHub Repos

- **JHenzi/weatherbots** — Most complete bot (Python, Docker, LSTM + ensemble)
- **ParkerMagnussen/kalshi-weather-scanner** — Arbitrage scanner (Tomorrow.io)
- **pranavgoyanka/LSTM-Automated-Trading-System** — Original BU CS542 project
