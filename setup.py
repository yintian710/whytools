# -*- coding: gbk -*-
"""
@File    : setup.py
@Date    : 2024/4/15 下午7:23
@Author  : yintian
@Desc    : 
"""
# Note: To use the 'upload' functionality of this file, you must:
#   $ pipenv install twine --dev

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command

from ytools.utils.file import get_file_read
from ytools.log import logger
from ytools.version import update_version, save_version

# Package meta-data.
NAME = 'why-tools'
DESCRIPTION = '为什么还要使用别的工具呢？'
URL = 'https://github.com/yintian710/whytools'
EMAIL = 'yintian710@gmail.com'
AUTHOR = 'yintian'
REQUIRES_PYTHON = '>=3.8.0'

VERSION = update_version(save=False)

# What packages are required for this module to be executed?
REQUIRED = [
    line.strip() for line in get_file_read('requirements.txt', safe=True).splitlines()
    if not line.startswith('#')
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {
    '__version__': VERSION
}


class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def log(s):
        logger.info(s)

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):

        if len(sys.argv) > 1:
            return
        try:
            self.log('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.log('Building Source and Wheel (universal) distribution…')
        os.system(f'{sys.executable} setup.py sdist bdist_wheel --universal')
        self.log('Building Source and Wheel (universal) distribution…')
        os.system(f'{sys.executable} setup.py sdist build')

        self.log('Uploading the package to PyPI via Twine…')
        os.system('twine upload dist/*')
        save_version(version=about['__version__'])

        self.log('Pushing git tags…')
        os.system('git commit -a -m v{0}'.format(about['__version__']))
        os.system('git push')
        # os.system()
        if 'b' not in about['__version__']:
            os.system('git tag v{0}'.format(about['__version__']))
            os.system('git push --tags')
        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=[*find_packages(exclude=["test", "demo", "old"])],
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],
    # entry_points={
    #     'console_scripts': ['mycli=mymodule:cli'],
    # },
    package_data={
        'ytools': ['tpls/*']
    },
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
    },
    script_name="setup.py",
    script_args=["upload"] if len(sys.argv) == 1 else sys.argv[1:],
    keywords=['ytools']
)

if __name__ == '__main__':
    pass
