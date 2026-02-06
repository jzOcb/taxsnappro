#!/bin/bash
# Fetch NWS CLI actual temperatures for Day 1 settlement verification
# Run: Feb 6, 8AM ET (13:00 UTC)

cd /home/clawdbot/clawd/btc-arbitrage

CITIES="KBOS KORD KLAX KMIA KPHX KSEA KSFO KLAS KATL KDEN KMSP KPHL KAUS KDCA KMSY"
OUTFILE="research/weather/actuals_2026-02-05.json"

echo "{" > "$OUTFILE"
echo '  "date": "2026-02-05",' >> "$OUTFILE"
echo '  "fetched_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",' >> "$OUTFILE"
echo '  "stations": {' >> "$OUTFILE"

for station in $CITIES; do
    # NWS CLI: get yesterday's high
    HIGH=$(curl -s "https://forecast.weather.gov/product.php?site=NWS&issuedby=${station:1:3}&product=CLI&format=txt" 2>/dev/null | grep -A1 "MAXIMUM" | tail -1 | awk '{print $1}' | tr -d '[:space:]')
    echo "    \"$station\": \"$HIGH\"," >> "$OUTFILE"
done

echo '  }' >> "$OUTFILE"
echo '}' >> "$OUTFILE"

echo "✅ Weather actuals saved to $OUTFILE"
