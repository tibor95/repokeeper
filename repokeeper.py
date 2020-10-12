#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Repokeeper - creates and maintain local repository from AUR packages
# for ARCH LINUX!
# dependencies: python-simplejson,python-distribute
# contact: tiborb95 at gmail dot com

# IMPORTING MODULES
try:
    from urllib import urlopen
    from urllib import urlretrieve
except:
    try:
        from urllib.request import urlopen
        from urllib.request import urlretrieve
    except:
        print("ERROR: You need urllib package for python2")
        print(" or urllib.request package for python3 installed")
        exit()

import json, os, tarfile, shutil, subprocess, time, glob, sys, signal

try:
    from pkg_resources import parse_version
except:
    print(" ERROR Failed to import pkg_resources module. You need to have package python-distribute")
    print(" for python3 or python2-distribute for python2 installed. Quitting...")
    exit()

import getpass
from typing import List, Tuple, Optional, Dict
from enum import Enum

# DEFINING VARIABLES
# defaults:
conffileloc = "/etc/repokeeper.conf"
logfile = "/tmp/repokeeper.log"
BOLD = "\033[1m"
WARNING = "\033[91m"
HIGHLIGHT = "\033[92m"
UNCOLOR = "\033[0m"
package_regexp = "*pkg.tar.zst"
version = "0.3.0"

pkgs_conf: List[str] = []  # list of packages listed in conf file
latest_in_repo: Dict[str, "pkg_identification"]
pkgs_aurversion = {}  # dictionary (pck:version) of packages from local repo with versions from AUR
pkgs_tobuild = {}  # final dictionary (name:url) of packages to be updated


# problems with cases - discrepancie with cases in aur names and package names


class LogType(Enum):
    NORMAL = 0
    BOLD = 1
    WARNING = 2
    ERROR = 3
    CUSTOM = 4
    HIGHLIGHT = 5


# DEFINING FUNCTIONS
def signal_handler(signal, frame):
    log(console_txt="\nSIGINT signal received. Quitting...", err_code=0)

signal.signal(signal.SIGINT, signal_handler)

def log(logtype: LogType = LogType.NORMAL, console_txt: Optional[str] = None, log_txt: Optional[str] = None,
        err_code: int = -1, log_eof: str = "\n"):
    if logtype == LogType.WARNING:
        open_col = WARNING
    elif logtype == LogType.ERROR:
        open_col = WARNING + BOLD
    elif logtype == LogType.HIGHLIGHT:
        open_col = HIGHLIGHT
    else:
        open_col = ""

    if isinstance(console_txt, str):
        print(open_col + console_txt + UNCOLOR)
    if isinstance(log_txt, str):
        with open(logfile, 'w', 1) as lf:
            lf.write(log_txt + log_eof)
    if err_code >= 0:
        sys.exit(err_code)


class pkg_identification(object):
    def __init__(self, file: str, file_basename: str, ver: str):
        self.file = file
        self.file_basename = file_basename
        self.version = ver
        if not self.file_basename in self.file:
            log(LogType.ERROR, console_txt="pkg_identification failed", err_code=7)


def empty_dir(directory: str) -> None:  # recursivelly deletes content of given dir
    cmd = "rm -rf " + directory + "*"
    if subprocess.call(cmd, shell=True) > 0:
        log(LogType.WARNING, console_txt="Failed to clean up directory {}".format(directory))
        log(LogType.WARNING, console_txt="HINT: try manually: rm -rf " + directory + "*")
        log(LogType.WARNING, console_txt="Re-run when problem is resolved...")
        log(LogType.ERROR, log_txt="Failed to clean up the directory: " + directory + ", quitting...", err_code=1)


def get_version_from_basename(filename: str) -> str:
    try:
        return str(filename.split("-")[-3] + "." + filename.split("-")[-2])
    except Exception as e:
        text = "Failed to parse: {}: {}".format(filename, str(e))
        log(LogType.ERROR, log_txt=text, console_txt=text)
        raise


def get_basename_from_filename(fullname: str) -> str:
    return str(os.path.basename('-'.join(fullname.split("-")[:-3])))


def get_pkg_identification(filename: str) -> pkg_identification:
    file_basename = str(os.path.basename('-'.join(filename.split("-")[:-3])))
    ver = get_version_from_basename(filename)
    return pkg_identification(filename, file_basename, ver)


