#!/usr/bin/python
""" Generate and optionally email information about JIRA issues stuck in'Discussing' state"""

import json
from collections import namedtuple
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import ConfigParser
import os
import requests

Summary = namedtuple('Summary', 'key, title, owner, creator, age, lastmod, security')

class JiraIssueReporter(object):
    """ Main class for generating Jira issue reports. """

    def __init__(self):

        def _read_config(config, section, name, default):
            if config.has_option(section, name):
                return config.get(section, name)
            else:
                return default


        def _read_config_bool(config, section, name, default):
            if config.has_option(section, name):
                return config.getboolean(section, name)
            else:
                return default

        config = ConfigParser.ConfigParser()
        config.optionxform = str  # case sensitive

        if not os.path.exists('issues.ini'):
            raise RuntimeError("issues.ini not found")
        config.read('issues.ini')

        self.email_user = _read_config(config, "email", "user", None)
        self.email_password = _read_config(config, "email", "password", None)
        self.email_server = _read_config(config, "email", "SMTP", None)
        self.email_from = _read_config(config, "email", "from", "GitHubPullBot")

        self.jira_url = _read_config(config, "jira", "url", None)
        self.jira_user = _read_config(config, "jira", "user", None)
        self.jira_password = _read_config(config, "jira", "password", None)

        self.specified_only = _read_config_bool(config, "options", "specifiedOnly", True)
        self.verbose = _read_config_bool(config, "options", "verbose", False)
        self.emails = {}

        if config.has_section('emails'):
            # These are people that always get the report... even if not otherwise
            # mentioned on it
            for user in config.items('emails'):
                self.emails[user[0]] = user[1]

    def _check_security(self, user_id, security):
        if security:
            return self.emails[user_id].endswith('lexisnexis.com') or self.emails[user_id].endswith('lnssi.com')
        else:
            return True

    def _fetch_email(self, user_id):
        if user_id in self.emails:
            return self.emails[user_id]
        else:
            return "none"

    def _output_row(self, summary):
        summary_text = '%-12s %-12s %-12s %-5d %-5d %s\n' % (
            summary.key, summary.owner, summary.creator,
            summary.age.days, summary.lastmod.days, summary.title)
        summary_html = """ \
<tr>
<td><a href="%s/browse/%s">%s</a></td>
<td class="leftaligned">%s</td>
<td><a href="mailto:%s">%s</a></td>
<td><a href="mailto:%s">%s</a></td>
<td>%d</td><td>%d</td>
</tr>\n
""" % (self.jira_url, summary.key, summary.key,
       summary.title,
       self._fetch_email(summary.owner), summary.owner,
       self._fetch_email(summary.creator), summary.creator,
       summary.age.days, summary.lastmod.days)
        return (summary_text, summary_html)

    def fetch_jira(self):
        """ read JIRAs that are in "discuss" state. """
        summaries = []
        now = datetime.now()
        if self.jira_url:
            jira_session = requests.Session()
            if self.jira_user and self.jira_password:
                jira_session.auth = (self.jira_user, self.jira_password)
            retcode = jira_session.get(
                "%s/rest/api/2/search?jql=status=Discussing" % self.jira_url)
            if retcode.ok:
                tickets = json.loads(retcode.text or retcode.content)
                for ticket in tickets['issues']:
                    fields = ticket['fields']
                    key = ticket['key']
                    updated = datetime.strptime(
                        fields['updated'], "%Y-%m-%dT%H:%M:%S.%f+0000")
                    created = datetime.strptime(
                        fields['created'], "%Y-%m-%dT%H:%M:%S.%f+0000")
                    creator = fields['reporter']['name']
                    if not self.specified_only:
                        self.emails[creator] = fields['reporter']['emailAddress']
                    if fields['assignee']:
                        owner = fields['assignee']['name']
                        if not self.specified_only:
                            self.emails[owner] = fields['assignee']['emailAddress']
                    else:
                        owner = creator
                    if 'security' in fields:
                        security = fields['security']['name']
                    else:
                        security = None
                    summary = fields['summary']
                    summaries.append(Summary(key=key, title=summary, owner=owner, creator=creator,
                                             age=now - created, lastmod=now - updated,
                                             security=security))
        return summaries

    def send_emails(self, summaries):
        """ Send out emails for all the summaries we created."""
        if self.email_user and self.email_password and self.email_server:
            gmail = smtplib.SMTP(self.email_server)
            gmail.starttls()
            gmail.login(self.email_user, self.email_password)
        else:
            gmail = None

        # One email per person in the dictionary

        for email in self.emails:
            summary_text = ''
            summary_html = ''
            owner_text = ''
            owner_html = ''
            creator_text = ''
            creator_html = ''
            for summary in sorted(summaries, key=lambda x: x.key):
                if self._check_security(email, summary.security):
                    text, html = self._output_row(summary)
                    if summary.owner == email:
                        owner_text += text
                        owner_html += html
                    elif summary.creator == email:
                        creator_text += text
                        creator_html += html
                    summary_text += text
                    summary_html += html

            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Pending Jira tickets summary'
            msg['From'] = self.email_from
            msg['To'] = self.emails[email]

            # Generate plaintext email contents

            text = ""
            if owner_text:
                text += """\
The following Jira tickets appear to be waiting for your attention:
%-12s %-12s %-12s %-5s %-5s %s
%s
""" % ('Key', 'Owner', 'Creator', 'Age', 'Idle', 'Title', owner_text)
            if creator_text:
                text += """\
%-12s %-12s %-12s %-5s %-5s %s
%s
""" % ('Key', 'Owner', 'Creator', 'Age', 'Idle', 'Title', creator_text)
            text += """\
The full list of Jira tickets awaiting discussion is as follows:
%-12s %-12s %-12s %-5s %-5s %s
%s
""" % ('Key', 'Owner', 'Creator', 'Age', 'Idle', 'Title', summary_text)

            # Generate HTML email contents

            html = """\
<html>
    <head>
    <style>
    table { 
    color: #333; /* Lighten up font color */
    font-family: Helvetica, Arial, sans-serif; /* Nicer font */
    width: 100%%;
    border-collapse: 
    collapse; border-spacing: 0; 
    }
    td, th { border: 1px solid #CCC; height: 30px; } /* Make cells a bit taller */
    th {
    background: #F3F3F3; /* Light grey background */
    font-weight: bold; /* Make sure they're bold */
    }

    td {
    background: #FAFAFA; /* Lighter grey background */
    text-align: center;
    padding-left: 10px;
    padding-right: 10px;
    }
    .leftaligned {
    text-align: left;
    }

    </style>   
    </head>
    <body>
    <p>The following Jira tickets appear to be waiting for your atttention:</p>
    <p>
    <table>
        <tr><th>Key</th><th>Title</th><th>Owner</th><th>Creator</th><th>Age</th><th>Stalled for</th></tr>
        %s
    </table>
    </p>
    <p>The following Jira tickets created by you appear to be awaiting attention from someone else:</p>
    <p>
    <table>
        <tr><th>Key</th><th>Title</th><th>Owner</th><th>Creator</th><th>Age</th><th>Stalled for</th></tr>
        %s
    </table>
    </p>
    <p>The full list of Jira tickets awaiting discussion is as follows:</p>
    <p>
    <table>
        <tr><th>Key</th><th>Title</th><th>Owner</th><th>Creator</th><th>Age</th><th>Stalled for</th></tr>
        %s
    </table>
    </p>
    </body>
</html>""" % (owner_html, creator_html, summary_html)

            # And send the email

            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))
            print "Emailing %s" % msg['To']
            if gmail:
                gmail.sendmail(msg['From'], msg['To'], msg.as_string())
            else:
                print "No email server set"
                if self.verbose:
                    print msg.as_string()

    # All done

        if gmail:
            gmail.quit()

def _main():
    reporter = JiraIssueReporter()
    summaries = reporter.fetch_jira()
    reporter.send_emails(summaries)

if __name__ == '__main__':
    _main()
