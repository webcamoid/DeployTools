#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Webcamoid Deploy Tools.
# Copyright (C) 2020  Gonzalo Exequiel Pedone
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

import configparser
import json
import os
import platform
import re
import shutil
import subprocess # nosec
import sys
import time
import xml.etree.ElementTree as ET

from . import DTUtils
from . import DTBinary


def libBaseName(lib):
    basename = os.path.basename(lib)

    return basename[3: len(basename) - 3]

def fixLibsXml(globs, targetArch, dataDir):
    bundledInAssets = []
    assetsDir = os.path.join(dataDir, 'assets')

    for root, dirs, files in os.walk(assetsDir):
        for f in files:
            srcPath = os.path.join(root.replace(assetsDir, '')[1:], f)
            dstPath = os.path.sep.join(srcPath.split(os.path.sep)[1:])

            if (len(dstPath) > 0):
                bundledInAssets += [(srcPath, dstPath)]

    libsXml = os.path.join(dataDir, 'res', 'values', 'libs.xml')
    libsXmlTemp = os.path.join(dataDir, 'res', 'values', 'libsTemp.xml')

    tree = ET.parse(libsXml)
    root = tree.getroot()
    oldFeatures = set()
    oldPermissions = set()
    resources = {}

    for array in root:
        if not array.attrib['name'] in resources:
            resources[array.attrib['name']] = set()

        for item in array:
            if item.text:
                lib = item.text.strip()

                if len(lib) > 0:
                    lib = '<item>{}</item>'.format(lib)
                    resources[array.attrib['name']].add(lib)

    libs = []

    if 'libs' in globs:
        libs = globs['libs']

    qtLibs = set(['<item>{};{}</item>'.format(targetArch, libBaseName(lib)) for lib in libs])

    if 'qt_libs' in resources:
        qtLibs -= resources['qt_libs']

    qtLibs = '\n'.join(sorted(list(qtLibs)))
    bundledInLib = []

    if 'bundledInLib' in globs:
        bundledInLib = globs['bundledInLib']

    bundledInLib = set(['<item>{}:{}</item>'.format(lib[0], lib[1]) for lib in bundledInLib])

    if 'bundled_in_lib' in resources:
        bundledInLib -= resources['bundled_in_lib']

    bundledInLib = '\n'.join(sorted(list(bundledInLib)))
    bundledInAssets = set(['<item>{}:{}</item>'.format(lib[0], lib[1]) for lib in bundledInAssets])

    if 'bundled_in_assets' in resources:
        bundledInAssets -= resources['bundled_in_assets']

    bundledInAssets = '\n'.join(sorted(list(bundledInAssets)))
    localLibs = []

    if 'localLibs' in globs:
        localLibs = sorted(list(globs['localLibs']))

    localLibs = {'<item>{};{}</item>'.format(targetArch, ':'.join(localLibs))}

    if 'load_local_libs' in resources:
        localLibs -= resources['load_local_libs']

    localLibs = '\n'.join(sorted(list(localLibs)))

    replace = {'<!-- %%INSERT_EXTRA_LIBS%% -->'       : '',
               '<!-- %%INSERT_QT_LIBS%% -->'          : qtLibs,
               '<!-- %%INSERT_BUNDLED_IN_LIB%% -->'   : bundledInLib,
               '<!-- %%INSERT_BUNDLED_IN_ASSETS%% -->': bundledInAssets,
               '<!-- %%INSERT_LOCAL_LIBS%% -->'       : localLibs}

    with open(libsXml) as inFile:
        with open(libsXmlTemp, 'w') as outFile:
            for line in inFile:
                for key in replace:
                    line = line.replace(key, replace[key])

                outFile.write(line)

    os.remove(libsXml)
    shutil.move(libsXmlTemp, libsXml)

def copyAndroidTemplates(dataDir,
                         qtSourcesDir,
                         sdkBuildToolsRevision,
                         androidCompileSdkVersion):
    templates = [os.path.join(qtSourcesDir, '3rdparty/gradle'),
                 os.path.join(qtSourcesDir, 'android/templates')]

    for template in templates:
        DTUtils.copy(template, dataDir, overwrite=False)

    properties = os.path.join(dataDir, 'gradle.properties')
    javaDir = os.path.join(qtSourcesDir, 'android', 'java')

    with open(properties, 'w') as f:
        if len(sdkBuildToolsRevision) > 0:
            f.write('androidBuildToolsVersion={}\n'.format(sdkBuildToolsRevision))

        f.write('androidCompileSdkVersion={}\n'.format(androidCompileSdkVersion))
        f.write('qtMinSdkVersion={}\n'.format(androidCompileSdkVersion))
        f.write('qtTargetSdkVersion={}\n'.format(androidCompileSdkVersion))
        f.write('buildDir=build\n')
        f.write('qt5AndroidDir={}\n'.format(javaDir))

