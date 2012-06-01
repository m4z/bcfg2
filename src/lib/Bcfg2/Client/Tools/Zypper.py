"""This provides Bcfg2 support for zypper packages."""

import Bcfg2.Client.Tools

# Parts of this plugin are shamelessly ripped out of YUMng and RMPng.
# Thank you, authors.
class Zypper(Bcfg2.Client.Tools.PkgTool):
    """zypper package support."""
    name = 'Zypper'
    __execs__ = ["/bin/rpm", "/usr/bin/zypper"]
    # TODO also handle files?
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
        self.installed = {}
        self.RefreshPackages()

    def RefreshPackages(self):
        """Get list of currently installed packages."""
        self.logger.info("Zypper: Begin Refresh")
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

            #if arch is not None:
            #    self.logger.debug("Zypper: pkg:     p:%s  v:%s  r:%s  (a:%s)" %
            #                      (pkgname, version, release, arch))
            #else:
            #    self.logger.debug("Zypper: gpg-pkg: p:%s  v:%s  r:%s" %
            #                      (pkgname, version, release))

            self.installed[pkgname] = version
        self.logger.info("Zypper: End Refresh")

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
        self.logger.debug("Zypper: Verify: %s (t:%s  v:%s)" %
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
                self.logger.debug("Zypper: Verify: %s is version=auto" %
                                  entry.get('name'))
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

    #def Install(self, packages, states):
    #    install_pkgs = []
    #    for pkg in packages:
    #        if ++needs_change++:
    #            install_pkgs.append(pkg)
