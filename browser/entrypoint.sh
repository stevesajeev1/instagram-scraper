#!/bin/sh
set -e

BASE_URL="http://server:5000"
URL="$BASE_URL/accounts"
PROFILE_DIR="/profile"
SCREENSHOT_DIR="/output"
SIZE=1920
TIMEOUT=120

###############################################################################
# Timeout Helpers
###############################################################################

waitWithTimeout() {
    local seconds=$1
    local func=$2
    local start=$(date +%s)

    while true
    do
        if $func; then
            return 0
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

waitForLoad() {
    local loaded
    loaded=$(curl -s "$BASE_URL/status")
    [ "$loaded" = "true" ]
}

waitForInfo() {
    INFO=$(curl -s "$BASE_URL/info")
    [ -n "$INFO" ]
}

waitForScreenshotReady() {
    READY=$(curl -s "$BASE_URL/ready")
    [ -n "$READY" ]
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
    sleep 3
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

            import -window root "$SCREENSHOT_DIR/$INFO/$post.png"
            curl -s "$BASE_URL/screenshot" > /dev/null
            echo "Captured post $post"
            post=$((post + 1))
        done
    done
}

###############################################################################
# Setup
###############################################################################

Xvfb :99 -screen 0 ${SIZE}x${SIZE}x24 &
sleep 1

firefox --width "$SIZE" --height "$SIZE" --profile "$PROFILE_DIR" "$URL" &
sleep 3

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