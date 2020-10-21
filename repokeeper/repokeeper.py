#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Repokeeper - creates and maintain local repository from AUR packages

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

import json, os, tarfile, shutil, subprocess, time, glob, sys, signal, argparse
from packaging import version
from repokeeper.config_parser import get_conf_content

import getpass
from typing import List, Tuple, Optional, Dict
from enum import Enum


class LogType(Enum):
    NORMAL = 0
    BOLD = 1
    WARNING = 2
    ERROR = 3
    CUSTOM = 4
    HIGHLIGHT = 5


def get_version():
    return "0.3.2"


def get_args():
    parser = argparse.ArgumentParser(
        description="Python tool for ArchLinux to maintain local repository of AUR packages. Updates packages listed in configuration file")
    parser.add_argument("-v", "--version", action="store_true", default=False)

    args = parser.parse_args()

    return args.version


def signal_handler(signal, frame):
    Logger().log(console_txt="\nSIGINT signal received. Quitting...", err_code=0)


signal.signal(signal.SIGINT, signal_handler)


def parse_version(vers_str: str) -> version.Version:
    try:
        return version.Version(vers_str)
    except:
        raise ValueError("Failed to parse version from: {}".format(vers_str))


class Logger(object):
    # Could be singleton once
    _BOLD = "\033[1m"
    _WARNING = "\033[91m"
    _HIGHLIGHT = "\033[92m"
    _UNCOLOR = "\033[0m"
    __logfile = "/tmp/repokeeper.log"

    @property
    def logfile(self):
        return Logger.__logfile

    def log(self, logtype: LogType = LogType.NORMAL, console_txt: Optional[str] = None, log_txt: Optional[str] = None,
            err_code: int = -1, log_eof: str = "\n"):

        if logtype == LogType.WARNING:
            open_col = self._WARNING
        elif logtype == LogType.ERROR:
            open_col = Logger._WARNING + Logger._BOLD
        elif logtype == LogType.HIGHLIGHT:
            open_col = Logger._HIGHLIGHT
        else:
            open_col = ""

        if isinstance(console_txt, str):
            print(open_col + console_txt + Logger._UNCOLOR)
        if isinstance(log_txt, str):
            with open(Logger.__logfile, 'a', 1) as lf:
                lf.write(log_txt + log_eof)
        if err_code >= 0:
            sys.exit(err_code)


class pkg_identification(object):
    def __init__(self, file: str, file_basename: str, ver: str):
        self.file = file
        self.file_basename = file_basename
        self.version = ver
        if not self.file_basename in self.file:
            Logger().log(LogType.ERROR, console_txt="pkg_identification failed", err_code=7)


def empty_dir(directory: str) -> None:  # recursivelly deletes content of given dir
    lo = Logger()
    cmd = "rm -rf " + directory + "/*"
    if subprocess.call(cmd, shell=True) > 0:
        lo.log(LogType.WARNING, console_txt="Failed to clean up directory {}".format(directory))
        lo.log(LogType.WARNING, console_txt="HINT: try manually: rm -rf " + directory + "*")
        lo.log(LogType.WARNING, console_txt="Re-run when problem is resolved...")
        lo.log(LogType.ERROR, log_txt="Failed to clean up the directory: " + directory + ", quitting...", err_code=1)


def get_version_from_basename(filename: str) -> str:
    try:
        return str(filename.split("-")[-3] + "." + filename.split("-")[-2])
    except Exception as e:
        text = "Failed to parse: {}: {}".format(filename, str(e))
        Logger().log(LogType.ERROR, log_txt=text, console_txt=text)
        raise


def get_basename_from_filename(fullname: str) -> str:
    return str(os.path.basename('-'.join(fullname.split("-")[:-3])))


def get_pkg_identification(filename: str) -> pkg_identification:
    file_basename = str(os.path.basename('-'.join(filename.split("-")[:-3])))
    ver = get_version_from_basename(filename)
    return pkg_identification(filename, file_basename, ver)


