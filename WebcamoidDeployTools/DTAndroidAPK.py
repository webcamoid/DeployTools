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

from . import DTAndroid
from . import DTQt
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

def alignPackage(package, sdkBuildToolsRevision, verbose):
    zalign = zipalign(sdkBuildToolsRevision)

    if len(zalign) < 1:
        return False

    alignedPackage = os.path.join(os.path.dirname(package),
                                    'aligned-' + os.path.basename(package))
    params = [zalign,
              '-v',
              '-f', '4',
              package,
              alignedPackage]

    if verbose:
        process = subprocess.Popen(params) # nosec
    else:
        process = subprocess.Popen(params, # nosec
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process.communicate()

    if process.returncode != 0:
        return False

    DTUtils.move(alignedPackage, package)

    return True

def apkSignPackage(package, keystore, sdkBuildToolsRevision, verbose):
    if not alignPackage(package, sdkBuildToolsRevision, verbose):
        return False

    apksign = apksigner(sdkBuildToolsRevision)

    if len(apksign) < 1:
        return False

    params = [apksign,
              'sign',
              '-v',
              '--ks', keystore,
              '--ks-pass', 'pass:android',
              '--ks-key-alias', 'androiddebugkey',
              '--key-pass', 'pass:android',
              package]

    if verbose:
        process = subprocess.Popen(params) # nosec
    else:
        process = subprocess.Popen(params, # nosec
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process.communicate()

    return process.returncode == 0

def jarSignPackage(package, keystore, verbose):
    jsigner = jarsigner()

    if len(jsigner) < 1:
        return False

    signedPackage = os.path.join(os.path.dirname(package),
                                    'signed-' + os.path.basename(package))
    params = [jsigner,
              '-verbose',
              '-keystore', keystore,
              '-storepass', 'android',
              '-keypass', 'android',
              '-sigalg', 'SHA1withRSA',
              '-digestalg', 'SHA1',
              '-sigfile', 'CERT',
              '-signedjar', signedPackage,
              package,
              'androiddebugkey']

    if verbose:
        process = subprocess.Popen(params) # nosec
    else:
        process = subprocess.Popen(params, # nosec
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process.communicate()

    if process.returncode != 0:
        return False

    DTUtils.move(signedPackage, package)

    return alignPackage(package, verbose)

def signPackage(package, dataDir, sdkBuildToolsRevision, verbose):
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

        params = [ktool,
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
                  '-dname', 'CN=Android Debug,O=Android,C=US']

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        process.communicate()

        if process.returncode != 0:
            return False

    if apkSignPackage(package, keystore, sdkBuildToolsRevision, verbose):
        return True

    return jarSignPackage(package, keystore, verbose)

def createApk(globs,
              mutex,
              dataDir,
              outPackage,
              sdkBuildToolsRevision,
              verbose):
    localProperties = os.path.join(dataDir, 'local.properties')

    if not os.path.exists(localProperties):
        with open(localProperties, 'w') as f:
            if 'ANDROID_HOME' in os.environ:
                f.write('sdk.dir=' + os.environ['ANDROID_HOME'] + '\n')

            if 'ANDROID_NDK_ROOT' in os.environ:
                f.write('ndk.dir=' + os.environ['ANDROID_NDK_ROOT'] + '\n')

    DTQt.mergeXmlLibs(os.path.join(dataDir, 'res', 'values'))
    gradleSript = os.path.join(dataDir, 'gradlew')

    if DTUtils.hostPlatform() == 'windows':
        gradleSript += '.bat'

    if  os.path.exists(gradleSript):
        os.chmod(gradleSript, 0o755)
        params = [gradleSript,
                  '--no-daemon',
                  '--info',
                  'assembleRelease']

        if verbose:
            process = subprocess.Popen(params, # nosec
                                    cwd=dataDir)
        else:
            process = subprocess.Popen(params, # nosec
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
    signPackage(apk, dataDir, sdkBuildToolsRevision, verbose)
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
    sdkBuildToolsRevision = DTAndroid.buildToolsVersion(configs)
    verbose = configs.get('AndroidAPK', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)

    if len(DTUtils.whereBin('gradle')) < 1:
        if verbose:
            print('gradle not found')

        return False

    if len(keytool()) < 1:
        if verbose:
            print('keytool not found')

        return False

    if len(jarsigner()) < 1:
        if verbose:
            print('jarsigner not found')

        return False

    if len(apksigner(sdkBuildToolsRevision)) < 1:
        if verbose:
            print('apksigner not found')

        return False

    if len(zipalign(sdkBuildToolsRevision)) < 1:
        if verbose:
            print('zipalign not found')

        return False

    return True

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    sdkBuildToolsRevision = DTAndroid.buildToolsVersion(configs)
    packageName = configs.get('AndroidAPK', 'name', fallback=name).strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('AndroidAPK', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    verbose = configs.get('AndroidAPK', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    hideArch = configs.get('AndroidAPK', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
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
              sdkBuildToolsRevision,
              verbose)
