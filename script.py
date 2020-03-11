import mechanicalsoup
import re
import os
import time
import json
import urllib
import logging
import requests
import yaml

# setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# load config
CONFIG = "config.yml"
with open(CONFIG) as f:
    config = yaml.load(f, Loader=yaml.SafeLoader)

# setup env
envs = ["EVENTERNOTE_USERNAME", "EVENTERNOTE_PASSWORD", "SLACK_WEBHOOK_URL"]
username, password, slack_webhook_url = [
    config["EVENTERNOTE"]["EVENTERNOTE_USERNAME"]
    , config["EVENTERNOTE"]["EVENTERNOTE_PASSWORD"]
    , config["SLACK"]["WEBHOOK"]]

BASE_URL = "https://www.eventernote.com"

def slack_text(event_dict, cast_dict):
    text = "New %d events:\n\n" % len(event_dict)
    for k, v in cast_dict.items():
        text += "【%s】\n" % k
        for vv in sorted(v, key=lambda e: e["event"]):
            text += "・<%s|%s>\n" % (vv["url"], vv["event"])
    return text

def login_search():
    br = mechanicalsoup.StatefulBrowser()
    br.open(BASE_URL + "/login")
    br.select_form("#login_form")
    br["email"] = username
    br["password"] = password
    br.submit_selected()
    br.open(BASE_URL + "/users/notice")
    event_dict = {}
    new_events = sorted(
        br.get_current_page().select("div.gb_timeline_list > ul > li"),
        key=lambda e: e.find_all("a")[1].text
    )
    for event in [
        e for e in reversed(new_events)
        if not re.search("(日前|年前)", e.find("span").text)
            and e.attrs["class"] != "past"
            and not re.search("重複", e.find_all("a")[1].text)
    ]:
        cast = event.find("a").text
        title = event.find_all("a")[1].text
        url = BASE_URL + event.find_all("a")[1].attrs["href"]

        if not title in event_dict:
            event_dict[title] = {"cast": [cast], "url": url}
        else:
            event_dict[title]["cast"].append(cast)

    if len(event_dict.keys()) == 0:
        logger.info("no events")
        return
    return event_dict

def slack_cast(event_dict):
    cast_dict = {}
    for k, v in event_dict.items():
        casts = " / ".join(sorted(set(v["cast"])))

        if not casts in cast_dict:
            cast_dict[casts] = []

        cast_dict[casts].append({"event": k, "url": v["url"]})

    slack_payload = {
        "text": slack_text(event_dict, cast_dict),
    }
    logger.info(slack_payload)

#    binary_data = json.dumps(slack_payload).encode("utf8")
#    urllib.request.urlopen(slack_webhook_url, binary_data)

def lambda_handler(event, context):
    event_dict = login_search()
    slack_cast(event_dict)

if __name__ == "__main__":
    event_dict = login_search()
    slack_cast(event_dict)