## START: Set by rpmautospec
## (rpmautospec version 0.6.5)
## RPMAUTOSPEC: autorelease, autochangelog
%define autorelease(e:s:pb:n) %{?-p:0.}%{lua:
    release_number = 8;
    base_release_number = tonumber(rpm.expand("%{?-b*}%{!?-b:1}"));
    print(release_number + base_release_number - 1);
}%{?-e:.%{-e*}}%{?-s:.%{-s*}}%{!?-n:%{?dist}}
## END: Set by rpmautospec

%global forgeurl  https://pagure.io/go-rpm-macros
Version:   3.6.0
%forgemeta

#https://src.fedoraproject.org/rpms/redhat-rpm-config/pull-request/51
%global _spectemplatedir %{_datadir}/rpmdevtools/fedora
%global _docdir_fmt     %{name}

# Master definition that will be written to macro files
%global golang_arches_future x86_64 %{arm} aarch64 ppc64le s390x riscv64
%global golang_arches   %{ix86} %{golang_arches_future}
%global gccgo_arches    %{mips}
%if 0%{?rhel} >= 9
%global golang_arches   x86_64 aarch64 ppc64le s390x
%endif
%if 0%{?rhel} >= 10
%global golang_arches   x86_64 aarch64 ppc64le s390x riscv64
%endif
# Go sources can contain arch-specific files and our macros will package the
# correct files for each architecture. Therefore, move gopath to _libdir and
# make Go devel packages archful
%global gopath          %{_datadir}/gocode

# whether to bundle golist or require it as a dependency
%if 0%{?rhel}
%ifarch %{golang_arches} %{gccgo_arches}
%global bundle_golist 1
%endif
%endif

%global golist_version 0.10.4
%if 0%{?bundle_golist}
%global golist_builddir golist-%{golist_version}
%global golist_goipath pagure.io/golist
# where to bundle the golist executable
%global golist_execdir %{_libexecdir}/go-rpm-macros
# define gobuild to avoid this package requiring itself to build
%undefine _auto_set_build_flags
%global _dwz_low_mem_die_limit 0
%define gobuild(o:) GO111MODULE=on go build -buildmode pie -compiler gc -tags="rpm_crashtraceback ${GO_BUILDTAGS-${BUILDTAGS-}}" -a -v -x -ldflags "${GO_LDFLAGS-${LDFLAGS-}}  -B 0x$(echo "%{name}-%{version}-%{release}-${SOURCE_DATE_EPOCH:-}" | sha1sum | cut -d ' ' -f1) -compressdwarf=false -linkmode=external -extldflags '%{build_ldflags}'"  %{?**};
%else
%global debug_package %{nil}
%endif

Name:      go-rpm-macros
Release:   %autorelease
Summary:   Build-stage rpm automation for Go packages

License:   GPL-3.0-or-later
URL:       %{forgeurl}
Source:    %{forgesource}
Source1:   https://pagure.io/golist/archive/v%{golist_version}/golist-%{golist_version}.tar.gz
# vendored dependency tarball, to create:
# tar xf golist-%%{golist_version}.tar.gz ; pushd golist-%%{golist_version} ; \
# go mod init %%{golist_goipath} && go mod tidy && go mod vendor && \
# tar Jcf ../golist-%%{golist_version}-vendor.tar.xz go.mod go.sum vendor/ ; popd
Source2:   golist-%{golist_version}-vendor.tar.xz

Requires:  go-srpm-macros = %{version}-%{release}
Requires:  go-filesystem  = %{version}-%{release}

%if 0%{?bundle_golist}
BuildRequires: golang
Provides:  bundled(golist) = %{golist_version}
%else
Requires:  golist
%endif

%ifarch %{golang_arches}
Requires:  golang
Provides:  compiler(golang)
Provides:  compiler(go-compiler) = 2
Obsoletes: go-compilers-golang-compiler < %{version}-%{release}
%endif

%ifarch %{gccgo_arches}
Requires:  gcc-go
Provides:  compiler(gcc-go)
Provides:  compiler(go-compiler) = 1
Obsoletes: go-compilers-gcc-go-compiler < %{version}-%{release}
%endif

