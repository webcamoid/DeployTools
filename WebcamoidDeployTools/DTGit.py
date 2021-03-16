#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Webcamoid Deploy Tools.
# Copyright (C) 2021  Gonzalo Exequiel Pedone
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Web-Site: http://github.com/webcamoid/DeployTools/

import subprocess
import sys


def commitHash(path):
    try:
        process = subprocess.Popen(['git', 'rev-parse', 'HEAD'], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=path)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()
    except:
        return ''

def commitShortHash(path):
    try:
        process = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=path)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()
    except:
        return ''

def branch(path):
    try:
        process = subprocess.Popen(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=path)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()
    except:
        return ''

def commitCount(path):
    try:
        process = subprocess.Popen(['git', 'rev-list', '--count', 'HEAD'], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=path)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()
    except:
        return ''

def lastTag(path):
    try:
        process = subprocess.Popen(['git', 'describe', '--abbrev=0'], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=path)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()
    except:
        return ''

def commitCountSince(path, tag):
    try:
        process = subprocess.Popen(['git', 'rev-list', '--count', '{}..HEAD'.format(tag)], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=path)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()
    except:
        return ''

def commitCountSinceLastTag(path):
    tag = lastTag(path)

    if tag == '':
        return '';

    return commitCountSince(tag)
