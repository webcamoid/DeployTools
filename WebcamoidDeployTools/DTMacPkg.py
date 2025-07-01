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

import mimetypes
import os
import subprocess
import tempfile

from . import DTUtils


def pkgbuild():
    return DTUtils.whereBin('pkgbuild')

def productbuild():
    return DTUtils.whereBin('productbuild')

def createPkg(globs,
              dataDir,
              outPackage,
              version,
              targetDir,
              subFolder,
              appIdentifier,
              componentPlist,
              installScripts,
              uninstallScript,
              verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        installDestDir = tmpdir

        if subFolder != '':
            installDestDir = os.path.join(tmpdir, subFolder)

        DTUtils.copy(dataDir, installDestDir)

        if uninstallScript != '':
            DTUtils.copy(uninstallScript, installDestDir)
            os.chmod(os.path.join(installDestDir,
                                  os.path.basename(uninstallScript)),
                     0o755)

        params = [pkgbuild(),
                  '--identifier', appIdentifier,
                  '--version', version,
                  '--install-location', targetDir]

        if componentPlist != '':
            params += ['--component-plist', componentPlist]

        if installScripts != '':
            params += ['--scripts', installScripts]

        params += ['--root', tmpdir,
                   outPackage]
        process = None

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        process.communicate()

def createProduct(globs,
                  appName,
                  version,
                  description,
                  productTitle,
                  appPackage,
                  outPackage,
                  targetDir,
                  packagePath,
                  resourcesDir,
                  backgroundImage,
                  backgroundImageAlignment,
                  backgroundImageScaling,
                  welcomeFile,
                  conclusionFile,
                  licenseFile,
                  readmeFile,
                  verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        # https://developer.apple.com/library/archive/documentation/DeveloperTools/Reference/DistributionDefinitionRef/Chapters/Distribution_XML_Ref.html
        distribFile = os.path.join(tmpdir, 'distribution.xml')

        with open(distribFile, 'w') as f:
            f.write('<?xml version="1.0" encoding="utf-8" standalone="no"?>\n')
            f.write('<installer-script minSpecVersion="1.000000">\n')

            if productTitle != '':
                f.write('    <title>{}</title>\n'.format(productTitle))

            if backgroundImage != '':
                if backgroundImageAlignment != '':
                    backgroundImageAlignment = 'center'

                if backgroundImageScaling != '':
                    backgroundImageScaling = 'tofit'

                mimeType, _ = mimetypes.guess_type(os.path.join(resourcesDir,
                                                                backgroundImage))

                if mimeType != None:
                    f.write('    <background file="{}" mime-type="{}" alignment="{}" scaling="{}"/>\n'.format(backgroundImage, mimeType, backgroundImageAlignment, backgroundImageScaling))
                    f.write('    <background-darkAqua file="{}" mime-type="{}" alignment="{}" scaling="{}"/>\n'.format(backgroundImage, mimeType, backgroundImageAlignment, backgroundImageScaling))

            if welcomeFile != '':
                mimeType, _ = mimetypes.guess_type(os.path.join(resourcesDir,
                                                   welcomeFile))

                if mimeType != None:
                    f.write('    <welcome file="{}" mime-type="{}"/>\n'.format(welcomeFile, mimeType))

            if conclusionFile != '':
                mimeType, _ = mimetypes.guess_type(os.path.join(resourcesDir,
                                                   conclusionFile))

                if mimeType != None:
                    f.write('    <conclusion file="{}" mime-type="{}"/>\n'.format(conclusionFile, mimeType))

            if licenseFile != '':
                mimeType, _ = mimetypes.guess_type(os.path.join(resourcesDir,
                                                   licenseFile))

                if mimeType != None:
                    f.write('    <license file="{}" mime-type="{}"/>\n'.format(licenseFile, mimeType))

            if readmeFile != '':
                mimeType, _ = mimetypes.guess_type(os.path.join(resourcesDir,
                                                   readmeFile))

                if mimeType != None:
                    f.write('    <readme file="{}" mime-type="{}"/>\n'.format(readmeFile, mimeType))

            f.write('    <choices-outline>\n')
            f.write('        <line choice="{}"/>\n'.format(appName))
            f.write('    </choices-outline>\n')
            f.write('    <choice id="{0}" title="{0}" description="{1}"'.format(appName, description))

            if targetDir != '' and targetDir != '/Applications':
                f.write(' customLocation="{}"'.format(appName))

            f.write('>\n')
            pkgFile = os.path.basename(appPackage)
            f.write('        <pkg-ref id="{}"/>\n'.format(pkgFile))
            f.write('    </choice>\n')
            f.write('    <pkg-ref id="{0}" version="{1}">{0}</pkg-ref>\n'.format(pkgFile, version))
            f.write('</installer-script>\n')

        params = [productbuild(),
                  '--distribution', distribFile]

        if resourcesDir != '':
            params += ['--resources', resourcesDir]

        params += ['--package-path', packagePath,
                   outPackage]
        process = None

        if verbose:
            process = subprocess.Popen(params) # nosec
        else:
            process = subprocess.Popen(params, # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

        process.communicate()

def createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    appName,
                    version,
                    description,
                    productTitle,
                    targetDir,
                    subFolder,
                    appIdentifier,
                    component,
                    resourcesDir,
                    installScripts,
                    uninstallScript,
                    backgroundImage,
                    backgroundImageAlignment,
                    backgroundImageScaling,
                    welcomeFile,
                    conclusionFile,
                    licenseFile,
                    readmeFile,
                    verbose):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpInstallScripts = ''

        if installScripts != '':
            tmpInstallScripts = os.path.join(tmpdir, 'installScripts')
            DTUtils.copy(installScripts, tmpInstallScripts)

            for root, dirs, files in os.walk(tmpInstallScripts):
                for f in files:
                    os.chmod(os.path.join(root, f), 0o755)

        tmpPackagesDir = os.path.join(tmpdir, 'packages')

        try:
            os.makedirs(tmpPackagesDir)
        except:
            pass

        appPackage = os.path.join(tmpPackagesDir, appName + '.pkg')
        componentPlist = ''

        if component != '':
            componentPlist = os.path.join(tmpdir, 'component.plist')

            with open(componentPlist, 'w') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n')
                f.write('<plist version="1.0">\n')
                f.write('<array>\n')
                f.write('    <dict>\n')
                f.write('        <key>BundleIsVersionChecked</key>\n')
                f.write('        <true/>\n')
                f.write('        <key>BundleOverwriteAction</key>\n')
                f.write('        <string>upgrade</string>\n')
                f.write('        <key>RootRelativeBundlePath</key>\n')
                f.write('        <string>{}</string>\n'.format(component))
                f.write('    </dict>\n')
                f.write('</array>\n')
                f.write('</plist>\n')

        createPkg(globs,
                  dataDir,
                  appPackage,
                  version,
                  targetDir,
                  subFolder,
                  appIdentifier,
                  componentPlist,
                  tmpInstallScripts,
                  uninstallScript,
                  verbose)
        tmpResourcesDir = os.path.join(tmpdir, 'resources')

        if resourcesDir != '':
            DTUtils.copy(resourcesDir, tmpResourcesDir)

        outLicenceFile = os.path.basename(licenseFile)

        if licenseFile != '':
            if os.path.splitext(outLicenceFile)[1] == '':
                outLicenceFile += '.txt'

            try:
                os.makedirs(tmpResourcesDir)
            except:
                pass

            DTUtils.copy(licenseFile,
                         os.path.join(tmpResourcesDir, outLicenceFile))

        createProduct(globs,
                      appName,
                      version,
                      description,
                      productTitle,
                      appPackage,
                      outPackage,
                      targetDir,
                      tmpPackagesDir,
                      tmpResourcesDir,
                      backgroundImage,
                      backgroundImageAlignment,
                      backgroundImageScaling,
                      welcomeFile,
                      conclusionFile,
                      outLicenceFile,
                      readmeFile,
                      verbose)

        if not os.path.exists(outPackage):
            return

        mutex.acquire()

        if not 'outputPackages' in globs:
            globs['outputPackages'] = []

        globs['outputPackages'].append(outPackage)
        mutex.release()

def platforms():
    return ['mac']

def isAvailable(configs):
    return pkgbuild() != '' and productbuild() != ''

def run(globs, configs, dataDir, outputDir, mutex):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    packageName = configs.get('MacPkg', 'name', fallback=name).strip()
    appName = configs.get('MacPkg', 'appName', fallback=name).strip()
    defaultPkgTargetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    pkgTargetPlatform = configs.get('MacPkg', 'pkgTargetPlatform', fallback=defaultPkgTargetPlatform).strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    defaultTargetDir = '/Applications'
    targetDir = configs.get('MacPkg', 'targetDir', fallback=defaultTargetDir).strip()
    subFolder = configs.get('MacPkg', 'subFolder', fallback='').strip()
    defaultIdentifier = 'com.{}.{}'.format(name, appName)
    appIdentifier = configs.get('Package', 'identifier', fallback=defaultIdentifier).strip()
    component = configs.get('MacPkg', 'component', fallback='').strip()
    description = configs.get('MacPkg', 'description', fallback='').strip()
    productTitle = configs.get('MacPkg', 'productTitle', fallback='').strip()
    resourcesDir = configs.get('MacPkg', 'resourcesDir', fallback='').strip()

    if resourcesDir != '':
        resourcesDir = os.path.join(sourcesDir, resourcesDir)

    installScripts = configs.get('MacPkg', 'installScripts', fallback='').strip()

    if installScripts != '' and not installScripts.startswith('/'):
        installScripts = os.path.join(sourcesDir, installScripts)

    uninstallScript = configs.get('MacPkg', 'uninstallScript', fallback='').strip()

    if uninstallScript != '' and not uninstallScript.startswith('/'):
        uninstallScript = os.path.join(sourcesDir, uninstallScript)

    backgroundImage = configs.get('MacPkg', 'backgroundImage', fallback='').strip()
    backgroundImageAlignment = configs.get('MacPkg', 'backgroundImageAlignment', fallback='center').strip()
    backgroundImageScaling = configs.get('MacPkg', 'backgroundImageScaling', fallback='tofit').strip()
    welcomeFile = configs.get('MacPkg', 'welcomeFile', fallback='').strip()
    conclusionFile = configs.get('MacPkg', 'conclusionFile', fallback='').strip()
    licenseFile = configs.get('MacPkg', 'licenseFile', fallback='').strip()

    if licenseFile != '':
        licenseFile = os.path.join(sourcesDir, licenseFile)

    readmeFile = configs.get('MacPkg', 'readmeFile', fallback='').strip()
    verbose = configs.get('MacPkg', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    defaultHideArch = configs.get('Package', 'hideArch', fallback='false').strip()
    hideArch = configs.get('MacPkg', 'hideArch', fallback=defaultHideArch).strip()
    hideArch = DTUtils.toBool(hideArch)
    defaultShowTargetPlatform = configs.get('Package', 'showTargetPlatform', fallback='true').strip()
    showTargetPlatform = configs.get('MacPkg', 'showTargetPlatform', fallback=defaultShowTargetPlatform).strip()
    showTargetPlatform = DTUtils.toBool(showTargetPlatform)
    outPackage = os.path.join(outputDir, packageName)

    if showTargetPlatform:
        outPackage += '-' + pkgTargetPlatform

    outPackage += '-' + version

    if not hideArch:
        outPackage += '-' + targetArch

    outPackage += '.pkg'

    # Remove old file
    if os.path.exists(outPackage):
        os.remove(outPackage)

    createInstaller(globs,
                    mutex,
                    dataDir,
                    outPackage,
                    appName,
                    version,
                    description,
                    productTitle,
                    targetDir,
                    subFolder,
                    appIdentifier,
                    component,
                    resourcesDir,
                    installScripts,
                    uninstallScript,
                    backgroundImage,
                    backgroundImageAlignment,
                    backgroundImageScaling,
                    welcomeFile,
                    conclusionFile,
                    licenseFile,
                    readmeFile,
                    verbose)
