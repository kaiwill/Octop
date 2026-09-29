//go:build !production || darwin

package main

// Development builds look for Mingdian-<plat>.zip or Mingdian-portable-<plat>-*.zip
// beside the executable. macOS production copies the zip into Resources as
// Mingdian-<plat>.zip.
var embeddedPortable []byte