class Repo_Base(object):

    def __init__(self):
        # DEFINING VARIABLES
        # defaults:
        self.conffileloc = "/etc/repokeeper.conf"
        self.package_regexp = "*pkg.tar.zst"
        self.lo = Logger()
        self.lo.log(console_txt="* Parsing configuration file...")
        self.latest_in_repo: Dict[str, pkg_identification] = {}
        self.pkgs_conf, self.repodir, self.builddir, self.reponame = get_conf_content(self.conffileloc, "local-rk")
        time.sleep(1)

    def list_files_in_repo(self) -> List[str]:
        files = []
        files.extend(glob.glob(self.repodir + "/" + self.package_regexp))
        return list(set(files))  # removing duplicates

    def parse_localrepo(self, print_summary = True) -> Tuple[
        List[pkg_identification], List[pkg_identification], Dict[str, "pkg_identification"]]:  # elaborate this

        files = self.list_files_in_repo()

        in_repo_not_required: List[pkg_identification] = []  # list of files for packages not defined in repo.conf
        for file in files:
            pck_id = get_pkg_identification(file)
            if not pck_id.file_basename.lower() in [item.lower() for item in self.pkgs_conf]:
                in_repo_not_required.append(pck_id)

        required_but_with_newer_version: List[pkg_identification] = []  # list of possible old packages
        newest_required_in_repo: Dict[str, "pkg_identification"] = {}
        # now testing names in conf against files in repa
        for app_name in self.pkgs_conf:
            latest = None  # single latest package for aur_name (application)
            for file in files:
                pck_id = get_pkg_identification(file)
                if not app_name.lower() == pck_id.file_basename.lower():
                    continue
                if latest is None:
                    latest = pck_id
                    continue
                if parse_version(latest.version) > parse_version(pck_id.version):
                    required_but_with_newer_version.append(pck_id)
                else:
                    required_but_with_newer_version.append(latest)
                    latest = pck_id
            # now we have identified file for given aur name
            if latest is not None:
                newest_required_in_repo[app_name] = latest
        if print_summary:
            self.print_repo_summary(required_but_with_newer_version, in_repo_not_required, newest_required_in_repo)

        return required_but_with_newer_version, in_repo_not_required, newest_required_in_repo

    def print_repo_summary(self, required_but_with_newer_version: List[pkg_identification],
                           in_repo_not_required: List[pkg_identification],
                           newest_required_in_repo: Dict[str, "pkg_identification"]):
        # printing what is in repository with latest versions
        strcurrepo = ""
        for k, v in newest_required_in_repo.items():
            strcurrepo = strcurrepo + " " + newest_required_in_repo[k].file_basename + "-" + newest_required_in_repo[
                k].version
        self.lo.log(LogType.BOLD, console_txt="* Newest versions of packages in your local repository:")
        self.lo.log(console_txt=strcurrepo)
        if len(required_but_with_newer_version) > 0 or len(in_repo_not_required) > 0:
            self.lo.log(LogType.BOLD,
                        console_txt="* View the log file {} for a list of outdated packages [{}] or packages not listed in your conf file [{}].".format(self.lo.logfile,
                        len(required_but_with_newer_version),
                        len(in_repo_not_required)))

    def fetch_pck_info_from_aur_web(self, pck: str) -> Optional[Dict]:
        response = urlopen('http://aur.archlinux.org/rpc.php?type=info&arg=' + pck)
        html = response.read()
        data = json.loads(html.decode('utf-8'))

        if data['type'] == 'error' or data['resultcount'] == 0:
            text = ' {:<22s} !  wrong name/not found in AUR'.format(pck)
            self.lo.log(LogType.NORMAL, console_txt=text, log_txt=text)

            return None

        if not isinstance(data['results'], list):
            data['results'] = [data['results'], ]

        if len(data['results']) > 1:
            text = pck + " more then one results for package, skipping.... "
            self.lo.log(LogType.NORMAL, console_txt=text, log_txt=text)
            return None

        return data['results'][0]

    def check_aur_web(self) -> Dict[str, str]:
        pkgs_tobuild: Dict[str, str] = {}  # final dictionary (name:url) of packages to be updated
        self.lo.log(LogType.BOLD, console_txt="* Checking AUR for latest versions...")
        self.lo.log(console_txt=" ")
        time.sleep(1)

        for pck in self.pkgs_conf:
            aur_web_info = self.fetch_pck_info_from_aur_web(pck)
            if aur_web_info is None:
                continue

            aurversion = str(aur_web_info['Version'].replace("-", "."))

            if not pck in self.latest_in_repo:
                self.lo.log(console_txt=' {:<22s} + Building version {:}'.format(pck, aur_web_info['Version']))
                pkgs_tobuild[pck] = str("http://aur.archlinux.org" + aur_web_info['URLPath'])
            else:
                curversion = self.latest_in_repo[pck].version
                if parse_version(aurversion) == parse_version(curversion):
                    text = ' {:<22s} - {:s} In latest version, no need to update'.format(pck, aur_web_info['Version'])
                    self.lo.log(LogType.NORMAL, console_txt=text, log_txt=text)

                elif parse_version(aurversion) < parse_version(curversion):
                    self.lo.log(console_txt=' {:<22s} - {:s} Local package newer({:s}), doing nothing'.format(pck,
                                                                                                              aur_web_info[
                                                                                                                  'Version'],
                                                                                                              aurversion))
                else:
                    self.lo.log(console_txt=' {:<22s} + updating {:s} -> {:s}'.format(pck, curversion,
                                                                                      aur_web_info['Version']))
                    pkgs_tobuild[pck] = "http://aur.archlinux.org" + str(aur_web_info['URLPath'])
            time.sleep(0.5)
        return pkgs_tobuild

    def get_compiledir(self, package: str) -> str:
        # Looking for PKGBUILD
        for root, dirs, files in os.walk(self.builddir):
            for ldir in dirs:
                for root2, dirs2, files2 in os.walk(os.path.join(self.builddir, ldir)):
                    for lfile in files2:
                        if lfile == "PKGBUILD":
                            return os.path.join(root, ldir)
        raise ValueError("No PKGBUILD within {} folder".format(self.builddir))

    def building(self, pkgs: Dict[str, str]) -> None:
        # receving dictionary of package name : aur url
        for position, (package, url) in enumerate(pkgs.items()):
            text_body = package + " (" + str(position + 1) + "/" + str(
                len(pkgs)) + ") - " + time.strftime("%H:%M:%S", time.localtime())
            self.lo.log(console_txt="\n  * * BUILDING: " + text_body, log_txt="\n Building: " + text_body)

            # emptying builddir
            empty_dir(self.builddir)


            # downloading package into builddir, appending _tmp to name to avoid overwriting of anything
            localarchive = os.path.join(self.builddir, package + "_tmp")
            urlretrieve(url, localarchive)

            # unpacking
            tararchive = tarfile.open(localarchive, "r:*")
            tararchive.extractall(self.builddir)

            # defining work directory
            compiledir = self.get_compiledir(package)

            try:
                result = subprocess.call("makepkg", cwd=compiledir, shell=True)
                text = " ( makepkg's return code: {} )".format(result)
                self.lo.log(log_txt=text, console_txt=text)
                if int(result) > 0:
                    text = "skipping next steps for the {}".format(package)
                    self.lo.log(logtype=LogType.ERROR, log_txt=text, console_txt=text)
                    continue

            except Exception as e:
                self.lo.log(console_txt=" ERROR: Build of {} failed with: {}".format(package, str(e)))
                time.sleep(4)

            self.lo.log(console_txt=" ")
            copied_count = 0
            for lfile in glob.glob(compiledir + "/*pkg.tar.zst"):
                self.lo.log(console_txt="   Copying " + lfile + " to " + self.repodir)
                try:
                    shutil.copy(lfile, self.repodir)
                    self.lo.log(log_txt=" Copying final package: {}".format(lfile))
                    copied_count += 1
                except:
                    self.lo.log(console_txt=" Copying FAILED !?")
                    time.sleep(4)
                self.lo.log(console_txt=" ")
            if copied_count == 0:
                self.lo.log(LogType.WARNING,
                            console_txt="No final files found and copied from {}, teminating".format(compiledir),
                            err_code=7)

    def folder_check(self) -> None:
        if self.repodir == "unset":
            self.lo.log(LogType.WARNING, console_txt="ERROR: No REPODIR is set in " + self.conffileloc, err_code=3)
        if self.builddir == "unset":
            self.lo.log(LogType.WARNING, console_txt="ERROR: No BUILDDIR is set in " + self.conffileloc, err_code=3)
        if not os.path.exists(self.repodir):
            self.lo.log(LogType.WARNING, console_txt="ERROR: non-existent REPODIR: " + self.repodir, err_code=4)
        else:
            self.lo.log(console_txt="* Repository location: " + self.repodir)
        if not os.path.exists(self.builddir):
            self.lo.log(LogType.WARNING, console_txt="ERROR: non-existent REPODIR: " + self.builddir, err_code=4)
        else:
            self.lo.log(console_txt="* Build/temp. directory: " + self.builddir)

    def update_repo_file(self) -> None:
        repo_file = os.path.join(self.repodir, self.reponame + ".db.tar.gz")
        self.lo.log(LogType.BOLD, console_txt="* Updating local repo db file: {}".format(repo_file))
        if os.path.isfile(repo_file):
            os.remove(repo_file)
        else:
            self.lo.log(LogType.WARNING, console_txt="Warning - {} was not removed - not found".format(repo_file))
        # creating new one
        try:
            pr = subprocess.Popen("repo-add " + repo_file + " " + os.path.join(self.repodir, self.package_regexp),
                                  shell=True)
            rc = pr.wait()
            if rc != 0:
                self.lo.log(LogType.WARNING, console_txt="ERROR: repo-add returned: {}".format(rc))
                raise ValueError("Building failed with RC: {}".format(rc))
            self.lo.log(console_txt="   ")
            self.lo.log(LogType.BOLD, console_txt="* To use the repo you need following two lines in /etc/pacman.conf")
            self.lo.log(LogType.CUSTOM,
                        Logger._HIGHLIGHT + "    [" + self.reponame + "]" + Logger._UNCOLOR + "                          # repository will be named '" + self.reponame + "'")
            self.lo.log(LogType.HIGHLIGHT, console_txt="    Server = file://" + self.repodir)
            self.lo.log(console_txt=
                        "* Note that all packages/files present in repository folder [{}] was put into repo db file, not only those in your config file.".format(
                            self.repodir))
        except Exception as e:
            text = "   repodb file creation failed with {}".format(str(e))
            self.lo.log(LogType.ERROR, console_txt=text, log_txt=text, err_code=11)


