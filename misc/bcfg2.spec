%define release 0.2
%define __python python
%{!?py_ver: %define py_ver %(%{__python} -c 'import sys;print(sys.version[0:3])')}
%define pythonversion %{py_ver}
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?_initrddir: %define _initrddir %{_sysconfdir}/rc.d/init.d}

Name:             bcfg2
Version:          1.2.2
Release:          %{release}
Summary:          Configuration management system

%if 0%{?suse_version}
# http://en.opensuse.org/openSUSE:Package_group_guidelines
Group:            System/Management
%else
Group:            Applications/System
%endif
License:          BSD
URL:              http://bcfg2.org
Source0:          ftp://ftp.mcs.anl.gov/pub/bcfg/%{name}-%{version}.tar.gz
%if 0%{?suse_version}
# SUSEs OBS does not understand the id macro below.
BuildRoot:        %{_tmppath}/%{name}-%{version}-%{release}
%else
BuildRoot:        %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
%endif
BuildArch:        noarch

BuildRequires:    python-devel
BuildRequires:    python-lxml
%if 0%{?mandriva_version}
# mandriva seems to behave differently than other distros and needs this explicitly.
BuildRequires:    python-setuptools
%endif
%if 0%{?mandriva_version} == 201100
# mandriva 2011 has multiple providers for libsane, so (at least when building on OBS)
# one must be chosen explicitly:
# "have choice for libsane.so.1 needed by python-imaging: libsane1 sane-backends-iscan"
BuildRequires:    libsane1
%endif

# %{rhel} wasn't set before rhel 6.  so this checks for old RHEL
# %systems (and potentially very old Fedora systems, too)
%if "%{_vendor}" == "redhat" && 0%{?rhel} < 6 && 0%{?fedora} == 0
BuildRequires:    python-sphinx10
# the python-sphinx10 package doesn't set sys.path correctly, so we
# have to do it for them
%define pythonpath %(find /usr/lib/python%{py_ver}/site-packages -name %Sphinx*.egg)
%else
BuildRequires:    python-sphinx >= 0.6
%endif

Requires:         python-nose
Requires:         python-lxml >= 0.9
%if 0%{?rhel_version}
# the debian init script needs redhat-lsb.
# iff we switch to the redhat one, this might not be needed anymore.
Requires:         redhat-lsb
%endif
%if "%{_vendor}" != "redhat"
# fedora and rhel (and possibly other distros) do not know this tag.
Recommends:       cron
%endif

%description
Bcfg2 helps system administrators produce a consistent, reproducible,
and verifiable description of their environment, and offers
visualization and reporting tools to aid in day-to-day administrative
tasks. It is the fifth generation of configuration management tools
developed in the Mathematics and Computer Science Division of Argonne
National Laboratory.

It is based on an operational model in which the specification can be
used to validate and optionally change the state of clients, but in a
feature unique to bcfg2 the client's response to the specification can
also be used to assess the completeness of the specification. Using
this feature, bcfg2 provides an objective measure of how good a job an
administrator has done in specifying the configuration of client
systems. Bcfg2 is therefore built to help administrators construct an
accurate, comprehensive specification.

Bcfg2 has been designed from the ground up to support gentle
reconciliation between the specification and current client states. It
is designed to gracefully cope with manual system modifications.

Finally, due to the rapid pace of updates on modern networks, client
systems are constantly changing; if required in your environment,
Bcfg2 can enable the construction of complex change management and
deployment strategies.

This package includes the Bcfg2 client software.

%package server
Version:          1.2.2
Summary:          Bcfg2 Server
%if 0%{?suse_version}
Group:            System/Management
%else
Group:            System Tools
%endif
Requires:         bcfg2
%if "%{py_ver}" < "2.6"
Requires:         python-ssl
%endif
Requires:         python-lxml >= 1.2.1
%if "%{_vendor}" == "redhat"
Requires:         gamin-python
%endif
Requires:         /usr/sbin/sendmail
Requires:         /usr/bin/openssl

%description server
Bcfg2 helps system administrators produce a consistent, reproducible,
and verifiable description of their environment, and offers
visualization and reporting tools to aid in day-to-day administrative
tasks. It is the fifth generation of configuration management tools
developed in the Mathematics and Computer Science Division of Argonne
National Laboratory.

