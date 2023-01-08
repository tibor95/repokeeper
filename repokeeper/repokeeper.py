#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Repokeeper - creates and maintain local repository from AUR packages

# IMPORTING MODULES
try:
    from urllib import urlopen
    from urllib import urlretrieve
    from urllib.error import HTTPError
except:
    try:
        from urllib.request import urlopen
        from urllib.request import urlretrieve
        from urllib.error import HTTPError
    except:
        print("ERROR: You need urllib package for python2")
        print(" or urllib.request package for python3 installed")
        exit()

import json, os, tarfile, shutil, subprocess, time, glob, sys, signal, argparse
from packaging import version
from repokeeper.config_parser import get_conf_content

import getpass
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum

class FailedPackage(object):
    def __init__(self, name: str, reason:str) -> None:
        self.name = name
        self.reason = str(reason)

class PackageToBuild(object):
    def __init__(self, name: str, url: str, dependencies: List[str], build_dependencies: List[str]) -> None:
        self.name = name
        self.url = url
        self.dependencies = dependencies
        self.build_dependencies = build_dependencies

class pkg_identification(object):
    def __init__(self, file: str, file_basename: str, ver: str):
        self.file = file
        self.file_basename = file_basename
        self.version = ver
        if not self.file_basename in self.file:
            Logger().log(LogType.ERROR, console_txt="pkg_identification failed", err_code=7)
        
    def __repr__(self) -> str:
        return f"<{self.file}|{self.file_basename}|{self.version}>"

class RepoContent(object):
    
    def __init__(self, path_regexp, in_config: List[str]) -> None:
        self._content: List[pkg_identification, bool, bool] = [] #Tuple(pkg_identification, in config(bool), newest)
        for pck_file in glob.glob(path_regexp):
            pck_ident = get_pkg_identification(pck_file)
            self._content.append([pck_ident, pck_ident.file_basename in in_config])
        for item in self._content:
            item.append(item[0].version == self.get_highest_version(item[0].file_basename))
        self._content.sort(key=lambda x: f"{x[0].file_basename}___{x[0].version}")
    
    def list(self) -> List[str]:
        res = []
        for item in self._content:
            res.append(f"{item[0].file_basename:<22}  {item[0].version:<12}  {'newest ver. in repo' if item[2] else ''}")
        return res
    
    def get_highest_version(self, pck_name):
        res = None
        for item in self._content:
            if item[0].file_basename != pck_name:
                continue
            if res is None or res < item[0].version:
                res = item[0].version
        return res

    @property
    def new_versions(self) -> List[pkg_identification]:
        return [item[0] for item in self._content if item[2] is True]
    
    @property
    def old_versions(self) -> List[pkg_identification]:
        return [item[0] for item in self._content if not item[2]]

    @property
    def new_but_not_in_config(self) -> List[pkg_identification]:
        return [item[0] for item in self._content if not item[1] and item[2]]
    
    @property
    def list_pck_names(self) -> Set[str]:
        return set([item[0].file_basename for item in self._content])

class LogType(Enum):
    NORMAL = 0
    BOLD = 1
    WARNING = 2
    ERROR = 3
    CUSTOM = 4
    HIGHLIGHT = 5


def get_version():
    return "0.3.8"


def get_args():
    parser = argparse.ArgumentParser(
        description="Python tool for ArchLinux to maintain local repository of AUR packages. It updates packages listed in configuration file.")
    parser.add_argument("-v", "--version", action="store_true", default=False)
    parser.add_argument("-n", "--nodeps", action="store_true", default=False, help="Disable checking and building dependencies from AUR")
    parser.add_argument("--dryrun", action="store_true", default=False, help="Do not build nor recreate repo index")
    parser.add_argument("-l", "--list", action="store_true", default=False, help="Print content of repo and exit")


    args = parser.parse_args()

    return args.version, args.dryrun, args.nodeps, args.list


def signal_handler(signal, frame):
    Logger().log(console_txt="\nSIGINT signal received. Quitting...", err_code=0)


signal.signal(signal.SIGINT, signal_handler)


