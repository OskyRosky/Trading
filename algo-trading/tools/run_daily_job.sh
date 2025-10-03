#!/usr/bin/env bash
set -euo pipefail
cd /Users/sultan/Trading/algo-trading
source .venv/bin/activate
python tools/run_daily_delta.py
python tools/qa_report.py
python tools/qa_consolidate.py
python tools/run_features_all.py
python tools/ml/train_baseline.py
python tools/ml/export_signals_from_preds.py
python tools/bt/rebuild_equity_from_preds.py
python tools/bt/create_bt_views.py
python tools/bt/compare_with_benchmark.py --all
python tools/bt/report_bt.py
python tools/bt/alerts_bt.py
