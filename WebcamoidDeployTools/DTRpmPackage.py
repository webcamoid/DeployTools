
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Webcamoid Deploy Tools.
# Copyright (C) 2024  Gonzalo Exequiel Pedone
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
import tempfile

from . import DTUtils


# https://www.redhat.com/sysadmin/create-rpm-package

def fakeroot():
    return DTUtils.whereBin('fakeroot')

# rpmdev-setuptree

def dpkgDeb():
    return DTUtils.whereBin('dpkg-deb')

def lintian():
    return DTUtils.whereBin('lintian')

def createDebFile(globs,
                  mutex,
                  targetArch,
                  dataDir,
                  outPackage,
                  packageName,
                  version,
                  installPrefix,
                  links,
                  verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        debDataDirName = os.path.splitext(os.path.basename(outPackage))[0]
        debDataDir = os.path.join(tmpdir, debDataDirName)
        prefixDir = os.path.join(debDataDir, installPrefix) if len(installPrefix) > 0 else debDataDir

        if not os.path.exists(prefixDir):
            os.makedirs(prefixDir)

        DTUtils.copy(dataDir, prefixDir)

def platforms():
    return ['posix']

def isAvailable(configs):
    if fakeroot() == '':
        return False

    return dpkgDeb() != ''

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    packageName = configs.get('DebPackage', 'name', fallback=name).strip()
    defaultTargetArch = configs.get('Package', 'targetArch', fallback='').strip()
    targetArch = configs.get('DebPackage', 'targetArch', fallback=defaultTargetArch).strip()
    section = configs.get('DebPackage', 'section', fallback='').strip()
    priority = configs.get('DebPackage', 'priority', fallback='optional').strip()
    maintainer = configs.get('DebPackage', 'maintainer', fallback='').strip()
    title = configs.get('DebPackage', 'title', fallback='').strip()
    descriptionFile = configs.get('DebPackage', 'descriptionFile', fallback='').strip()
    homepage = configs.get('DebPackage', 'homepage', fallback='').strip()
    depends = configs.get('DebPackage', 'depends', fallback='').strip()
    deps = set()

    if depends != '':
        for dep in depends.split(','):
            dep = dep.strip()

            if len(dep) > 0:
                deps.add(dep.strip())

    depends = list(deps)
    recommends = configs.get('DebPackage', 'recommends', fallback='').strip()
    deps = set()

    if recommends != '':
        for dep in recommends.split(','):
            dep = dep.strip()

            if len(dep) > 0:
                deps.add(dep.strip())

    recommends = list(deps)
    suggests = configs.get('DebPackage', 'suggests', fallback='').strip()
    deps = set()

    if suggests != '':
        for dep in suggests.split(','):
            dep = dep.strip()

            if len(dep) > 0:
                deps.add(dep.strip())

    suggests = list(deps)
    conflicts = configs.get('DebPackage', 'conflicts', fallback='').strip()
    deps = set()

    if conflicts != '':
        for dep in conflicts.split(','):
            dep = dep.strip()

            if len(dep) > 0:
                deps.add(dep.strip())

    conflicts = list(deps)

    links = configs.get('DebPackage', 'links', fallback='').strip()
    lnks = set()

    if links != '':
        for lnk in links.split(','):
            lnk = lnk.strip()

            if len(lnk) > 0:
                lnks.add(lnk.strip())

    links = [lnk.split(':') for lnk in lnks]
    installPrefix = configs.get('DebPackage', 'installPrefix', fallback='').strip()
    verbose = configs.get('DebPackage', 'verbose', fallback='true').strip()
    verbose = DTUtils.toBool(verbose)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    hideArch = configs.get('AppImage', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    releaseVersion = 1
    outPackage = os.path.join(outputDir, '{}-{}-{}'.format(packageName, version, releaseVersion))

    if not hideArch:
        outPackage += '.{}'.format(targetArch)

    outPackage += '.rpm'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createDebFile(globs,
                  mutex,
                  targetArch,
                  dataDir,
                  outPackage,
                  packageName,
                  version,
                  installPrefix,
                  links,
                  verbose)