def parse_version(vers_str: str) -> version.Version:
    try:
        return version.Version(vers_str)
    except:
        raise ValueError("Failed to parse version from string: '{}'".format(vers_str))


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
        elif logtype == LogType.BOLD:
            open_col = Logger._BOLD
        else:
            open_col = ""

        if isinstance(console_txt, str):
            print(open_col + console_txt + Logger._UNCOLOR)
        if isinstance(log_txt, str):
            with open(Logger.__logfile, 'a', 1) as lf:
                lf.write(log_txt + log_eof)
        if err_code >= 0:
            sys.exit(err_code)





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

    def __init__(self, skip_dependencies: bool = False):
        # DEFINING VARIABLES
        # defaults:
        self.conffileloc = "/etc/repokeeper.conf"
        self.package_regexp = "*pkg.tar.zst"
        self.lo = Logger()
        self.lo.log(console_txt="* Parsing configuration file...")
        #self.latest_in_repo: Dict[str, pkg_identification] = {}
        self.skip_dependencies = skip_dependencies
        try:
            self.pkgs_conf, self.repodir, self.builddir, self.reponame = get_conf_content(self.conffileloc, "local-rk")
        except Exception as e:
            self.lo.log(LogType.ERROR, console_txt=str(e), log_txt=str(e), err_code=10)
        self.repo_content = None
        self.parse_repo()

    def parse_repo(self):
        self.repo_content = RepoContent(self.repodir + "/" + self.package_regexp  ,self.pkgs_conf)
        time.sleep(1)

    def print_repo_summary(self):
        # printing what is in repository with latest versions
        self.lo.log(LogType.BOLD, console_txt="* Newest versions of packages in your local repository:")
        for item in self.repo_content.new_versions:
            log_txt = f"  {item.file_basename} - {item.version}"
            self.lo.log(console_txt=log_txt)

        if len(self.repo_content.old_versions) > 0:
            self.lo.log(LogType.BOLD,
                        console_txt="* View the log file {} for a list of outdated packages [{}]".format(self.lo.logfile,
                        len(self.repo_content.old_versions)))

    def fetch_pck_info_from_aur_web(self, pck: str, silent_failure: bool = False) -> Optional[Dict]:
        url = f"https://aur.archlinux.org/rpc/?v=5&type=info&arg={pck}"
        response = urlopen(url)
        html = response.read()
        data = json.loads(html.decode('utf-8'))

        if "error" in data:
            text = ' {:<22s} !  Error: {}'.format(pck, data["error"])
            self.lo.log(LogType.NORMAL, console_txt=text, log_txt=text)
            return None

        if data['type'] == 'error' or data['resultcount'] == 0:
            #if not silent_failure:
            text = ' {:<22s} !  wrong name/not found in AUR'.format(pck)
            self.lo.log(LogType.NORMAL, console_txt=None if silent_failure else text, log_txt=text)
            return None

        if not isinstance(data['results'], list):
            data['results'] = [data['results'], ]

        if len(data['results']) > 1:
            text = pck + " more then one results for package, skipping.... "
            self.lo.log(LogType.NORMAL, console_txt=text, log_txt=text)
            return None

        return data['results'][0]

    def check_single_package(self, pck_name: str, silent_failure: bool = False) -> Optional[PackageToBuild]:
        aur_web_info = self.fetch_pck_info_from_aur_web(pck_name, silent_failure)
        if aur_web_info is None:
            return
        
        pck_to_build = PackageToBuild(pck_name, str("http://aur.archlinux.org" + aur_web_info['URLPath']),
        aur_web_info.get("Depends",[]), aur_web_info.get("MakeDepends",[]))

        aurversion = str(aur_web_info['Version'].replace("-", "."))

        if not pck_name in self.repo_content.list_pck_names:
            log_txt = ' {:<22s} + Building version {:}'.format(pck_name, aur_web_info['Version'])
            self.lo.log(console_txt=log_txt, log_txt=log_txt)
            return pck_to_build

        else:
            curversion = self.repo_content.get_highest_version(pck_name)
            try:
                curversion_obj = parse_version(curversion)
                aurversion_obj = parse_version(aurversion)
            except Exception as e:
                text = ' ERROR with {}: {}'.format(pck_name, str(e))
                return
            if aurversion_obj == curversion_obj:
                text = ' {:<22s} - {:s} In latest version, no need to update'.format(pck_name, aur_web_info['Version'])
                self.lo.log(LogType.NORMAL, console_txt=text, log_txt=text)

            elif aurversion_obj < curversion_obj:
                self.lo.log(console_txt=' {:<22s} - {:s} Local package newer({:s}), doing nothing'.format(pck_name,
                                                                                                            aur_web_info[
                                                                                                                'Version'],
                                                                                                            aurversion))
            else:
                log_txt = ' {:<22s} + updating {:s} -> {:s}'.format(pck_name, curversion,
                                                                                    aur_web_info['Version'])
                self.lo.log(console_txt=log_txt, log_txt=log_txt)
                return pck_to_build
            

    def check_aur_web(self) -> List[PackageToBuild]:
        """
        Returns list of PackageToBuild, ones that are explicitelly listed in config and dependencies
        if not disables by CLI switch
        """
        pkgs_tobuild: List[PackageToBuild] = []  # final dictionary (name:url) of packages to be updated
        self.lo.log(LogType.BOLD, console_txt="\n* Checking AUR for latest versions...")
        self.lo.log(console_txt=" ")
        dependencies: Set[str] = set()  # both normal and build ones
        time.sleep(1)

        for pck in self.pkgs_conf:
            to_build: Optional[PackageToBuild] = self.check_single_package(pck)
            if to_build:
                pkgs_tobuild.append(to_build)
                dependencies.update(set(to_build.dependencies))
                dependencies.update(set(to_build.build_dependencies))
            time.sleep(0.5)
        
        if not self.skip_dependencies and dependencies:
            log_txt = f"Querying AUR for normal and build dependencies: {', '.join(dependencies)}"
            self.lo.log(console_txt="\n "+log_txt, log_txt="\n" + log_txt)
            checked_pcks: Set[str] = set()

            while dependencies:
                dependency: str = dependencies.pop()
                if dependency in self.pkgs_conf or dependency in checked_pcks:
                    continue
                checked_pcks.add(dependency)
                to_build = self.check_single_package(dependency, True)  # Quietly ignoring if not in AUR
                if to_build:
                    pkgs_tobuild.append(to_build)
                    for dependency in to_build.dependencies + to_build.build_dependencies:
                        if dependency not in checked_pcks:
                            dependencies.add(dependency)

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

    def building(self, pkgs: List[PackageToBuild]) -> List[FailedPackage]:
        """
        Actual building the application and copying package files into repo directory
        :param pkgs: Dictionary of package_name: aur_url_of_MAKEPKG
        :return: List of failing packages, can be empty
        """

        failed_packages: List[FailedPackage] = []

        for position, pkg_to_build in enumerate(pkgs):
            text_body = pkg_to_build.name + " (" + str(position + 1) + "/" + str(
                len(pkgs)) + ") - " + time.strftime("%H:%M:%S", time.localtime())
            self.lo.log(console_txt="\n  * * BUILDING: " + text_body, log_txt="\n Building: " + text_body)

            # emptying builddir
            empty_dir(self.builddir)

            try:
                # downloading package into builddir, appending _tmp to name to avoid overwriting of anything
                localarchive = os.path.join(self.builddir, pkg_to_build.name + "_tmp")
                #print(pkg_to_build.url)
                urlretrieve(pkg_to_build.url, localarchive)

                # unpacking
                tararchive = tarfile.open(localarchive, "r:*")
                tararchive.extractall(self.builddir)

                # defining work directory
                compiledir = self.get_compiledir(pkg_to_build.name)

                result = subprocess.call("makepkg", cwd=compiledir, shell=True)
                text = " ( makepkg's return code: {} )".format(result)
                self.lo.log(log_txt=text, console_txt=text)
                if int(result) > 0:
                    fp = FailedPackage(pkg_to_build.name, f"makepkg RC: {result}")
                    failed_packages.append(fp)
                    self.lo.log(console_txt=f" ERROR: Build of {fp.name} failed with: {fp.reason}")
                    continue

            except Exception as e:
                e_txt = str(e)
                if isinstance(e, HTTPError):
                    down_error_text = f" Got HTTPError while retrieveing: {pkg_to_build.url}"
                    self.lo.log(console_txt=down_error_text, log_txt=down_error_text)
                    e_txt += f" [{pkg_to_build.url}]"
                self.lo.log(console_txt=" ERROR: Build of {} failed with: {}".format(pkg_to_build.name, str(e)))
                fp = FailedPackage(pkg_to_build.name, e_txt)
                failed_packages.append(fp)
                time.sleep(2)
                continue

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
                text = "No package files found for {}".format(pkg_to_build.name)
                self.lo.log(LogType.ERROR, console_txt=text, log_txt=text)
                failed_packages.append(FailedPackage(pkg_to_build.name, "No built archives found"))

        return failed_packages

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
        self.lo.log(LogType.BOLD, console_txt="\n\n* Updating local repo db file: {}".format(repo_file))
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

        except Exception as e:
            text = "   repodb file creation failed with {}".format(str(e))
            self.lo.log(LogType.ERROR, console_txt=text, log_txt=text, err_code=11)


