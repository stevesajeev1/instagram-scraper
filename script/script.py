from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
from discord_webhook import DiscordWebhook
import json
import os
import schedule
import shutil
from skimage.metrics import structural_similarity
import stat
import subprocess
import time

PREVIOUS_DIR = os.path.join(".", "previous")
OUTPUT_DIR = os.path.join("..", "output")


with open('../config.json') as f:
    webhook_url = json.load(f)['webhook']


def cleanup_dir(parent_dir):
    for dir in os.listdir(parent_dir):
        dirpath = os.path.join(parent_dir, dir)

        if os.path.isdir(dirpath):
            shutil.rmtree(dirpath) 


def copy_dir(src, dest):
    for root, dirs, files in os.walk(src):
        for d in dirs:
            os.chmod(os.path.join(root, d), stat.S_IRWXU)
        for f in files:
            os.chmod(os.path.join(root, f), stat.S_IRWXU)

    for dir in os.listdir(src):
        dirpath = os.path.join(src, dir)
        if not os.path.isdir(dirpath):
            continue

        shutil.move(dirpath, dest)

        new_dirpath = os.path.join(dest, dir)
        for file in os.listdir(new_dirpath):
            if file.startswith("captions-"):
                filepath = os.path.join(new_dirpath, file)
                os.remove(filepath)


def run_scraper(profile):
    subprocess.run(
        [
            "docker", "compose", "run",
            "--rm", "--no-deps",
            "-e", f"PROFILE={profile}",
            "browser"
        ],
        check=True
    )


def send_post(username, dir, filepaths):
    post_filepath = os.path.join(dir, filepaths[0])
    caption_filepath = os.path.join(dir, filepaths[1])
    with open(post_filepath, "rb") as f:
        post = f.read()
    with open(caption_filepath, "rb") as f:
        caption = f.read()

    webhook = DiscordWebhook(url=webhook_url, username=username)
    webhook.add_file(file=post, filename="post.png")
    webhook.add_file(file=caption, filename="caption.png")
    webhook.execute()


def get_image_similarity(img1_path, img2_path) -> float:
    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)

    score = structural_similarity(img1, img2)
    return score # type: ignore


def compare_output(new, old, notify):
    for dir in os.listdir(new):
        new_dirpath = os.path.join(new, dir)
        if not os.path.isdir(new_dirpath):
            continue

        old_dirpath = os.path.join(old, dir)

        files = os.listdir(new_dirpath)
        posts_files = sorted(f for f in files if f.startswith("posts-"))
        captions_files = sorted(f for f in files if f.startswith("captions-"))
        new_files = list(zip(posts_files, captions_files))

        # First-time account: send everything
        if not os.path.isdir(old_dirpath):
            print(f"First time seeing account: {dir}")
            if notify:
                for file in new_files:
                    send_post(dir, new_dirpath, file)
            continue

        old_files = os.listdir(old_dirpath)

        # Determine which posts are new by comparing images
        new_posts = []
        max_similarities = []
        for new_file in new_files:
            new_file_path = os.path.join(new_dirpath, new_file[0])

            # Check if the new post exists in any old post
            is_new = True
            max_similarity = 0
            for old_file in old_files:
                old_file_path = os.path.join(old_dirpath, old_file)

                similarity = get_image_similarity(new_file_path, old_file_path)
                max_similarity = max(max_similarity, similarity)
                if similarity > 0.9:
                    is_new = False
                    break

            if is_new:
                new_posts.append(new_file)
                max_similarities.append(max_similarity)

        if new_posts:
            if notify:
                for file, sim in zip(new_posts, max_similarities):
                    print(f"New post by {dir}, similarity: {sim}")
                    send_post(dir, new_dirpath, file)
        else:
            print(f"No new posts by {dir}")


def job(notify=True):
    # Copy output to previous output
    print("Saving previous output...")
    cleanup_dir(PREVIOUS_DIR)
    copy_dir(OUTPUT_DIR, PREVIOUS_DIR)

    # Run scraper
    print("Running scrapers...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_scraper, "posts"), executor.submit(run_scraper, "captions")]
        for f in as_completed(futures):
            try:
                f.result()
            except subprocess.CalledProcessError as e:
                print("Scraper failed:", e)
                return

    # Compare images
    print("Comparing output...")
    compare_output(OUTPUT_DIR, PREVIOUS_DIR, notify)

    print("Job finished!")

subprocess.run(["docker", "compose", "up", "-d", "server"])
job(False)

schedule.every(30).to(90).minutes.do(job)
while True:
    schedule.run_pending()
    time.sleep(1)