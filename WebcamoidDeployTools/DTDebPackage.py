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


def fakeroot():
    return DTUtils.whereBin('fakeroot')

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
                  section,
                  priority,
                  maintainer,
                  title,
                  descriptionFile,
                  homepage,
                  depends,
                  suggests,
                  recommends,
                  conflicts,
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

        # Create DEBIAN folder

        debianDir = os.path.join(debDataDir, 'DEBIAN')

        if not os.path.exists(debianDir):
            os.makedirs(debianDir)

        # Write the files links

        for link in links:
            try:
                lnk = os.path.join(debDataDir, link[0])
                os.makedirs(os.path.dirname(lnk))
                os.symlink(link[1], lnk)
            except:
                return False

        # Write the control file

        controlFile = os.path.join(debianDir, 'control')

        with open(controlFile, 'w', encoding='utf-8') as ctrlFile:
            ctrlFile.write('Package: {}\n'.format(packageName))
            ctrlFile.write('Version: {}\n'.format(version))

            if len(section) > 0:
                ctrlFile.write('Section: {}\n'.format(section))

            if len(priority) > 0:
                ctrlFile.write('Priority: {}\n'.format(priority))

            ctrlFile.write('Architecture: {}\n'.format(targetArch))
            ctrlFile.write('Maintainer: {}\n'.format(maintainer))
            ctrlFile.write('Description: {}\n'.format(title))

            if len(descriptionFile) > 0 and os.path.exists(descriptionFile):
                with open(descriptionFile) as description:
                    for line in description:
                        ctrlFile.write(' {}'.format(line))

            if len(depends) > 0:
                ctrlFile.write('Depends: {}\n'.format(', '.join(depends)))

            if len(suggests) > 0:
                ctrlFile.write('Suggests: {}\n'.format(', '.join(suggests)))

            if len(recommends) > 0:
                ctrlFile.write('Recommends: {}\n'.format(', '.join(recommends)))

            if len(conflicts) > 0:
                ctrlFile.write('Conflicts: {}\n'.format(', '.join(conflicts)))

            if len(homepage) > 0:
                ctrlFile.write('Homepage: {}\n'.format(homepage))

        # Build the package

        params = [fakeroot(),
                  dpkgDeb(),
                  '-v',
                  '--build',
                  debDataDir,
                  outPackage]

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        process.communicate()

        # Check with the linter

        lint = lintian()

        if len(lint) > 0:
            params = [lint, outPackage]

            if verbose:
                process = subprocess.Popen(params) # nosec
            else:
                process = subprocess.Popen(params, # nosec
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

            process.communicate()

        if not os.path.exists(outPackage):
            return

        mutex.acquire()

        if not 'outputPackages' in globs:
            globs['outputPackages'] = []

        globs['outputPackages'].append(outPackage)
        mutex.release()

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
    outPackage = os.path.join(outputDir, '{}_{}'.format(packageName, version))

    if not hideArch:
        outPackage += '_{}'.format(targetArch)

    outPackage += '.deb'

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
                  section,
                  priority,
                  maintainer,
                  title,
                  descriptionFile,
                  homepage,
                  depends,
                  suggests,
                  recommends,
                  conflicts,
                  installPrefix,
                  links,
                  verbose)
