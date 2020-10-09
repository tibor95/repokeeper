#!/usr/bin/env python
# -*- coding: utf-8 -*-
#Repokeeper - creates and maintain local repository from AUR packages
#for ARCH LINUX!
#dependencies: python-simplejson,python-distribute
#contact: tiborb95 at gmail dot com

#IMPORTING MODULES
try:
	from urllib import urlopen
	from urllib import urlretrieve
except:
	try:
		from urllib.request import urlopen
		from urllib.request import urlretrieve
	except:
		print ("ERROR: You need urllib package for python2")
		print (" or urllib.request package for python3 installed")
		exit()

import json,os,tarfile,shutil,subprocess,time,glob,sys,signal

try:
	from pkg_resources import parse_version
except:
	print (" ERROR Failed to import pkg_resources module. You need to have package python-distribute")
	print (" for python3 or python2-distribute for python2 installed. Quitting...")
	exit()

import getpass
if getpass.getuser() == "root":
    print ("root is not allowed to run this tool")
    sys.exit()


#DEFINING VARIABLES
# defaults:
repodir="unset"
builddir="unset"
conffileloc="/etc/repokeeper.conf"
reponame="local-rk"

logfile="/tmp/repokeeper.log"
BOLD = "\033[1m"
WARNING = "\033[91m"
HIGHLGHT = "\033[92m"
UNCOLOR = "\033[0m"

package_regexp = "*pkg.tar.zst"

version="0.2.1"

pkgs_conf=[]   # list of packages listed in conf file
pkgs_repofilename={}   # dictionary (conf filename:package name)
pkgs_repoversion={}    # dictionary (pck:version) of packages in repo directory
pkgs_aurversion={}    # dictionary (pck:version) of packages from local repo with versions from AUR
pkgs_tobuild={}   # final dictionary (name:url) of packages to be updated

# problems with cases - discrepancie with cases in aur names and package names



#DEFINING FUNCTIONS
def signal_handler(signal, frame):
	#stdout.flush()
	print ("\nSIGINT signal received. Quitting...")
	#stdout.flush()
	exit(0)

signal.signal(signal.SIGINT, signal_handler)



def empty_dir(directory):   #recursivelly deletes content of given dir
	cmd="rm -rf "+directory+"*"
	#print ("command to be run: ",cmd)
	result=subprocess.call(cmd,shell=True)
	if result>0:
		print (WARNING+"Failed to clean up directory "+directory)
		print ("HINT: try manually: rm -rf "+directory+"*")
		print ("Re-run when problem is resolved..."+UNCOLOR)
		lf.write("Failed to clean up the directory: "+directory+", quitting...\n")
		exit (1)


def parse_localrepo():
	# testing if package listed in conf file has a package in repodir

	not_in_repo=[] # list of files not defined in repo.conf

	#getting a list of files in repo
	files=[]
	files.extend(glob.glob(repodir+"/"+package_regexp))
	files = list(set(files)) #removing duplicates

	#print (files)

	for file in files:
		file_basename=str(os.path.basename('-'.join(file.split("-")[:-3])))
		version=str(file.split("-")[-3]+"."+file.split("-")[-2])
		if not file_basename.lower() in [item.lower() for item in pkgs_conf]:
			not_in_repo.append(file)

	#print (not_in_repo)

	older=[]  #list of possible old packages
	#now testing names in conf against files in repa
	for aur_name in pkgs_conf:
		latest=[] #single latest package for aur_name
		for file in files:
			file_basename=str(os.path.basename('-'.join(file.split("-")[:-3])))
			version=str(file.split("-")[-3]+"."+file.split("-")[-2])
			if not 	aur_name.lower() == file_basename.lower():
				continue
			if len(latest)==0:
				latest=[file,file_basename,version]
				continue
			if parse_version(latest[2])> parse_version(version):
				older.append(file)
			else:
				older.append(latest[0])
				latest=[file,file_basename,version]
		#now we have identified file for given aur name
		if len(latest)>0	:
			pkgs_repofilename[aur_name]=latest[1]
			pkgs_repoversion[aur_name]=latest[2]
			#print (pkgs_repofilename[aur_name],pkgs_repoversion[aur_name])


	#printing what is in repository with latest versions
	strcurrepo=""
	for k,v in pkgs_repofilename.items():
		strcurrepo=strcurrepo+" "+pkgs_repofilename[k]+"-"+pkgs_repoversion[k]
	print (BOLD+"* Newest versions of packages in your local repository:"+UNCOLOR+strcurrepo)
	if len(older)>0 or len(not_in_repo) >0:
		print (BOLD+"* View the log file "+logfile+" for a list of outdated packages or packages not listed in your conf file."+UNCOLOR)
	return older,not_in_repo

