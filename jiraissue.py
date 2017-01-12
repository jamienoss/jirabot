""" Simple interface to update jira issues in response to creation of a GitHub pull request."""
from jira.client import JIRA

ACTIVE_STATUS = ['Active', 'Open', 'New', 'Discussing', 'Awaiting Information']
JIRA_OPTIONS = {'server': 'https://track.hpccsystems.com'}
JIRA_URL = 'https://track.hpccsystems.com/browse/'
TRANSLATE_NAMES = {
    'dehilsterlexis': 'dehilster'
}

def update_jira(issue_name, pull_url, user, action, auth):
    """ Update a Jira issue to attach a pull request. """
    jira = JIRA(options=JIRA_OPTIONS, basic_auth=auth)
    issue = jira.issue(issue_name)
    if action == 'opened' or action == 'reopened':
        if user in TRANSLATE_NAMES:
            user = TRANSLATE_NAMES['user']
        status = JIRA_URL + issue_name + '\n'
        if not issue.fields.status.name in ACTIVE_STATUS:
            status += 'Jira not updated (state was not active or new)'
        elif issue.fields.customfield_10010 != None:
            status += 'Jira not updated (pull request already registered)'
        elif issue.fields.assignee is not None and \
             issue.fields.assignee.name.lower() != user.lower():
            status += 'Jira not updated (user does not match)'
        else:
            if issue.fields.assignee is None:
                jira.assign_issue(issue, user)
            issue.update(fields={'customfield_10010': pull_url})
            if issue.fields.status.name != 'Active':
                jira.transition_issue(issue, '71')   # Assign and schedule
            jira.transition_issue(issue, '81')   # Attach Pull Request
            status += 'Jira updated'
    else:
        status = ''  # Don't know if it was closed for accept or reject...
    return status
