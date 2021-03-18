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
import re
import subprocess
import tempfile
import time

from . import DTUtils


def binarycreator(targetPlatform):
    # Try official Qt binarycreator first because it is statically linked.
    homeQt = ''

    if DTUtils.hostPlatform() == 'windows':
        homeQt = 'C:\\Qt'
    elif targetPlatform == 'windows':
        if 'WINEPREFIX' in os.environ:
            homeQt = os.path.expanduser(os.path.join(os.environ['WINEPREFIX'],
                                                     'drive_c/Qt'))
        else:
            homeQt = os.path.expanduser('~/.wine/drive_c/Qt')
    else:
        homeQt = os.path.expanduser('~/Qt')

    binCreator = 'binarycreator'

    if targetPlatform == 'windows':
        binCreator += '.exe'

    for root, _, files in os.walk(homeQt):
        for f in files:
            if f == binCreator:
                return os.path.join(root, f)

    # binarycreator offered by the system is most probably dynamically
    # linked, so it's useful for test purposes only, but not recommended
    # for distribution.

    return DTUtils.whereBin(binCreator)

def readChangeLog(changeLog, appName, version):
    if os.path.exists(changeLog):
        with open(changeLog) as f:
            for line in f:
                if not line.startswith('{0} {1}:'.format(appName, version)):
                    continue

                # Skip first line.
                f.readline()
                changeLogText = ''

                for line_ in f:
                    if re.match('{} \d+\.\d+\.\d+:'.format(appName), line):
                        # Remove last line.
                        i = changeLogText.rfind('\n')

                        if i >= 0:
                            changeLogText = changeLogText[: i]

                        return changeLogText

                    changeLogText += line_

    return ''

def createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    targetPlatform,
                    name,
                    version,
                    organization,
                    appName,
                    appIcon,
                    title,
                    description,
                    licenseFile,
                    licenseName,
                    url,
                    targetDir,
                    runProgram,
                    runProgramDescription,
                    installScript,
                    changeLog,
                    requiresAdminRights):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create layout
        componentName = '{}.{}'.format(organization, name)
        installerConfig = os.path.join(tmpdir, 'config')
        installerPackages = os.path.join(tmpdir, 'packages')
        packageDir = os.path.join(installerPackages, componentName)

        if not os.path.exists(installerConfig):
            os.makedirs(installerConfig)

        installerDataDir = os.path.join(packageDir, 'data')
        installerMetaDir = os.path.join(packageDir, 'meta')

        if not os.path.exists(installerDataDir):
            os.makedirs(installerDataDir)

        if not os.path.exists(installerMetaDir):
            os.makedirs(installerMetaDir)

        iconName = ''

        if appIcon != '' and os.path.exists(appIcon):
            DTUtils.copy(appIcon, installerConfig)
            iconName = os.path.splitext(os.path.basename(appIcon))[0]

        licenseOutFile = os.path.basename(licenseFile)

        if not '.' in licenseOutFile and \
            (targetPlatform == 'windows'):
            licenseOutFile += '.txt'

        DTUtils.copy(licenseFile, os.path.join(installerMetaDir, licenseOutFile))
        DTUtils.copy(dataDir, installerDataDir)

        configXml = os.path.join(installerConfig, 'config.xml')

        with open(configXml, 'w') as config:
            config.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            config.write('<Installer>\n')
            config.write('    <Name>{}</Name>\n'.format(appName))

            if 'DAILY_BUILD' in os.environ:
                config.write('    <Version>0.0.0</Version>\n')
            else:
                config.write('    <Version>{}</Version>\n'.format(version))

            config.write('    <Title>{}</Title>\n'.format(title))
            config.write('    <Publisher>{}</Publisher>\n'.format(appName))
            config.write('    <ProductUrl>{}</ProductUrl>\n'.format(url))

            if iconName != '':
                config.write('    <InstallerWindowIcon>{}</InstallerWindowIcon>\n'.format(iconName))
                config.write('    <InstallerApplicationIcon>{}</InstallerApplicationIcon>\n'.format(iconName))
                config.write('    <Logo>{}</Logo>\n'.format(iconName))

            if runProgram != '':
                config.write('    <RunProgram>{}</RunProgram>\n'.format(runProgram))

                if runProgramDescription != '':
                    config.write('    <RunProgramDescription>{}</RunProgramDescription>\n'.format(runProgramDescription))

                config.write('    <StartMenuDir>{}</StartMenuDir>\n'.format(appName))

            config.write('    <MaintenanceToolName>{}Uninstall</MaintenanceToolName>\n'.format(appName))
            config.write('    <AllowNonAsciiCharacters>true</AllowNonAsciiCharacters>\n')
            config.write('    <TargetDir>{}</TargetDir>\n'.format(targetDir))
            config.write('</Installer>\n')

        script = os.path.basename(installScript)
        DTUtils.copy(installScript,
                     os.path.join(installerMetaDir, script))

        with open(os.path.join(installerMetaDir, 'package.xml'), 'w') as f:
            f.write('<?xml version="1.0"?>\n')
            f.write('<Package>\n')
            f.write('    <DisplayName>{}</DisplayName>\n'.format(appName))
            f.write('    <Description>{}</Description>\n'.format(description))

            if 'DAILY_BUILD' in os.environ:
                f.write('    <Version>0.0.0</Version>\n')
            else:
                f.write('    <Version>{}</Version>\n'.format(version))

            f.write('    <ReleaseDate>{}</ReleaseDate>\n'.format(time.strftime('%Y-%m-%d')))
            f.write('    <Name>{}</Name>\n'.format(componentName))
            f.write('    <Licenses>\n')
            f.write('        <License name="{0}" file="{1}" />\n'.format(licenseName, licenseOutFile))
            f.write('    </Licenses>\n')
            f.write('    <Script>{}</Script>\n'.format(script))
            f.write('    <UpdateText>\n')

            if not 'DAILY_BUILD' in os.environ:
                f.write(readChangeLog(changeLog, appName, version))

            f.write('    </UpdateText>\n')
            f.write('    <Default>true</Default>\n')
            f.write('    <ForcedInstallation>true</ForcedInstallation>\n')
            f.write('    <Essential>false</Essential>\n')

            if requiresAdminRights:
                f.write('    <RequiresAdminRights>true</RequiresAdminRights>\n')

            f.write('</Package>\n')

        params = []

        if DTUtils.hostPlatform() != 'windows' and targetPlatform == 'windows':
            params = ['wine']

        params += [binarycreator(targetPlatform),
                   '--offline-only',
                   '-c', configXml,
                   '-p', installerPackages,
                   '-v',
                   outPackage]
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
    return ['mac', 'posix', 'windows']

