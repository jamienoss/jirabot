#!/bin/bash
cd ~/jira
LANG=uk_UA.UTF-8 /usr/bin/python2.7 pulls.py
/usr/bin/python2.7 issues.py
