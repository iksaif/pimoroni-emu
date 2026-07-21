#!/usr/bin/env bash
# Smoke test for the emulator's badgeware (Tufty 2350) path.
# Usage:
#   scripts/smoke.sh                # run all apps + summary
#   scripts/smoke.sh menu           # run only a specific upstream app
#   scripts/smoke.sh menu --autosave # save frames to /tmp/smoke_frames/<app>/
#
# Reports OK / FAIL per app and (with --autosave) shows the unique colors
# present in the last rendered frame so you can spot "all-black" regressions.

set -u

OUT=/tmp/smoke_frames
DEVICE="tufty"
APPS_ROOT="vendor/tufty2350/firmware/apps"
SAVE=""

# Allow `--device <name>` as first arg to switch the badge family.
if [ $# -ge 2 ] && [ "$1" = "--device" ]; then
    DEVICE="$2"
    case "$DEVICE" in
        tufty*) APPS_ROOT="vendor/tufty2350/firmware/apps" ;;
        badger*) APPS_ROOT="vendor/badger2350/firmware/apps" ;;
        blinky*) APPS_ROOT="vendor/blinky2350/firmware/apps" ;;
    esac
    shift 2
fi

# Default app list — anything that's parseable by Python 3.10. (Hydrate uses
# 3.12 f-string syntax so it's excluded for Tufty.) We just list every app
# that exists under APPS_ROOT.
DEFAULT_APPS=($(ls "$APPS_ROOT" 2>/dev/null))

if [ $# -ge 1 ] && [ "$1" != "--autosave" ]; then
    apps=("$1")
    shift
else
    apps=("${DEFAULT_APPS[@]}")
fi

for arg in "$@"; do
    if [ "$arg" = "--autosave" ]; then SAVE="1"; fi
done

rm -rf "$OUT"
mkdir -p "$OUT"

pass=0; fail=0
for app in "${apps[@]}"; do
    app_path="$APPS_ROOT/$app/__init__.py"
    if [ ! -f "$app_path" ]; then
        printf "  SKIP %-22s (no __init__.py)\n" "$app"
        continue
    fi
    autosave_args=""
    if [ -n "$SAVE" ]; then
        mkdir -p "$OUT/$app"
        autosave_args="--autosave $OUT/$app"
    fi
    output=$(timeout 8 python -m emulator --device "$DEVICE" --headless --max-frames 3 $autosave_args "$app_path" 2>&1)
    # E-ink apps in FAST_UPDATE|NON_BLOCKING mode legitimately stop
    # refreshing once nothing has changed (matches real hardware) — with
    # no button input in headless mode they never reach max_frames, so an
    # idle timeout after at least one rendered frame is a pass, not a hang.
    if echo "$output" | grep -qE "Reached max frames|Idle timeout after [1-9][0-9]* frames"; then
        printf "  OK   %-22s" "$app"
        pass=$((pass+1))
        if [ -n "$SAVE" ] && [ -f "$OUT/$app/frame_00003.png" ]; then
            colors=$(python3 -c "
from PIL import Image
img = Image.open('$OUT/$app/frame_00003.png')
seen = set()
for y in range(0, img.height, 8):
    for x in range(0, img.width, 8):
        seen.add(img.getpixel((x, y)))
print(len(seen))" 2>/dev/null)
            printf " (%s unique colors in frame 3)" "$colors"
        fi
        printf "\n"
    else
        printf "  FAIL %-22s %s\n" "$app" "$(echo "$output" | grep -E 'App error|Error' | head -1 | cut -c -100)"
        fail=$((fail+1))
    fi
done

echo
echo "Summary: $pass pass / $fail fail (frames in $OUT/<app>/ when --autosave is set)"
