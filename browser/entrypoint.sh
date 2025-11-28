#!/bin/sh
set -e

BASE_URL="http://server:5000"
URL="$BASE_URL/accounts"
PROFILE_DIR="/profile"
SCREENSHOT_DIR="/output"
SIZE=1920

waitForLoad() {
    while true
    do
        LOADED=$(curl -s "$BASE_URL/status")
        if [ "$LOADED" = "true" ]; then
            break
        fi
        sleep 1
    done
}

waitForInfo() {
    while true
    do
        INFO=$(curl -s "$BASE_URL/info")
        if [ -n "$INFO" ]; then
            break
        fi
        sleep 1
    done
}

waitForScreenshotReady() {
    while true
    do
        READY=$(curl -s "$BASE_URL/ready")
        if [ -n "$READY" ]; then
            break
        fi
        sleep 1
    done
}

Xvfb :99 -screen 0 ${SIZE}x${SIZE}x24 &

sleep 1

firefox --width "$SIZE" --height "$SIZE" --profile "$PROFILE_DIR" "$URL" &

echo "Waiting for page to finish loading..."
waitForLoad
echo "Page has loaded!"

while true
do
    echo "Waiting for info..."
    waitForInfo
    if [ "$INFO" = "finish" ]; then
        echo "Finished scraping!"
        break
    fi
    echo "Scraping: $INFO!"
    mkdir -p "$SCREENSHOT_DIR/$INFO"

    post=1
    while true
    do
        waitForScreenshotReady
        if [ "$READY" = "finish" ]; then
            echo "Finished scraping posts for $INFO!"
            break
        fi

        import -window root "$SCREENSHOT_DIR/$INFO/$post.png"
        curl -s "$BASE_URL/screenshot" > /dev/null
        echo "Screenshotted post $post"
        post=$((post + 1))
    done
done