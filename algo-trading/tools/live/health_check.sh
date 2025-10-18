#!/bin/zsh
set -euo pipefail
DB="/Users/sultan/Trading/data/duck/qa.duckdb"
DUTC=$(date -u +%F)
echo "=== HEALTH CHECK $(date -u +'%F %T')Z ==="
q_csv() { duckdb "$DB" -csv -c "$1" | tail -n 1; }
n_positions=$(q_csv "SELECT COUNT(*) FROM live.positions WHERE as_of = DATE '$DUTC';")
equity_calc=$(q_csv "SELECT COALESCE(SUM(qty*mark),0) FROM live.positions WHERE as_of = DATE '$DUTC';")
equity_mark=$(q_csv "SELECT COALESCE(MAX(equity_mark),0) FROM live.pnl_daily WHERE as_of = DATE '$DUTC';")
if [ -z "$n_positions" ]; then n_positions=0; fi
if [ -z "$equity_calc" ]; then equity_calc=0; fi
if [ -z "$equity_mark" ]; then equity_mark=0; fi
if [ "$n_positions" -gt 0 ]; then ok_positions=1; else ok_positions=0; fi
diff=$(awk -v a="$equity_calc" -v b="$equity_mark" 'BEGIN{d=a-b; if (d<0) d=-d; printf "%.6f", d}')
ok_equity=$(awk -v d="$diff" 'BEGIN{print (d<0.01)?1:0}')
if [ "$ok_positions" -eq 1 ] && [ "$ok_equity" -eq 1 ]; then
  echo "HEALTH OK positions=$n_positions equity~$equity_mark"
  exit 0
else
  echo "HEALTH FAIL positions=$n_positions equity_calc=$equity_calc pnl_daily=$equity_mark diff=$diff"
  exit 1
fi
