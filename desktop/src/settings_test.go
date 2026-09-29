package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadSettingsMigratesLegacyPreventSleepMac(t *testing.T) {
	temp := t.TempDir()
	t.Setenv("OCTOP_HOME", temp)
	if err := os.WriteFile(
		filepath.Join(temp, "desktop-settings.json"),
		[]byte(`{"preventSleepMac":true}`),
		0o644,
	); err != nil {
		t.Fatal(err)
	}

	if !loadSettings().PreventSleep {
		t.Fatal("legacy preventSleepMac should migrate to preventSleep")
	}
}

// setFakeHome points os.UserHomeDir() at a scratch dir on every platform.
func setFakeHome(t *testing.T) string {
	t.Helper()
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)
	return home
}

func clearHomeEnv(t *testing.T) {
	t.Helper()
	t.Setenv(envHome, "")
	t.Setenv(legacyEnvHome, "")
}

func TestOctopHomePrefersMingdianHomeEnv(t *testing.T) {
	setFakeHome(t)
	clearHomeEnv(t)
	t.Setenv(legacyEnvHome, filepath.Join("legacy", "env"))
	t.Setenv(envHome, filepath.Join("primary", "env"))

	if got := octopHome(); got != filepath.Join("primary", "env") {
		t.Fatalf("octopHome() = %q, want MINGDIAN_HOME to win", got)
	}
}

func TestOctopHomeFallsBackToLegacyEnv(t *testing.T) {
	setFakeHome(t)
	clearHomeEnv(t)
	t.Setenv(legacyEnvHome, filepath.Join("legacy", "env"))

	if got := octopHome(); got != filepath.Join("legacy", "env") {
		t.Fatalf("octopHome() = %q, want OCTOP_HOME", got)
	}
}

func TestOctopHomePrefersExistingMingdianDir(t *testing.T) {
	home := setFakeHome(t)
	clearHomeEnv(t)
	mustMkdir(t, filepath.Join(home, homeDirName))
	mustMkdir(t, filepath.Join(home, legacyHomeDirName))

	if got := octopHome(); got != filepath.Join(home, homeDirName) {
		t.Fatalf("octopHome() = %q, want ~/.mingdian", got)
	}
}

func TestOctopHomeKeepsLegacyDirWhenOnlyItExists(t *testing.T) {
	home := setFakeHome(t)
	clearHomeEnv(t)
	mustMkdir(t, filepath.Join(home, legacyHomeDirName))

	if got := octopHome(); got != filepath.Join(home, legacyHomeDirName) {
		t.Fatalf("octopHome() = %q, want existing ~/.octop", got)
	}
}

func TestOctopHomeDefaultsToMingdianOnFreshInstall(t *testing.T) {
	home := setFakeHome(t)
	clearHomeEnv(t)

	if got := octopHome(); got != filepath.Join(home, homeDirName) {
		t.Fatalf("octopHome() = %q, want ~/.mingdian for a fresh install", got)
	}
}

func mustMkdir(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatal(err)
	}
}
