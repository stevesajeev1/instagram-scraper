#!/bin/sh
set -e

###############################################################################
# Config
###############################################################################

BASE_URL="http://server:5000"
SCREENSHOT_DIR="/output"
SIZE=1920
TIMEOUT=$((15 * 60))

URL="$BASE_URL/accounts/$PROFILE"
PROFILE_DIR="/profiles/$PROFILE"

curl() {
    command curl -H "X-Profile: $PROFILE" "$@"
}

###############################################################################
# Xvfb Helpers
###############################################################################

ensureXvfb() {
    local display_num="${DISPLAY#:}"
    local socket="/tmp/.X11-unix/X${display_num}"

    Xvfb "$DISPLAY" -screen 0 "${SIZE}x${SIZE}x24" &

    # Wait until the X socket appears
    while [ ! -e "$socket" ]; do
        sleep 1
    done
}

###############################################################################
# Timeout Helpers
###############################################################################

waitWithTimeout() {
    local seconds=$1
    local func=$2
    local start=$(date +%s)

    while true; do
        $func
        local status=$?

        if [ "$status" -eq 0 ]; then
            return 0   # success
        elif [ "$status" -eq 2 ]; then
            return 1   # fail immediately
        fi

        local now=$(date +%s)
        local elapsed=$((now - start))
        if [ "$elapsed" -ge "$seconds" ]; then
            echo "Timeout reached for $func!"
            return 1
        fi

        sleep 1
    done
}

waitForImageLoad() {
    local luma
    luma=$(import -window root miff:- | convert miff:- -resize 1x1! -format "%[fx:100*luma]" info:)

    local luma_int=${luma%.*}
    [ "$luma_int" -lt 93 ] || [ "$luma_int" -gt 97 ]
}

waitForLoad() {
    local loaded
    loaded=$(curl -s "$BASE_URL/status")

    if [ "$loaded" = "retry" ]; then
        return 2
    elif [ -n "$loaded" ]; then
        return 0
    else
        return 1
    fi
}

waitForInfo() {
    INFO=$(curl -s "$BASE_URL/info")

    if [ "$INFO" = "retry" ]; then
        return 2
    elif [ -n "$INFO" ]; then
        return 0
    else
        return 1
    fi
}

waitForScreenshotReady() {
    READY=$(curl -s "$BASE_URL/ready")

    if [ "$READY" = "retry" ]; then
        return 2
    elif [ -n "$READY" ]; then
        return 0
    else
        return 1
    fi
}

###############################################################################
# Firefox Restart
###############################################################################

restartFirefox() {
    echo "Restarting Firefox..."
    curl -s "$BASE_URL/retry" > /dev/null

    pkill -9 firefox || true
    sleep 1

    firefox --width "$SIZE" --height "$SIZE" --profile "$PROFILE_DIR" "$URL" &
    sleep 10
}

###############################################################################
# Main Scraper Logic (restartable)
###############################################################################

runScraper() {
    echo "Waiting for page load..."
    if ! waitWithTimeout "$TIMEOUT" waitForLoad; then
        restartFirefox
        return 1
    fi
    echo "Loaded!"

    while true
    do
        echo "Waiting for info..."

        if ! waitWithTimeout "$TIMEOUT" waitForInfo; then
            restartFirefox
            return 1
        fi

        if [ "$INFO" = "finish" ]; then
            echo "All scraping finished!"
            return 0
        fi

        echo "Scraping: $INFO"
        mkdir -p "$SCREENSHOT_DIR/$INFO"

        post=1
        while true
        do
            if ! waitWithTimeout "$TIMEOUT" waitForScreenshotReady; then
                restartFirefox
                return 1
            fi

            if [ "$READY" = "finish" ]; then
                echo "Finished posts for $INFO"
                break
            fi

            if [ "$PROFILE" = "posts" ]; then
                if ! waitWithTimeout "$TIMEOUT" waitForImageLoad; then
                    restartFirefox
                    return 1
                fi
            fi

            import -window root "$SCREENSHOT_DIR/$INFO/$PROFILE-$post.png"
            curl -s "$BASE_URL/screenshot" > /dev/null
            echo "Captured post $post"
            post=$((post + 1))
        done
    done
}

###############################################################################
# Setup
###############################################################################

ensureXvfb

firefox --width "$SIZE" --height "$SIZE" --profile "$PROFILE_DIR" "$URL" &
sleep 5

###############################################################################
# Supervising Loop (always restart from beginning on failure)
###############################################################################

while true
do
    if runScraper; then
        break
    fi

    echo "Restarting full workflow..."
done

echo "Done!"