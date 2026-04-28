#!/usr/bin/env bash
set -e

PROJECT_PATH="$1"
BEFORE_REF="$2"
AFTER_REF="$3"

if [ -z "$PROJECT_PATH" ] || [ -z "$BEFORE_REF" ] || [ -z "$AFTER_REF" ]; then
  echo "Usage: ./benchmark/runner.sh /path/to/project before-ref after-ref"
  exit 1
fi

echo "== ASTANALYZER BENCHMARK =="

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$PROJECT_ROOT/benchmark/results/$TIMESTAMP"

mkdir -p "$OUT_DIR"

echo "Output directory: $OUT_DIR"

run_scan () {
  REF=$1
  OUT_FILE=$2

  echo ""
  echo ">> Running for: $REF"

  git checkout "$REF"

  # reinstall (important if rules changed)
  pip install -e . > /dev/null

  # clean previous artifacts
  astanalyzer clean || true

  START=$(date +%s)

  astanalyzer scan "$PROJECT_PATH" --no-open

  END=$(date +%s)

  mv scan_report.json "$OUT_FILE"

  echo "Time: $((END - START))s" >> "$OUT_DIR/timing.txt"
  echo "$REF: $((END - START))s"
}

run_scan "$BEFORE_REF" "$OUT_DIR/before.json"
run_scan "$AFTER_REF" "$OUT_DIR/after.json"

# Save metadata
echo "Saving metadata..."

git rev-parse HEAD > "$OUT_DIR/analyzer_commit.txt"

pushd "$PROJECT_PATH" > /dev/null
git rev-parse HEAD > "$OUT_DIR/project_commit.txt" 2>/dev/null || echo "N/A" > "$OUT_DIR/project_commit.txt"
popd > /dev/null

cat <<EOF > "$OUT_DIR/meta.json"
{
  "project_path": "$PROJECT_PATH",
  "before_ref": "$BEFORE_REF",
  "after_ref": "$AFTER_REF",
  "timestamp": "$TIMESTAMP"
}
EOF

# Evaluate
echo ""
echo "== Evaluating =="

python "$PROJECT_ROOT/benchmark/evaluate.py" \
  "$OUT_DIR/before.json" \
  "$OUT_DIR/after.json" \
  > "$OUT_DIR/summary.txt"

echo "Done."
echo "Results in: $OUT_DIR"