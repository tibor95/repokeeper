from setuptools import find_packages, setup
from repokeeper.repokeeper import get_version


setup(
    name='repokeeper',
    version=get_version(),
    description='repokeeper is python helper to keep local repository of built AUR packages',
    keywords='repohelper python3 archlinux aur pacman',
    url='https://github.com/tibor95/repokeeper',
    author='Tibor Bamhor',
    author_email='tiborb95@gmail.com',
    license='GPLv3',
    packages=find_packages(),
    python_requires='>=3.4',
    install_requires=[
        'config_parser',
        'signal',
        'packaging',
        'argsparse'
    ],
    entry_points={
        'console_scripts': [
            'repokeeper = repokeeper.repokeeper:main'
        ]
    },
    long_description="""\
Repokeeper helps you to keep (update) local repository of AUR packages. It parses your config file for intended packages,
then queries AUR web page to find out actual version, compare it with versions in your repository and builds
new packages if needed. Your local repository should be configured in pacman.conf so that pacman can treat the repo
the same as other regular on-line ones.
""",
    long_description_content_type='text/x-rst',
    data_files=[
        ('share/doc/repokeeper', ['README.md']),
        ('share/man/uk/man1/', ['repokeeper.1'])
    ],
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: System'
    ]
)

