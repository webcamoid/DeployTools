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
import sys
import subprocess
import tempfile
import time

from . import DTUtils


def cygpath():
    path = DTUtils.whereBin('cygpath')

    if os.path.exists(path):
        return path

    for rootDir in ['C:', '/c']:
        path = os.path.join(rootDir, 'msys64', 'usr', 'bin', 'cygpath.exe')

        if os.path.exists(path):
            return path

    return ''

def winPath(path, verbose=False):
    if DTUtils.hostPlatform() == 'windows':
        cygpathBin = cygpath()
        print('cygpath: {}'.format(cygpathBin))

        if len(cygpathBin) < 1:
            if re.match('^/[a-zA-Z]/', path):
                path = '{}:{}'.format(path[1].upper(), path[2:])
                path = path.replace('/', '\\')

            return path

        params = [cygpathBin, '-w', path]
        process = None

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        if not stdout:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()
    elif DTUtils.whereBin('makensis') == '':
        params = ['winepath', '-w', path]
        process = None

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        stdout, _ = process.communicate()

        if process.returncode != 0:
            return ''

        if not stdout:
            return ''

        return stdout.decode(sys.getdefaultencoding()).strip()

    return path

def isccDataDir(isccVersion):
    issCompiler = 'iscc'
    isFolder = 'Inno Setup {}'.format(isccVersion)

    if DTUtils.hostPlatform() == 'windows':
        for rootDir in ['C:', '/c']:
            homeInnoSetup = \
                [os.path.join(rootDir, 'Program Files (x86)', isFolder),
                 os.path.join(rootDir, 'Program Files', isFolder)]

            for path in homeInnoSetup:
                if os.path.exists(path):
                    return path

        issCompilerPath = DTUtils.whereBin(issCompiler + '.exe')

        if issCompilerPath != '':
            return os.path.dirname(issCompilerPath)
    else:
        if 'WINEPREFIX' in os.environ:
            rootPath = os.path.expanduser(os.path.join(os.environ['WINEPREFIX'],
                                                       'drive_c'))
        else:
            rootPath = os.path.expanduser('~/.wine/drive_c')

        homeInnoSetup = [os.path.join(rootPath, 'Program Files (x86)', isFolder),
                         os.path.join(rootPath, 'Program Files', isFolder)]

        for path in homeInnoSetup:
            if os.path.exists(path):
                return path

    return ''

def iscc(isccVersion):
    issCompiler = 'iscc'
    isFolder = 'Inno Setup {}'.format(isccVersion)

    if DTUtils.hostPlatform() == 'windows':
        for rootDir in ['C:', '/c']:
            homeInnoSetup = \
                [os.path.join(rootDir, 'Program Files (x86)', isFolder),
                 os.path.join(rootDir, 'Program Files', isFolder)]

            for path in homeInnoSetup:
                issCompilerPath = os.path.join(path, issCompiler + '.exe')

                if os.path.exists(issCompilerPath):
                    return issCompilerPath

        return DTUtils.whereBin(issCompiler + '.exe')
    else:
        if 'WINEPREFIX' in os.environ:
            rootPath = os.path.expanduser(os.path.join(os.environ['WINEPREFIX'],
                                                       'drive_c'))
        else:
            rootPath = os.path.expanduser('~/.wine/drive_c')

        homeInnoSetup = [os.path.join(rootPath, 'Program Files (x86)', isFolder),
                         os.path.join(rootPath, 'Program Files', isFolder)]

        for path in homeInnoSetup:
            issCompilerPath = os.path.join(path, issCompiler + '.exe')

            if os.path.exists(issCompilerPath):
                return issCompilerPath

    return ''

def createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    targetArch,
                    appName,
                    version,
                    productVersion,
                    isccVersion,
                    organization,
                    icon,
                    description,
                    copyright,
                    licenseFile,
                    url,
                    supportUrl,
                    updatesUrl,
                    targetDir,
                    runProgram,
                    runProgramDescription,
                    installScript,
                    requiresAdminRights,
                    multiUserInstall,
                    verbose):
    isccdataDir = isccDataDir(isccVersion)
    langs = {'English': 'Default.isl'}

    if isccdataDir != '':
        langsdir = os.path.join(isccdataDir, 'Languages')

        if os.path.exists(langsdir):
            for f in os.listdir(langsdir):
                if f.endswith('.isl'):
                    lang = f.replace('.isl', '')
                    langs[lang] = os.path.join('Languages', f)

    with tempfile.TemporaryDirectory() as tmpdir:
        installerVars = {
            'DATA_DIR': winPath(dataDir),
            'OUT_PACKAGE_NAME': os.path.splitext(os.path.basename(outPackage))[0],
            'OUT_PACKAGE_DIR': winPath(os.path.dirname(outPackage)),
            'APP_NAME': appName,
            'VERSION': version,
            'PRODUCT_VERSION': productVersion,
            'DESCRIPTION': description,
            'ORGANIZATION': organization,
            'COPYRIGHT': copyright,
            'LICENSE_FILE': winPath(licenseFile),
            'RUN_PROGRAM': runProgram.replace('/', '\\'),
            'RUN_PROGRAM_DESCRIPTION': runProgramDescription,
            'ICON': winPath(icon),
            'INSTALL_SCRIPT': os.path.basename(installScript),
            'TARGET_DIR': targetDir,
            'PUBLISHER_URL': url,
            'SUPPORT_URL': supportUrl,
            'UPDATES_URL': updatesUrl
        }

        if installScript != '':
            DTUtils.copy(installScript, tmpdir)

        issScript = os.path.join(tmpdir, 'script.iss')

        with open(issScript, 'w') as f:
            f.write('[Setup]\n')
            f.write('AppName={#APP_NAME}\n')
            f.write('AppVersion={#VERSION}\n')
            f.write('AppPublisher={#ORGANIZATION}\n')
            f.write('AppPublisherURL={#PUBLISHER_URL}\n')
            f.write('AppSupportURL={#SUPPORT_URL}\n')
            f.write('AppUpdatesURL={#UPDATES_URL}\n')

            if targetArch == 'win64':
                f.write('ArchitecturesAllowed=x64\n')
                f.write('ArchitecturesInstallIn64BitMode=x64\n')
            elif targetArch == 'win64_arm':
                f.write('ArchitecturesAllowed=arm64\n')
                f.write('ArchitecturesInstallIn64BitMode=arm64\n')

            f.write('SetupIconFile={#ICON}\n')
            f.write('LicenseFile={#LICENSE_FILE}\n')
            f.write('SourceDir={#DATA_DIR}\n')
            f.write('VersionInfoCompany={#ORGANIZATION}\n')
            f.write('VersionInfoCopyright={#COPYRIGHT}\n')
            f.write('VersionInfoDescription={#DESCRIPTION}\n')
            f.write('VersionInfoProductName={#APP_NAME}\n')
            f.write('VersionInfoProductTextVersion={#APP_NAME} version {#VERSION}\n')
            f.write('VersionInfoProductVersion={}\n'.format(productVersion))
            f.write('VersionInfoTextVersion={#VERSION}\n')
            f.write('VersionInfoVersion={#VERSION}\n')

            if requiresAdminRights:
                f.write('PrivilegesRequired=admin\n')
            else:
                f.write('PrivilegesRequired=lowest\n')

            if multiUserInstall:
                f.write('PrivilegesRequiredOverridesAllowed=dialog\n')

            f.write('WizardStyle=modern\n')
            f.write('DefaultDirName={autopf}\{#APP_NAME}\n')
            f.write('DefaultGroupName={#APP_NAME}\n')
            f.write('Compression=lzma2\n')
            f.write('SolidCompression=yes\n')
            f.write('AllowCancelDuringInstall=yes\n')
            f.write('OutputBaseFilename={#OUT_PACKAGE_NAME}\n')
            f.write('OutputDir={#OUT_PACKAGE_DIR}\n')
            f.write('\n')

            if len(langs) > 0:
                f.write('[Languages]\n')

                for lang in langs:
                    f.write('Name: "{}"; MessagesFile: "compiler:{}"\n'.format(lang, langs[lang]))

                f.write('\n')

            f.write('[Files]\n')
            f.write('Source: "{#DATA_DIR}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs\n')
            f.write('\n')
            f.write('[Tasks]\n')
            f.write('Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"\n')
            f.write('\n')
            f.write('[Icons]\n')
            f.write('Name: "{group}\{#APP_NAME}"; Filename: "{app}\{#RUN_PROGRAM}"\n')
            f.write('Name: "{group}\\Uninstall"; Filename: "{uninstallexe}"\n')
            f.write('Name: "{autodesktop}\{#APP_NAME}"; Filename: "{app}\{#RUN_PROGRAM}; Tasks: desktopicon"\n')
            f.write('\n')
            f.write('[Run]\n')
            f.write('Filename: "{app}\{#RUN_PROGRAM}"; ')

            if len(runProgramDescription) > 0:
                f.write('Description: "{#RUN_PROGRAM_DESCRIPTION}"; ')

            f.write('Flags: nowait postinstall skipifsilent\n')

            if installScript != '':
                f.write('\n')
                f.write('#include "{#INSTALL_SCRIPT}"\n')

        optmrk = '/'
        params = []

        if DTUtils.hostPlatform() != 'windows':
            params = ['wine']

        params += [iscc(isccVersion)]

        for key in installerVars:
            params += [optmrk + 'D{}={}'.format(key, installerVars[key])]

        params += [winPath(issScript)]
        process = None

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
    return ['windows']