def parse_localrepo() -> Tuple[List[pkg_identification], List[pkg_identification]]:
    # testing if package listed in conf file has a package in repodir

    not_in_repo: List[pkg_identification] = []  # list of files for packages not defined in repo.conf

    # getting a list of files in repo
    files = []
    files.extend(glob.glob(repodir + "/" + package_regexp))
    files = list(set(files))  # removing duplicates

    for file in files:
        pck_id = get_pkg_identification(file)
        if not pck_id.file_basename.lower() in [item.lower() for item in pkgs_conf]:
            not_in_repo.append(pck_id)

    older_packages: List[pkg_identification] = []  # list of possible old packages
    # now testing names in conf against files in repa
    for aur_name in pkgs_conf:
        latest = None  # single latest package for aur_name
        for file in files:
            pck_id = get_pkg_identification(file)
            if not aur_name.lower() == pck_id.file_basename.lower():
                continue
            if latest is None:
                latest = pck_id
                continue
            if parse_version(latest.version) > parse_version(pck_id.version):
                older_packages.append(pck_id)
            else:
                older_packages.append(latest)
                latest = pck_id
        # now we have identified file for given aur name
        if latest is not None:
            latest_in_repo[aur_name] = latest

    # printing what is in repository with latest versions
    strcurrepo = ""
    for k, v in latest_in_repo.items():
        strcurrepo = strcurrepo + " " + latest_in_repo[k].file_basename + "-" + latest_in_repo[k].version
    log(LogType.BOLD, console_txt = "* Newest versions of packages in your local repository:")
    log(console_txt = strcurrepo)
    if len(older_packages) > 0 or len(not_in_repo) > 0:
        log(LogType.BOLD,
            console_txt = "* View the log file " + logfile + " for a list of outdated packages or packages not listed in your conf file.")
    return older_packages, not_in_repo


def printfirsttimenote():
    log(LogType.BOLD, console_txt = "  WELCOME!")
    log(console_txt = "It seems you are running the repokeeper for the first time so some setup is needed.")
    log(console_txt = "Now you have to open " + conffileloc + " and edit it (as root probably). 3 changes at least must be done:")
    log(console_txt = " 1. Edit and uncoment 'repodir' - the directory where compiled packages will be stored.")
    log(console_txt =
        " 2. Edit and uncoment 'buildir' - the directory where building will take place. (The directory will be emptied before each compilation).")
    log(console_txt = " 3. change 'firsttimemode' to 'no' - to get rid of First Time Mode you are in now.")
    log(console_txt =
        " OPTIONALLY you might add more packages into PACKAGES section. Also changing the ownership of /etc/repokeeper.conf to other user might be usefful.")
    log(console_txt = "When done, re-run the repokeeper.py.")


def parse_conffile(conffileloc: str) -> Tuple[str, str, str]:

    # searching for conf file, /etc/repokeeper.conf is preffered
    if not os.path.isfile(conffileloc):
        log(LogType.WARNING, console_txt = "FAILED to open configuration file: " + conffileloc, err_code=6)
    log(console_txt="  Using configuration file: " + conffileloc)

    with open(conffileloc, 'r') as repolistf:
        mode = "none"
        for line in repolistf:
            line = line.split('#')[0]
            if len(line) < 3:
                continue
            elif line.replace(' ', '').split('=')[0] == "firsttimemode":
                firsttimemode = line.replace(' ', '').split('=')[1].replace("\n", "")
                if firsttimemode == "yes":
                    printfirsttimenote()
                    exit(2)
                continue
            elif line.startswith("[packages]"):
                mode = "packages"
                continue
            elif line.startswith("[options]"):
                mode = "options"
                continue
            elif mode == "packages":
                pkgs_conf.append(line.split(' ')[0].replace("\n", ""))
            elif mode == "options":
                if line.replace(' ', '').split('=')[0] == "repodir":
                    repodir = line.replace(' ', '').split('=')[1].replace("\n", "")
                    if not repodir.endswith('/'):
                        repodir = repodir + '/'

                if line.replace(' ', '').split('=')[0] == "reponame":
                    reponame = line.replace(' ', '').split('=')[1].replace("\n", "")

                if line.replace(' ', '').split('=')[0] == "builddir":
                    builddir = line.replace(' ', '').split('=')[1].replace("\n", "")
                    if not builddir.endswith('/'):
                        builddir = builddir + '/'

                if line.replace(' ', '').split('=')[0] == "colors":
                    if line.replace(' ', '').split('=')[1].replace("\n", "") == "off":
                        log(console_txt="   Collors off..")
                        BOLD = ''
                        WARNING = ''
                        UNCOLOR = ''

    if len(pkgs_conf) == 0:
        log(LogType.WARNING, console_txt="  ! No packages found in config file, going on anyway...")
    else:
        log(console_txt="  Packages in your conf file: " + ' '.join(item for item in pkgs_conf))
    return builddir, repodir, reponame


