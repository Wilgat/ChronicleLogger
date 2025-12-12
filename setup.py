# setup.py — works on Python 2.7 and Python 3.8–3.13
from __future__ import print_function
import io
import os
from setuptools import setup, find_packages

def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()

def get_version():
    version_file = os.path.join("src", "chronicle_logger", "__init__.py")
    with open(version_file) as f:
        for line in f:
            if line.startswith("__version__"):
                return eval(line.split("=")[-1])
    raise RuntimeError("Unable to find __version__")

# ------------------------------------------------------------------
setup(
    name="ChronicleLogger",
    version=get_version(),
    description="Privilege-aware, auto-rotating daily logger for Linux daemons & CLI tools",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Wilgat Wong",
    author_email="wilgat.wong@gmail.com",
    url="https://github.com/Wilgat/ChronicleLogger",
    project_urls={
        "Bug Tracker": "https://github.com/Wilgat/ChronicleLogger/issues",
        "Source": "https://github.com/Wilgat/ChronicleLogger",
    },
    license="MIT",
    keywords="logging linux daemon sudo privilege log rotation daily",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=True,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Logging",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
    ],
)