def main():
    print_version, dry_run, no_dependencies, list_only = get_args()
    if print_version:
        Logger().log(console_txt = get_version(), err_code = 0)

    rp = Repo_Base(skip_dependencies=no_dependencies)

    if list_only:
        rp.lo.log(logtype=LogType.HIGHLIGHT, console_txt = "\nContent of repository:")
        for item in rp.repo_content.list():
            rp.lo.log(console_txt =f"  {item}")
        return

    if getpass.getuser() == "root":
        rp.lo.log(LogType.ERROR, console_txt="root is not allowed to run this tool", err_code=10)

    rp.lo.log(console_txt=" [REPOKEEPER v. {}]".format(get_version()))
    rp.lo.log(log_txt=f"\n\n{'# ' * 10}  starting at {time.strftime('%d %b %Y %H:%M:%S', time.localtime())}   {'# ' * 10}")

    # testing existence of repordir and builddir
    rp.folder_check()

    # checking what is in AUR and what version
    if len(rp.pkgs_conf) > 0:
        pkgs_to_built = rp.check_aur_web()  # also print out output from aur check
    else:
        pkgs_to_built = {}

    print(" ")
    if dry_run:
        text="Dry-run mode, quitting..."
        rp.lo.log(LogType.BOLD, console_txt="* "+text, log_txt=text, err_code=0)
    if len(pkgs_to_built) > 0:
        rp.lo.log(LogType.BOLD, console_txt="* Building packages...")
    else:
        rp.lo.log(LogType.BOLD, console_txt="* Nothing to build...")
        rp.lo.log(log_txt="\nNo packages to be build")

    # iterating and updating packages in pkgs_to_built list
    time.sleep(1)

    failed_packages = rp.building(pkgs_to_built)

    # updating repository
    time.sleep(1)
    rp.update_repo_file()

    # parsing local repo once more to identify outdated packages
    rp.parse_repo() # refresh the information

    #printing content of repo into log file
    rp.lo.log(console_txt = f"\nCheck log file {rp.lo.logfile} for list of all packages and versions in repo\n",
    log_txt="\nRepository packages and versions:")
    for item in rp.repo_content.list():
        rp.lo.log(console_txt = None, log_txt=f"  {item}")
    rp.lo.log(console_txt = None, log_txt=" ")


    if len(rp.repo_content.old_versions) > 0:
        rp.lo.log(log_txt="\nFollowing files/packages have newer version in the repo and might be deleted from the repo folder:")
        for item in rp.repo_content.old_versions:
            rp.lo.log(log_txt="rm {} ;".format(item.file))

    if len(rp.repo_content.new_but_not_in_config) > 0:

        rp.lo.log(log_txt="\nFollowing packages are not listed in your repokeeper.conf, but might be \
dependencies, so delete them on your own responsibility (just copy&paste it en block into a console):")
        for item in rp.repo_content.new_but_not_in_config:
            rp.lo.log(log_txt="rm {} ;".format(item.file))

    if len(failed_packages) > 0:
        text = f"Following {len(failed_packages)} packages had not been built:"
        rp.lo.log(logtype=LogType.WARNING, console_txt="* "+text, log_txt=text)
        for fp in failed_packages:
            text = f"  {fp.name:<22} {fp.reason}"
            rp.lo.log(console_txt=" "+text, log_txt=text)

    rp.lo.log(log_txt="")
    rp.lo.log(log_txt="All done at {}, quitting ".format(time.strftime("%d %b %Y %H:%M:%S", time.localtime())))


if __name__ == "__main__":
    main()
