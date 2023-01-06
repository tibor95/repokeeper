REPOKEEPER.py

is tool that helps you to maintain own local database of packages buid from aur

For Arch Linux only !!!

HOMEPAGE:

https://github.com/tibor95/repokeeper

WIKI:

https://github.com/tibor95/repokeeper/wiki

BASIC SETUP:

You need to edit /etc/repokeeper.conf. Especially you will need two directories -
one as building / working directory another one as permanent storage of generated
packages.

Anyway, if you run repokeeper.py without any preparation no harm will be done...

HOW IT WORKS:

1. It reads config file to find out what packages you want to have in your repo
2. It checks actual versions of those packages in your repo
3. It sends query to AUR website to find out what are latest version of those
packages
4. If AUR contains newer version, it builds the packages and put the into repo dir
5. Unless disabled by CLI switch it checks and builds direct dependencies including
make dependencies if they are found in AUR (since 0.3.8)
6. Regenerates repo db file. Note, it puts there all pkgs located in repo dir,
even those that are not in your config file. Repokeeper doesnt delete any
packages from repo directory, you have to do it by hand. Afterwards you
can re-run repokeeper to rebuild repo db file, to get rid of entries for deleted
packages.

ADDING REPOSITORY INTO /etc/pacman.conf:

at the end of repokeeper.py output, you will see two lines that have to be
added to/present in pacman.conf. Afterwards ussual command "pacman -Sy" will
fetch data also from your local repository.
Repository name is now customizable via /etc/repokeeper.conf. The repository
name in /etr/pacman.conf must be the same, of course.
The default is local-rk, in this case no entry in /etc/repokeeper.conf
is needed.

LOG file:

/tmp/repokeeper.log


Feedback welcomed


January 06, 2022


