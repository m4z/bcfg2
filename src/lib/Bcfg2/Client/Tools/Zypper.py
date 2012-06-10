"""This provides Bcfg2 support for zypper packages."""

import Bcfg2.Client.Tools

# TODO handle locks in a smart way
class Zypper(Bcfg2.Client.Tools.PkgTool):
    """zypper package support."""
    name = 'Zypper'
    __execs__ = ["/bin/rpm", "/usr/bin/zypper"]
    __handles__ = [('Package', 'zypper'),
                   ('Package', 'yum'),
                   ('Package', 'rpm'),
                   ('Path', 'ignore')]
    # TODO do i need version?
    __req__ = {'Package': ['name', 'version'],
               'Path': ['type']}
    # TODO might be needed
    # __req_gpg__ = {'Package': ['name'], 'Instance': ['version', 'release']}
    # TODO remove?
    conflicts = ['RPM', 'RPMng', 'YUM24', 'YUMng']
    pkgtype = 'rpm'
    pkgtool = ('/usr/bin/zypper install %s', ('%s', ['name']))

    def __init__(self, logger, setup, config):
        Bcfg2.Client.Tools.PkgTool.__init__(self, logger, setup, config)
        # Handle important entries. These directly influence zypper behavior.
        self.__important__ = self.__important__ + \
                             [entry.get('name') for struct in config \
                              for entry in struct \
                              if entry.tag == 'Path' and \
                              entry.get('name').startswith('/etc/zypp')]
        # Handle <Path type=ignore>.
        self.ignores = [entry.get('name') for struct in config \
                        for entry in struct \
                        if entry.tag == 'Path' and \
                        entry.get('type') == 'ignore']
        # Get the list of currently installed packages.
        self.installed = {}
        self.RefreshPackages()
        # Get the list of the most recent available packages.
        self.available = {}
        self.RefreshPackagesLocally()

    #def __zypperListUpdates(self):
    #def __zypperSearch(self):
    #    zypper se -t package -s

    def __getCurrentVersion(self, pkgname):
        """Return version string for currently installed package.

           The version of package <pkgname> is returned in the format
           <version>-<release>.<arch> (without the package name itself),
           or None if not installed.
        """
        try:
            old = self.installed[pkgname][0]
            return (old.get('version') +
                    '-' + old.get('release') +
                    '.' + old.get('arch'))
        except KeyError:
            return None

    # TODO: This takes about 8 minutes for all packages on a minimal
    #       openSUSE 12.1 system. There *must* be a better way.
    def __getNewestVersion(self, pkgname):
        """Return version string of the newest available version of package.

           The version of package <pkgname> is returned in the format
           <version>-<release>.<arch> (without the package name itself),
           for package, or None if the package is unknown.
        """
        versions = self.cmd.run("/usr/bin/zypper --quiet --non-interactive "
                                "search -t package -s --match-exact %s" %
                                pkgname)[1]
        # try to get the current version, might not be installed
        try:
            currentversion = self.__getCurrentVersion(pkgname).rsplit('.', 1)[0]
            newestversion = currentversion
        except AttributeError:
            newestversion = '0'

        for ver in versions:
            # we need to skip the header
            if ver.startswith('S |') or ver.startswith('--+') or len(ver) == 0:
                pass
            else:
                # Returns "status | package name | package type | \
                #          version-release | arch | repository"
                try:
                    _, pname, _, versionrelease, arch, _ = \
                            ver.strip().split('|')
                except ValueError:
                    self.logger.info("Zypper: Wrong data or unknown package "
                                     "(%s, %s)" % (pkgname, ver))
                    return None

                pname = pname.strip()
                versionrelease = versionrelease.strip()
                arch = arch.strip()

                if pname != pkgname:
                    self.logger.info("Zypper: Got wrong data (versions).")

                # we cannot add the '.arch' suffix yet.
                thisversion = versionrelease

                vcmp = self.__vcmp(currentversion, thisversion)
                if vcmp == -1:
                    self.logger.debug("Zypper: Newest: Update available for "
                                      "%s: %s -> %s" %
                                     (pkgname, currentversion, thisversion))
                    # we might find multiple updates, so check if this one is
                    # newer than the newest one we know up to this point.
                    if self.__vcmp(thisversion, newestversion) == -1:
                        self.logger.debug("Zypper: Newest: Update: %s/%s/%s" %
                                          (currentversion,
                                          newestversion,
                                          thisversion))
                        newestversion = thisversion
                elif vcmp == 1 or vcmp == 0:
                #    self.logger.debug("Zypper: Nothing to do for %s" %
                #                     pkgname)
                    pass
                else:
                    self.logger.info("Zypper: got wrong data (vcmp).")
        # now it's time to add the suffix.
        return newestversion + '.' + arch

    def __vcmp(self, ver1, ver2):
        """Compare package versions."""
        # negative: current is older
        # positive: current is newer
        # zero: both versions are equal
        vcmp = self.cmd.run("/usr/bin/zypper --terse versioncmp %s %s" %
                            (ver1, ver2))[1][0]
        #self.logger.debug("Zypper: vcmp: %s" % vcmp)
        return int(vcmp)

    #def __stripZypperHeader(self,

    def RefreshPackages(self):
        """Create self.installed, the list of currently installed packages.

           Format:
               self.installed['foo'] = [ {'name':'foo', 'version':'...',
                                          'release':'...', 'arch':'...'},
                                         {...} ]
        """
        #self.logger.debug("Zypper: Begin Refresh")
        pkgcache = self.cmd.run("/bin/rpm --query --all")[1]
        self.installed = {}
        for pkg in pkgcache:
            # format: <name-with-optional-dashes>-<version>-<release>.<arch>
            pkgname = pkg.rsplit('-', 2)[0]
            version = pkg.rsplit('-', 2)[1]

            arch = None
            try:
                arch = pkg.rsplit('.', 1)[1]
                release = pkg.rsplit('-', 2)[2].rsplit('.', 1)[0]
            except IndexError:
                release = pkg.rsplit('-', 2)[2]

            currentpkg = {}
            currentpkg['name'] = pkgname
            currentpkg['version'] = version
            currentpkg['release'] = release
            if arch is not None:
                currentpkg['arch'] = arch
            else:
                currentpkg['arch'] = 'noarch'
            #self.logger.debug("Zypper: pkg:     p:%s  v:%s  r:%s  (a:%s)" %
            #                  (pkgname, version, release, arch))
            self.installed.setdefault(pkgname, []).append(currentpkg)
            #self.logger.debug("Zypper:    %s" % currentpkg)
        #self.logger.debug("Zypper: End Refresh")

    def RefreshPackagesLocally(self):
        """Get list of newest available packages.

           Format:
               self.available['name'] = '<version>-<release>.<arch>'
        """
        #self.logger.debug("Zypper: Begin local Refresh")
        # Force a refresh now, because depending on the zypper configuration,
        # the metadata might be old.
        # TODO there *must* be a smarter way.
        refreshnow = self.cmd.run("/usr/bin/zypper --quiet --non-interactive "
                                  "refresh --force")
        updates_available = \
                self.cmd.run("/usr/bin/zypper --quiet --non-interactive "
                             "list-updates --type package")[1]
        if not self.available:
            self.available = {}
        for update in updates_available:
            # we need to skip the header
            if update.startswith('S |') or update.startswith('--+'):
                pass
            else:
                # Returns "status | repo description | pkgname | \
                #          oldversion-release | newversion-release | arch"
                try:
                    _, _, pkgname, _, newversionrelease, arch = \
                            update.strip().split('|')
                except ValueError:
                    self.logger.info("Zypper: got wrong data")
                pkgname = pkgname.strip()
                newversionrelease = newversionrelease.strip()
                arch = arch.strip()
                self.available[pkgname] = newversionrelease + '.' + arch

                self.logger.debug("Zypper: Update available for %s: %s -> %s" %
                                 (pkgname,
                                  self.__getCurrentVersion(pkgname),
                                  self.available[pkgname]))
        #self.logger.debug("Zypper: End local Refresh")

    def VerifyPackage(self, entry, modlist):
        """Verify Package status for entry, by comparing the versions the server
           wants us to have (entry) to the version we have (self.installed).

           Returns True if the correct and unmodified version is installed,
                   False otherwise.
        """
        # TODO refactor
        pn = entry.get('name')
        cur = self.__getCurrentVersion(pn)

        # attribs are: name, priority, version, type, uri
        self.logger.debug("Zypper: Verify: %s (t:%s), Client has v:%s, "
                          "Server wants v:%s)" %
                          (pn, entry.get('type'), cur, entry.get('version')))

        if not 'version' in entry.attrib:
        #if not entry.get('version'):
            self.logger.info("Cannot verify unversioned package %s" % pn)
            return False

        if pn in self.installed:
            # package is already installed, check for correct version etc.
            if (self.installed[pn] == \
                entry.get('version') or entry.get('version') == 'any'):
                self.logger.debug("Zypper: Verify: %s is correct version %s" %
                                  (pn, self.installed[pn]))
                return True

            # server wants newest version.
            elif entry.get('version') == 'auto':
                # short-circuit check for updates.
                if pn in self.available:
                    self.logger.debug("Zypper: Verify: update available"
                                      " for %s: %s -> %s" %
                                      (pn, cur, self.available[pn]))
                    return False
                # no direct update found. this might be very redundant.
                else:
                    newest = self.__getNewestVersion(pn)
                    if cur == newest:
                        #self.logger.debug("Zypper: Verify: no update for %s" %
                        #                  pn)
                        return True
                    # current is not newest. i am confused.
                    else:
                        return False
            else:
                self.logger.info("  %s: Wrong version installed.  "
                                 "Want %s, but have %s" %
                                 (pn, entry.get("version"), self.installed[pn]))
                return False
        else:
            # package is not installed on the client.
            self.logger.debug("Zypper: Verify: %s is missing" % pn)
            return False

    def RemovePackages(self, packages):
        """Remove extra packages.

           packages is TODO
        """
        for pkg in packages:
            self.logger.info("Removing packages: %s" % " ".join(names))
            self.cmd.run("/usr/bin/zypper --quiet --non-interactive remove %s" %
                         pkg)
    #    names = [pkg.get('name') for pkg in packages]
    #    self.logger.info("Removing packages: %s" % " ".join(names))
    #    self.cmd.run("/usr/bin/zypper remove --type package --clean-deps %s" %
    #                 " ".join(names))
    #    self.RefreshPackages()
    #    self.extra = self.FindExtraPackages()

    def Install(self, packages, states):
        """Install packages.

           This will be called *after* confirmation in interactive mode.

           Format:
               packages: TODO

               states contains the verify states of the packages:
                   states = { {'name':'foo', 'version':'...', ...}:True,
                              {'name':'bar', ...}:False,
                              ...}

           Gotta lotta 'splainin' TODO.
        """
        #install_pkgs = []
        for pkg in states.keys():
            if states[pkg] is False:
                self.logger.info("Zypper: Change: %s" % pkg)

        for pkg in packages:
            newver = self.__getNewestVersion(pkg.get('name'))
            instname = pkg + '-' + newver
            self.logger.info("Zypper: Install package: %s" % instname)
            self.cmd.run("/usr/bin/zypper --quiet --non-interactive "
                         "--no-recommends install %s" % instname)

    def FindExtraPackages(self):
        """Find extra packages."""
        packages = [e.get('name') for e in self.getSupportedEntries()]
        extras = []

        for pkg in list(self.installed.keys()):
            if pkg not in packages:
                entry = Bcfg2.Client.XML.Element('Package', name=pkg,
                                                 type=self.pkgtype)
                for i in self.installed[pkg]:
                    inst = Bcfg2.Client.XML.SubElement(entry,
                                                       'Instance',
                                                       version=i['version'],
                                                       release=i['release'],
                                                       arch=i['arch'])
                extras.append(entry)
        return extras

    def VerifyPath(self, entry, _):
        """Do nothing here since we only verify Path type=ignore"""
        return True