def printfirsttimenote():
	print (BOLD+"  WELCOME!")
	print ("It seems you are running the repokeeper for the first time so some setup is needed.")
	print ("Now you have to open "+conffileloc+" and edit it (as root probably). 3 changes at least must be done:")
	print (" 1. Edit and uncoment 'repodir' - the directory where compiled packages will be stored.")
	print (" 2. Edit and uncoment 'buildir' - the directory where building will take place. (The directory will be emptied before each compilation).")
	print (" 3. change 'firsttimemode' to 'no' - to get rid of First Time Mode you are in now.")
	print (" OPTIONALLY you might add more packages into PACKAGES section. Also changing the ownership of /etc/repokeeper.conf to other user might be usefful." )
	print ("When done, re-run the repokeeper.py."+UNCOLOR)

def parse_conffile():
	global builddir,repodir,reponame,BOLD,WARNING,UNCOLOR
	#searching for conf file, /etc/repokeeper.conf is preffered
	if not os.path.isfile(conffileloc):
		print (WARNING+"FAILED to open configuration file: "+conffileloc+UNCOLOR)
		exit (6)
	print ("  Using configuration file: "+conffileloc)

	repolistf = open(conffileloc, 'r')
	mode="none"
	for line in repolistf:
		line=line.split('#')[0]
		if len(line)< 3:
			continue
		elif line.replace(' ','').split('=')[0]=="firsttimemode":
			firsttimemode=line.replace(' ','').split('=')[1].replace("\n", "")
			if firsttimemode=="yes":
				printfirsttimenote()
				exit(2)
			continue
		elif line.startswith("[packages]"):
			mode="packages"
			continue
		elif line.startswith("[options]"):
			mode="options"
			continue
		elif mode=="packages":
			pkgs_conf.append(line.split(' ')[0].replace("\n", ""))
		elif mode=="options":
			if line.replace(' ','').split('=')[0]=="repodir":
				repodir=line.replace(' ','').split('=')[1].replace("\n", "")
				if not repodir.endswith('/'):
					repodir=repodir+'/'

			if line.replace(' ','').split('=')[0]=="reponame":
				reponame=line.replace(' ','').split('=')[1].replace("\n", "")

			if line.replace(' ','').split('=')[0]=="builddir":
				builddir=line.replace(' ','').split('=')[1].replace("\n", "")
				if not builddir.endswith('/'):
					builddir=builddir+'/'

			if line.replace(' ','').split('=')[0]=="colors":
				if line.replace(' ','').split('=')[1].replace("\n", "") == "off":
					print ("   Collors off..")
					BOLD=''
					WARNING=''
					UNCOLOR=''

	#if not firsttimemode=="no"
		#print (WARNING+"It seems that your configuration file "+conffileloc+" is not fully compatible with repokeeper v 1.2 and latter")
		#print ("Following settings are required now:")
		#print (" - REPODIR and BUILDDIR must be set.")
		#print (" - line 'firsttimemode=yes|NO' must be present. Please fix and re-run"+UNCOLOR)
		#exit(5)

	if len(pkgs_conf) == 0:
		print ("  ! No packages found in config file, going on anyway...")
	else:
		print ("  Packages in your conf file: "+' '.join(item for item in pkgs_conf))

