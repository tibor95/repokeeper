
pkgbase=repokeeper
pkgname=repokeeper
pkgver=0.3.0
pkgrel=1
pkgdesc="AUR package repository keeper"
arch=('any')
url="https://github.com/tibor95/repokeeper"
license=('GPL3')
makedepends=()
source=("https://github.com/tibor95/repokeeper.git#commit=1234abcd")
md5sums=('SKIP')

package() {
    install -D -m0755 ${srcdir}/${pkgname}/repokeeper.py ${pkgdir}/usr/bin/repokeeper.py
    install -D -m0666 ${srcdir}/${pkgname}/repokeeper.conf ${pkgdir}/etc/repokeeper.conf
}