def check_aur():
    log(LogType.BOLD, console_txt="* Checking AUR for latest versions...")
    log(console_txt=" ")
    time.sleep(1)
    for pck in pkgs_conf:
        response = urlopen('http://aur.archlinux.org/rpc.php?type=info&arg=' + pck)
        html = response.read()
        data = json.loads(html.decode('utf-8'))

        if data['type'] == 'error' or data['resultcount'] == 0:
            text = ' {:<18s} !  wrong name/not found in AUR'.format(pck)
            log(LogType.NORMAL, console_txt=text, log_txt=text)

            continue

        if not isinstance(data['results'], list):
            data['results'] = [data['results'], ]

        resultscount = len(data['results'])
        if resultscount > 1:
            text = pck + " more then one results for package, skipping.... "
            log(LogType.NORMAL, console_txt=text, log_txt=text)
            continue

        aurpkg = data['results'][0]
        pkgs_aurversion[pck] = str(aurpkg['Version'].replace("-", "."))

        if not pck in pkgs_repoversion:
            log(console_txt=' {:<18s} + Building version {:}'.format(pck, aurpkg['Version']))
            pkgs_tobuild[pck] = str("http://aur.archlinux.org" + aurpkg['URLPath'])
        else:
            curversion = pkgs_repoversion[pck]
            if parse_version(pkgs_aurversion[pck]) == parse_version(curversion):
                text = ' {:<18s} - {:s} In latest version, no need to update'.format(pck, aurpkg['Version'])
                log(LogType.NORMAL, console_txt=text, log_txt=text)

            elif parse_version(pkgs_aurversion[pck]) < parse_version(curversion):
                log(console_txt=' {:<18s} - {:s} Local package newer({:s}), doing nothing'.format(pck,
                                                                                                  aurpkg['Version'],
                                                                                                  pkgs_repoversion[
                                                                                                      pck]))
            else:
                log(console_txt=' {:<18s} + updating {:s} -> {:s}'.format(pck, pkgs_repoversion[pck],
                                                                          aurpkg['Version']))
                pkgs_tobuild[pck] = "http://aur.archlinux.org" + str(aurpkg['URLPath'])
        time.sleep(0.5)


def get_compiledir(lbuilddir: str, package: str) -> str:
    if os.path.isfile(lbuilddir + package + "/PKGBUILD"):
        return lbuilddir + package
    if os.path.isfile(lbuilddir + package.lower() + "/PKGBUILD"):
        return lbuilddir + package.lower()
    if os.path.isfile(lbuilddir + "/PKGBUILD"):
        return lbuilddir
    # if the PKGBUILD was not found in reasonable location:
    for root, dirs, files in os.walk(lbuilddir):
        for ldir in dirs:
            for root2, dirs2, files2 in os.walk(lbuilddir + ldir):
                for lfile in files2:
                    if lfile == "PKGBUILD":
                        return root + ldir + "/"
    return "unknown"