def isAvailable(configs):
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()

    if len(binarycreator(targetPlatform)) < 1:
        return False

    return True

def run(globs, configs, dataDir, outputDir, mutex):
    name = configs.get('Package', 'name', fallback='app').strip()
    version = configs.get('Package', 'version', fallback='1.0.0').strip()
    packageName = configs.get('QtIFW', 'name', fallback=name).strip()
    appName = configs.get('QtIFW', 'appName', fallback=name).strip()
    organization = configs.get('QtIFW', 'organization', fallback='project').strip()
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()

    icon = configs.get('QtIFW', 'icon', fallback='').strip()

    if icon != '':
        icon = os.path.join(sourcesDir, icon)
    
    title = configs.get('QtIFW', 'title', fallback='').strip()
    description = configs.get('QtIFW', 'description', fallback='').strip()
    licenseFile = configs.get('QtIFW', 'license', fallback='COPYING').strip()
    licenseFile = os.path.join(sourcesDir, licenseFile)
    licenseName = configs.get('QtIFW', 'licenseName', fallback='Unknown').strip()
    url = configs.get('QtIFW', 'url', fallback='').strip()
    defaultTargetDir = '@ApplicationsDir@/{}'.format(appName)
    targetDir = configs.get('QtIFW', 'targetDir', fallback=defaultTargetDir).strip()
    runProgram = configs.get('QtIFW', 'runProgram', fallback='').strip()
    runProgramDescription = configs.get('QtIFW', 'runProgramDescription', fallback='').strip()
    installScript = configs.get('QtIFW', 'script', fallback='install.qs').strip()
    installScript = os.path.join(sourcesDir, installScript)
    changeLog = configs.get('QtIFW', 'changeLog', fallback='').strip()
    changeLog = os.path.join(sourcesDir, changeLog)
    requiresAdminRights = configs.get('QtIFW', 'requiresAdminRights', fallback='false').strip()
    requiresAdminRights = DTUtils.toBool(requiresAdminRights)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    defaultHideArch = DTUtils.toBool(defaultHideArch)
    defaultHideArch = 'true' if defaultHideArch else 'false'
    hideArch = configs.get('QtIFW', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    outPackage = os.path.join(outputDir, '{}-{}'.format(packageName, version))
                     
    if not hideArch:
        outPackage += '-' + targetArch

    if targetPlatform == 'mac':
        outPackage += '.dmg'
    elif targetPlatform == 'posix':
        outPackage += '.run'
    elif targetPlatform == 'windows':
        outPackage += '.exe'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    targetPlatform,
                    name,
                    version,
                    organization,
                    appName,
                    icon,
                    title,
                    description,
                    licenseFile,
                    licenseName,
                    url,
                    targetDir,
                    runProgram,
                    runProgramDescription,
                    installScript,
                    changeLog,
                    requiresAdminRights)