%description
This package provides build-stage rpm automation to simplify the creation of Go
language (golang) packages.

It does not need to be included in the default build root: go-srpm-macros will
pull it in for Go packages only.

%package -n go-srpm-macros
Summary:   Source-stage rpm automation for Go packages
BuildArch: noarch
Requires:  redhat-rpm-config

%description -n go-srpm-macros
This package provides SRPM-stage rpm automation to simplify the creation of Go
language (golang) packages.

It limits itself to the automation subset required to create Go SRPM packages
and needs to be included in the default build root.

The rest of the automation is provided by the go-rpm-macros package, that
go-srpm-macros will pull in for Go packages only.

%package -n go-filesystem
Summary:   Directories used by Go packages
License:   LicenseRef-Fedora-Public-Domain

%description -n go-filesystem
This package contains the basic directory layout used by Go packages.

%package -n go-rpm-templates
Summary:   RPM spec templates for Go packages
License:   MIT
# go-rpm-macros only exists on some architectures, so this package cannot be noarch
Requires:  go-rpm-macros = %{version}-%{release}
#https://src.fedoraproject.org/rpms/redhat-rpm-config/pull-request/51
#Requires:  redhat-rpm-templates

%description -n go-rpm-templates
This package contains documented rpm spec templates showcasing how to use the
macros provided by go-rpm-macros to create Go packages.

