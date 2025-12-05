#!/home/adm01/.pyenv/versions/3.12.11/bin/python3
from setuptools import setup
from Cython.Build import cythonize

setup(
  ext_modules=cythonize("src/ChronicleLogger.pyx",compiler_directives={"language_level" : "3"})
)
