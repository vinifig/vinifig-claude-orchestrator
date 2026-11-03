# Flutter: how to show what changed

| What | How |
|---|---|
| App on a simulator | `/app-run` (picks a booted simulator/emulator; flavor as argument) |
| Components | Widgetbook (`flutter run -t widgetbook/main.dart -d macos` or the project's target) |
| Goldens | `flutter test --tags golden` (or the golden files of the changed widgets) |

Screenshots: iOS `xcrun simctl io booted screenshot <file>.png`; Android `adb exec-out screencap -p > <file>.png`. Matrix: one phone per platform (e.g. iPhone 15 and Pixel 7), one tablet when the layout is adaptive, light and dark (`xcrun simctl ui booted appearance dark` / `adb shell cmd uimode night yes`), and the largest text size for screens with text-heavy layouts.
