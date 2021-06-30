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

from . import DTUtils


def keytool():
    if 'JAVA_HOME' in os.environ:
        ktool = os.path.join(os.environ['JAVA_HOME'], 'bin', 'keytool')

        if DTUtils.hostPlatform() == 'windows':
            ktool += '.exe'

        if os.path.exists(ktool):
            return ktool

    return DTUtils.whereBin('keytool')

def jarsigner():
    if 'JAVA_HOME' in os.environ:
        jsigner = os.path.join(os.environ['JAVA_HOME'], 'bin', 'jarsigner')

        if DTUtils.hostPlatform() == 'windows':
            jsigner += '.exe'

        if os.path.exists(jsigner):
            return jsigner

    return DTUtils.whereBin('jarsigner')

def apksigner(buildToolsVersion):
    if 'ANDROID_HOME' in os.environ:
        apksign = os.path.join(os.environ['ANDROID_HOME'],
                               'build-tools',
                               buildToolsVersion,
                               'apksigner')

        if DTUtils.hostPlatform() == 'windows':
            apksign += '.exe'

        if os.path.exists(apksign):
            return apksign

    return DTUtils.whereBin('apksigner')

def zipalign(buildToolsVersion):
    if 'ANDROID_HOME' in os.environ:
        zalign = os.path.join(os.environ['ANDROID_HOME'],
                              'build-tools',
                              buildToolsVersion,
                              'zipalign')

        if DTUtils.hostPlatform() == 'windows':
            zalign += '.exe'

        if os.path.exists(zalign):
            return zalign

    return DTUtils.whereBin('zipalign')

def alignPackage(package, sdkBuildToolsRevision):
    zalign = zipalign(sdkBuildToolsRevision)

    if len(zalign) < 1:
        return False

    alignedPackage = os.path.join(os.path.dirname(package),
                                    'aligned-' + os.path.basename(package))
    process = subprocess.Popen([zalign, # nosec
                                '-v',
                                '-f', '4',
                                package,
                                alignedPackage],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    process.communicate()

    if process.returncode != 0:
        return False

    DTUtils.move(alignedPackage, package)

    return True

def apkSignPackage(package, keystore, sdkBuildToolsRevision):
    if not alignPackage(package, sdkBuildToolsRevision):
        return False

    apksign = apksigner(sdkBuildToolsRevision)

    if len(apksign) < 1:
        return False

    process = subprocess.Popen([apksign, # nosec
                                'sign',
                                '-v',
                                '--ks', keystore,
                                '--ks-pass', 'pass:android',
                                '--ks-key-alias', 'androiddebugkey',
                                '--key-pass', 'pass:android',
                                package],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    process.communicate()

    return process.returncode == 0

def jarSignPackage(package, keystore):
    jsigner = jarsigner()

    if len(jsigner) < 1:
        return False

    signedPackage = os.path.join(os.path.dirname(package),
                                    'signed-' + os.path.basename(package))
    process = subprocess.Popen([jsigner, # nosec
                                '-verbose',
                                '-keystore', keystore,
                                '-storepass', 'android',
                                '-keypass', 'android',
                                '-sigalg', 'SHA1withRSA',
                                '-digestalg', 'SHA1',
                                '-sigfile', 'CERT',
                                '-signedjar', signedPackage,
                                package,
                                'androiddebugkey'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    process.communicate()

    if process.returncode != 0:
        return False

    DTUtils.move(signedPackage, package)

    return alignPackage(package)

def signPackage(package, dataDir, sdkBuildToolsRevision):
    ktool = keytool()

    if len(ktool) < 1:
        return False

    keystore = os.path.join(dataDir, 'debug.keystore')

    if 'KEYSTORE_PATH' in os.environ:
        keystore = os.environ['KEYSTORE_PATH']

    if not os.path.exists(keystore):
        try:
            os.makedirs(os.path.dirname(keystore))
        except:
            pass

        process = subprocess.Popen([ktool, # nosec
                                    '-genkey',
                                    '-v',
                                    '-storetype', 'pkcs12',
                                    '-keystore', keystore,
                                    '-storepass', 'android',
                                    '-alias', 'androiddebugkey',
                                    '-keypass', 'android',
                                    '-keyalg', 'RSA',
                                    '-keysize', '2048',
                                    '-validity', '10000',
                                    '-dname', 'CN=Android Debug,O=Android,C=US'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        process.communicate()

        if process.returncode != 0:
            return False

    if apkSignPackage(package, keystore, sdkBuildToolsRevision):
        return True

    return jarSignPackage(package, keystore)

def createApk(globs,
              mutex,
              dataDir,
              outPackage,
              sdkBuildToolsRevision):
    gradleSript = os.path.join(dataDir, 'gradlew')

    if DTUtils.hostPlatform() == 'windows':
        gradleSript += '.bat'

    os.chmod(gradleSript, 0o744)
    process = subprocess.Popen([gradleSript, # nosec
                                '--no-daemon',
                                '--info',
                                'assembleRelease'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=dataDir)
    process.communicate()
    name = os.path.basename(dataDir)
    apk = os.path.join(dataDir,
                       'build',
                       'outputs',
                       'apk',
                       'release',
                       '{}-release-unsigned.apk'.format(name))
    signPackage(apk, dataDir, sdkBuildToolsRevision)
    DTUtils.copy(apk, outPackage)

    if not os.path.exists(outPackage):
        return

    mutex.acquire()

    if not 'outputPackages' in globs:
        globs['outputPackages'] = []

    globs['outputPackages'].append(outPackage)
    mutex.release()

def platforms():
    return ['android']

def isAvailable(configs):
    sdkBuildToolsRevision = configs.get('System', 'sdkBuildToolsRevision', fallback='30.0.3').strip()

    if len(DTUtils.whereBin('gradle')) < 1:
        return False

    if len(keytool()) < 1:
        return False

    if len(jarsigner()) < 1:
        return False

    if len(apksigner(sdkBuildToolsRevision)) < 1:
        return False

    if len(zipalign(sdkBuildToolsRevision)) < 1:
        return False

    return True

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    sdkBuildToolsRevision = configs.get('System', 'sdkBuildToolsRevision', fallback='30.0.3').strip()
    packageName = configs.get('AndroidAPK', 'name', fallback=name).strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('AndroidAPK', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    defaultHideArch = DTUtils.toBool(defaultHideArch)
    defaultHideArch = 'true' if defaultHideArch else 'false'
    hideArch = configs.get('AndroidAPK', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
    defaultShowTargetPlatform = DTUtils.toBool(defaultShowTargetPlatform)
    defaultShowTargetPlatform = 'true' if defaultShowTargetPlatform else 'false'
    showTargetPlatform = configs.get('AndroidAPK', 'showTargetPlatform', fallback=defaultShowTargetPlatform).strip()
    showTargetPlatform = DTUtils.toBool(showTargetPlatform)
    outPackage = os.path.join(outputDir, packageName)

    if showTargetPlatform:
        outPackage += '-' + pkgTargetPlatform

    outPackage += '-' + version

    if not hideArch:
        outPackage += '-' + targetArch

    outPackage += '.apk'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createApk(globs,
              mutex,
              dataDir,
              outPackage,
              sdkBuildToolsRevision)