def check_aur():
	print (BOLD+"* Checking AUR for latest versions..."+UNCOLOR)
	print (" ")
	time.sleep(1)
	for pck in pkgs_conf:

		#print (" DEBUG - querrying aur for "+pck)
		response = urlopen('http://aur.archlinux.org/rpc.php?type=info&arg='+pck)
		html = response.read()
		data=json.loads(html.decode('utf-8'))
		#print (" DEBUG - data from aur: "+str(data))

		if data['type'] == 'error' or data['resultcount'] == 0:
			#print 'Error: %s' % data['results']
			text=' {:<18s} !  wrong name/not found in AUR'.format(pck)
			print (text)

			lf.write(text+ "\n")

			continue

		if not isinstance(data['results'], list):
			data['results'] = [data['results'],]

		resultscount=len (data['results'])
		if resultscount >1:
			text=pck+" more then one results for package, skipping.... "
			print (text)

			lf.write(text+ "\n")

			#print (pck+" more then one results for package, skipping.... ")
			continue

		aurpkg=data['results'][0]
		pkgs_aurversion[pck]=str(aurpkg['Version'].replace("-","."))

		if not pck in pkgs_repoversion:
			print (' {:<18s} + Building version {:}'.format(pck,aurpkg['Version']))
			pkgs_tobuild[pck]=str("http://aur.archlinux.org"+aurpkg['URLPath'])
		else:
			curversion=pkgs_repoversion[pck]
			if parse_version(pkgs_aurversion[pck]) == parse_version(curversion):
				text=' {:<18s} - {:s} In latest version, no need to update'.format(pck,aurpkg['Version'])
				print (text)

				lf.write(text+ "\n")

				#print (' {:<18s} - {:s} In latest version, no need to update'.format(pck,aurpkg['Version']))
			elif parse_version(pkgs_aurversion[pck]) < parse_version(curversion):
				print (' {:<18s} - {:s} Local package newer({:s}), doing nothing'.format(pck,aurpkg['Version'],pkgs_repoversion[pck]))
			else:
				print (' {:<18s} + updating {:s} -> {:s}'.format(pck,pkgs_repoversion[pck],aurpkg['Version']))
				pkgs_tobuild[pck]="http://aur.archlinux.org"+str(aurpkg['URLPath'])
		time.sleep(0.5)


def get_compiledir(lbuilddir,package):
	#print (" DEBUG: testing: "+lbuilddir+package+"/PKGBUILD")
	if os.path.isfile(lbuilddir+package+"/PKGBUILD"):
		return lbuilddir+package
	#print (" DEBUG: testing: "+package.lower()+"/PKGBUILD")
	if os.path.isfile(lbuilddir+package.lower()+"/PKGBUILD"):
		return lbuilddir+package.lower()
	#print (" DEBUG: testing: "+	lbuilddir+"/PKGBUILD")
	if os.path.isfile(lbuilddir+"/PKGBUILD"):
		return lbuilddir
	# if the PKGBUILD was not found in reasonable location:
	for root, dirs, files in os.walk(lbuilddir):
		for ldir in dirs:
			for root2, dirs2, files2 in os.walk(lbuilddir+ldir):
				for lfile in files2:
					if lfile == "PKGBUILD":
						#print (" DEBUG: testing: "+	root+ldir)
						return root+ldir+"/"
	return "unknown"

# # # # # # # # # # # # # # # # # # # # # # # #

print (" [REPOKEEPER v. "+version+"]")
try:
    lf = open(logfile, 'w', 1)
except Exception as e:
    print("ERROR: failed to open {}: {}".format(logfile, str(e)))
    sys.exit()
lf.write("starting at " + time.strftime("%d %b %Y %H:%M:%S", time.localtime()) + "\n")

#time.sleep(10)

#parsing conffile
print ("* Parsing configuration file...")
parse_conffile()
time.sleep(1)

# testing existence of repordir and builddir
if repodir=="unset":
	print (WARNING+"ERROR: No REPODIR is set in "+conffileloc+UNCOLOR)
	exit(3)
if builddir=="unset":
	print (WARNING+"ERROR: No BUILDDIR is set in "+conffileloc+UNCOLOR)
	exit(3)
if not os.path.exists(repodir):
	print (WARNING+"ERROR: non-existent REPODIR: "+repodir+UNCOLOR)
	exit(4)
else:
	print ("* Repository location: "+repodir)
if not os.path.exists(builddir):
	print (WARNING+"ERROR: non-existent REPODIR: "+builddir+UNCOLOR)
	exit(4)
else:
	print ("* Build/temp. directory: "+builddir)


#finding what is in localrepo directory
parse_localrepo()   #also prints out packages in localrepo
time.sleep(1)

