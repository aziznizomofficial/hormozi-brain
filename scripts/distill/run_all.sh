#!/usr/bin/env bash
# Bulk distillation as used for the published knowledge layer. Workers coordinate through .lock files, so any
# number of them (different CLIs, different terminals) can share one run. Re-run any time to resume/retry.
#   run_all.sh books-codex      Codex, front of the book queue
#   run_all.sh books-gemini     Gemini Flash (Antigravity CLI), back of the book queue
#   run_all.sh videos-gemini    Gemini Flash, all videos in order: his channel, guests, Acquisition.com, coaching
#   run_all.sh videos-codex     Codex, guest interviews + Acquisition.com, then his channel from the back
#   run_all.sh videos-codex-back / videos-gemini-back   extra workers from the back of the coaching queue
cd "$(dirname "$0")/../.."; export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
PY=.venv/bin/python; D=scripts/distill/distill.py; mkdir -p build/distill; LOG=build/distill/$1.log
run() { $PY $D run "$@" 2>&1 | tee -a "$LOG"; }
case "$1" in
  books-codex)   run book --backend codex:gpt-6-astra:medium --run books --jobs 4 ;;
  books-gemini)  run book --backend agy:gemini-3.8-flash-high --run books --jobs 3 --reverse ;;
  videos-gemini) for k in main guest acq coaching; do run video --backend agy:gemini-3.8-flash-high --run videos --kinds $k --jobs 12; done ;;
  videos-codex)  run video --backend codex:gpt-6-astra:medium --run videos --kinds guest,acq --jobs 3
                 run video --backend codex:gpt-6-astra:medium --run videos --kinds main --jobs 3 --reverse ;;
  videos-codex-back)  run video --backend codex:gpt-6-astra:medium --run videos --kinds coaching --jobs 4 --reverse ;;
  videos-gemini-back) run video --backend agy:gemini-3.8-flash-high --run videos --kinds coaching,acq,guest --jobs 5 --reverse ;;
  *) echo "usage: $0 books-codex|books-gemini|videos-gemini|videos-codex|videos-codex-back|videos-gemini-back"; exit 1 ;;
esac
echo "== $1 finished; failures so far: $(ls build/distill/*/*.err 2>/dev/null | wc -l)"
