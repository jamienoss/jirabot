#!/usr/bin/python
from jira.client import JIRA
import github

#github.register_github_hooks('eclide', 'http://82.152.241.50:8080/notification/github')
github.register_github_hooks('h2h', 'http://82.152.241.50:8080/notification/github')
#github.register_github_hooks('HPCC-Platform', 'http://82.152.241.50:8080/notification/github')

