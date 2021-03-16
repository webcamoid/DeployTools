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

import os
import subprocess
import sys

from . import DTUtils


def searchBrew(path):
    brew = DTUtils.whereBin('brew')

    if len(brew) > 0:
        process = subprocess.Popen([brew, '--cellar'], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()
        cellarPath = stdout.decode(sys.getdefaultencoding()).strip()

        if not path.startswith(cellarPath):
            return ''

        return ' '.join(path.replace(cellarPath + os.sep, '').split(os.sep)[0: 2])

    return ''

def searchPacman(path):
    path = path.replace('\\', '/')
    pacman = DTUtils.whereBin('pacman')

    if len(pacman) > 0:
        process = subprocess.Popen([pacman, '-Qo', path], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        info = stdout.decode(sys.getdefaultencoding()).split(' ')

        if len(info) < 2:
            return ''

        package, version = info[-2:]

        return ' '.join([package.strip(), version.strip()])

    return ''

def searchDpkg(path):
    dpkg = DTUtils.whereBin('dpkg')

    if len(dpkg) > 0:
        process = subprocess.Popen([dpkg, '-S', path], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        package = stdout.split(b':')[0].decode(sys.getdefaultencoding()).strip()
        process = subprocess.Popen([dpkg, '-s', package], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        for line in stdout.decode(sys.getdefaultencoding()).split('\n'):
            line = line.strip()

            if line.startswith('Version:'):
                return ' '.join([package, line.split()[1].strip()])

        return ''

    return ''

def searchRpm(path):
    rpm = DTUtils.whereBin('rpm')

    if len(rpm) > 0:
        process = subprocess.Popen([rpm, '-qf', path], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()

    return ''

def searchPkg(path):
    pkg = DTUtils.whereBin('pkg')

    if len(pkg) > 0:
        process = subprocess.Popen([pkg, 'which', '-q', path], # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()

    return ''

def searchPackageFor(path):
    os.environ['LC_ALL'] = 'C'
    packageManagers = {
        'brew': searchBrew,
        'pacman': searchPacman,
        'dpkg': searchDpkg,
        'rpm': searchRpm,
        'pkg': searchPkg
    }

    for manager in packageManagers:
        mgr = DTUtils.whereBin(manager)

        if len(mgr) > 0:
            return packageManagers[manager](path)

    return ''
