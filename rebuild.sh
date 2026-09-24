#!/usr/bin/env bash
# Rebuild the whole Hormozi Brain library from public sources. Safe to re-run: it only fetches what's missing.
set -euo pipefail
cd "$(dirname "$0")"; S=sources; mkdir -p $S/main-channel/vtt $S/acq-official $S/books
[ -d $S/moremozi-ask-hormozi ] || git clone -q --depth 1 https://github.com/poseljacob/ask-hormozi.git $S/moremozi-ask-hormozi
[ -d $S/acq-free-courses ]     || git clone -q --depth 1 https://github.com/Risedial/Alex-Hormozi-Full-Course-Content.git $S/acq-free-courses
[ -f $S/acq-official/100M-Journal.pdf ] || curl -sL -o $S/acq-official/100M-Journal.pdf 'https://www.acquisition.com/hubfs/$100M%20Journal.pdf'
[ -f $S/acq-official/100M-Journal.txt ] || pdftotext -layout $S/acq-official/100M-Journal.pdf $S/acq-official/100M-Journal.txt
# @AlexHormozi captions (new uploads are picked up on every run)
cd $S/main-channel
for t in videos streams; do yt-dlp --flat-playlist --print id "https://www.youtube.com/@AlexHormozi/$t" 2>/dev/null; done | sort -u > ids.txt
ls vtt/*.vtt 2>/dev/null | sed -E 's|.*/[0-9]{8}_(.*)\.en.*|\1|' | sort -u > done.txt || true
comm -23 ids.txt done.txt | xargs -P 4 -I{} yt-dlp --skip-download --write-auto-subs --write-subs --sub-langs "en,en-orig" \
  --sub-format vtt --ignore-errors --no-overwrites --write-info-json --sleep-requests 0.5 \
  -o "vtt/%(upload_date)s_%(id)s.%(ext)s" "https://youtu.be/{}" >> dl.log 2>&1 || true
cd ../..
python3 scripts/vtt2md.py $S/main-channel/vtt $S/main-channel/md
python3 scripts/build_index.py