It is based on an operational model in which the specification can be
used to validate and optionally change the state of clients, but in a
feature unique to bcfg2 the client's response to the specification can
also be used to assess the completeness of the specification. Using
this feature, bcfg2 provides an objective measure of how good a job an
administrator has done in specifying the configuration of client
systems. Bcfg2 is therefore built to help administrators construct an
accurate, comprehensive specification.

Bcfg2 has been designed from the ground up to support gentle
reconciliation between the specification and current client states. It
is designed to gracefully cope with manual system modifications.

Finally, due to the rapid pace of updates on modern networks, client
systems are constantly changing; if required in your environment,
Bcfg2 can enable the construction of complex change management and
deployment strategies.

This package includes the Bcfg2 server software.

%package doc
Summary:          Configuration management system documentation
%if 0%{?suse_version}
Group:            Documentation/HTML
%else
Group:            Documentation
%endif

%description doc
Bcfg2 helps system administrators produce a consistent, reproducible,
and verifiable description of their environment, and offers
visualization and reporting tools to aid in day-to-day administrative
tasks. It is the fifth generation of configuration management tools
developed in the Mathematics and Computer Science Division of Argonne
National Laboratory.

It is based on an operational model in which the specification can be
used to validate and optionally change the state of clients, but in a
feature unique to bcfg2 the client's response to the specification can
also be used to assess the completeness of the specification. Using
this feature, bcfg2 provides an objective measure of how good a job an
administrator has done in specifying the configuration of client
systems. Bcfg2 is therefore built to help administrators construct an
accurate, comprehensive specification.

Bcfg2 has been designed from the ground up to support gentle
reconciliation between the specification and current client states. It
is designed to gracefully cope with manual system modifications.

Finally, due to the rapid pace of updates on modern networks, client
systems are constantly changing; if required in your environment,
Bcfg2 can enable the construction of complex change management and
deployment strategies.

This package includes the Bcfg2 documentation.

%package web
Version:          1.2.2
Summary:          Bcfg2 Web Reporting Interface
%if 0%{?suse_version}
Group:            System/Management
%else
Group:            System Tools
%endif
Requires:         bcfg2-server
Requires:         httpd,Django
%if "%{_vendor}" == "redhat"
Requires:         mod_wsgi
%define apache_conf %{_sysconfdir}/httpd
%else
Requires:         apache2-mod_wsgi
%define apache_conf %{_sysconfdir}/apache2
%endif

%description web
Bcfg2 helps system administrators produce a consistent, reproducible,
and verifiable description of their environment, and offers
visualization and reporting tools to aid in day-to-day administrative
tasks. It is the fifth generation of configuration management tools
developed in the Mathematics and Computer Science Division of Argonne
National Laboratory.

It is based on an operational model in which the specification can be
used to validate and optionally change the state of clients, but in a
feature unique to bcfg2 the client's response to the specification can
also be used to assess the completeness of the specification. Using
this feature, bcfg2 provides an objective measure of how good a job an
administrator has done in specifying the configuration of client
systems. Bcfg2 is therefore built to help administrators construct an
accurate, comprehensive specification.

Bcfg2 has been designed from the ground up to support gentle
reconciliation between the specification and current client states. It
is designed to gracefully cope with manual system modifications.

Finally, due to the rapid pace of updates on modern networks, client
systems are constantly changing; if required in your environment,
Bcfg2 can enable the construction of complex change management and
deployment strategies.

This package includes the Bcfg2 reports web frontend.

%prep
%setup -q -n %{name}-%{version}

%build
%{__python}%{pythonversion} setup.py build
%{__python}%{pythonversion} setup.py build_dtddoc

%{?pythonpath: export PYTHONPATH="%{pythonpath}"}
%{__python}%{pythonversion} setup.py build_sphinx