def isAvailable(configs):
    isccVersion = configs.get('InnoSetup', 'isccVersion', fallback='6').strip()

    return iscc(isccVersion) != ''

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    productVersion = configs.get('InnoSetup', 'productVersion', fallback='0.0.0.0').strip()
    packageName = configs.get('InnoSetup', 'name', fallback=name).strip()
    appName = configs.get('InnoSetup', 'appName', fallback=name).strip()
    organization = configs.get('InnoSetup', 'organization', fallback='project').strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('InnoSetup', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    isccVersion = configs.get('InnoSetup', 'isccVersion', fallback='6').strip()
    icon = configs.get('InnoSetup', 'icon', fallback='').strip()

    if icon != '':
        icon = os.path.join(sourcesDir, icon)

    description = configs.get('InnoSetup', 'description', fallback='').strip()
    copyright = configs.get('InnoSetup', 'copyright', fallback='').strip()
    licenseFile = configs.get('InnoSetup', 'license', fallback='COPYING').strip()
    licenseFile = os.path.join(sourcesDir, licenseFile)
    url = configs.get('InnoSetup', 'url', fallback='').strip()
    supportUrl = configs.get('InnoSetup', 'supportUrl', fallback='').strip()
    updatesUrl = configs.get('InnoSetup', 'updatesUrl', fallback='').strip()
    targetDir = configs.get('InnoSetup', 'targetDir', fallback='').strip()
    runProgram = configs.get('InnoSetup', 'runProgram', fallback='').strip()
    runProgramDescription = configs.get('InnoSetup', 'runProgramDescription', fallback='').strip()
    installScript = configs.get('InnoSetup', 'script', fallback='').strip()

    if installScript != '':
        installScript = os.path.join(sourcesDir, installScript)

    requiresAdminRights = configs.get('InnoSetup', 'requiresAdminRights', fallback='true').strip()
    requiresAdminRights = DTUtils.toBool(requiresAdminRights)
    multiUserInstall = configs.get('InnoSetup', 'multiUserInstall', fallback='false').strip()
    multiUserInstall = DTUtils.toBool(multiUserInstall)
    verbose = configs.get('InnoSetup', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    hideArch = configs.get('InnoSetup', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
    showTargetPlatform = configs.get('InnoSetup', 'showTargetPlatform', fallback=defaultShowTargetPlatform).strip()
    showTargetPlatform = DTUtils.toBool(showTargetPlatform)
    outPackage = os.path.join(outputDir, packageName)

    if showTargetPlatform:
        outPackage += '-' + pkgTargetPlatform

    outPackage += '-' + version

    if not hideArch:
        outPackage += '-' + targetArch

    outPackage += '.exe'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    targetArch,
                    appName,
                    version,
                    productVersion,
                    isccVersion,
                    organization,
                    icon,
                    description,
                    copyright,
                    licenseFile,
                    url,
                    supportUrl,
                    updatesUrl,
                    targetDir,
                    runProgram,
                    runProgramDescription,
                    installScript,
                    requiresAdminRights,
                    multiUserInstall,
                    verbose)
