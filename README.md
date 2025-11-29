# Instagram Scraper

**A scraper that can be used to grab and get notified of the latest posts of <ins>public</ins> Instagram accounts.**

The scraping is performed via the [embedding feature](https://help.instagram.com/620154495870484) of Instagram. Two Docker containers are created, one with an instance of the Firefox browser and the other serving a page with the embeds of the public accounts configured to be scraped. The browser container takes screenshots of the embeds (coordinated via WebSockets), allowing for the posts to be scraped.

### Limitations
- The Instagram account must be public in order to be scraped.
- The scraper can only grab the latest **6** posts of a public Instagram account due to embed limitations.
- The scraper can only output square (1920x1920) images due to embed limitations. This means that if the post is of a different aspect ratio, it may be outputted cropped.
- The scraper, by default, sends notifications on new post via a Discord webhook.


## Usage
1. Install [Python](https://www.python.org/downloads/) and [Docker](https://docs.docker.com/engine/install/).


2. Create a `config.json` configuration file in the root directory. [This example file](./config.json.example) contains a list of keys with their descriptions.

3. Install packages for the Python script that coordinates and schedules scraping.
```shell
$ cd script
$ python -m venv venv

# activate venv
$ source venv/bin/activate # Linux
$ ./venv/Scripts/activate # Windows

$ pip install -r requirements.txt
```

4. Run the Python script.
```shell
$ python script.py
```