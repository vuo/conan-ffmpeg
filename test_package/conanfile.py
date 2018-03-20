from conans import ConanFile
import platform

class FfmpegTestConan(ConanFile):
    generators = 'qbs'

    def build(self):
        self.run('qbs -f "%s"' % self.source_folder)

    def imports(self):
        self.copy('*', src='bin', dst='bin')
        self.copy('*', dst='lib', src='lib')

    def test(self):
        libs = ['avcodec', 'avdevice', 'avfilter', 'avformat', 'swresample', 'swscale']
        for f in libs:
            self.run('otool -L "lib/lib%s.dylib"' % f)
            self.run('echo %s rpath:' % f)
            self.run('otool -l "lib/lib%s.dylib" | grep -A2 LC_RPATH | cut -d"(" -f1' % f)

        self.run('qbs run')

        # Ensure we only link to system libraries and our own libraries.
        if platform.system() == 'Darwin':
            self.run('! (otool -L lib/*.dylib | grep -v "^lib/" | egrep -v "^\s*(/usr/lib/|/System/|@rpath/)")')
        elif platform.system() == 'Linux':
            self.run('! (ldd lib/*.so | grep -v "^lib/" | grep "/" | egrep -v "\s/lib64/")')
        else:
            raise Exception('Unknown platform "%s"' % platform.system())
