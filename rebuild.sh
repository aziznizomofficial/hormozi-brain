#!/usr/bin/env bash
# Rebuild the Hormozi Brain library. Safe to re-run: only fetches what is missing, picks up new uploads.
# Needs: python3.12, git, yt-dlp, pdftotext (poppler), rclone (only for the Drive books step).
set -euo pipefail
cd "$(dirname "$0")"; ROOT=$PWD; S=$ROOT/sources
mkdir -p $S/{main-channel,guest-interviews,acq-channel}/vtt $S/books/{drive,text,paged} $S/acq-official

# 0. Python env for semantic search
[ -x .venv/bin/python ] || { python3.12 -m venv .venv && .venv/bin/pip install -q fastembed numpy; }

# 1. Your own books/playbooks. Default: the Drive folder via rclone remote g1. Or drop PDFs into sources/books/drive yourself.
BOOKS_REMOTE="${BOOKS_REMOTE:-g1:Books BAZA/English/Alex Hormozi (All Books)}"
command -v rclone >/dev/null && rclone copy "$BOOKS_REMOTE" $S/books/drive --exclude "*ALL BOOKS*" 2>/dev/null || echo "skip Drive books (rclone/remote unavailable)"
.venv/bin/python scripts/prepare_books.py

# 2. Public corpora
[ -d $S/moremozi-ask-hormozi ] || git clone -q --depth 1 https://github.com/poseljacob/ask-hormozi.git $S/moremozi-ask-hormozi
[ -d $S/acq-free-courses ]     || git clone -q --depth 1 https://github.com/Risedial/Alex-Hormozi-Full-Course-Content.git $S/acq-free-courses

# 3. YouTube captions: @AlexHormozi (all, incl. new uploads), curated guest interviews, Acquisition.com channel
fetch() { # $1 = dir, stdin = video ids
  cd "$S/$1"; sort -u > want.txt
  ls vtt/*.vtt 2>/dev/null | sed -E 's|.*/[0-9]{8}_(.*)\.en.*|\1|' | sort -u > have.txt || true
  comm -23 want.txt have.txt | xargs -P 4 -I{} yt-dlp --skip-download --write-auto-subs --write-subs --sub-langs "en,en-orig" \
    --sub-format vtt --ignore-errors --no-overwrites --write-info-json --sleep-requests 0.5 \
    -o "vtt/%(upload_date)s_%(id)s.%(ext)s" "https://youtu.be/{}" >> dl.log 2>&1 || true
  cd "$ROOT"; rm -rf "$S/$1/md"; .venv/bin/python scripts/vtt2md.py "$S/$1/vtt" "$S/$1/md"
}
for t in videos streams; do yt-dlp --flat-playlist --print id "https://www.youtube.com/@AlexHormozi/$t" 2>/dev/null; done | fetch main-channel
cut -f1 scripts/guest-interviews.tsv | fetch guest-interviews
cat scripts/acq-channel-ids.txt | fetch acq-channel

# 4. Index (BM25 + embeddings), then card vectors are built lazily on first search
.venv/bin/python scripts/build_index.py
echo "Done. Try: scripts/hormozi search \"how do I raise prices\""
