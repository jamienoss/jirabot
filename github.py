# Copyright 2012 litl, LLC.  Licensed under the MIT license.

""" Simple Python api to github. Based on code at https://github.com/litl/leeroy """

import logging
from flask import json
import requests

GITHUB_BASE = "https://api.github.com"
GITHUB_COMMENT_URL = GITHUB_BASE + "/repos/{owner}/{repo_name}/issues/{number}/comments"
GITHUB_HOOKS_URL = GITHUB_BASE + "/repos/{owner}/{repo_name}/hooks"

def get_repo_name(pull_request, key):
    """ Extract repo name from a pull request dict. """
    return pull_request[key]["repo"]["name"]

def update_pull_request(number, comment, repo_owner, repo_name, auth):
    """ Update a github pull request by adding a comment. """
    url = GITHUB_COMMENT_URL.format(owner=repo_owner, repo_name=repo_name, number=number)
    params = dict(body=comment)
    headers = {"Content-Type": "application/json"}
    requests.post(url,
                  auth=auth,
                  data=json.dumps(params),
                  headers=headers)

def register_github_hooks(repo_name, repo_owner, auth, endpoint):
    """ Register hooks with github. Auth needs appropriate access to be allowed to do so. """
    url = GITHUB_HOOKS_URL.format(owner=repo_owner, repo_name=repo_name)
    response = requests.get(url, auth=auth)

    if not response.ok:
        logging.warn("Unable to install GitHub hook for repo %s (%s): %s %s",
                     repo_name, url, response.status_code, response.reason)
        return

    found_hook = False
    for hook in response.json:
        if hook["name"] != "web":
            continue

        if hook['config']['url'] == endpoint:
            found_hook = True
            break

    if not found_hook:
        params = {"name": "web",
                  "config": {"url": endpoint,
                             "content_type": "json"},
                  "events": ["pull_request"]}
        headers = {"Content-Type": "application/json"}

        response = requests.post(url,
                                 auth=auth,
                                 data=json.dumps(params),
                                 headers=headers)

        if response.ok:
            logging.info("Registered github hook for %s", repo_name)
        else:
            logging.error("Unable to register github hook for %s: %s",
                          repo_name, response.status_code)
