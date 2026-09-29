package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"sync"
)

type Locale string

const (
	LocaleZH Locale = "zh"
	LocaleEN Locale = "en"
)

// Mirrors brand.py. Keep in sync with octop/infra/utils/paths.py PathLayout.
const (
	envHome           = "MINGDIAN_HOME"
	legacyEnvHome     = "OCTOP_HOME"
	homeDirName       = ".mingdian"
	legacyHomeDirName = ".octop"
)

// Settings is persisted at ~/.mingdian/desktop-settings.json
type Settings struct {
	Locale         Locale `json:"locale"`
	Autostart      bool   `json:"autostart"`
	MinimizeToTray bool   `json:"minimizeToTray"`
	PreventSleep   bool   `json:"preventSleep"`
	Port           int    `json:"port,omitempty"`
}

func defaultSettings() Settings {
	return Settings{
		Locale:         LocaleEN,
		Autostart:      false,
		MinimizeToTray: true,
		PreventSleep:   false,
		Port:           8088,
	}
}

func isDir(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

// octopHome resolves the data directory with the same priority the Python side
// uses (PathLayout.from_env): MINGDIAN_HOME > OCTOP_HOME > ~/.mingdian >
// ~/.octop, falling back to ~/.mingdian for fresh installs. The ~/.octop probe
// keeps an existing pre-rebrand install on its current data.
func octopHome() string {
	if v := os.Getenv(envHome); v != "" {
		return v
	}
	if v := os.Getenv(legacyEnvHome); v != "" {
		return v
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return homeDirName
	}
	newPath := filepath.Join(home, homeDirName)
	if isDir(newPath) {
		return newPath
	}
	legacyPath := filepath.Join(home, legacyHomeDirName)
	if isDir(legacyPath) {
		return legacyPath
	}
	return newPath
}

func portableDir() string {
	return filepath.Join(octopHome(), "portable")
}

func settingsPath() string {
	return filepath.Join(octopHome(), "desktop-settings.json")
}

type settingsStore struct {
	mu  sync.Mutex
	cur Settings
}

func loadSettings() Settings {
	s := defaultSettings()
	data, err := os.ReadFile(settingsPath())
	if err != nil {
		return s
	}
	_ = json.Unmarshal(data, &s)
	var legacy struct {
		PreventSleepMac bool `json:"preventSleepMac"`
	}
	_ = json.Unmarshal(data, &legacy)
	if !s.PreventSleep {
		s.PreventSleep = legacy.PreventSleepMac
	}
	if s.Port == 0 {
		s.Port = 8088
	}
	if s.Locale != LocaleZH {
		s.Locale = LocaleEN
	}
	return s
}

func (st *settingsStore) get() Settings {
	st.mu.Lock()
	defer st.mu.Unlock()
	return st.cur
}

func (st *settingsStore) save(next Settings) error {
	st.mu.Lock()
	defer st.mu.Unlock()
	if next.Port == 0 {
		next.Port = 8088
	}
	if err := os.MkdirAll(octopHome(), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(next, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(settingsPath(), data, 0o644); err != nil {
		return err
	}
	st.cur = next
	return nil
}

func greenPlat() string {
	osName := runtime.GOOS
	arch := runtime.GOARCH
	switch osName {
	case "darwin":
		osName = "darwin"
	case "windows":
		osName = "windows"
	default:
		osName = "linux"
	}
	switch arch {
	case "arm64":
		arch = "arm64"
	default:
		arch = "amd64"
	}
	return osName + "-" + arch
}
