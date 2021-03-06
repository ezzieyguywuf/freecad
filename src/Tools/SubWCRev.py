#! python
# -*- coding: utf-8 -*-
# (c) 2006 Werner Mayer LGPL
#
# FreeCAD RevInfo script to get the revision information from Subversion.
#
# Under Linux the Subversion tool SubWCRev shipped with TortoiseSVN isn't 
# available which is provided by this script. 
# 2011/02/05: The script was extended to support also Bazaar

import os,sys,string,re,time,getopt
import xml.sax
import xml.sax.handler
import xml.sax.xmlreader
import StringIO

# SAX handler to parse the subversion output
class SvnHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.inUrl = 0
        self.inDate = 0
        self.mapping = {}

    def startElement(self, name, attributes):
        if name == "entry":
            self.buffer = ""
            self.mapping["Rev"] = attributes["revision"]
        elif name == "url":
            self.inUrl = 1
        elif name == "date":
            self.inDate = 1
 
    def characters(self, data):
        if self.inUrl:
            self.buffer += data
        elif self.inDate:
            self.buffer += data

    def endElement(self, name):
        if name == "url":
            self.inUrl = 0
            self.mapping["Url"] = self.buffer
            self.buffer = ""
        elif name == "date":
            self.inDate = 0
            self.mapping["Date"] = self.buffer
            self.buffer = ""

class VersionControl:
    def __init__(self):
        self.rev = ""
        self.date = ""
        self.url = ""

    def extractInfo(self, srcdir):
        return False

    def printInfo(self):
        print ""

    def writeVersion(self, lines):
        content=[]
        for line in lines:
            line = string.replace(line,'$WCREV$',self.rev)
            line = string.replace(line,'$WCDATE$',self.date)
            line = string.replace(line,'$WCURL$',self.url)
            content.append(line)
        return content

class UnknownControl(VersionControl):
    def extractInfo(self, srcdir):
        # Do not overwrite existing file with almost useless information
        if os.path.exists(srcdir+"/src/Build/Version.h"):
            return False
        self.rev = "Unknown"
        self.date = "Unknown"
        self.url = "Unknown"
        return True

    def printInfo(self):
        print "Unknown version control"

class DebianChangelog(VersionControl):
    def extractInfo(self, srcdir):
        # Do not overwrite existing file with almost useless information
        if os.path.exists(srcdir+"/src/Build/Version.h"):
            return False
        try:
            f = open(srcdir+"/debian/changelog")
        except:
            return False
        c = f.readline()
        f.close()
        r=re.search("bzr(\\d+)",c)
        if r != None:
            self.rev = r.groups()[0] + " (Launchpad)"
        
        t = time.localtime()
        self.date = ("%d/%02d/%02d %02d:%02d:%02d") % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
        self.url = "https://code.launchpad.net/~vcs-imports/freecad/trunk"
        return True

    def printInfo(self):
        print "debian/changelog"

class BazaarControl(VersionControl):
    def extractInfo(self, srcdir):
        info=os.popen("bzr log -l 1 %s" % (srcdir)).read()
        if len(info) == 0:
            return False
        lines=info.split("\n")
        for i in lines:
            r = re.match("^revno: (\\d+)$", i)
            if r != None:
                self.rev = r.groups()[0]
                continue
            r=re.match("^timestamp: (\\w+ \\d+-\\d+-\\d+ \\d+:\\d+:\\d+)",i)
            if r != None:
                self.date = r.groups()[0]
                continue
        return True

    def printInfo(self):
        print "bazaar"

