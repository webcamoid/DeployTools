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

        return stdout.decode(sys.getdefaultencoding()).strip()

    return path

def nsisDataDir():
    makeNSIS = 'makensis'

    if DTUtils.hostPlatform() == 'windows':
        for rootDir in ['C:', '/c']:
            homeNSIS = [os.path.join(rootDir, 'Program Files (x86)', 'NSIS'),
                        os.path.join(rootDir, 'Program Files', 'NSIS')]

            for path in homeNSIS:
                if os.path.exists(path):
                    return path

        makeNSISPath = DTUtils.whereBin(makeNSIS + '.exe')

        if makeNSISPath != '':
            dataDir = os.path.join(os.path.dirname(makeNSISPath),
                                   '..',
                                   'share',
                                   'nsis')
            dataDir = os.path.abspath(dataDir)

            if os.path.exists(dataDir):
                return dataDir
            else:
                return os.path.dirname(makeNSISPath)
    else:
        makeNSISPath = DTUtils.whereBin(makeNSIS)

        if makeNSISPath != '':
            dataDir = os.path.join(os.path.dirname(makeNSISPath),
                                   '..',
                                   'share',
                                   'nsis')
            dataDir = os.path.abspath(dataDir)

            if os.path.exists(dataDir):
                return dataDir
        else:
            if 'WINEPREFIX' in os.environ:
                rootPath = os.path.expanduser(os.path.join(os.environ['WINEPREFIX'],
                                                           'drive_c'))
            else:
                rootPath = os.path.expanduser('~/.wine/drive_c')

            homeNSIS = [os.path.join(rootPath, 'Program Files (x86)', 'NSIS'),
                        os.path.join(rootPath, 'Program Files', 'NSIS')]

            for path in homeNSIS:
                if os.path.exists(path):
                    return path

    return ''

def makensis():
    makeNSIS = 'makensis'

    if DTUtils.hostPlatform() == 'windows':
        for rootDir in ['C:', '/c']:
            homeNSIS = [os.path.join(rootDir, 'Program Files (x86)', 'NSIS'),
                        os.path.join(rootDir, 'Program Files', 'NSIS')]

            for path in homeNSIS:
                makeNSISPath = os.path.join(path, makeNSIS + '.exe')

                if os.path.exists(makeNSISPath):
                    return makeNSISPath

        return DTUtils.whereBin(makeNSIS + '.exe')
    else:
        makeNSISPath = DTUtils.whereBin(makeNSIS)

        if makeNSISPath != '':
            return makeNSISPath
        else:
            if 'WINEPREFIX' in os.environ:
                rootPath = os.path.expanduser(os.path.join(os.environ['WINEPREFIX'],
                                                           'drive_c'))
            else:
                rootPath = os.path.expanduser('~/.wine/drive_c')

            homeNSIS = [os.path.join(rootPath, 'Program Files (x86)', 'NSIS'),
                        os.path.join(rootPath, 'Program Files', 'NSIS')]

            for path in homeNSIS:
                makeNSISPath = os.path.join(path, makeNSIS + '.exe')

                if os.path.exists(makeNSISPath):
                    return makeNSISPath

    return ''

def createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    targetArch,
                    appName,
                    version,
                    productVersion,
                    organization,
                    icon,
                    description,
                    copyright,
                    licenseFile,
                    targetDir,
                    runProgram,
                    installScript,
                    requiresAdminRights,
                    multiUserInstall,
                    verbose):
    embedInstallScript = True
    nsisdataDir = nsisDataDir()
    langs = []

    if nsisdataDir != '':
        langsdir = os.path.join(nsisdataDir, 'Contrib', 'Language files')

        if os.path.exists(langsdir):
            for f in os.listdir(langsdir):
                if f.endswith('.nsh'):
                    langs += [f.replace('.nsh', '')]

    if 'English' in langs:
        langs.remove('English')
        langs = ['English'] + langs

    if langs == []:
        langs = ['English']

    with tempfile.TemporaryDirectory() as tmpdir:
        installScriptBn = os.path.basename(installScript)

        installerVars = {
            'DATA_DIR': winPath(dataDir, verbose),
            'OUT_PACKAGE': winPath(outPackage, verbose),
            'APP_NAME': appName,
            'VERSION': version,
            'PRODUCT_VERSION': productVersion,
            'DESCRIPTION': description,
            'ORGANIZATION': organization,
            'COPYRIGHT': copyright,
            'LICENSE_FILE': winPath(licenseFile, verbose),
            'RUN_PROGRAM': runProgram.replace('/', '\\'),
            'ICON': winPath(icon, verbose),
            'INSTALL_SCRIPT': installScriptBn,
            'TARGET_DIR': targetDir
        }

        if installScript != '' and not embedInstallScript:
            outInstallScript = os.path.join(tmpdir, installScriptBn)
            DTUtils.copy(installScript, outInstallScript)

        nsiScript = os.path.join(tmpdir, 'script.nsi')

        with open(nsiScript, 'w') as f:
            f.write('Unicode True\n')

            if requiresAdminRights:
                f.write('RequestExecutionLevel highest\n')
            else:
                f.write('RequestExecutionLevel user\n')

            if multiUserInstall:
                f.write('!define MULTIUSER_EXECUTIONLEVEL Highest\n')
                f.write('!define MULTIUSER_INSTALLMODE_COMMANDLINE\n')
                f.write('!define MULTIUSER_MUI\n')

            f.write('!define UNINST_KEY "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${' + 'APP_NAME' + '}"\n')

            f.write('SetCompressor /SOLID lzma\n')
            f.write('\n')
            f.write('!include MUI2.nsh\n')

            if multiUserInstall:
                f.write('!include MultiUser.nsh\n')

            if installScript != '':
                if embedInstallScript:
                    with open(installScript) as script:
                        f.write(script.read())
                else:
                    f.write('!include "${' + 'INSTALL_SCRIPT' + '}"\n')

            f.write('\n')
            f.write('Name "${' + 'APP_NAME' + '} ${' + 'VERSION' + '}"\n')

            if icon != '':
                f.write('Icon "${' + 'ICON' + '}"\n')

            f.write('OutFile "${' + 'OUT_PACKAGE' + '}"\n')

            if targetDir != '':
                f.write('InstallDir "${' + 'TARGET_DIR' + '}"\n')
            else:
                if targetArch == 'win64' or targetArch == 'win64_arm':
                    f.write('InstallDir "$PROGRAMFILES64\\${' + 'APP_NAME' + '}"\n')
                else:
                    f.write('InstallDir "$PROGRAMFILES\\${' + 'APP_NAME' + '}"\n')

            f.write('XPStyle on\n')
            f.write('\n')
            f.write('VIFileVersion "${' + 'PRODUCT_VERSION' + '}"\n')
            f.write('VIProductVersion "${' + 'PRODUCT_VERSION' + '}"\n')
            f.write('VIAddVersionKey "ProductName" "${' + 'APP_NAME' + '}"\n')
            f.write('VIAddVersionKey "CompanyName" "${' + 'ORGANIZATION' + '}"\n')
            f.write('VIAddVersionKey "LegalCopyright" "${' + 'COPYRIGHT' + '}"\n')
            f.write('VIAddVersionKey "FileDescription" "${' + 'DESCRIPTION' + '}"\n')
            f.write('VIAddVersionKey "FileVersion" "${' + 'VERSION' + '}"\n')
            f.write('VIAddVersionKey "ProductVersion" "${' + 'PRODUCT_VERSION' + '}"\n')
            f.write('\n')

            if icon != '':
                f.write('!define MUI_ICON "${' + 'ICON' + '}"\n')

            f.write('\n')
            f.write('!define MUI_ABORTWARNING\n')
            f.write('!define MUI_UNABORTWARNING\n')
            f.write('!define MUI_LANGDLL_ALLLANGUAGES\n')
            f.write('!define MUI_LANGDLL_REGISTRY_ROOT "HKCU"\n')
            f.write('!define MUI_LANGDLL_REGISTRY_KEY "Software\\${' + 'APP_NAME' + '}"\n')
            f.write('!define MUI_LANGDLL_REGISTRY_VALUENAME "Installer Language"\n')
            f.write('\n')
            f.write('!insertmacro MUI_PAGE_WELCOME\n')
            f.write('!insertmacro MUI_PAGE_LICENSE "${' + 'LICENSE_FILE' + '}"\n')
            f.write('!insertmacro MUI_PAGE_COMPONENTS\n')

            if multiUserInstall:
                f.write('!insertmacro MULTIUSER_PAGE_INSTALLMODE\n')

            f.write('!insertmacro MUI_PAGE_DIRECTORY\n')
            f.write('!ifmacrodef INSTALL_SCRIPT_PAGES\n')
            f.write('!insertmacro INSTALL_SCRIPT_PAGES\n')
            f.write('!endif\n')
            f.write('!insertmacro MUI_PAGE_INSTFILES\n')

            if runProgram != '':
                f.write('!define MUI_FINISHPAGE_RUN "$INSTDIR\\${' + 'RUN_PROGRAM' + '}"\n')

            f.write('!insertmacro MUI_PAGE_FINISH\n')
            f.write('\n')
            f.write('!insertmacro MUI_UNPAGE_WELCOME\n')
            f.write('!insertmacro MUI_UNPAGE_CONFIRM\n')
            f.write('!insertmacro MUI_UNPAGE_COMPONENTS\n')
            f.write('!ifmacrodef INSTALL_SCRIPT_UNPAGES\n')
            f.write('!insertmacro INSTALL_SCRIPT_UNPAGES\n')
            f.write('!endif\n')
            f.write('!insertmacro MUI_UNPAGE_INSTFILES\n')
            f.write('!insertmacro MUI_UNPAGE_FINISH\n')
            f.write('\n')

            for lang in langs:
                f.write('!insertmacro MUI_LANGUAGE "{}"\n'.format(lang))

            f.write('\n')
            f.write('!insertmacro MUI_RESERVEFILE_LANGDLL\n')
            f.write('\n')
            f.write('Section "${' + 'APP_NAME' + '}"\n')
            f.write('SectionIn RO\n')
            f.write('!ifmacrodef INSTALL_SCRIPT_BEFORE_INSTALL\n')
            f.write('!insertmacro INSTALL_SCRIPT_BEFORE_INSTALL\n')
            f.write('!endif\n')

            for root, dirs, files in os.walk(dataDir):
                outPath = ''

                if root == dataDir:
                    outPath = '$INSTDIR'
                else:
                    outPath = os.path.join('$INSTDIR', os.path.relpath(root, dataDir))
                    outPath = outPath.replace('/', '\\')

                if len(files) > 0:
                    f.write('SetOutPath "{}"\n'.format(outPath))

                    for fil in files:
                        filpath = os.path.join(root, fil)
                        f.write('File "{}"\n'.format(winPath(filpath, verbose)))

            f.write('SetOutPath $INSTDIR\n')
            f.write('WriteUninstaller $INSTDIR\\uninstall.exe\n')
            f.write('CreateDirectory "$SMPROGRAMS\\${' + 'APP_NAME' + '}"\n')

            if multiUserInstall:
                f.write('CreateShortCut "$SMPROGRAMS\\${' + 'APP_NAME' + '}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe" /$MultiUser.InstallMode\n')
            else:
                f.write('CreateShortCut "$SMPROGRAMS\\${' + 'APP_NAME' + '}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"\n')

            f.write('!ifmacrodef INSTALL_SCRIPT_AFTER_INSTALL\n')
            f.write('!insertmacro INSTALL_SCRIPT_AFTER_INSTALL\n')
            f.write('!endif\n')

            # Add uninstall information to Add/Remove Programs

            f.write('WriteRegStr SHCTX "${' + 'UNINST_KEY' + '}" "DisplayName" "${' + 'APP_NAME' + '}"\n')

            if runProgram != '':
                f.write('WriteRegStr SHCTX "${' + 'UNINST_KEY' + '}" "DisplayIcon" "$\\"$INSTDIR\\${' + 'RUN_PROGRAM' + '},0"\n')

            if multiUserInstall:
                f.write('WriteRegStr SHCTX "${' + 'UNINST_KEY' + '}" "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\" /$MultiUser.InstallMode"\n')
                f.write('WriteRegStr SHCTX "${' + 'UNINST_KEY' + '}" "QuietUninstallString" "$\\"$INSTDIR\\uninstall.exe$\\" /$MultiUser.InstallMode /S"\n')
            else:
                f.write('WriteRegStr SHCTX "${' + 'UNINST_KEY' + '}" "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\""\n')
                f.write('WriteRegStr SHCTX "${' + 'UNINST_KEY' + '}" "QuietUninstallString" "$\\"$INSTDIR\\uninstall.exe$\\" /S"\n')

            f.write('SectionEnd\n')
            f.write('\n')
            f.write('Function .onInit\n')
            f.write('    !insertmacro MUI_LANGDLL_DISPLAY\n')

            if multiUserInstall:
                f.write('    !insertmacro MULTIUSER_INIT\n')

            f.write('!ifmacrodef INSTALL_SCRIPT_INIT\n')
            f.write('!insertmacro INSTALL_SCRIPT_INIT\n')
            f.write('!endif\n')
            f.write('FunctionEnd\n')
            f.write('\n')

            if runProgram != '':
                f.write('SectionGroup /e "Shortcuts"\n')

                f.write('Section "Start menu"\n')
                f.write('SectionIn RO\n')
                f.write('CreateShortCut "$SMPROGRAMS\\${' + 'APP_NAME' + '}\\${' + 'APP_NAME' + '}.lnk" "$INSTDIR\\${' + 'RUN_PROGRAM' + '}"\n')
                f.write('SectionEnd\n')
                f.write('\n')

                f.write('Section "Desktop"\n')
                f.write('CreateShortCut "$DESKTOP\\${' + 'APP_NAME' + '}.lnk" "$INSTDIR\\${' + 'RUN_PROGRAM' + '}"\n')
                f.write('SectionEnd\n')
                f.write('\n')

                f.write('SectionGroupEnd\n')
                f.write('\n')

            f.write('!ifmacrodef INSTALL_SCRIPT_SECTIONS\n')
            f.write('!insertmacro INSTALL_SCRIPT_SECTIONS\n')
            f.write('!endif\n')
            f.write('\n')

            f.write('Section "Uninstall"\n')
            f.write('SectionIn RO\n')
            f.write('Delete $INSTDIR\\uninstall.exe\n')
            f.write('!ifmacrodef INSTALL_SCRIPT_UNINSTALL\n')
            f.write('!insertmacro INSTALL_SCRIPT_UNINSTALL\n')
            f.write('!endif\n')

            for root, dirs, files in os.walk(dataDir, topdown=False):
                outPath = ''

                if root == dataDir:
                    outPath = '$INSTDIR'
                else:
                    outPath = os.path.join('$INSTDIR', os.path.relpath(root, dataDir))
                    outPath = outPath.replace('/', '\\')

                for fil in files:
                    filpath = os.path.join(outPath, fil)
                    filpath = filpath.replace('/', '\\')
                    f.write('Delete "{}"\n'.format(filpath))

                f.write('RMDir "{}"\n'.format(outPath))

            f.write('RMDir /r "$SMPROGRAMS\\${' + 'APP_NAME' + '}"\n')
            f.write('Delete "$DESKTOP\\${' + 'APP_NAME' + '}.lnk"\n')
            f.write('Delete "$SMSTARTUP\\${' + 'APP_NAME' + '}.lnk"\n')
            f.write('DeleteRegKey SHCTX "${' + 'UNINST_KEY' + '}"\n')
            f.write('SectionEnd\n')
            f.write('\n')
            f.write('Function un.onInit\n')

            if multiUserInstall:
                f.write('    !insertmacro MULTIUSER_UNINIT\n')

            f.write('    !ifmacrodef INSTALL_SCRIPT_UNINIT\n')
            f.write('    !insertmacro INSTALL_SCRIPT_UNINIT\n')
            f.write('    !endif\n')
            f.write('    !insertmacro MUI_UNGETLANGUAGE\n')
            f.write('FunctionEnd\n')

        optmrk = '/'

        if DTUtils.hostPlatform() != 'windows':
            optmrk = '-'

        params = []
        makensisbin = makensis()

        if DTUtils.hostPlatform() != 'windows' \
            and makensisbin.lower().endswith('.exe'):
            params = ['wine']

        params += [makensisbin, optmrk + 'V4']

        for key in installerVars:
            params += [optmrk + 'D{}={}'.format(key, installerVars[key])]

        params += [winPath(nsiScript, verbose)]
        process = None
        print('Params: {}'.format(params))

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
    return makensis() != ''

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    productVersion = configs.get('Nsis', 'productVersion', fallback='0.0.0.0').strip()
    packageName = configs.get('Nsis', 'name', fallback=name).strip()
    appName = configs.get('Nsis', 'appName', fallback=name).strip()
    organization = configs.get('Nsis', 'organization', fallback='project').strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('Nsis', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    icon = configs.get('Nsis', 'icon', fallback='').strip()

    if icon != '':
        icon = os.path.join(sourcesDir, icon)

    description = configs.get('Nsis', 'description', fallback='').strip()
    copyright = configs.get('Nsis', 'copyright', fallback='').strip()
    licenseFile = configs.get('Nsis', 'license', fallback='COPYING').strip()
    licenseFile = os.path.join(sourcesDir, licenseFile)
    targetDir = configs.get('Nsis', 'targetDir', fallback='').strip()
    runProgram = configs.get('Nsis', 'runProgram', fallback='').strip()
    installScript = configs.get('Nsis', 'script', fallback='').strip()

    if installScript != '':
        installScript = os.path.join(sourcesDir, installScript)

    requiresAdminRights = configs.get('Nsis', 'requiresAdminRights', fallback='true').strip()
    requiresAdminRights = DTUtils.toBool(requiresAdminRights)
    multiUserInstall = configs.get('Nsis', 'multiUserInstall', fallback='false').strip()
    multiUserInstall = DTUtils.toBool(multiUserInstall)
    verbose = configs.get('Nsis', 'verbose', fallback='true').strip()
    verbose = DTUtils.toBool(verbose)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    hideArch = configs.get('Nsis', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
    showTargetPlatform = configs.get('Nsis', 'showTargetPlatform', fallback=defaultShowTargetPlatform).strip()
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
                    organization,
                    icon,
                    description,
                    copyright,
                    licenseFile,
                    targetDir,
                    runProgram,
                    installScript,
                    requiresAdminRights,
                    multiUserInstall,
                    verbose)
