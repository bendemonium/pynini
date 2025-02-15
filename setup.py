# Copyright 2016-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For general information on the Pynini grammar compilation library, see
# pynini.opengrm.org.
"""Setup for Pynini."""

import os.path
import pathlib
import sys

import subprocess
from Cython.Build import cythonize
from setuptools import Extension
from setuptools import find_packages
from setuptools import setup

IS_MACOS = sys.platform.startswith("darwin")
IS_ARM64 = sys.platform == "darwin" and "arm64" in os.uname().machine

# Static OpenFst flag
ENABLE_STATIC_OPENFST = "--enable-static-openfst" in sys.argv
if ENABLE_STATIC_OPENFST:
    sys.argv.remove("--enable-static-openfst")

COMPILE_ARGS = [
    "-std=c++17",
    "-Wno-register",
    "-Wno-deprecated-declarations",
    "-Wno-unused-function",
    "-Wno-unused-local-typedefs",
    "-funsigned-char",
]
if IS_MACOS:
    COMPILE_ARGS.append("-stdlib=libc++")
    COMPILE_ARGS.append("-mmacosx-version-min=10.12")

# Default OpenFst paths for ARM64 macOS (Homebrew default for Apple Silicon)
OPENFST_PREFIX = "/opt/homebrew" if IS_ARM64 else "/usr/local"
OPENFST_INCLUDE = os.path.join(OPENFST_PREFIX, "include")
OPENFST_LIB = os.path.join(OPENFST_PREFIX, "lib")

if ENABLE_STATIC_OPENFST and IS_MACOS:
    OPENFST_VERSION = "1.8.4"
    OPENFST_DIR = f"openfst-{OPENFST_VERSION}"
    OPENFST_URL = f"http://www.openfst.org/twiki/pub/FST/FstDownload/{OPENFST_DIR}.tar.gz"

    if not os.path.exists(OPENFST_DIR):
        print(f"Downloading and building OpenFst {OPENFST_VERSION} for static linking (ARM64)...")
        subprocess.run(f"curl -L {OPENFST_URL} -o openfst.tar.gz", shell=True, check=True)
        subprocess.run("tar -xzf openfst.tar.gz", shell=True, check=True)
        os.chdir(OPENFST_DIR)
        
        arch_flag = "--host=aarch64-apple-darwin" if IS_ARM64 else ""
        subprocess.run(f"./configure {arch_flag} --enable-static --disable-shared --prefix=$(pwd)/build", shell=True, check=True)
        subprocess.run("make -j$(sysctl -n hw.ncpu) && make install", shell=True, check=True)
        os.chdir("..")

    # Update include and lib paths
    OPENFST_INCLUDE = os.path.abspath(f"{OPENFST_DIR}/build/include")
    OPENFST_LIB = os.path.abspath(f"{OPENFST_DIR}/build/lib")

    print(f"Using static OpenFst from {OPENFST_LIB} (ARM64)")

LIBRARIES = ["fstfarscript", "fstfar", "fstscript", "fst", "m", "dl"]

if ENABLE_STATIC_OPENFST and IS_MACOS:
    LIBRARIES = [os.path.join(OPENFST_LIB, "libfst.a")]

pywrapfst = Extension(
    name="_pywrapfst",
    language="c++",
    extra_compile_args=COMPILE_ARGS,
    libraries=LIBRARIES,
    library_dirs=[OPENFST_LIB],
    include_dirs=[OPENFST_INCLUDE],
    sources=["extensions/_pywrapfst.pyx"],
)

pynini = Extension(
    name="_pynini",
    language="c++",
    extra_compile_args=COMPILE_ARGS,
    libraries=["fstmpdtscript", "fstpdtscript"] + LIBRARIES,
    library_dirs=[OPENFST_LIB],
    include_dirs=[OPENFST_INCLUDE],
    sources=[
        "extensions/_pynini.pyx",
        "extensions/cdrewritescript.cc",
        "extensions/concatrangescript.cc",
        "extensions/crossscript.cc",
        "extensions/defaults.cc",
        "extensions/getters.cc",
        "extensions/lenientlycomposescript.cc",
        "extensions/optimizescript.cc",
        "extensions/pathsscript.cc",
        "extensions/stringcompile.cc",
        "extensions/stringcompilescript.cc",
        "extensions/stringfile.cc",
        "extensions/stringmapscript.cc",
        "extensions/stringprintscript.cc",
        "extensions/stringutil.cc",
    ],
)


this_directory = pathlib.Path(os.path.abspath(os.path.dirname(__file__)))
with (this_directory / "README.md").open(encoding="utf8") as source:
  long_description = source.read()


def get_version(rel_path):
  # Searches through a file to find a `__version__ = "X.Y.Z"` string.
  # From https://packaging.python.org/guides/single-sourcing-package-version/.
  with (this_directory / rel_path).open(encoding="utf8") as fp:
    for line in fp:
      if line.startswith("__version__"):
        delim = '"' if '"' in line else "'"
        return line.split(delim)[1]
    else:
      raise RuntimeError("Unable to find version string.")


__version__ = get_version("pynini/__init__.py")


def main() -> None:
  setup(
      name="pynini",
      version=__version__,
      author="Kyle Gorman",
      author_email="kbg@google.com",
      description="Finite-state grammar compilation",
      long_description=long_description,
      long_description_content_type="text/markdown",
      url="http://pynini.opengrm.org",
      keywords=[
          "computational linguistics",
          "natural language processing",
          "speech recognition",
          "machine learning",
      ],
      classifiers=[
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: 3.10",
          "Programming Language :: Python :: 3.11",
          "Programming Language :: Python :: 3.12",
          "Programming Language :: Python :: 3.13",
          "Development Status :: 5 - Production/Stable",
          "Environment :: Other Environment",
          "Environment :: Console",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: OS Independent",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Topic :: Text Processing :: Linguistic",
          "Topic :: Scientific/Engineering :: Artificial Intelligence",
          "Topic :: Scientific/Engineering :: Mathematics",
      ],
      license="Apache 2.0",
      ext_modules=cythonize([pywrapfst, pynini]),
      packages=find_packages(exclude=["scripts", "tests"]),
      package_data={
          "pywrapfst": ["__init__.pyi", "py.typed"],
          "pynini": ["__init__.pyi", "py.typed"],
          "pynini.examples": ["py.typed"],
          "pynini.export": ["py.typed"],
          "pynini.lib": ["py.typed"],
      },
      zip_safe=False,
  )


if __name__ == "__main__":
  main()