#checking what is in AUR and what version
if len(pkgs_conf)>0:
	check_aur()  #also print out output from aur check


#print pkgs_tobuild (list of packages to be update)
print (" ")
if len(pkgs_tobuild)>0 :
	print (BOLD+"* Building packages..."+UNCOLOR)
else:
	print (BOLD+"* Nothing to build..."+UNCOLOR)
	lf.write("\nNo packages to be build\n")




#iterating and updating packages in pkgs_tobuild list
time.sleep(1)

for position,package in enumerate(pkgs_tobuild):
	print ("\n  * * BUILDING: "+package+" ("+str(position+1)+"/"+str(len(pkgs_tobuild))+") - "+time.strftime("%H:%M:%S", time.localtime()))


	lf.write("\nBuilding: "+package+" ("+str(position+1)+"/"+str(len(pkgs_tobuild))+")- "+time.strftime("%H:%M:%S", time.localtime())+"\n")

	#emptying builddir
	empty_dir(builddir)

	#downloading package into builddir
	localarchive=builddir+pkgs_tobuild[package].split('/')[-1]
	urlretrieve(pkgs_tobuild[package],localarchive )

	#unpacking
	tararchive = tarfile.open(localarchive, "r:gz")
	tararchive.extractall(builddir)

	#defining work directory
	compiledir=get_compiledir(builddir,package)


	try:
		result=subprocess.call("makepkg",cwd=compiledir,shell=True)
	except:
		print (" ERROR: Build of "+package+" failed")
		time.sleep(4)

	try:
		print (" ( makepkg's return code: "+str(result)+")")
		lf.write(" makepkg's return code: "+str(result)+"\n")
	except:
		pass


	print (" ")
	copied_count = 0
	for lfile in glob.glob(compiledir+"/*pkg.tar.zst"):
		print ("   Copying "+lfile+" to "+repodir)
		try:
			shutil.copy(lfile, repodir)
			lf.write(" Copying final package: "+lfile+"\n")
			copied_count += 1
		except:
			print (" Copying FAILED !?")
			time.sleep(4)
		print (" ")
	if copied_count == 0:
		print(WARNING+BOLD+"No final files found and copied from {}, teminating".format(compiledir)+UNCOLOR)
		sys.exit()

#updating repository
time.sleep(1)
repo_db_file = repodir+reponame+".db.tar.gz"
print (BOLD+"* Updating local repo db file: {}".format(repo_db_file)+UNCOLOR)
if os.path.isfile(repo_db_file):
	os.remove(repo_db_file)
else:
    print (WARNING + "Warning - {} was not removed - not found".format(repo_db_file) + UNCOLOR)
#creating new one
try:
    pr = subprocess.Popen("repo-add "+repo_db_file+" "+repodir+package_regexp,shell=True)
    rc = pr.wait()
    if rc != 0:
        print (WARNING + BOLD + "ERROR: repo-add returned: {}".format(rc) + UNCOLOR)
        raise
    print ("   ")
    print (BOLD+"* To use the repo you need following two lines in /etc/pacman.conf"+UNCOLOR)
    print (HIGHLGHT+"    ["+reponame+"]"+UNCOLOR+"                          # repository will be named '"+reponame+"'")
    print (HIGHLGHT+"    Server = file://"+repodir+UNCOLOR)
    print (" Also note that all pkg packages present in repodir was put into repo db file, not only those in your config file.")
    #print (" You have to manualy delete unneeded packages, and rerun repokeeper to update repo db file.")
except:
	print ("   repodb file creation failed")


#parsing local repo to identify outdate packages
outdated,not_in_conf=parse_localrepo()
if len(outdated) >0:
	lf.write("\nFollowing packages has newer versions and might be deleted from your repo:\n")
	for item in outdated:
		lf.write("rm "+item+" ;\n")

if len(not_in_conf) >0:
	lf.write("\nFollowing packages are not listed in your repokeeper.conf and might \
be deleted from your repo (just copy&paste it en block into a console):\n")
	for item in not_in_conf:
		lf.write("rm "+item+" ;\n")

lf.write("\n")
lf.write("All done at " + time.strftime("%d %b %Y %H:%M:%S", time.localtime()) + ", quitting\n")
