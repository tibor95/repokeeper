import os

from setuptools import find_packages, setup

from repokeeper import get_version


setup(
    name='repokeeper',
    version=get_version(),
    description='repokeeper is python helper to keep local repository based on AUR packages',
    keywords='repokeeper python3 archlinux aur',
    url='https://github.com/tibor95/repokeeper',
    author='Tibor Bamhor',
    author_email='tiborb95@gmail.com',
    license='GPLv3',
    packages=find_packages(),
    #test_suite='',
    python_requires='>=3.4',
    install_requires=[
        'config_parser',
        'signal'
    ],
    entry_points={
        'console_scripts': [
            'repokeeper = repokeeper.__main__:main'
        ]
    },
    long_description="""\
Repokeeper is a python script that parses your config file for intended packages, then
compares AUR db with you local repository and builds new packages if needed.
Built packages are available to pacman as onw local repository. Pacman has to be configured for it
""",
    long_description_content_type='text/x-rst',
    data_files=[
        # By filtering on `os.path.exists`, install should succeed even when
        #   the compressed manual page is not available (iterable would be empty).
        ('share/man/man1', filter(os.path.exists, ['dist/archey.1.gz'])),
        ('share/doc/repokeeper', ['README.md'])
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
        'Topic :: System'
    ]
)