%prep
%autosetup -p1 %{forgesetupargs} -a1
%writevars -f rpm/macros.d/macros.go-srpm golang_arches golang_arches_future gccgo_arches gopath
for template in templates/rpm/*\.spec ; do
  target=$(echo "${template}" | sed "s|^\(.*\)\.spec$|\1-bare.spec|g")
  grep -v '^#' "${template}" > "${target}"
  touch -r "${template}" "${target}"
done

# unpack golist and vendor deps
%if 0%{?bundle_golist}
tar -C %{golist_builddir} -xf %{SOURCE2}
cp %{golist_builddir}/LICENSE LICENSE-golist
%endif

%build
# build golist
%if 0%{?bundle_golist}
pushd %{golist_builddir}
for cmd in cmd/* ; do
  %gobuild -o bin/$(basename $cmd) ./$cmd
done
popd
%endif

%install
install -m 0755 -vd   %{buildroot}%{rpmmacrodir}

install -m 0755 -vd   %{buildroot}%{_rpmluadir}/fedora/srpm
install -m 0644 -vp   rpm/lua/srpm/*lua \
                      %{buildroot}%{_rpmluadir}/fedora/srpm

%ifarch %{golang_arches} %{gccgo_arches}
# Some of those probably do not work with gcc-go right now
# This is not intentional, but mips is not a primary Fedora architecture
# Patches and PRs are welcome

install -m 0755 -vd   %{buildroot}%{gopath}/src

install -m 0755 -vd   %{buildroot}%{_spectemplatedir}

install -m 0644 -vp   templates/rpm/*spec \
                      %{buildroot}%{_spectemplatedir}

install -m 0755 -vd   %{buildroot}%{_bindir}
install -m 0755 bin/* %{buildroot}%{_bindir}

install -m 0644 -vp   rpm/macros.d/macros.go-*rpm* \
                      %{buildroot}%{rpmmacrodir}
install -m 0755 -vd   %{buildroot}%{_rpmluadir}/fedora/rpm
install -m 0644 -vp   rpm/lua/rpm/*lua \
                      %{buildroot}%{_rpmluadir}/fedora/rpm
install -m 0755 -vd   %{buildroot}%{_rpmconfigdir}/fileattrs
install -m 0644 -vp   rpm/fileattrs/*.attr \
                      %{buildroot}%{_rpmconfigdir}/fileattrs/
install -m 0755 -vp   rpm/*\.{prov,deps} \
                      %{buildroot}%{_rpmconfigdir}/
%else
install -m 0644 -vp   rpm/macros.d/macros.go-srpm \
                      %{buildroot}%{rpmmacrodir}
%endif

%ifarch %{golang_arches}
install -m 0644 -vp   rpm/macros.d/macros.go-compilers-golang{,-pie} \
                      %{buildroot}%{_rpmconfigdir}/macros.d/
%endif

%ifarch %{gccgo_arches}
install -m 0644 -vp   rpm/macros.d/macros.go-compilers-gcc \
                      %{buildroot}%{_rpmconfigdir}/macros.d/
%endif

# install golist
%if 0%{?bundle_golist}
install -m 0755 -vd                     %{buildroot}%{golist_execdir}
install -m 0755 -vp %{golist_builddir}/bin/* %{buildroot}%{golist_execdir}/
sed -i "s,golist ,%{golist_execdir}/golist ,g" \
  %{buildroot}%{_bindir}/go-rpm-integration \
  %{buildroot}%{_rpmconfigdir}/gosymlink.deps \
  %{buildroot}%{_rpmmacrodir}/macros.go-rpm
%endif

%ifarch %{golang_arches} %{gccgo_arches}
%files
%license LICENSE.txt
%if %{defined bundle_golist}
%license LICENSE-golist %{golist_builddir}/vendor/modules.txt
%endif
%doc README.md
%{_bindir}/*
%{_rpmconfigdir}/fileattrs/*.attr
%{_rpmconfigdir}/*.prov
%{_rpmconfigdir}/*.deps
%{_rpmmacrodir}/macros.go-rpm*
%{_rpmmacrodir}/macros.go-compiler*
%{_rpmluadir}/fedora/rpm/*.lua
# package golist
%if 0%{?bundle_golist}
%{golist_execdir}/golist
%endif


%files -n go-rpm-templates
%license LICENSE-templates.txt
%doc README.md
# https://src.fedoraproject.org/rpms/redhat-rpm-config/pull-request/51
%dir %{dirname:%{_spectemplatedir}}
%dir %{_spectemplatedir}
%{_spectemplatedir}/*.spec

%files -n go-filesystem
%dir %{gopath}
%dir %{gopath}/src
%endif

# we only build go-srpm-macros on all architectures
%files -n go-srpm-macros
%license LICENSE.txt
%doc README.md
%{_rpmmacrodir}/macros.go-srpm
%{_rpmluadir}/fedora/srpm/*.lua

%changelog
## START: Generated by rpmautospec
* Fri Apr 17 2026 Alejandro Sáez <asm@redhat.com> - 3.6.0-8
- Rebuild with latest Go

* Tue Mar 03 2026 dbenoit <dbenoit@redhat.com> - 3.6.0-7
- Rebuild with latest Go

* Thu Apr 03 2025 Edjunior Machado <emachado@redhat.com> - 3.6.0-6
- Update CI support

* Thu Mar 13 2025 Andrea Bolognani <abologna@redhat.com> - 3.6.0-5
- Add riscv64 to golang_arches for RHEL 10+

* Tue Oct 29 2024 Troy Dawson <tdawson@redhat.com> - 3.6.0-4
- Bump release for October 2024 mass rebuild:

* Fri Sep 27 2024 Alejandro Sáez <asm@redhat.com> - 3.6.0-3
- Delete rpminspect.yaml

* Fri Sep 27 2024 Yaakov Selkowitz <yselkowi@redhat.com> - 3.6.0-2
- Enable debuginfo

* Wed Jul 24 2024 Alejandro Sáez <asm@redhat.com> - 3.6.0-1
- Update to 3.6.0

* Wed Jun 26 2024 Edjunior Machado <emachado@redhat.com> - 3.3.0-5
- Add rpminspect.yaml

* Mon Jun 24 2024 Troy Dawson <tdawson@redhat.com> - 3.3.0-4
- Bump release for June 2024 mass rebuild

* Thu May 23 2024 Alejandro Sáez <asm@redhat.com> - 3.3.0-3
- Remove explicit dependency of forge-srpm-macros

* Fri May 03 2024 Edjunior Machado <emachado@redhat.com> - 3.3.0-2
- gating.yaml: Add gating config for rhel-10

* Sun Oct 29 2023 Robert-André Mauchin <zebob.m@gmail.com> - 3.3.0-1
- Update to 3.3.0

* Sun Oct 29 2023 Yaakov Selkowitz <yselkowi@redhat.com> - 3.2.0-9
- Update golist to 0.10.4

* Thu Sep 07 2023 Maxwell G <maxwell@gtmx.me> - 3.2.0-8
- Add explicit dependency on forge-srpm-macros

* Thu Jun 22 2023 Maxwell G <maxwell@gtmx.me> - 3.2.0-7
- Simplify golist tarball unpacking

* Tue Jun 20 2023 Yaakov Selkowitz <yselkowi@redhat.com> - 3.2.0-6
- Bundle golist in RHEL builds

* Mon Apr 24 2023 Edjunior Machado <emachado@redhat.com> - 3.2.0-4
- tests: Fix fmf plan deprecated attributes

* Sun Apr 16 2023 Nianqing Yao <imbearchild@outlook.com> - 3.2.0-3
- Add riscv64 to %%golang_arches

* Thu Jan 19 2023 Fedora Release Engineering <releng@fedoraproject.org> - 3.2.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_38_Mass_Rebuild

* Fri Sep 02 2022 Maxwell G <gotmax@e.email> - 3.2.0-1
- Update to 3.2.0.

* Fri Sep 02 2022 Maxwell G <gotmax@e.email> - 3.1.0-5
- Use %%{_rpmmacrodir} macro

* Tue Aug 09 2022 Maxwell G <gotmax@e.email> - 3.1.0-4
- Use correct SPDX identifier for Public Domain

* Mon Aug 08 2022 Maxwell G <gotmax@e.email> - 3.1.0-3
- Convert top level license to SPDX.

* Mon Aug 08 2022 Maxwell G <gotmax@e.email> - 3.1.0-2
- Stop installing duplicate go-compilers macros

* Mon Aug 08 2022 Maxwell G <gotmax@e.email> - 3.1.0-1
- Update to 3.1.0.

* Fri Jul 29 2022 Maxwell G <gotmax@e.email> - 3.0.15-4
- Add %%%%golang_arches_future macro

* Thu Jul 21 2022 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.15-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_37_Mass_Rebuild

* Thu Jun 02 2022 Miro Hrončok <miro@hroncok.cz> - 3.0.15-2
- Drop ExclusiveArch, always build go-srpm-macros and go-filesystem

* Sun Jan 30 2022 Maxwell G <gotmax@e.email> - 3.0.15-1
- Update to 3.0.15.

* Sat Jan 29 2022 Maxwell G <gotmax@e.email> - 3.0.14-1
- Update to 3.0.14.

* Sat Jan 22 2022 Robert-André Mauchin <zebob.m@gmail.com> - 3.0.13-4
- Fix typo

* Sat Jan 22 2022 Robert-André Mauchin <zebob.m@gmail.com> - 3.0.13-3
- Fix typo

* Sat Jan 22 2022 Robert-André Mauchin <zebob.m@gmail.com> - 3.0.13-2
- Fix archive upload

* Sat Jan 22 2022 Robert-André Mauchin <zebob.m@gmail.com> - 3.0.13-1
- Update to 3.0.13

* Sat Jan 22 2022 Robert-André Mauchin <zebob.m@gmail.com> - 3.0.12-3
- Update to 3.0.12

* Thu Jan 20 2022 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.11-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_36_Mass_Rebuild

* Thu Jul 22 2021 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.11-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild

* Mon May 17 2021 Robert-André Mauchin <zebob.m@gmail.com> - 3.0.11-1
- Update to 3.0.11

* Mon Apr 26 2021 Alejandro Sáez <asm@redhat.com> - 3.0.10-1
- Update to 3.0.10

* Thu Feb 11 2021 Jeff Law  <law@redhat.com> - 3.0.9-3
- Drop 32 bit arches in EL 9 (originally from Petr Sabata)

* Tue Jan 26 2021 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.9-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_34_Mass_Rebuild

* Thu Aug 13 2020 Neal Gompa <ngompa13@gmail.com> - 3.0.9-1
- Update to 3.0.9

* Mon Jul 27 2020 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.8-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Tue Jan 28 2020 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.8-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_32_Mass_Rebuild

* Thu Jul 25 2019 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.8-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Wed Jun 05 2019 Nicolas Mailhot <nim@fedoraproject.org>
- 3.0.8-3
- initial Fedora import, for golist 0.10.0 and redhat-rpm-config 130

## END: Generated by rpmautospec