def main():
    print_version = get_args()
    if print_version:
        Logger().log(console_txt = get_version(), err_code = 0)

    rp = Repo_Base()

    if getpass.getuser() == "root":
        rp.lo.log(LogType.ERROR, console_txt="root is not allowed to run this tool", err_code=10)

    rp.lo.log(console_txt=" [REPOKEEPER v. {}]".format(get_version()))
    rp.lo.log(log_txt="starting at " + time.strftime("%d %b %Y %H:%M:%S", time.localtime()))

    # testing existence of repordir and builddir
    rp.folder_check()

    # finding what is in localrepo directory
    rp.older_packages, rp.not_in_repo, rp.latest_in_repo = rp.parse_localrepo(print_summary=False)  # also prints out packages in localrepo
    time.sleep(1)

    # checking what is in AUR and what version
    if len(rp.pkgs_conf) > 0:
        # print(latest_in_repo)
        pkgs_to_built = rp.check_aur_web()  # also print out output from aur check
    else:
        pkgs_to_built = {}

    print(" ")
    if len(pkgs_to_built) > 0:
        rp.lo.log(LogType.BOLD, console_txt="* Building packages...")
    else:
        rp.lo.log(LogType.BOLD, console_txt="* Nothing to build...")
        rp.lo.log(log_txt="\nNo packages to be build")

    # iterating and updating packages in pkgs_to_built list
    time.sleep(1)

    rp.building(pkgs_to_built)

    # updating repository
    time.sleep(1)
    rp.update_repo_file()

    # parsing local repo to identify outdated packages
    older_packages, packages_not_required, rp.latest_in_repo = rp.parse_localrepo()
    if len(older_packages) > 0:
        #rp.lo.log(console_txt="* There are {} old files (packages) in your local repo folder, see the log file".format(len(older_packages)))
        rp.lo.log(log_txt="\nFollowing files/packages have newer version in the repo and might be deleted from the repo folder:")
        for item in older_packages:
            rp.lo.log(log_txt="rm {} ;".format(item.file))

    if len(packages_not_required) > 0:

        rp.lo.log(log_txt="\nFollowing packages are not listed in your repokeeper.conf and might \
    be deleted from your repo (just copy&paste it en block into a console):")
        for item in packages_not_required:
            rp.lo.log(log_txt="rm {} ;".format(item.file))

    rp.lo.log(log_txt="")
    rp.lo.log(log_txt="All done at {}, quitting ".format(time.strftime("%d %b %Y %H:%M:%S", time.localtime())))


if __name__ == "__main__":
    main()
