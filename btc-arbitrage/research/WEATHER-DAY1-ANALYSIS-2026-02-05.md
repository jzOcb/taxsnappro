# Weather Trading Day 1 Analysis — Feb 5, 2026

## Results
- 23 trades, 10W/13L (43% WR)
- P&L: +$2,347.76 on $777 deployed = +302% ROI
- Bankroll: $1000 → $2,348

## Forecast Accuracy
- Ensemble MAE: 5.4°F (target: <3°F)
- NWS Grid MAE: 5.6°F
- Open-Meteo MAE: 5.3°F (slightly better)
- RMSE: 6.4°F
- Bias: +1.4°F (forecasts systematically low)
- Only 25% within 1σ (should be 68%) → σ was WAY too tight

## City Reliability Tiers
### 🟢 Reliable (≤4°F error): BOS, CHI, LV, MIA, NYC, PHX, SEA, SFO
### 🟡 Moderate (4-7°F): AUS, LAX, PHI
### 🔴 Unreliable (>7°F): ATL(+12), DEN(-11), MIN(-10), NOLA(+8), DC(+8)

## Top Winners
1. DEN <60°F YES @4¢ → +$1,150 (forecast wrong but bet right)
2. LAX >84°F YES @5¢ → +$865 (LAX hit 87°F RECORD)
3. CHI <29°F YES @6¢ → +$750 (true edge — forecast close to actual)
4. SEA 62-63°F YES @10¢ → +$169

## Key Findings
1. **NWS Grid ≠ Station**: The #1 identified risk materialized. 7 cities off by >5°F
2. **Cheap tail bets = structural edge**: 3-6¢ YES bets have 20-25x payout when they hit
3. **σ was criminally underestimated**: MIN_SIGMA=1.5°F was insane. Need ≥3.0°F minimum
4. **Win rate doesn't matter if sizing is right**: 43% WR but +302% ROI
5. **Both NWS and OM were similarly bad**: Need more sources and calibration

## V2 Improvements Required
1. Per-city bias calibration offsets
2. Wider σ (3.0-8.0°F minimum by tier)
3. Only trade reliable cities initially
4. Kelly-inspired sizing (lean into cheap tail bets)
5. Add METAR observations (actual current temp)
6. Fix process lifetime bug (V1 died after 30min)
7. Accumulate forecast history for ongoing calibration