class GitControl(VersionControl):
    #http://www.hermanradtke.com/blog/canonical-version-numbers-with-git/
    #http://blog.marcingil.com/2011/11/creating-build-numbers-using-git-commits/
    #http://gitref.org/remotes/#fetch
    #http://cworth.org/hgbook-git/tour/
    #http://git.or.cz/course/svn.html
    #git help log
    def getremotes(self):
        """return a mapping of remotes and their fetch urls"""
        rr=os.popen("git remote -v")
        rrstr=rr.read().strip()
        if rr.close() is None: # exit code == 0
            self.remotes=dict(l[:-8].split('\t') for l in rrstr.splitlines() \
                    if l.endswith(' (fetch)'))
            self.branchlst=os.popen("git show -s --pretty=%d HEAD").read()\
            .strip(" ()\n").split(', ') #used for possible remotes
    def geturl(self):
        urls=[]
        for ref in self.branchlst:
            if '/' in ref:
                remote,branch = ref.split('/',1)
                if remote in self.remotes:
                    url=self.remotes[remote]
                    #rewrite github to public url
                    import re
                    match = re.match('git@github\.com:(\S+?)/(\S+\.git)',url) \
                            or re.match('https://github\.com/(\S+)/(\S+\.git)'\
                            ,url)
                    if match is not None:
                        url = 'git://github.com/%s/%s' % match.groups()
                    match = re.match('ssh://\S+?@(\S+)',url)
                    if match is not None:
                        url = 'git://%s' % match.group(1)
                    entryscore=(url=='git://git.code.sf.net/p/free-cad/code',\
                            'github.com' in url,branch==self.branch,\
                            branch=='master', '@' not in url)
                            #used for sorting the list
                    if branch==self.branch: #add branch name
                        url = '%s %s' % (url,branch)
                    urls.append((entryscore,url))
        if len(urls) > 0:
            self.url = sorted(urls)[-1][1]
        else:
            self.url = "Unknown"

    def revisionNumber(self, srcdir,origin=None):
        """sets the revision number
for master and release branches all commits are counted
for other branches the version numver is split in two parts
the first number reflects the number of commits in common with the
blessed master repository.
the second part, seperated by " +"reflects the number of commits that are
different form the master repository"""
        #referencecommit="f119e740c87918b103140b66b2316ae96f136b0e"
        #referencerevision=4138
        referencecommit="49646282910aeef73db44943b88df06f0957422c"
        referencerevision=4244

        result = None
        countallfh=os.popen("git rev-list --count %s..HEAD" % \
                referencecommit)
        countallstr=countallfh.read().strip()
        if countallfh.close() is not None: #reference commit not present
            self.rev = '%04d (Git shallow)' % referencerevision
            return
        else:
            countall = int(countallstr)

        if origin is not None and self.branch.lower() != 'master' and \
                'release' not in self.branch.lower():
            mbfh=os.popen("git merge-base %s/master HEAD" % origin)
            mergebase = mbfh.read().strip()
            if mbfh.close() is None: # exit code == 0
                try:
                    countmergebase=int(os.popen("git rev-list --count %s..%s"\
                        % (referencecommit,mergebase)).read().strip())
                    if countall > countmergebase:
                        result = '%04d +%d (Git)' % (countmergebase +\
                            referencerevision,countall-countmergebase)
                except ValueError:
                    pass
        self.rev = result or ('%04d (Git)' % (countall+referencerevision))

    def namebranchbyparents(self):
        """name multiple branches in case that the last commit was a merge
a merge is identified by having two or more parents
if the describe does not return a ref name (the hash is added)
if one parent is the master and the second one has no ref name, one branch was
merged."""
        parents=os.popen("git log -n1 --pretty=%P").read()\
                .strip().split(' ')
        if len(parents) >= 2: #merge commit
            parentrefs=[]
            names=[]
            hasnames=0
            for p in parents:
                refs=os.popen("git show -s --pretty=%%d %s" % p).read()\
                        .strip(" ()\n").split(', ')
                if refs[0] != '': #has a ref name
                    parentrefs.append(refs)
                    names.append(refs[-1])
                    hasnames += 1
                else:
                    parentrefs.append(p)
                    names.append(p[:7])
            if hasnames >=2: # merging master into dev is not enough
                self.branch=','.join(names)

    def extractInfo(self, srcdir):
        self.hash=os.popen("git log -1 --pretty=format:%H").read().strip()
        if self.hash == "":
            return False # not a git repo
        # date/time
        import time
        info=os.popen("git log -1 --date=raw --pretty=format:%cd").read()
        # commit time is more meaningfull than author time
        # use UTC
        self.date = time.strftime("%Y/%m/%d %H:%M:%S",time.gmtime(\
                float(info.strip().split(' ',1)[0])))
        for self.branch in os.popen("git branch --no-color").read().split('\n'):
            if re.match( "\*", self.branch ) != None:
                break 
        self.branch=self.branch[2:]
        self.getremotes() #setup self.remotes and branchlst

        remote='origin' #used to determine the url
        self.geturl()
        origin = None #remote for the blessed master
        for fetchurl in ("git.code.sf.net/p/free-cad/code",\
            "git@github.com:FreeCAD/FreeCAD_sf_master.git",\
            "https://github.com/FreeCAD/FreeCAD_sf_master.git"):
            for key,url in self.remotes.iteritems():
                if fetchurl in url:
                    origin = key
                    break
            if origin is not None:
                break

        self.revisionNumber(srcdir,origin)
        if self.branch.lower() != 'master' and \
                'release' not in self.branch.lower():
            self.namebranchbyparents()
        if self.branch == '(no branch)': #check for remote branches
            if len(self.branchlst) >= 2:
                self.branch = self.branchlst[1]
                if '/' in self.branch:
                    remote=self.branch.split('/',1)[0]
            else: # guess
                self.branch = '(%s)' % \
                    os.popen("git describe --all --dirty").read().strip()
        #if the branch name conainted any slashes but was not a remote
        #there might be not result by now. Hence we assume origin
        if self.url == "Unknown":
            for i in info:
                r = re.match("origin\\W+(\\S+)",i)
                if r != None:
                    self.url = r.groups()[0]
                    break
        return True

    def printInfo(self):
        print "git"

    def writeVersion(self, lines):
        content = VersionControl.writeVersion(self, lines)
        content.append('// Git relevant stuff\n')
        content.append('#define FCRepositoryHash   "%s"\n' % (self.hash))
        content.append('#define FCRepositoryBranch "%s"\n' % (self.branch))
        return content

