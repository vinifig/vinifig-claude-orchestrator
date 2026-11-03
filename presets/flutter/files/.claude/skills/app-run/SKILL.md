---
name: app-run
description: Run the Flutter app on a simulator, emulator or desktop for validation — finds booted devices, picks the flavor and target, starts `flutter run` in the background and reports how to take screenshots. Use when asked to run, launch or open the app, or before /ui-validate on a Flutter screen.
argument-hint: "[flavor] [device]"
---

# Run the app

Args: $ARGUMENTS

## Current state
- Devices: !`flutter devices 2>/dev/null | tail -n +2 | head -8`
- Running: !`ps aux | grep '[f]lutter run' | awk '{print $2}' | head -3`

1. Pick the device: the one named in the args; else a booted iOS simulator, else an Android emulator, else `macos`. None booted: `open -a Simulator` (Mac) or `flutter emulators --launch <id>` and wait for it.
2. Flavor and target: the arg (e.g. `development`), else the default in the README or `.vscode/launch.json`. Command: `flutter run -d <device> [--flavor <f>] [-t lib/main_<f>.dart]`.
3. Run it in the background, writing the log to the scratchpad; wait for "Flutter run key commands" or the VM service URI in the log.
4. Report the device, flavor and how to capture: `xcrun simctl io booted screenshot <file>` (iOS) or `adb exec-out screencap -p > <file>` (Android). Hot reload: send `r` to the process; stop with `q`.

Never run release/store builds or uploads here; those need the approver.
