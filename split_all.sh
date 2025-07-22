#!/usr/bin/bash

set -euo pipefail


display_usage() {
  echo "Usage: $0 [-s|-c|-m] <bench-list-file>"
}

display_help() {
    display_usage
    echo ""
    echo "-s    Split benchmarks into <benchmark>_main.c and <benchmark>_module.[c|h] files"
    echo "-c    Clean created files"
    echo "-m    Monte Carlo Autotuning"
}


split=false
clean=false

while getopts ":hsc" opt; do
    case $opt in
        h)  display_help;
            exit 0;;
        s)  split=true;;
        c)  clean=true;;
        m)  monte_carlo=true;;
        *)  display_usage;
            exit 0 ;;
    esac
done

shift $((OPTIND-1))
if [[ $# -ne 1 ]]; then
    display_usage
    exit 1
fi
LIST_FILE="$1"
SCRIPT_DIR="$(dirname "$0")"
SPLIT_SCRIPT="$SCRIPT_DIR/split_kernel.py"

if [[ ! -f "$SPLIT_SCRIPT" && "$split" ]]; then
  echo "Error: cannot find split_kernel.py in $SCRIPT_DIR"
  exit 1
fi

while IFS= read -r bench_path; do
  # skip empty lines or comments
  [[ -z "$bench_path" || "${bench_path:0:1}" == "#" ]] && continue
  if $split; then
    echo "Splitting $bench_path..."
    python3 "$SPLIT_SCRIPT" "$bench_path"
  fi
  if $clean; then
    path=$(dirname "$bench_path")
    echo "Cleaning $path..."
    rm -f "$path"/*_main.c "$path"/*_module.* "$path"/*.bc "$path"/*.o
  fi
done < "$LIST_FILE"
