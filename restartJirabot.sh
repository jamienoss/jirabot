#!/bin/bash
cd ~/jira
/bin/kill -9 `/bin/ps auxf | /bin/grep python | /bin/grep hello | /usr/bin/awk '{ print $2}'`
/usr/bin/python2.7 jirabot.py 2>&1 > jirabot.out & 