class MercurialControl(VersionControl):
    def extractInfo(self, srcdir):
        return False

    def printInfo(self):
        print "mercurial"

class Subversion(VersionControl):
    def extractInfo(self, srcdir):
        parser=xml.sax.make_parser()
        handler=SvnHandler()
        parser.setContentHandler(handler)

        #Create an XML stream with the required information and read in with a SAX parser
        Ver=os.popen("svnversion %s -n" % (srcdir)).read()
        Info=os.popen("svn info %s --xml" % (srcdir)).read()
        try:
            inpsrc = xml.sax.InputSource()
            strio=StringIO.StringIO(Info)
            inpsrc.setByteStream(strio)
            parser.parse(inpsrc)
        except:
            return False

        #Information of the Subversion stuff
        self.url = handler.mapping["Url"]
        self.rev = handler.mapping["Rev"]
        self.date = handler.mapping["Date"]
        self.date = self.date[:19]
        #Same format as SubWCRev does
        self.date = string.replace(self.date,'T',' ')
        self.date = string.replace(self.date,'-','/')

        #Date is given as GMT. Now we must convert to local date.
        m=time.strptime(self.date,"%Y/%m/%d %H:%M:%S")
        #Copy the tuple and set tm_isdst to 0 because it's GMT
        l=(m.tm_year,m.tm_mon,m.tm_mday,m.tm_hour,m.tm_min,m.tm_sec,m.tm_wday,m.tm_yday,0)
        #Take timezone into account
        t=time.mktime(l)-time.timezone
        self.date=time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(t))

        #Get the current local date
        self.time = time.strftime("%Y/%m/%d %H:%M:%S")

        self.mods = 'Src not modified'
        self.mixed = 'Src not mixed'
        self.range = self.rev

        # if version string ends with an 'M'
        r=re.search("M$",Ver)
        if r != None:
            self.mods = 'Src modified'

        # if version string contains a range
        r=re.match("^\\d+\\:\\d+",Ver)
        if r != None:
            self.mixed = 'Src mixed'
            self.range = Ver[:r.end()]
        return True

    def printInfo(self):
        print "subversion"


def main():
    #if(len(sys.argv) != 2):
    #    sys.stderr.write("Usage:  SubWCRev \"`svn info .. --xml`\"\n")

    srcdir="."
    bindir="."
    try:
        opts, args = getopt.getopt(sys.argv[1:], "sb:", ["srcdir=","bindir="])
    except getopt.GetoptError:
        pass

    for o, a in opts:
        if o in ("-s", "--srcdir"):
            srcdir = a
        if o in ("-b", "--bindir"):
            bindir = a

    vcs=[GitControl(), BazaarControl(), Subversion(), MercurialControl(), DebianChangelog(), UnknownControl()]
    for i in vcs:
        if i.extractInfo(srcdir):
            # Open the template file and the version file
            file = open("%s/src/Build/Version.h.in" % (srcdir))
            lines = file.readlines()
            file.close()
            lines = i.writeVersion(lines)
            out  = open("%s/src/Build/Version.h" % (bindir),"w");
            out.writelines(lines)
            out.write('\n')
            out.close()
            i.printInfo()
            sys.stdout.write("%s/src/Build/Version.h written\n" % (bindir))
            break

if __name__ == "__main__":
    main()

