
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
import shutil
import subprocess
import tarfile
import tempfile

from . import DTUtils


def rpmbuild():
    return DTUtils.whereBin('rpmbuild')

def rpmlint():
    return DTUtils.whereBin('rpmlint')

def createRpmFile(globs,
                  mutex,
                  targetArch,
                  dataDir,
                  outPackage,
                  packageName,
                  version,
                  summary,
                  descriptionFile,
                  changelogFile,
                  licenseName,
                  homepage,
                  requires,
                  suggests,
                  recommends,
                  conflicts,
                  installPrefix,
                  links,
                  verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        rpmbuildDir = os.path.join(os.path.expanduser("~"), 'rpmbuild')

        # Delete old rpmbuild directory

        try:
            shutil.rmtree(rpmbuild)
        except:
            pass

        # Create folder templates

        folderTemplates = ['BUILD',
                           'RPMS',
                           'SOURCES',
                           'SPECS',
                           'SRPMS']

        for folder in folderTemplates:
            path = os.path.join(rpmbuildDir, folder)

            if not os.path.exists(path):
                os.makedirs(path)

        # Move files to a temporal directory

        tempDataDir = os.path.join(tmpdir, 'data')
        prefixDir = os.path.join(tempDataDir, installPrefix) if len(installPrefix) > 0 else tempDataDir

        if not os.path.exists(prefixDir):
            os.makedirs(prefixDir)

        DTUtils.copy(dataDir, prefixDir)

        # Write the files links

        for link in links:
            try:
                lnk = os.path.join(tempDataDir, link[0])
                os.makedirs(os.path.dirname(lnk))
                os.symlink(link[1], lnk)
            except:
                return False

        # List installed files

        installedFiles = []

        for root, dirs, files in os.walk(tempDataDir):
            installRootPath = root.replace(tempDataDir, '')

            for f in files:
                installedFiles.append(os.path.join(installRootPath, f))

        # Write files to the SOURCES directory

        compression = 'gz'
        rpmDataDirName = '{}-{}'.format(packageName, version)
        sourceFileName = '{}.tar.{}'.format(rpmDataDirName, compression)
        compressedFile = os.path.join(rpmbuildDir, 'SOURCES', sourceFileName)

        with tarfile.open(compressedFile, "w:" + compression) as tar:
            tar.add(tempDataDir, arcname=rpmDataDirName)

        # Write .spec file

        specFile = os.path.join(rpmbuildDir, 'SPECS', packageName + '.spec')

        with open(specFile, 'w', encoding='utf-8') as spec:
            spec.write('Name: {}\n'.format(packageName))
            spec.write('Version: {}\n'.format(version))
            spec.write('Release: 1%{?dist}\n')
            spec.write('Summary: {}\n'.format(summary))
            spec.write('BuildArch: {}\n'.format(targetArch))
            spec.write('License: {}\n'.format(licenseName))
            spec.write('URL: {}\n'.format(homepage))
            spec.write('Source0: {}\n'.format(sourceFileName))

            for dep in requires:
                spec.write('Requires: {}\n'.format(dep))

            for dep in suggests:
                spec.write('Suggests: {}\n'.format(dep))

            for dep in recommends:
                spec.write('Recommends: {}\n'.format(dep))

            for dep in conflicts:
                spec.write('Conflicts: {}\n'.format(dep))

            spec.write('\n')
            spec.write('%description\n')

            if len(descriptionFile) > 0 and os.path.exists(descriptionFile):
                with open(descriptionFile) as description:
                    for line in description:
                        spec.write(line)

            spec.write('\n')
            spec.write('%prep\n')
            spec.write('\n')
            spec.write('%build\n')
            spec.write('\n')
            spec.write('%install\n')
            spec.write('cp -rvf %{name}-%{version}/* "%{buildroot}"\n')
            spec.write('\n')
            spec.write('%files\n')

            for f in installedFiles:
                spec.write(f + '\n')

            spec.write('\n')

            if len(changelogFile) > 0 and os.path.exists(changelogFile):
                spec.write('%changelog\n')

                with open(changelogFile) as changelog:
                    for line in changelog:
                        spec.write(line)

        # Check with the linter

        lint = rpmlint()

        if len(lint) > 0:
            params = [lint, specFile]

            if verbose:
                process = subprocess.Popen(params) # nosec
            else:
                process = subprocess.Popen(params, # nosec
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

            process.communicate()

        # Build the package

        params = [rpmbuild(),
                  '-v',
                  '-bb',
                  specFile]

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        process.communicate()

        outRpm = os.path.join(rpmbuildDir,
                              'RPMS',
                              targetArch,
                              os.path.basename(outPackage))

        if os.path.exists(outRpm):
            outDir = os.path.dirname(outPackage)

            if not os.path.exists(outDir):
                os.makedirs(outDir)

            # Remove old file
            if os.path.exists(outPackage):
                os.remove(outPackage)

            DTUtils.copy(outRpm, outPackage)

        # Delete rpmbuild directory

        try:
            shutil.rmtree(rpmbuild)
        except:
            pass

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
    return rpmbuild() != ''

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)

    if not re.match('^[0-9]', version):
        version = '0.0.0'

    packageName = configs.get('RpmPackage', 'name', fallback=name).strip()
    defaultTargetArch = configs.get('Package', 'targetArch', fallback='').strip()
    targetArch = configs.get('RpmPackage', 'targetArch', fallback=defaultTargetArch).strip()
    summary = configs.get('RpmPackage', 'summary', fallback='').strip()
    descriptionFile = configs.get('RpmPackage', 'descriptionFile', fallback='').strip()
    changeLogFile = configs.get('RpmPackage', 'changelog', fallback='').strip()

    if len(changeLogFile) > 0:
        changeLogFile = os.path.join(sourcesDir, changeLogFile)

    homepage = configs.get('RpmPackage', 'homepage', fallback='').strip()
    licenseName = configs.get('RpmPackage', 'license', fallback='').strip()
    requires = configs.get('RpmPackage', 'requires', fallback='').strip()
    deps = set()

    if requires != '':
        for dep in requires.split(','):
            dep = dep.strip()

            if len(dep) > 0:
                deps.add(dep.strip())

    requires = list(deps)
    recommends = configs.get('RpmPackage', 'recommends', fallback='').strip()
    deps = set()

    if recommends != '':
        for dep in recommends.split(','):
            dep = dep.strip()

            if len(dep) > 0:
                deps.add(dep.strip())

    recommends = list(deps)
    suggests = configs.get('RpmPackage', 'suggests', fallback='').strip()
    deps = set()

    if suggests != '':
        for dep in suggests.split(','):
            dep = dep.strip()

            if len(dep) > 0:
                deps.add(dep.strip())

    suggests = list(deps)
    conflicts = configs.get('RpmPackage', 'conflicts', fallback='').strip()
    deps = set()

    if conflicts != '':
        for dep in conflicts.split(','):
            dep = dep.strip()

            if len(dep) > 0:
                deps.add(dep.strip())

    conflicts = list(deps)

    links = configs.get('RpmPackage', 'links', fallback='').strip()
    lnks = set()

    if links != '':
        for lnk in links.split(','):
            lnk = lnk.strip()

            if len(lnk) > 0:
                lnks.add(lnk.strip())

    links = [lnk.split(':') for lnk in lnks]
    installPrefix = configs.get('RpmPackage', 'installPrefix', fallback='').strip()
    verbose = configs.get('RpmPackage', 'verbose', fallback='true').strip()
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

    createRpmFile(globs,
                  mutex,
                  targetArch,
                  dataDir,
                  outPackage,
                  packageName,
                  version,
                  summary,
                  descriptionFile,
                  changeLogFile,
                  licenseName,
                  homepage,
                  requires,
                  suggests,
                  recommends,
                  conflicts,
                  installPrefix,
                  links,
                  verbose)
