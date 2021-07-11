import os
from setuptools import setup

from bloggen import __version__


description = """Pandoc based blog generator for automatic
conversion from markdown with support for categories and tags."""

with open("README.md") as f:
    long_description = f.read()

setup(
    name="bloggen",
    version=__version__,
    description=description,
    long_description=long_description,
    url="https://github.com/akshaybadola/bloggen",
    author="Akshay Badola",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Topic :: Documentation",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Content Management System",
        "Topic :: Text Processing :: Markup",
        "Topic :: Text Processing :: Markup :: HTML",
        "Topic :: Text Processing :: Markup :: Markdown",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Natural Language :: English",
    ],
    packages=["bloggen"],
    include_package_data=True,
    keywords='blog html markdown',
    python_requires=">=3.6, <=4.0",
    install_requires=[
        "PyYAML==5.4.1",
        "beautifulsoup4==4.9.3"],
    entry_points={
        'console_scripts': [
            'bloggen = bloggen.__main__:main',
        ],
    }
)
