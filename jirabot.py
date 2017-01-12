#!/usr/bin/env python

""" Simple server to responds to notifications from github when a pull request is opened, and
    link it to Jira issues. """

# pylint: disable=I0011,C0103,W0602,W0603


import re
import sys
import jiraissue
import github
from flask import Flask
from flask import request

jira_auth = None
github_auth = None

app = Flask(__name__)

@app.route("/notification/github", methods=['GET', 'POST'])
def jirabot():
    """ Responds to notifications from github when a pull request is opened. """
    global jira_auth
    global github_auth
    action = request.json["action"]
    pull_request = request.json["pull_request"]
    number = pull_request["number"]
    user = pull_request["user"]["login"]
    html_url = pull_request["html_url"]
    title = pull_request["title"]
    repo_owner = pull_request["base"]["repo"]["owner"]
    repo_name = pull_request["base"]["repo"]["name"]
    issue_match = re.search("(HPCC|HH|IDE|EPE|ML|ODBC)-[0-9]+", title)
    if (action == 'opened' or action == 'reopened') and issue_match:
        issue = issue_match.group()
        print "Received GitHub pull request notification from %s for %s (%s): %s: %s" % \
              (user, number, issue, action, title)
        status = jiraissue.update_jira(issue, html_url, user, action, jira_auth)
        if status != '':
            github.update_pull_request(number, status, repo_owner, repo_name, github_auth)

    return "Hello World!"

def _main():
    global jira_auth
    global github_auth
    jira_auth = (sys.argv[1], sys.argv[2])
    github_auth = (sys.argv[3], sys.argv[4])
    app.debug = True
    app.run(host="192.168.253.4", port=8080)

if __name__ == "__main__":
    _main()
