#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, AutoToolsBuildEnvironment, MSBuild
from conans.errors import ConanException
import os


class VorbisConan(ConanFile):
    name = "vorbis"
    version = "1.3.5"
    description = "The VORBIS audio codec library"
    url = "http://github.com/bincrafters/conan-vorbis"
    homepage = "https://xiph.org/vorbis/"
    license = "BSD"
    exports = ["LICENSE.md", "FindVORBIS.cmake"]
    source_subfolder = "sources"
    settings = "os", "arch", "build_type", "compiler"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"
    requires = "ogg/1.3.3@bincrafters/stable"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.remove("fPIC")

    def configure(self):
        if self.settings.os == "Windows" and self.settings.compiler != "Visual Studio":
            raise ConanException(
                "On Windows, version 1.3.5 of the vorbis package only supports "
                "the Visual Studio compiler for the time being."
            )

        del self.settings.compiler.libcxx

    def source(self):
        source_url = "http://downloads.xiph.org/releases"
        archive_name = "lib" + self.name + "-" + self.version
        tools.get("{url}/{libname}/{archive_name}.tar.gz".format(
            url=source_url, libname=self.name, archive_name=archive_name)
        )
        os.rename(archive_name, self.source_subfolder)

    def build_with_visual_studio(self):

        def update_projects_in_solution(solution_folder, shared):
            """
            Update vs projects in solution_folder to build with ogg dependency from conan
            :param solution_folder: solution folder
            :param shared: True or False
            :returns solution filename
            """
            suffix = "_dynamic" if shared else "_static"

            for project in ["vorbisenc", "vorbisdec", "libvorbis", "libvorbisfile"]:
                filename = project + suffix + ".vcxproj"
                path = os.path.join(solution_folder, project, filename)
                libdirs = "<AdditionalLibraryDirectories>"
                libdirs_ext = "<AdditionalLibraryDirectories>$(LIB);"

                updated_content = tools \
                    .load(path) \
                    .replace("libogg.lib", "ogg.lib") \
                    .replace("libogg_static.lib", "ogg.lib") \
                    .replace(libdirs, libdirs_ext)

                tools.save(path, updated_content)

            return "vorbis" + suffix + ".sln"

        sln_folder = os.path.join(self.source_subfolder, "win32", "VS2010")
        sln_filename = update_projects_in_solution(sln_folder, self.options.shared)

        with tools.chdir(sln_folder):
            msbuild = MSBuild(self)
            msbuild.build(sln_filename, platforms={"x86": "Win32"})

    def build_with_autotools(self):
        env = AutoToolsBuildEnvironment(self)

        with tools.chdir(self.source_subfolder):
            with tools.environment_append(env.vars):

                if self.settings.compiler == "clang" and self.settings.arch == "x86":
                    # http://lists.llvm.org/pipermail/llvm-bugs/2015-November/043264.html
                    tools.replace_in_file("configure", " -mno-ieee-fp ", " ")

                configure_args = ["--prefix=%s" % self.package_folder]

                if self.options.shared:
                    configure_args.extend(["--disable-static", "--enable-shared"])
                else:
                    configure_args.extend(["--disable-shared", "--enable-static"])
                env.configure(args=configure_args)
                env.make()
                env.make(args=["install"])

    def build(self):
        if self.settings.compiler == "Visual Studio":
            self.build_with_visual_studio()
        else:
            self.build_with_autotools()

    def package(self):
        self.copy("FindOGG.cmake")
        self.copy("COPYING", src=self.source_subfolder, dst="licenses", keep_path=False)
        self.copy("LICENSE.md", dst="licenses", keep_path=False)

        if self.settings.compiler == "Visual Studio":
            # Visual Studio build is not installing installing any artifact.
            # Packaging needs to be done.
            src_include_dir = os.path.join(self.source_subfolder, "include")
            self.copy("*.h", dst="include", src=src_include_dir, keep_path=True)
            self.copy(pattern="*.pdb", dst="bin", keep_path=False)
            self.copy(pattern="*.lib", dst="lib", keep_path=False)

            if self.options.shared:
                self.copy(pattern="*.dll", dst="bin", keep_path=False)

    def package_info(self):
        if self.settings.compiler == "Visual Studio":
            if self.options.shared:
                self.cpp_info.libs = ['libvorbis', 'libvorbisfile']
            else:
                self.cpp_info.libs = ['libvorbis_static', 'libvorbisfile_static']
                self.cpp_info.exelinkflags.append('-NODEFAULTLIB:LIBCMTD')
                self.cpp_info.exelinkflags.append('-NODEFAULTLIB:LIBCMT')
        else:
            self.cpp_info.libs = ['vorbisfile', 'vorbisenc', 'vorbis']

        if self.settings.os == "Linux" and not self.options.shared:
            self.cpp_info.libs.append("m")
