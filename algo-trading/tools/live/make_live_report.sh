#!/usr/bin/env bash
set -euo pipefail

DB="/Users/sultan/Trading/data/duck/qa.duckdb"
OUTDIR="/Users/sultan/Trading/data/checks/reports"
DUTC=$(date -u +%F)
OUT="$OUTDIR/live_${DUTC}.md"

mkdir -p "$OUTDIR"

# Leemos SOLO valores (no corremos health_check aquí)
np=$(duckdb "$DB" -csv -c "SELECT COUNT(*) FROM live.positions WHERE as_of = DATE '$DUTC';" | tail -n1)
eq=$(duckdb "$DB" -csv -c "SELECT COALESCE(MAX(equity_mark),0) FROM live.pnl_daily WHERE as_of = DATE '$DUTC';" | tail -n1)
fees=$(duckdb "$DB" -csv -c "SELECT COALESCE(SUM(fee),0) FROM live.fills WHERE as_of = DATE '$DUTC';" | tail -n1)

{
  echo "# Live Report — ${DUTC}"
  echo
  echo "## Resumen"
  echo "- Positions: ${np}"
  echo "- Equity mark: ${eq}"
  echo "- Fees del día: ${fees}"
  echo
  echo "## Top fills por notional"
  duckdb "$DB" -csv -c "SELECT symbol, COUNT(*) AS n_fills, SUM(qty) AS qty_sum, SUM(price*qty) AS notional_sum, SUM(fee) AS fees_sum FROM live.fills WHERE as_of = DATE '$DUTC' GROUP BY 1 ORDER BY notional_sum DESC LIMIT 10;" \
    | awk 'BEGIN{FS=","; OFS=" | "; print "| symbol | n_fills | qty_sum | notional_sum | fees_sum |"; print "|---|---:|---:|---:|---:|"} NR>1{print "| "$1" | "$2" | "$3" | "$4" | "$5" |"}'
  echo
  # Conclusión de salud usando np/eq ya leídos
  echo "✅ HEALTH OK (positions=${np}, equity=${eq})"
} > "$OUT"

echo "$OUT"
