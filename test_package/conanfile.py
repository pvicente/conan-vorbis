#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from conans import ConanFile, CMake, tools
import os
import subprocess
import sys

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def imports(self):
        self.copy("*.dll", dst="bin", src="bin")
        self.copy("*.dylib*", dst="bin", src="lib")
        self.copy('*.so*', dst='bin', src='lib')

        test_package_dir = os.path.dirname(os.path.abspath(__file__))
        self.copy("sample.wav", src=test_package_dir, dst="bin")

    def test(self):
        with tools.chdir("bin"):
            with open("sample.wav", "rb") as input:
                with open("sample.ogg", "wb") as output:
                    try:
                        subprocess.check_call(
                            [".%stest_package" % os.sep],
                            stdin=input,
                            stdout=output,
                            stderr=subprocess.STDOUT
                        )
                    except subprocess.CalledProcessError as e:
                        print("Test Error!!! cmd: %s return code: %s output: %s" % (e.cmd, e.returncode, e.output))
                        sys.exit(e.returncode)
                    else:
                        print("Test OK!!!")
