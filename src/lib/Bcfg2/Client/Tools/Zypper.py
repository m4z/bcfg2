"""This provides Bcfg2 support for zypper packages."""

import Bcfg2.Client.Tools

# Parts of this plugin are shamelessly ripped out of YUMng and RMPng.
# Thank you, authors.
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

    def RefreshPackages(self):
        """Create self.installed, the list of currently installed packages.

           Format:
               self.installed[name] = [ {'name':'...', 'version':'...',
                                         'release':'...', 'arch':'...'},
                                        {...} ]
        """
        self.logger.debug("Zypper: Begin Refresh")
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
                #self.installed[pkgname] = version + '-' + release + '.' + arch
                currentpkg['arch'] = arch
                #self.logger.debug("Zypper: pkg:     p:%s  v:%s  r:%s  (a:%s)" %
                #                  (pkgname, version, release, arch))
            else:
                #self.installed[pkgname] = version + '-' + release
                currentpkg['arch'] = 'noarch'
                #self.logger.debug("Zypper: gpg-pkg: p:%s  v:%s  r:%s" %
                #                  (pkgname, version, release))
            self.installed.setdefault(pkgname, []).append(currentpkg)
            #self.logger.debug("Zypper:    %s" % currentpkg)
        self.logger.debug("Zypper: End Refresh")

    # TODO this takes a moment, so maybe we should log an info msg.
    def RefreshPackagesLocally(self):
        """Get list of newest available packages."""
        self.logger.debug("Zypper: Begin local Refresh")
        # Force a refresh now, because depending on the zypper configuration,
        # the metadata might be old.
        refreshnow = self.cmd.run("/usr/bin/zypper --quiet --non-interactive \
                                  refresh --force")
        updates_available = \
                self.cmd.run("/usr/bin/zypper --quiet --non-interactive \
                             list-updates --type package")[1]
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
                    _, _, pkgname, _, newversionrelease, arch = update.strip().split('|')
                except ValueError:
                    self.logger.info("Zypper: got wrong data")
                pkgname = pkgname.strip()
                newversionrelease = newversionrelease.strip()
                arch = arch.strip()
                self.available[pkgname] = newversionrelease + '.' + arch
                self.logger.debug("Zypper: Update to v:%s available for %s" %
                                 (self.available[pkgname], pkgname))
        self.logger.debug("Zypper: End local Refresh")

    def VerifyPackage(self, entry, modlist):
        """Verify Package status for entry, by comparing the versions the server
           wants us to have (entry) to the version we have (self.installed).

           Returns True if the correct and unmodified version is installed,
                   False otherwise.
        """
        #self.logger.debug("Zypper: Verify: %s" % entry.get('name'))

        #for a in entry.attrib:
        #    # attribs are: name, priority, version, type, uri
        #    for a in ['version', 'type']:
        #        self.logger.debug("Zypper: %s=%s" % (a, entry.get(a)))
        self.logger.debug("Zypper: Verify: %s (t:%s v:%s)" %
                          (entry.get('name'),
                           entry.get('type'),
                           entry.get('version')))

        if not 'version' in entry.attrib:
        #if not entry.get('version'):
            self.logger.info("Cannot verify unversioned package %s" %
               (entry.get('name')))
            return False

        if entry.get('name') in self.installed:
            # package is already installed, check for correct version etc.
            if (self.installed[entry.get('name')] == \
                entry.get('version') or entry.get('version') == 'any'):
                self.logger.debug("Zypper: Verify: %s is correct version %s" %
                                  (entry.get('name'),
                                   self.installed[entry.get('name')]))
                return True

            elif entry.get('version') == 'auto':
                # TODO what has to be done here?
                # TODO get most recent version of packages?
                if entry.get('name') in self.available:
                    self.logger.debug("Zypper: Verify: update available" + \
                                      " for %s: %s -> %s" %
                                      (entry.get('name'),
                                       #self.installed[entry.get('name')].index('version'),
                                       self.installed[entry.get('name')],
                                       self.available[entry.get('name')]))
                #else:
                #   self.logger.debug("Zypper: Verify: no update for %s" %
                #                      entry.get('name'))
                return False

            else:
                self.logger.info("  %s: Wrong version installed.  "
                                 "Want %s, but have %s" %
                                 (entry.get("name"),
                                  entry.get("version"),
                                  self.installed[entry.get("name")]))
                return False
        else:
            # package is not installed on the client.
            self.logger.debug("Zypper: Verify: %s is missing" %
                              entry.get('name'))
            return False

    #            entry.set('current_version', self.installed[entry.get('name')])
    #            return False
    #    entry.set('current_exists', 'false')
    #    return False

    def RemovePackages(self, packages):
        """Remove extra packages."""
        pass
    #    names = [pkg.get('name') for pkg in packages]
    #    self.logger.info("Removing packages: %s" % " ".join(names))
    #    self.cmd.run("/usr/bin/zypper remove --type package --clean-deps %s" %
    #                 " ".join(names))
    #    self.RefreshPackages()
    #    self.extra = self.FindExtraPackages()

    def Install(self, packages, states):
        pass
    #    install_pkgs = []
    #    for pkg in packages:
    #        if ++needs_change++:
    #            install_pkgs.append(pkg)

    def FindExtraPackages(self):
        """Find extra packages."""
        pass
        packages = [e.get('name') for e in self.getSupportedEntries()]
        extras = []

        for p in list(self.installed.keys()):
            if p not in packages:
                entry = Bcfg2.Client.XML.Element('Package', name=p,
                                                 type=self.pkgtype)
                for i in self.installed[p]:
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