def solvedepsAndroid(globs,
                     dataDir,
                     libDir,
                     sysLibDir,
                     appName,
                     appLibName,
                     version):
    jars = []
    permissions = set()
    features = set()
    initClasses = set()
    libs = set()

    for f in os.listdir(libDir):
        basename = os.path.basename(f)[3:]
        basename = os.path.splitext(basename)[0]

        if not basename.startswith('Qt'):
            continue

        for ldir in sysLibDir:
            depFile = os.path.join(ldir,
                                   basename + '-android-dependencies.xml')

            if os.path.exists(depFile):
                tree = ET.parse(depFile)
                root = tree.getroot()

                for jar in root.iter('jar'):
                    jars.append(jar.attrib['file'])

                    if 'initClass' in jar.attrib:
                        initClasses.append(jar.attrib['initClass'])

                for permission in root.iter('permission'):
                    permissions.add(permission.attrib['name'])

                for feature in root.iter('feature'):
                    features.add(feature.attrib['name'])

                for lib in root.iter('lib'):
                    if 'file' in lib.attrib:
                        libs.add(lib.attrib['file'])


    if not 'localLibs' in globs:
        globs['localLibs'] = set()

    for lib in libs:
        globs['localLibs'].add(os.path.basename(lib))

    print('Copying jar files')
    qtInstallPrefx = qmakeQuery('QT_INSTALL_PREFIX')
    outJarsDir = os.path.join(dataDir, 'libs')
    print()
    print('From: ', os.path.join(qtInstallPrefx, 'jar'))
    print('To: ', outJarsDir)
    print()

    for jar in sorted(jars):
        srcPath = os.path.join(qtInstallPrefx, jar)

        if os.path.exists(srcPath):
            dstPath = os.path.join(outJarsDir,
                                   os.path.basename(jar))
            print('    {} -> {}'.format(srcPath, dstPath))
            DTUtils.copy(srcPath, dstPath)

    manifest = os.path.join(dataDir, 'AndroidManifest.xml')
    manifestTemp = os.path.join(dataDir, 'AndroidManifestTemp.xml')
    tree = ET.parse(manifest)
    root = tree.getroot()
    oldFeatures = set()
    oldPermissions = set()

    for element in root:
        if element.tag == 'uses-feature':
            for key in element.attrib:
                if key.endswith('name'):
                    oldFeatures.add(element.attrib[key])
        elif element.tag == 'uses-permission':
            for key in element.attrib:
                if key.endswith('name'):
                    oldPermissions.add(element.attrib[key])

    features -= oldFeatures
    permissions -= oldPermissions
    featuresWritten = len(features) < 1
    permissionsWritten = len(permissions) < 1
    replace = {'-- %%INSERT_APP_NAME%% --'     : appName,
               '-- %%INSERT_APP_LIB_NAME%% --' : appLibName,
               '-- %%INSERT_VERSION_NAME%% --' : version,
               '-- %%INSERT_VERSION_CODE%% --' : DTUtils.versionCode(version),
               '-- %%INSERT_INIT_CLASSES%% --' : ':'.join(sorted(initClasses)),
               '-- %%BUNDLE_LOCAL_QT_LIBS%% --': '1',
               '-- %%USE_LOCAL_QT_LIBS%% --'   : '1',
               '-- %%INSERT_LOCAL_LIBS%% --'   : ':'.join(sorted(libs)),
               '-- %%INSERT_LOCAL_JARS%% --'   : ':'.join(sorted(jars))}

    with open(manifest) as inFile:
        with open(manifestTemp, 'w') as outFile:
            for line in inFile:
                for key in replace:
                    line = line.replace(key, replace[key])

                outFile.write(line)
                spaces = len(line)
                line = line.lstrip()
                spaces -= len(line)

                if line.startswith('<uses-feature') and not featuresWritten:
                    print('\nUpdating features\n')

                    for feature in features:
                        print('    ' + feature)
                        outFile.write(spaces * ' ' + '<uses-feature android:name="{}"/>\n'.format(feature))

                    featuresWritten = True

                if line.startswith('<uses-permission') and not permissionsWritten:
                    print('\nUpdating permissions\n')

                    for permission in permissions:
                        print('    ' + permission)
                        outFile.write(spaces * ' ' + '<uses-permission android:name="{}"/>\n'.format(permission))

                    permissionsWritten = True

    os.remove(manifest)
    shutil.move(manifestTemp, manifest)

