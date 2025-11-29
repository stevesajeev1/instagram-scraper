import cv2
from discord_webhook import DiscordWebhook
from elevate import elevate
import json
import os
import schedule
import shutil
from skimage.metrics import structural_similarity as ssim
import subprocess
import time

PREVIOUS_DIR = os.path.join(".", "previous")
OUTPUT_DIR = os.path.join("..", "output")

with open('../config.json') as f:
    webhook_url = json.load(f)['webhook']


def cleanup_dir(dir):
    for dir in os.listdir(dir):
        dirpath = os.path.join(dir, dir)

        if os.path.isdir(dirpath):
            shutil.rmtree(dirpath) 


def copy_dir(src, dest):
    for dir in os.listdir(src):
        dirpath = os.path.join(src, dir)

        if os.path.isdir(dirpath):
            shutil.copytree(dirpath, dest, dirs_exist_ok=True)


def send_file(filepath):
    with open(filepath, "rb") as f:
        webhook = DiscordWebhook(url=webhook_url)
        webhook.add_file(file=f.read(), filename="post.png")
        webhook.execute()


def get_image_similarity(img1_path, img2_path) -> float:
    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)

    score = ssim(img1, img2)
    return score # type: ignore


def compare_output(new, old):
    for dir in os.listdir(new):
        new_dirpath = os.path.join(new, dir)
        if not os.path.isdir(new_dirpath):
            continue

        old_dirpath = os.path.join(old, dir)
        new_files = os.listdir(new_dirpath)

        # First-time account: send everything
        if not os.path.isdir(old_dirpath):
            print(f"New posts by {dir}")
            DiscordWebhook(url=webhook_url, content=f"New posts by {dir}").execute()
            for file in new_files:
                send_file(os.path.join(new_dirpath, file))
            continue

        old_files = os.listdir(old_dirpath)

        # Determine which posts are new by comparing images
        new_posts = []
        for new_file in new_files:
            new_file_path = os.path.join(new_dirpath, new_file)

            # Check if the new post exists in any old post
            is_new = True
            max_similarity = 0
            for old_file in old_files:
                old_file_path = os.path.join(old_dirpath, old_file)

                similarity = get_image_similarity(new_file_path, old_file_path)
                max_similarity = max(max_similarity, similarity)
                if similarity > 0.7:
                    is_new = False
                    break

            if is_new:
                new_posts.append(new_file)

        if new_posts:
            print(f"New posts by {dir}")
            DiscordWebhook(url=webhook_url, content=f"New posts by {dir} (max similarity {max_similarity})").execute()
            for file in new_posts:
                send_file(os.path.join(new_dirpath, file))
                pass
        else:
            print(f"No new posts by {dir}")


def job():
    # Copy output to previous output
    print("Saving previous output...")
    cleanup_dir(PREVIOUS_DIR)
    copy_dir(OUTPUT_DIR, PREVIOUS_DIR)
    cleanup_dir(OUTPUT_DIR)

    # Run scraper
    print("Running scraper...")
    try:
        subprocess.run(["docker", "compose", "run", "--rm", "browser"], check=True)
    except subprocess.CalledProcessError as e:
        print("Scraper failed:", e)
        return

    # Compare images
    print("Comparing output...")
    compare_output(OUTPUT_DIR, PREVIOUS_DIR)

    print("Job finished!")

elevate()
job()

schedule.every(60).to(120).minutes.do(job)
while True:
    schedule.run_pending()
    time.sleep(1)