%install
rm -rf %{buildroot}
%{__python}%{pythonversion} setup.py install --root=%{buildroot} --record=INSTALLED_FILES --prefix=/usr
%{__install} -d %{buildroot}%{_bindir}
%{__install} -d %{buildroot}%{_sbindir}
%{__install} -d %{buildroot}%{_initrddir}
%{__install} -d %{buildroot}%{_sysconfdir}/default
%{__install} -d %{buildroot}%{_sysconfdir}/cron.daily
%{__install} -d %{buildroot}%{_sysconfdir}/cron.hourly
%{__install} -d %{buildroot}%{_prefix}/lib/bcfg2
mkdir -p %{buildroot}%{_defaultdocdir}/bcfg2-doc-%{version}
%if 0%{?suse_version}
%{__install} -d %{buildroot}/var/adm/fillup-templates
%endif

%{__mv} %{buildroot}%{_bindir}/bcfg2* %{buildroot}%{_sbindir}
%{__install} -m 755 debian/bcfg2.init %{buildroot}%{_initrddir}/bcfg2
%{__install} -m 755 debian/bcfg2-server.init %{buildroot}%{_initrddir}/bcfg2-server
%{__install} -m 755 debian/bcfg2.default %{buildroot}%{_sysconfdir}/default/bcfg2
%{__install} -m 755 debian/bcfg2-server.default %{buildroot}%{_sysconfdir}/default/bcfg2-server
%{__install} -m 755 debian/bcfg2.cron.daily %{buildroot}%{_sysconfdir}/cron.daily/bcfg2
%{__install} -m 755 debian/bcfg2.cron.hourly %{buildroot}%{_sysconfdir}/cron.hourly/bcfg2
%{__install} -m 755 tools/bcfg2-cron %{buildroot}%{_prefix}/lib/bcfg2/bcfg2-cron
%if 0%{?suse_version}
%{__install} -m 755 debian/bcfg2.default %{buildroot}/var/adm/fillup-templates/sysconfig.bcfg2
%{__install} -m 755 debian/bcfg2-server.default %{buildroot}/var/adm/fillup-templates/sysconfig.bcfg2-server
ln -s %{_initrddir}/bcfg2 %{buildroot}%{_sbindir}/rcbcfg2
ln -s %{_initrddir}/bcfg2-server %{buildroot}%{_sbindir}/rcbcfg2-server
%endif