if __name__ == "__main__":

    if getpass.getuser() == "root":
        log(LogType.ERROR, console_txt="root is not allowed to run this tool", err_code=10)

    log(console_txt=" [REPOKEEPER v. " + version + "]")
    log(log_txt="starting at " + time.strftime("%d %b %Y %H:%M:%S", time.localtime()))

    # parsing conffile
    log(console_txt="* Parsing configuration file...")
    builddir, repodir, reponame = parse_conffile(conffileloc)
    time.sleep(1)

    # testing existence of repordir and builddir
    if repodir == "unset":
        log(LogType.WARNING, console_txt="ERROR: No REPODIR is set in " + conffileloc, err_code=3)
    if builddir == "unset":
        log(LogType.WARNING, console_txt="ERROR: No BUILDDIR is set in " + conffileloc, err_code=3)
    if not os.path.exists(repodir):
        log(LogType.WARNING, console_txt="ERROR: non-existent REPODIR: " + repodir, err_code=4)
    else:
        log(console_txt="* Repository location: " + repodir)
    if not os.path.exists(builddir):
        log(LogType.WARNING, console_txt="ERROR: non-existent REPODIR: " + builddir, err_code=4)
    else:
        log(console_txt="* Build/temp. directory: " + builddir)

    # finding what is in localrepo directory
    parse_localrepo()  # also prints out packages in localrepo
    time.sleep(1)

    # checking what is in AUR and what version
    if len(pkgs_conf) > 0:
        check_aur()  # also print out output from aur check

    # print pkgs_tobuild (list of packages to be update)
    print(" ")
    if len(pkgs_tobuild) > 0:
        log(LogType.BOLD, console_txt="* Building packages...")
    else:
        print(BOLD + "* Nothing to build..." + UNCOLOR)
        log(log_txt="\nNo packages to be build")

    # iterating and updating packages in pkgs_tobuild list
    time.sleep(1)

    for position, package in enumerate(pkgs_tobuild):
        text_body = package + " (" + str(position + 1) + "/" + str(
            len(pkgs_tobuild)) + ") - " + time.strftime("%H:%M:%S", time.localtime())
        log(console_txt="\n  * * BUILDING: " + text_body, log_txt="\n Building: " + text_body)

        # emptying builddir
        empty_dir(builddir)

        # downloading package into builddir
        localarchive = builddir + pkgs_tobuild[package].split('/')[-1]
        urlretrieve(pkgs_tobuild[package], localarchive)

        # unpacking
        tararchive = tarfile.open(localarchive, "r:gz")
        tararchive.extractall(builddir)

        # defining work directory
        compiledir = get_compiledir(builddir, package)

        try:
            result = subprocess.call("makepkg", cwd=compiledir, shell=True)
        except:
            log(console_txt=" ERROR: Build of " + package + " failed")
            time.sleep(4)

        try:
            text = " ( makepkg's return code: {} )".format(result)
            log(log_txt=text, console_txt=text)
        except:
            pass

        log(console_txt=" ")
        copied_count = 0
        for lfile in glob.glob(compiledir + "/*pkg.tar.zst"):
            log(console_txt="   Copying " + lfile + " to " + repodir)
            try:
                shutil.copy(lfile, repodir)
                log(log_txt=" Copying final package: {}".format(lfile))
                copied_count += 1
            except:
                log(console_txt=" Copying FAILED !?")
                time.sleep(4)
            log(console_txt=" ")
        if copied_count == 0:
            log(LogType.WARNING, console_txt="No final files found and copied from {}, teminating".format(compiledir),
                err_code=7)

    # updating repository
    time.sleep(1)
    repo_db_file = repodir + reponame + ".db.tar.gz"
    log(LogType.BOLD, console_txt="* Updating local repo db file: {}".format(repo_db_file))
    if os.path.isfile(repo_db_file):
        os.remove(repo_db_file)
    else:
        log(LogType.WARNING, console_txt="Warning - {} was not removed - not found".format(repo_db_file))
    # creating new one
    try:
        pr = subprocess.Popen("repo-add " + repo_db_file + " " + repodir + package_regexp, shell=True)
        rc = pr.wait()
        if rc != 0:
            log(LogType.WARNING, console_txt="ERROR: repo-add returned: {}".format(rc))
            raise
        log(console_txt="   ")
        log(LogType.BOLD, console_txt="* To use the repo you need following two lines in /etc/pacman.conf")
        log(LogType.CUSTOM,
            HIGHLIGHT + "    [" + reponame + "]" + UNCOLOR + "                          # repository will be named '" + reponame + "'")
        log(LogType.HIGHLIGHT, console_txt="    Server = file://" + repodir)
        log(console_txt=
            " Also note that all pkg packages present in repodir was put into repo db file, not only those in your config file.")
    except:
        log(LogType.ERROR, console_txt="   repodb file creation failed")

    # parsing local repo to identify outdated packages
    outdated, not_in_conf = parse_localrepo()
    if len(outdated) > 0:
        log(log_txt="\nFollowing packages has newer versions and might be deleted from your repo:")
        for item in outdated:
            log(log_txt="rm {} ;".format(item.file))

    if len(not_in_conf) > 0:
        log(log_txt="\nFollowing packages are not listed in your repokeeper.conf and might \
    be deleted from your repo (just copy&paste it en block into a console):")
        for item in not_in_conf:
            log(log_txt="rm {} ;".format(item.file))

    log(log_txt="")
    log(log_txt="All done at {}, quitting ".format(time.strftime("%d %b %Y %H:%M:%S", time.localtime())))
