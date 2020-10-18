
pkgbase=repokeeper
pkgname=repokeeper
pkgver=0.3.1
pkgrel=1
pkgdesc="AUR package repository keeper"
arch=('any')
url="https://github.com/tibor95/repokeeper"
license=('GPL3')
makedepends=()
source=("git+https://github.com/tibor95/repokeeper.git#commit=1234abcd")
md5sums=('SKIP')
backup=('etc/repokeeper.conf')

package() {
    cd ${srcdir}/${pkgname}
    python3 setup.py -q install --root="$pkgdir"
    install -D -m0666 ${srcdir}/${pkgname}/repokeeper.conf ${pkgdir}/etc/repokeeper.conf
}
