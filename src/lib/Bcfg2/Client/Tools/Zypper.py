"""This provides Bcfg2 support for zypper packages."""
# TODO: After Install or Remove, the entries are still listed as Incorrect.
#       Is this what self.modified is used for?
# TODO: use 'dup' to support distribution upgrades ("vendor changes")?

import Bcfg2.Client.Tools

# TODO what should be done if a pkg is locked, trust the server or this box?
#      -> this box, use the usual zypper config and logic on the client.
class Zypper(Bcfg2.Client.Tools.PkgTool):
    """zypper package support.

       A few words of caution:
           In the case of installation and removal, even if the user selects not
           to change state for pkg A (install or remove), but then decides
           differently for another pkg B that pkg A depends on (removal) or is
           depended upon (install), the state of pkg A will still change.
           This might be unexpected or even undesired, but this is the behavior
           that is shown by zypper itself.
           We could implement elaborate checks here to stop changing pkg B in
           these cases too, because the user is obviously asking us to do
           something impossible, but since this would complicate this plugin
           further, it hasn't been done yet.
    """
    name = 'Zypper'
    __execs__ = ["/bin/rpm", "/usr/bin/zypper"]
    __handles__ = [('Package', 'zypper'),
                   ('Package', 'yum'),
                   ('Package', 'rpm'),
                   ('Path', 'ignore')]
    # Unsure if i need version, like this:
    #__req__ = {'Package': ['name', 'version'],
    __req__ = {'Package': ['name'],
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

    def _getCurrentVersion(self, pkg):
        """Return version string for currently installed package.

           The version of package <pkgname> is returned in the format
           <version>-<release>.<arch> (without the package name itself),
           or None if not installed.
        """
        # gpg-pubkey package with multiple instances (type entry).
        try:
            try:
                #self.logger.debug("Zypper: _cur: %s" %
                #                  self.installed[pkg.get('name')])
                keys = []
                for child in self.installed[pkg.get('name')]:
                    #self.logger.debug("Zypper: _cur: %s" % child)
                    keys.append("%s-%s" %
                                (child.get('version'), child.get('release')))
                return keys
            except KeyError:
                return None
        # "normal" package, type string.
        except AttributeError:
            try:
                #self.logger.debug("Zypper: _cur: %s" %
                #                  self.installed[pkg])
                c_pkgs = []
                for child in self.installed[pkg]:
                    c_pkgs.append("%s-%s.%s" % (child.get('version'),
                                                child.get('release'),
                                                child.get('arch')))
                return c_pkgs
            except KeyError:
                return None

    # TODO this is very fragile. if, f.e., there's a problem with a single repo,
    # this function will have a hard time dealing with the zypper output.
    def _getNewestVersion(self, pkgname):
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
            currentversion = self._getCurrentVersion(pkgname).rsplit('.', 1)[0]
            newestversion = currentversion
        except AttributeError:
            currentversion = '0'
            newestversion = '0'

        for ver in versions:
            # we need to skip the header
            if ver.startswith('S |') or ver.startswith('--+') or len(ver) == 0:
                pass
            # skip some common errors, too.
            elif ver.startswith('File \'/repodata/repomd.xml\' not found') or \
                     ver.startswith('Problem retrieving files from') or \
                     ver.startswith('Abort, retry, ignore?') or \
                     ver.startswith('Warning: Disabling repository'):
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

                vcmp = self._vcmp(currentversion, thisversion)
                if vcmp == -1:
                    #self.logger.debug("Zypper: Newest: Update available for "
                    #                  "%s: %s -> %s" %
                    #                 (pkgname, currentversion, thisversion))
                    # we might find multiple updates, so check if this one is
                    # newer than the newest one we know up to this point.
                    if self._vcmp(newestversion, thisversion) == -1:
                        #self.logger.debug("Zypper: Newest: Update: %s/%s/%s" %
                        #                  (currentversion,
                        #                  newestversion,
                        #                  thisversion))
                        newestversion = thisversion
                elif vcmp == 1 or vcmp == 0:
                #    self.logger.debug("Zypper: Nothing to do for %s" %
                #                     pkgname)
                    pass
                else:
                    self.logger.info("Zypper: got wrong data (vcmp).")
        # TODO: in case of a vendor change, the new package will not be
        # installable, example:
        # v | xorg-x11-libs | package | 7.6-37.1.1 | noarch | openSUSE-12.2-Oss
        # i | xorg-x11-libs | package | 7.6-25.1.2 | i586   | (System Packages)
        # Zypper: Newest: Returning version xorg-x11-libs-7.6-37.1.1
        # Zypper: Install package: xorg-x11-libs-7.6-37.1.1.i586
        # Package 'xorg-x11-libs-7.6-37.1.1.i586' not found.
        # so TODO: handle vendor changes (with dup?)
        self.logger.debug("Zypper: Newest: Returning version %s-%s" %
                          (pkgname, newestversion))
        # Now it's time to add the suffix.
        # Please note that this will return None in case of gpg-pubkey pkgs.
        return newestversion + '.' + arch

    def _vcmp(self, ver1, ver2):
        """Compare package versions.

           Returns an integer that is...
               negative, if ver1 is older than ver2;
               positive, if ver1 is newer;
               zero,     if both versions are equal.
        """
        vcmp = self.cmd.run("/usr/bin/zypper --terse versioncmp %s %s" %
                            (ver1, ver2))[1][0]
        #self.logger.debug("Zypper: vcmp: %s" % vcmp)
        return int(vcmp)

    def _handleGPGPubkeyInstances(self, pkg):
        """Make handling of gpg-pubkey packages possible.

           GPG public keys are a special case in RPM land.

           Returns a list of the package instances, or None if none.
        """
        keys = []
        for child in pkg.getchildren():
            # TODO make this smarter, work with only ver-rel
            keys.append("%s-%s" % (child.get('version'), child.get('release')))
        return keys

    def RefreshPackages(self):
        """Create self.installed, the list of currently installed packages.

           Format:
               self.installed['foo'] = [ {'name':'foo', 'version':'...',
                                          'release':'...', 'arch':'...'},
                                         {...} ]
        """
        c_pkgcache = self.cmd.run("/bin/rpm --query --all")[1]
        self.installed = {}
        for c_pkg in c_pkgcache:
            # format: <name-with-optional-dashes>-<version>-<release>.<arch>
            c_pkgname = c_pkg.rsplit('-', 2)[0]
            c_version = c_pkg.rsplit('-', 2)[1]

            c_arch = None
            try:
                # this is the usual case, where an arch is set.
                c_arch = c_pkg.rsplit('.', 1)[1]
                c_release = c_pkg.rsplit('-', 2)[2].rsplit('.', 1)[0]
            except IndexError:
                # gpg-pubkey packages, and possibly others, do not possess
                # an arch, not even "noarch".
                c_release = c_pkg.rsplit('-', 2)[2]
                #self.logger.debug("Zypper: Refresh: archless: %s %s-%s" %
                #                  (c_pkgname, c_version, c_release))

            c_currentpkg = {}
            c_currentpkg['name'] = c_pkgname
            c_currentpkg['version'] = c_version
            c_currentpkg['release'] = c_release
            if c_arch is not None:
                c_currentpkg['arch'] = c_arch
            else:
                c_currentpkg['arch'] = 'noarch'
            self.installed.setdefault(c_pkgname, []).append(c_currentpkg)

    def RefreshPackagesLocally(self):
        """Get list of newest available packages.

           These are the updates and new packages that zypper *could* install.

           Format:
               self.available['name'] = '<version>-<release>.<arch>'
        """
        # Force a refresh now, because depending on the zypper configuration,
        # the metadata might be old.
        # TODO: This takes a moment, maybe do not force?
        # TODO: If the refresh timeouts, it takes 3 minutes * number of repos to
        # finish. I haven't found zypp or zypper options to shorten this.
        #   (maybe indirectly via curl options)?
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
                    pkgname = pkgname.strip()
                    newversionrelease = newversionrelease.strip()
                    arch = arch.strip()
                    self.available[pkgname] = newversionrelease + '.' + arch

                    #try:
                    #    # "normal" packages are returned as arrays.
                    #    self.logger.debug("Zypper: Update available for %s:"
                    #                      " %s -> %s" %
                    #                      (pkgname,
                    #                       # TODO use entry if possible
                    #                       self._getCurrentVersion(pkgname)[0],
                    #                       self.available[pkgname]))
                    #except TypeError:
                    #    # gpg-pubkey packages are returned as strings.
                    #    self.logger.debug("Zypper: Update available for %s:"
                    #                      " %s -> %s" %
                    #                      (pkgname,
                    #                       # TODO use entry if possible
                    #                       self._getCurrentVersion(pkgname),
                    #                       self.available[pkgname]))
                except ValueError:
                    # Might be caused by an error during update, for example.
                    self.logger.info("Zypper: got wrong data")

    def VerifyPackage(self, entry, modlist):
        """Verify Package status for entry, by comparing the version(s)
           the server wants us to have (entry) to the version we have
           (self.installed).

           TODO what is modlist?

           Returns True if the correct and unmodified version is installed,
                   False otherwise.
        """
        # attribs are: name, priority, version, type, uri
        s_pn = entry.get('name')
        s_pt = entry.get('type')
        s_pv = entry.get('version')
        # TODO refactor
        if s_pt != 'yum' and s_pn == 'gpg-pubkey':
            c_cur = self._getCurrentVersion(entry)
            s_pubkeys = self._handleGPGPubkeyInstances(entry)
            # let's not duplicate the effort here just for printing early.
            self.logger.debug("Zypper: Verify: %s:%s, Server wants v:%s, "
                              "Client has v:%s." % (s_pt, s_pn, s_pubkeys,
                                                    c_cur))
        else:
            c_cur = self._getCurrentVersion(s_pn)
            if c_cur is None:
                # this will happen if the server wants the client to install a
                # package, but the client does not know that a package exists,
                # for example because it doesn't have the right repos or
                # because the plugin developer is doing a distribution upgrade
                # with an outdated package list.
                self.logger.debug("Zypper: Verify: Server asked for a package"
                                  " the Client doesn't know: %s:%s (%s)." %
                                  (s_pt, s_pn, s_pv))
            else:
                self.logger.debug("Zypper: Verify: %s:%s, Server wants v:%s, "
                                  "Client has v:%s.)" % (s_pt, s_pn, s_pv,
                                                         c_cur[0]))

        # in case of gpg-pubkey packages, it's ok if there is no version yet.
        if not 'version' in entry.attrib and s_pubkeys is None:
            self.logger.info("Cannot verify unversioned package %s" % s_pn)
            return False

        if s_pn in self.installed:
            # Handle gpg-pubkey packages first
            if s_pn == 'gpg-pubkey':
                # if the current key is in the list of wanted keys, accept.
                correct_keys = {}
                for k in s_pubkeys:
                    # format: <version>-<release>
                    version = k.rsplit('-', 1)[0]
                    release = k.rsplit('-', 1)[1]
                    thiskey = "%s-%s" % (version, release)
                    correct_keys[thiskey] = False

                    for c_haskey in c_cur:
                        if c_haskey == thiskey:
                            correct_keys[thiskey] = True
                            self.logger.debug("Zypper: Verify: gpg-pubkey is"
                                              " correct instance %s" % c_haskey)
                            # no need to check the remaining keys here.
                            break

                # TODO what about extra entries?
                for key in correct_keys.keys():
                    if correct_keys[key] == False:
                        #rpm -q --queryformat="%{Summary}\n" \
                        #   gpg-pubkey-6144af68-4c58609c
                        #gpg(home:m4z OBS Project <home:m4z@build.opensuse.org>)
                        keystring = self.cmd.run("/bin/rpm --query "
                                                 "--queryformat='%%{Summary}\n'"
                                                 " %s-%s" % (s_pn, key))[1]
                        #self.logger.debug("Zypper: Verify: Something wrong.")
                        self.logger.debug("Zypper: Missing %s-%s: %s"
                                          % (s_pn, key, keystring))
                        return False
                    else:
                        self.logger.debug("Zypper: Verify: All keys correct.")
                        return True


            # package is already installed, check for correct version etc.
            elif (self.installed[s_pn] == s_pv or s_pv == 'any'):
                self.logger.debug("Zypper: Verify: %s is correct version %s" %
                                  (s_pn, self.installed[s_pn]))
                return True

            # server wants newest version.
            elif s_pv == 'auto':
                # short-circuit check for updates.
                if s_pn in self.available:
                    # we don't need to handle the gpg-pubkey case here, it has
                    # already been taken care of above.
                    self.logger.debug("Zypper: Verify: update available"
                                      " for %s: %s -> %s" %
                                      (s_pn, c_cur[0], self.available[s_pn]))
                    return False
                # no direct update found.
                else:
                    # TODO: This might be the thorough way to do things,
                    #       but takes a reeeally long time. (About 8 minutes
                    #       for all packages on an absolutely minimal openSUSE
                    #       12.1 system, versus 30 seconds with the
                    #       short-circuit workaround to trust the local
                    #       machines' "zypper list-updates".)
                    #
                    #newest = self._getNewestVersion(s_pn)
                    #if c_cur == newest:
                    #    #self.logger.debug("Zypper: Verify: no update for %s" %
                    #    #                  s_pn)
                    #    return True
                    ## currently installed version is not the newest.
                    #else:
                    #    return False

                    # Workaround: zypper didn't find any updates above.
                    return True
            else:
                self.logger.info("Zypper: %s: Wrong version installed. "
                                 "Want %s, but have %s." %
                                 (s_pn, entry.get("version"),
                                  self.installed[s_pn]))
                return False
        else:
            # package is not (yet) installed on the client.
            self.logger.debug("Zypper: Verify: %s is missing" % s_pn)
            return False

    # TODO: gpg-pubkey
    def RemovePackages(self, packages):
        """Remove extra packages.

           This will remove additional packages if they depend on a package you
           selected for removal.

           packages is the list of items that were selected to be removed.
               Package = {'type':'rpm', 'name':'foo'}
        """
        rmpkgs = []
        # TODO can this fail if no packages were selected?
        for pkg in packages:
            pn = pkg.get('name')
            # TODO this can fail, f.e. when a list is returned
            #try:
            pv =  self._getCurrentVersion(pn)
            #except TypeError:
            #    # ...
            pname = pn + "-" + pv
            if pn == 'gpg-pubkey':
                # TODO: this is never reached?
                self.logger.info("Zypper: Skipping removal of %s" % pname)
            rmpkgs.append(pname)

        if rmpkgs != []:
            rmpkgs_str = " ".join(rmpkgs)
            self.logger.info("Zypper: Removing packages: %s" % rmpkgs_str)
            self.cmd.run("/usr/bin/zypper --non-interactive remove %s" %
                         rmpkgs_str)
            #
            # in order to display the correct verify state in state=final, we
            # have to refresh the package list and then recalculate the verify
            # state.
            self.RefreshPackages()
            self.FindExtraPackages()
            # TODO: still need to re-verify now?
            #for pkg in rmpkgs:
            # can't set state for uninstalled pkg
            #    pn = pkg.rsplit('.', 1)[0]
            #    states[pkg] = self.VerifyPackage(pkg, [])


    def Install(self, packages, states):
        """Install packages.

           This will be called *after* confirmation in interactive mode.
           TODO: It relies on zypper, so even if the user selects not to change
           package A, but then selects to install package B which needs A, both
           will be changed. This might be unexpected or even undesired.

           Format:
               packages: TODO list of all packages from the server?
                         TODO list of all non-verifying packages?

               states contains the verify states of the packages:
                   states = { {'name':'foo', 'version':'...', ...}:True,
                              {'name':'bar', ...}:False,
                              ...}
               (True indicates the entry is fine, False means it needs action.)
        """
        for pkgstate in states.keys():
            if states[pkgstate] is False:
                self.logger.info("Zypper: Change: Server wants to change %s" %
                                 pkgstate.get('name'))
            #else:
            #    self.logger.info("Zypper: Change: No change for %s" %
            #                     pkgstate.get('name'))

        # TODO: gpg
        for pkg in packages:
            newver = self._getNewestVersion(pkg.get('name'))
            # TODO newver can still be None in case of gpg-pubkey pkgs.
            # "gpg-pubkey v:56b4177a-4be18cab.noarch, Server wants v:None
            # TODO this is also very fragile in other cases, like when
            # _getNewestVersion() fails. make more robust.
            #try:
            instname = pkg.get('name') + '-' + newver
            #except TypeError:
            #    # TODO
            self.logger.info("Zypper: Install package: %s" % instname)
            self.cmd.run("/usr/bin/zypper --non-interactive "
                         "install --no-recommends %s" % instname)
            # TODO: we might need to collect all changed packages here so we can
            # change their verify states.

        # in order to display the correct verify state in state=final, we have
        # to refresh the package list and then recalculate the verify state.
        self.RefreshPackages()
        for pkg in packages:
            states[pkg] = self.VerifyPackage(pkg, [])

    # This is shamelessly ripped from the YUMng plugin.
    def FindExtraPackages(self):
        """Find extra packages."""
        self.logger.debug("Zypper: Begin FindExtraPackages")
        packages = [e.get('name') for e in self.getSupportedEntries()]
        extras = []

        for pkg in list(self.installed.keys()):
            if pkg not in packages:
                entry = Bcfg2.Client.XML.Element('Package', name=pkg,
                                                 type=self.pkgtype)
                self.logger.debug("Zypper: FindExtraPkg: %s" % pkg)
                for i in self.installed[pkg]:
                    inst = Bcfg2.Client.XML.SubElement(entry,
                                                       'Instance',
                                                       version=i['version'],
                                                       release=i['release'],
                                                       arch=i['arch'])
                extras.append(entry)
        return extras
        self.logger.debug("Zypper: End FindExtraPackages")

    def VerifyPath(self, entry, _):
        """Do nothing here since we only verify Path type=ignore."""
        return True
