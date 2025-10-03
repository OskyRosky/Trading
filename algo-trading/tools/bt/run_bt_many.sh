#!/usr/bin/env bash
set -e
SYMS=("BTCUSDT" "ETHUSDT" "SOLUSDT" "BNBUSDT" "XRPUSDT")
for s in "${SYMS[@]}"; do
  python tools/bt/backtest_symbol_vs_hodl.py --symbol "$s" --fee_bps 2.0
done
