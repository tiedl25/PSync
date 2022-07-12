# This is an example PKGBUILD file. Use this as a start to creating your own,
# and remove these comments. For more information, see 'man PKGBUILD'.
# NOTE: Please fill out the license field for your package! If it is unknown,
# then please put 'unknown'.

# Maintainer: Your Name <youremail@domain.com>
pkgname='psync'
_name=${pkgname#python-}#Note that a custom _name variable is used instead of pkgname since Python packages are generally prefixed with python-.
pkgver=0.0.1
pkgrel=1
epoch=
pkgdesc="Implementation of Rclone and Inotify to perform file syncing between local and remote by monitoring file changes."
arch=('x86_64')
url="https://github.com/tiedl25/PSync"
license=('GPL')
groups=()
depends=(rclone)
makedepends=(git python-build python-installer python-wheel)
source=("psync-0.0.1::git+https://github.com/tiedl25/PSync.git")
noextract=()
md5sums=('SKIP')
validpgpkeys=()



#pkgver() {
#	cd "$pkgname"
#	git describe --long | sed 's/\([⁻]*-g\)/r\1/;s/-/./g'
#}

build() {
    cd "psync-0.0.1"
    python -m build --wheel --no-isolation
}

package() {
    cd "psync-0.0.1"
    python -m installer --destdir="$pkgdir" dist/*.whl
}