mv build/sphinx/html/* %{buildroot}%{_defaultdocdir}/bcfg2-doc-%{version}
mv build/dtd %{buildroot}%{_defaultdocdir}/bcfg2-doc-%{version}/

%{__install} -d %{buildroot}%{apache_conf}/conf.d
%{__install} -m 644 misc/apache/bcfg2.conf %{buildroot}%{apache_conf}/conf.d/wsgi_bcfg2.conf

%{__mkdir_p} %{buildroot}%{_localstatedir}/cache/bcfg2

%clean
[ "%{buildroot}" != "/" ] && %{__rm} -rf %{buildroot} || exit 2

%files
%defattr(-,root,root,-)
%{_sbindir}/bcfg2
%dir %{python_sitelib}/Bcfg2
%{python_sitelib}/Bcfg2/*.py*
%dir %{python_sitelib}/Bcfg2/Client
%{python_sitelib}/Bcfg2/Client/*
%{_mandir}/man1/bcfg2.1*
%{_mandir}/man5/bcfg2.conf.5*
%{_initrddir}/bcfg2
%config(noreplace) %{_sysconfdir}/default/bcfg2
%{_sysconfdir}/cron.hourly/bcfg2
%{_sysconfdir}/cron.daily/bcfg2
%{_prefix}/lib/bcfg2/bcfg2-cron
%{_localstatedir}/cache/bcfg2
%if 0%{?suse_version}
%{_sbindir}/rcbcfg2
%config(noreplace) /var/adm/fillup-templates/sysconfig.bcfg2
%endif
%if 0%{?mandriva_version} == 0
# mandriva (on OBS, at least) can't handle %ghost
%ghost %attr(0600,root,root) %{_sysconfdir}/bcfg2.conf
%endif

%files server
%defattr(-,root,root,-)
%{_initrddir}/bcfg2-server
%dir %{python_sitelib}/Bcfg2
%{python_sitelib}/Bcfg2/Server

%if "%{pythonversion}" >= "2.5"
%{python_sitelib}/*egg-info
%endif

%dir %{_datadir}/bcfg2
%{_datadir}/bcfg2/Hostbase
%{_datadir}/bcfg2/schemas
%{_datadir}/bcfg2/xsl-transforms
%config(noreplace) %{_sysconfdir}/default/bcfg2-server
%{_sbindir}/bcfg2-admin
%{_sbindir}/bcfg2-build-reports
%{_sbindir}/bcfg2-info
%{_sbindir}/bcfg2-ping-sweep
%{_sbindir}/bcfg2-lint
%{_sbindir}/bcfg2-repo-validate
%{_sbindir}/bcfg2-reports
%{_sbindir}/bcfg2-server
%{_sbindir}/bcfg2-yum-helper
%{_sbindir}/bcfg2-test
%if 0%{?suse_version}
%{_sbindir}/rcbcfg2-server
%config(noreplace) /var/adm/fillup-templates/sysconfig.bcfg2-server
%endif

%{_mandir}/man5/bcfg2-lint.conf.5*
%{_mandir}/man8/*.8*
%dir %{_prefix}/lib/bcfg2
%if 0%{?mandriva_version} == 0
%ghost %attr(0600,root,root) %{_sysconfdir}/bcfg2.conf
%endif

%files doc
%defattr(-,root,root,-)
%doc %{_defaultdocdir}/bcfg2-doc-%{version}

%files web
%defattr(-,root,root,-)
%{_datadir}/bcfg2/reports.wsgi
%{_datadir}/bcfg2/site_media
%dir %{apache_conf}
%dir %{apache_conf}/conf.d
%config(noreplace) %{apache_conf}/conf.d/wsgi_bcfg2.conf
%if 0%{?mandriva_version} == 0
%ghost %attr(0600,root,root) %{_sysconfdir}/bcfg2-web.conf
%endif

%post server
# enable daemon on first install only (not on update).
if [ $1 -eq 1 ]; then
%if 0%{?suse_version}
  %fillup_and_insserv -f bcfg2-server
%else
  /sbin/chkconfig --add bcfg2-server
%endif
fi

%preun
%if 0%{?suse_version}
# stop on removal (not on update).
if [ $1 -eq 0 ]; then
  %stop_on_removal bcfg2
fi
%endif

%preun server
%if 0%{?suse_version}
if [ $1 -eq 0 ]; then
  %stop_on_removal bcfg2-server
fi
%endif

%postun
%if 0%{?suse_version}
if [ $1 -eq 0 ]; then
  %insserv_cleanup
fi
%endif

%postun server
%if 0%{?suse_version}
if [ $1 -eq 0 ]; then
  # clean up on removal.
  %insserv_cleanup
fi
%endif

%changelog
* Sat Feb 18 2012 Christopher 'm4z' Holm <686f6c6d@googlemail.com> 1.2.1
- Added Fedora and Mandriva compatibilty (for Open Build Service).
- Added missing dependency redhat-lsb.

* Tue Feb 14 2012 Christopher 'm4z' Holm <686f6c6d@googlemail.com> 1.2.1
- Added openSUSE compatibility.
- Various changes to satisfy rpmlint.

* Thu Jan 27 2011 Chris St. Pierre <stpierreca@ornl.gov> 1.2.0pre1-0.0
- Added -doc sub-package

* Mon Jun 21 2010 Fabian Affolter <fabian@bernewireless.net> - 1.1.0rc3-0.1
- Changed source0 in order that it works with spectool

* Fri Feb 2 2007 Mike Brady <mike.brady@devnull.net.nz> 0.9.1
- Removed use of _libdir due to Red Hat x86_64 issue.

* Fri Dec 22 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-5
- Server needs client library files too so put them in main package

* Wed Dec 20 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-4
- Yes, actually we need to require openssl

* Wed Dec 20 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-3
- Don't generate SSL cert in post script, it only needs to be done on
  the server and is handled by the bcfg2-admin tool.
- Move the /etc/bcfg2.key file to the server package
- Don't install a sample copy of the config file, just ghost it
- Require gamin-python for the server package
- Don't require openssl
- Make the client a separate package so you don't have to have the
  client if you don't want it

* Wed Dec 20 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-2
- Add more documentation

* Mon Dec 18 2006 Jeffrey C. Ollie <jeff@ocjtech.us> - 0.8.7.1-1
- First version for Fedora Extras

* Fri Sep 15 2006 Narayan Desai <desai@mcs.anl.gov> - 0.8.4-1
- Initial log