def createRccBundle(outputAssetsDir, verbose):
    outputAssetsDir = os.path.join(outputAssetsDir, 'android_rcc_bundle')
    assetsDir = os.path.abspath(os.path.join(outputAssetsDir, '..'))
    assetsFolder = os.path.relpath(outputAssetsDir, assetsDir)
    qrcFile = os.path.join(outputAssetsDir, assetsFolder + '.qrc')

    params = ['rcc',
              '--verbose',
              '--project',
              '-o', qrcFile]

    if verbose:
        process = subprocess.Popen(params, # nosec
                                   cwd=outputAssetsDir)
    else:
        process = subprocess.Popen(params, # nosec
                                   cwd=outputAssetsDir,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process.communicate()

    params = ['rcc',
              '--verbose',
              '--root=/{}'.format(assetsFolder),
              '--binary',
              '-o', outputAssetsDir + '.rcc',
              qrcFile]

    if verbose:
        process = subprocess.Popen(params, # nosec
                                   cwd=assetsDir)
    else:
        process = subprocess.Popen(params, # nosec
                                   cwd=assetsDir,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    process.communicate()

    shutil.rmtree(outputAssetsDir, True)

def fixQtLibs(globs, libDir, outputQtPluginsDir, outputAssetsDir):
    if not 'bundledInLib' in globs:
        globs['bundledInLib'] = set()

    rccDir = os.path.abspath(os.path.join(outputQtPluginsDir, '..'))

    for root, dirs, files in os.walk(outputAssetsDir):
        for f in files:
            if f.endswith('.so'):
                srcPath = os.path.join(root, f)
                relPath = os.path.relpath(root, rccDir)
                prefix = 'lib' + relPath.replace(os.path.sep, '_') + '_'
                lib = ''

                if f.startswith(prefix):
                    lib = f
                else:
                    lib = prefix + f

                dstPath = os.path.join(libDir, lib)
                print('    {} -> {}'.format(srcPath, dstPath))
                DTUtils.move(srcPath, dstPath)
                globs['bundledInLib'].add((lib, os.path.join(relPath, f)))

    try:
        shutil.rmtree(outputQtPluginsDir)
    except:
        pass

def qmakeQuery(var=''):
    try:
        args = ['qmake', '-query']

        if var != '':
            args += [var]

        process = subprocess.Popen(args, # nosec
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, _ = process.communicate()

        return stdout.strip().decode(sys.getdefaultencoding())
    except:
        pass

    return ''

def modulePath(importLine):
    imp = importLine.strip().split()
    path = imp[1].replace('.', '/')
    majorVersion = imp[2].split('.')[0]

    if int(majorVersion) > 1:
        path += '.{}'.format(majorVersion)

    return path

def scanImports(path):
    if not os.path.isfile(path):
        return []

    fileName = os.path.basename(path)
    imports = set()

    if fileName.endswith('.qml'):
        with open(path, 'rb') as f:
            for line in f:
                if re.match(b'^import \\w+' , line):
                    imports.add(modulePath(line.strip().decode(sys.getdefaultencoding())))
    elif fileName == 'qmldir':
        with open(path, 'rb') as f:
            for line in f:
                if re.match(b'^depends ' , line):
                    imports.add(modulePath(line.strip().decode(sys.getdefaultencoding())))

    return list(imports)

def listQmlFiles(path):
    qmlFiles = set()

    if os.path.isfile(path):
        baseName = os.path.basename(path)

        if baseName == 'qmldir' or path.endswith('.qml'):
            qmlFiles.add(path)
    else:
        for root, _, files in os.walk(path):
            for f in files:
                if f == 'qmldir' or f.endswith('.qml'):
                    qmlFiles.add(os.path.join(root, f))

    return list(qmlFiles)

def solvedepsQml(globs, sourcesQmlDirs, outputQmlDir, qtQmlDir):
    qmlFiles = set()

    for path in sourcesQmlDirs:
        for f in listQmlFiles(path):
            qmlFiles.add(f)

    solved = set()
    solvedImports = set()

    if not 'dependencies' in globs:
        globs['dependencies'] = set()

    while len(qmlFiles) > 0:
        qmlFile = qmlFiles.pop()

        for imp in scanImports(qmlFile):
            if imp in solvedImports:
                continue

            sysModulePath = os.path.join(qtQmlDir, imp)
            installModulePath = os.path.join(outputQmlDir, imp)

            if os.path.exists(sysModulePath):
                print('    {} -> {}'.format(sysModulePath, installModulePath))
                DTUtils.copy(sysModulePath, installModulePath)
                solvedImports.add(imp)
                globs['dependencies'].add(os.path.join(sysModulePath, 'qmldir'))

                for f in listQmlFiles(sysModulePath):
                    if not f in solved:
                        qmlFiles.add(f)

        solved.add(qmlFile)

def solvedepsPlugins(globs,
                     targetPlatform,
                     targetArch,
                     dataDir,
                     outputQtPluginsDir,
                     qtPluginsDir,
                     sysLibDir,
                     stripCmd='strip'):
    pluginsMap = {
        'Qt53DRenderer': ['sceneparsers',
                          'renderers',
                          'renderplugins',
                          'geometryloaders'],
        'Qt53DQuickRenderer': ['renderplugins'],
        'Qt5Declarative': ['qml1tooling'],
        'Qt5EglFSDeviceIntegration': ['egldeviceintegrations'],
        'Qt5GamePad': ['gamepads'],
        'Qt5Gui': ['accessible',
                   'generic',
                   'iconengines',
                   'imageformats',
                   'platforms',
                   'platforminputcontexts',
                   'styles',
                   'virtualkeyboard'],
        'Qt5Location': ['geoservices'],
        'Qt5Multimedia': ['audio', 'mediaservice', 'playlistformats'],
        'Qt5Network': ['bearer', 'networkaccess', 'networkinformation', 'tls'],
        'Qt5Positioning': ['position'],
        'Qt5PrintSupport': ['printsupport'],
        'Qt5QmlTooling': ['qmltooling'],
        'Qt5Quick': ['scenegraph', 'qmltooling'],
        'Qt5Sensors': ['sensors', 'sensorgestures'],
        'Qt5SerialBus': ['canbus'],
        'Qt5ShaderTools': ['renderers'],
        'Qt5Sql': ['sqldrivers'],
        'Qt5TextToSpeech': ['texttospeech'],
        'Qt5WebEngine': ['qtwebengine'],
        'Qt5WebEngineCore': ['qtwebengine'],
        'Qt5WebEngineWidgets': ['qtwebengine'],
        'Qt5WebView': ['webview'],
        'Qt5Widgets': ['styles'],
    }

    pluginsMap.update({lib + 'd': pluginsMap[lib] for lib in pluginsMap})
    pluginsMap.update({lib.replace('Qt5', 'Qt'): pluginsMap[lib] for lib in pluginsMap})

    if targetPlatform == 'android':
        pluginsMap.update({lib + '_' + targetArch: pluginsMap[lib] for lib in pluginsMap})
    elif targetPlatform == 'mac':
        pluginsMap.update({lib + '.framework': pluginsMap[lib] for lib in pluginsMap})

    if not 'dependencies' in globs:
        globs['dependencies'] = set()

    solver = DTBinary.BinaryTools(DTUtils.hostPlatform(),
                                  targetPlatform,
                                  targetArch,
                                  sysLibDir,
                                  stripCmd)
    plugins = []

    for dep in solver.scanDependencies(dataDir):
        libName = solver.name(dep)

        if not libName in pluginsMap:
            continue

        for plugin in pluginsMap[libName]:
            if not plugin in plugins:
                sysPluginPath = os.path.join(qtPluginsDir, plugin)
                pluginPath = os.path.join(outputQtPluginsDir, plugin)

                if not os.path.exists(sysPluginPath):
                    continue

                print('    {} -> {}'.format(sysPluginPath, pluginPath))
                DTUtils.copy(sysPluginPath, pluginPath)
                plugins.append(plugin)
                globs['dependencies'].add(sysPluginPath)

def removeDebugs(dataDir):
    dbgFiles = set()
    libQtInstallDir = \
        qmakeQuery('QT_INSTALL_ARCHDATA') \
            .replace(qmakeQuery('QT_INSTALL_PREFIX'), dataDir)

    for root, _, files in os.walk(libQtInstallDir):
        for f in files:
            if f.endswith('.dll'):
                fname, ext = os.path.splitext(f)
                dbgFile = os.path.join(root, '{}d{}'.format(fname, ext))

                if os.path.exists(dbgFile):
                    dbgFiles.add(dbgFile)

    for f in dbgFiles:
        os.remove(f)

def removeInvalidAndroidArchs(targetArch, assetsDir):
    suffix = '_{}.so'.format(targetArch)

    for root, dirs, files in os.walk(assetsDir):
        for f in files:
            if f.endswith('.so') and not f.endswith(suffix):
                os.remove(os.path.join(root, f))

def writeQtConf(qtConfFile,
                mainExecutable,
                targetPlatform,
                outputQmlDir,
                outputQtPluginsDir):
    prefix = os.path.dirname(mainExecutable)

    if targetPlatform == 'mac':
        prefix = os.path.abspath(os.path.join(prefix, '..'))

    paths = {'Plugins': os.path.relpath(outputQtPluginsDir, prefix).replace('\\', '/'),
             'Imports': os.path.relpath(outputQmlDir, prefix).replace('\\', '/'),
             'Qml2Imports': os.path.relpath(outputQmlDir, prefix).replace('\\', '/')}
    confPath = os.path.dirname(qtConfFile)

    if not os.path.exists(confPath):
        os.makedirs(confPath)

    with open(qtConfFile, 'w') as qtconf:
        qtconf.write('[Paths]\n')
        print('[Paths]')

        for path in paths:
            qtconf.write('{} = {}\n'.format(path, paths[path]))
            print('{} = {}'.format(path, paths[path]))

def preRun(globs, configs, dataDir):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    libDir = configs.get('Package', 'libDir', fallback='').strip()
    libDir = os.path.join(dataDir, libDir)
    defaultSysLibDir = ''

    if targetPlatform == 'android':
        defaultSysLibDir = '/opt/android-libs/{}/lib'.format(targetArch)
    elif targetPlatform == 'mac':
        defaultSysLibDir = '/usr/local/lib'

    sysLibDir = configs.get('System', 'libDir', fallback=defaultSysLibDir)
    libs = set()

    for lib in sysLibDir.split(','):
        libs.add(lib.strip())

    sysLibDir = list(libs)
    sourcesQmlDirs = configs.get('Qt5', 'sourcesQmlDirs', fallback='').split(',')
    sourcesQmlDirs = [os.path.join(sourcesDir, module.strip()) for module in sourcesQmlDirs]
    outputQmlDir = configs.get('Qt5', 'outputQmlDir', fallback='qml').strip()
    outputQmlDir = os.path.join(dataDir, outputQmlDir)
    defaultQtQmlDir = qmakeQuery('QT_INSTALL_QML')
    qtQmlDir = configs.get('Qt5', 'qtQmlDir', fallback=defaultQtQmlDir).strip()
    outputQtPluginsDir = configs.get('Qt5', 'outputQtPluginsDir', fallback='plugins').strip()
    outputQtPluginsDir = os.path.join(dataDir, outputQtPluginsDir)
    defaultQtPluginsDir = qmakeQuery('QT_INSTALL_PLUGINS')
    qtPluginsDir = configs.get('Qt5', 'qtPluginsDir', fallback=defaultQtPluginsDir).strip()
    outputAssetsDir = configs.get('Android', 'outputAssetsDir', fallback='assets').strip()
    outputAssetsDir = os.path.join(dataDir, outputAssetsDir)
    mainExecutable = configs.get('Package', 'mainExecutable', fallback='').strip()
    mainExecutable = os.path.join(dataDir, mainExecutable)
    qtConfFile = configs.get('Qt5', 'qtConfFile', fallback='qt.conf').strip()
    qtConfFile = os.path.join(dataDir, qtConfFile)
    stripCmd = configs.get('System', 'stripCmd', fallback='strip').strip()

    print('Qt information')
    print()
    print('Qml sources directory: {}'.format(sourcesQmlDirs))
    print('Qt plugins directory: {}'.format(qtPluginsDir))
    print('Qt plugins output directory: {}'.format(outputQtPluginsDir))
    print('Qt Qml files directory: {}'.format(qtQmlDir))
    print('Qt Qml files output directory: {}'.format(outputQmlDir))
    print()
    print('Copying Qml modules')
    print()
    solvedepsQml(globs, sourcesQmlDirs, outputQmlDir, qtQmlDir)
    print()
    print('Copying required plugins')
    print()
    solvedepsPlugins(globs,
                     targetPlatform,
                     targetArch,
                     dataDir,
                     outputQtPluginsDir,
                     qtPluginsDir,
                     sysLibDir,
                     stripCmd)
    print()

    if targetPlatform == 'windows':
        print('Removing Qt debug libraries')
        removeDebugs(dataDir)
    elif targetPlatform == 'android':
        assetsDir = configs.get('Package', 'assetsDir', fallback='assets').strip()
        assetsDir = os.path.join(dataDir, assetsDir)
        qtSourcesDir = configs.get('Qt5', 'sourcesDir', fallback='').strip()
        sdkBuildToolsRevision = configs.get('System', 'sdkBuildToolsRevision', fallback='').strip()
        androidCompileSdkVersion = configs.get('System', 'androidCompileSdkVersion', fallback='').strip()

        print('Removing unused architectures')
        removeInvalidAndroidArchs(targetArch, assetsDir)
        print('Fixing Android libs')
        fixQtLibs(globs, libDir, outputQtPluginsDir, outputAssetsDir)
        print()
        print('Copying Android build templates')
        copyAndroidTemplates(dataDir,
                             qtSourcesDir,
                             sdkBuildToolsRevision,
                             androidCompileSdkVersion)

    if targetPlatform != 'android':
        print('Writting qt.conf file')
        print()
        writeQtConf(qtConfFile,
                    mainExecutable,
                    targetPlatform,
                    outputQmlDir,
                    outputQtPluginsDir)

    print()

    if not 'environment' in globs:
        globs['environment'] = set()

    if targetPlatform == 'windows':
        globs['environment'].add(('QT_OPENGL', 'angle', 'Default values: desktop | angle | software', True))
        globs['environment'].add(('QT_ANGLE_PLATFORM', 'd3d11', 'Default values: d3d11 | d3d9 | warp', True))
        globs['environment'].add(('QT_QUICK_BACKEND', '', 'Default values: software | d3d12 | openvg', True))

    globs['environment'].add(('QT_DEBUG_PLUGINS', 1, 'Enable plugin debugging', True))

def postRun(globs, configs, dataDir):
    sourcesDir = configs.get('Package', 'sourcesDir', fallback='.').strip()
    name = configs.get('Package', 'name', fallback='app').strip()
    version = DTUtils.programVersion(configs, sourcesDir)
    appLibName = configs.get('Android', 'appLibName', fallback=name).strip()
    targetPlatform = configs.get('Package', 'targetPlatform', fallback='').strip()
    targetArch = configs.get('Package', 'targetArch', fallback='').strip()
    verbose = configs.get('Qt5', 'verbose', fallback='false').strip()
    verbose = DTUtils.toBool(verbose)
    libDir = configs.get('Package', 'libDir', fallback='').strip()
    libDir = os.path.join(dataDir, libDir)
    defaultSysLibDir = ''

    if targetPlatform == 'android':
        defaultSysLibDir = '/opt/android-libs/{}/lib'.format(targetArch)
    elif targetPlatform == 'mac':
        defaultSysLibDir = '/usr/local/lib'

    sysLibDir = configs.get('System', 'libDir', fallback=defaultSysLibDir)
    libs = set()

    for lib in sysLibDir.split(','):
        libs.add(lib.strip())

    sysLibDir = list(libs)
    outputAssetsDir = configs.get('Android', 'outputAssetsDir', fallback='assets').strip()
    outputAssetsDir = os.path.join(dataDir, outputAssetsDir)

    if targetPlatform == 'android':
        print('Solving Android dependencies')
        solvedepsAndroid(globs,
                         dataDir,
                         libDir,
                         sysLibDir,
                         name,
                         appLibName,
                         version)
        print()
        print('Fixing libs.xml file')
        fixLibsXml(globs, targetArch, dataDir)
        print('Creating .rcc bundle file')
        createRccBundle(outputAssetsDir, verbose)
        print()
