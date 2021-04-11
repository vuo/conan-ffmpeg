from conans import AutoToolsBuildEnvironment, ConanFile, tools
import os
import platform

class FfmpegConan(ConanFile):
    name = 'ffmpeg'

    source_version = '4.4'
    package_version = '0'
    version = '%s-%s' % (source_version, package_version)

    build_requires = (
        'llvm/5.0.2-1@vuo+conan+llvm/stable',
        'macos-sdk/11.0-0@vuo+conan+macos-sdk/stable',
        'vuoutils/1.2@vuo+conan+vuoutils/stable',
    )
    requires = 'openssl/1.1.1h-0@vuo+conan+openssl/stable'
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'http://www.ffmpeg.org/'
    license = 'http://www.ffmpeg.org/legal.html'
    description = 'A cross-platform library for recording, converting, and streaming audio and video'
    source_dir = 'ffmpeg-%s' % source_version

    build_x86_dir = '_build_x86'
    build_arm_dir = '_build_arm'
    install_x86_dir = '_install_x86'
    install_arm_dir = '_install_arm'
    install_universal_dir = '_install_universal_dir'

    libs = {
        'avcodec': 58,
        'avdevice': 58,
        'avfilter': 7,
        'avformat': 58,
        'avutil': 56,
        'swresample': 3,
        'swscale': 5,
    }
    exports_sources = '*.patch'

    def requirements(self):
        if platform.system() == 'Linux':
            self.requires('patchelf/0.10pre-1@vuo/stable')
        elif platform.system() != 'Darwin':
            raise Exception('Unknown platform "%s"' % platform.system())

    def source(self):
        tools.get('http://www.ffmpeg.org/releases/ffmpeg-%s.tar.bz2' % self.source_version,
                  sha256='42093549751b582cf0f338a21a3664f52e0a9fbe0d238d3c992005e493607d0e')

        # On both Linux and macOS, tell ./configure to check for the presence of OPENSSL_init_ssl
        # (instead of the removed-in-openssl-1.1 SSL_library_init).
        if platform.system() == 'Linux':
            # Tell ./configure that it needs the dynamic linker in order to link with OpenSSL.
            # (`autotools.libs.append('dl')` doesn't work because it appears before the OpenSSL libraries on the ./configure command line.)
            tools.replace_in_file('%s/configure' % self.source_dir,
                                  '                               check_lib openssl openssl/ssl.h SSL_library_init -lssl -lcrypto ||',
                                  '                               check_lib openssl openssl/ssl.h OPENSSL_init_ssl -lssl -lcrypto -ldl -lpthread ||')
        else:
            tools.replace_in_file('%s/configure' % self.source_dir,
                                  '                               check_lib openssl openssl/ssl.h SSL_library_init -lssl -lcrypto ||',
                                  '                               check_lib openssl openssl/ssl.h OPENSSL_init_ssl -lssl -lcrypto ||')

        self.run('mv %s/LICENSE.md %s/%s.txt' % (self.source_dir, self.source_dir, self.name))

    def build(self):
        import VuoUtils

        autotools = AutoToolsBuildEnvironment(self)

        # The LLVM/Clang libs get automatically added by the `requires` line,
        # but this package doesn't need to link with them.
        autotools.libs = []

        autotools.flags.append('-I%s/include' % self.deps_cpp_info['openssl'].rootpath)
        autotools.link_flags.append('-L%s/lib' % self.deps_cpp_info['openssl'].rootpath)

        if platform.system() == 'Darwin':
            # autotools.flags.append('-Oz')  # Superseded by `--enable-small` below.
            autotools.flags.append('-isysroot %s' % self.deps_cpp_info['macos-sdk'].rootpath)
            autotools.flags.append('-mmacosx-version-min=10.11')
            autotools.link_flags.append('-isysroot %s' % self.deps_cpp_info['macos-sdk'].rootpath)
            autotools.link_flags.append('-Wl,-macos_version_min,10.11')
            autotools.link_flags.append('-Wl,-headerpad_max_install_names')
        elif platform.system() == 'Linux':
            autotools.flags.append('-O4')

        common_configure_args = [
            '--disable-programs',
            '--disable-doc',
            '--enable-shared',
            '--disable-stripping',  # Keep symbols during development; remove them during the final VuoPackageEditor/VuoPackageSDK step.
            '--disable-static',
            '--enable-pthreads',
            '--disable-debug',
            '--enable-demuxer=mpegts',
            '--enable-demuxer=mpegtsraw',
            '--disable-bsfs',
            '--disable-devices',
            '--enable-openssl',

            '--enable-small',  # Reduces library size by about 25%.
            # '--enable-lto',  # No effect on library size.
            # '--disable-runtime-cpudetect',  # No effect on library size.

            # Disable unneeded features; reduces library size by about 20%.
            '--disable-muxers',
            '--disable-devices',
            '--disable-filters',
            '--disable-bzlib',
            '--disable-iconv',
            # Only enable the encoder needed for RTMP.
            '--disable-encoders',
            '--enable-encoder=h264_videotoolbox',

            # Use AVFoundation's hardware-accelerated H.264 decoder instead.
            '--disable-decoder=h264',

            # Avoid patented codecs.
            '--disable-decoder=aac',
            '--disable-decoder=aac_latm',
            '--disable-encoder=aac',
            '--disable-parser=aac',
            '--disable-parser=aac_latm',
            '--disable-demuxer=aac',
            '--disable-decoder=mp3',
            '--disable-decoder=mp3adu',
            '--disable-decoder=mp3adufloat',
            '--disable-decoder=mp3float',
            '--disable-decoder=mp3on4',
            '--disable-decoder=mp3on4float',
            '--disable-demuxer=mp3',
            '--disable-muxer=mp3',
        ]

        env_vars = {
            'CC' : self.deps_cpp_info['llvm'].rootpath + '/bin/clang',
            'CXX': self.deps_cpp_info['llvm'].rootpath + '/bin/clang++',
        }
        with tools.environment_append(env_vars):
            build_root = os.getcwd()

            self.output.info("=== Build for x86_64 ===")
            tools.mkdir(self.build_x86_dir)
            with tools.chdir(self.build_x86_dir):
                autotools.flags.append('-arch x86_64')
                autotools.link_flags.append('-arch x86_64')

                autotools.configure(configure_dir='../%s' % self.source_dir,
                                    build=False,
                                    host=False,
                                    args=common_configure_args + [
                                        '--prefix=%s/%s' % (build_root, self.install_x86_dir),
                                        '--enable-x86asm'])

                autotools.make(args=['--quiet'])
                autotools.make(target='install', args=['--quiet'])
            with tools.chdir('%s/lib' % self.install_x86_dir):
                VuoUtils.fixLibs(self.libs, self.deps_cpp_info)

            self.output.info("=== Build for arm64 ===")
            tools.mkdir(self.build_arm_dir)
            with tools.chdir(self.build_arm_dir):
                autotools.flags.remove('-arch x86_64')
                autotools.flags.remove('-mmacosx-version-min=10.11')
                autotools.flags.append('-arch arm64')
                autotools.flags.append('-target arm64-apple-macosx11.0.0')
                autotools.link_flags.remove('-arch x86_64')
                autotools.link_flags.remove('-Wl,-macos_version_min,10.11')
                autotools.link_flags.append('-arch arm64')
                autotools.link_flags.append('-target arm64-apple-macosx11.0.0')

                autotools.configure(configure_dir='../%s' % self.source_dir,
                                    build=False,
                                    host=False,
                                    args=common_configure_args + [
                                        '--prefix=%s/%s' % (build_root, self.install_arm_dir),
                                        '--enable-cross-compile',
                                        '--disable-asm',
                                        '--target-os=darwin',
                                        '--arch=arm64'])

                autotools.make(args=['--quiet'])
                autotools.make(target='install', args=['--quiet'])
            with tools.chdir('%s/lib' % self.install_arm_dir):
                VuoUtils.fixLibs(self.libs, self.deps_cpp_info)

    def package(self):
        import VuoUtils

        tools.mkdir(self.install_universal_dir)
        with tools.chdir(self.install_universal_dir):
            for f in self.libs:
                self.run('lipo -create ..//%s/lib/lib%s.dylib ../%s/lib/lib%s.dylib -output lib%s.dylib' % (self.install_x86_dir, f, self.install_arm_dir, f, f))

        self.copy('*.h', src='%s/include' % self.install_x86_dir, dst='include')

        if platform.system() == 'Darwin':
            libext = 'dylib'
        elif platform.system() == 'Linux':
            libext = 'so'
        else:
            raise Exception('Unknown platform "%s"' % platform.system())

        for f in list(self.libs.keys()):
            self.copy('lib%s.%s' % (f, libext), src=self.install_universal_dir, dst='lib')

        self.copy('%s.txt' % self.name, src=self.source_dir, dst='license')

    def package_info(self):
        self.cpp_info.libs = list(self.libs.keys())
