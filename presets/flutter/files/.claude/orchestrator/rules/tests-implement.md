# Flutter rules for tests-implement

- Unit tests (`test/`) for domain and view models with mocktail/mockito, whichever the project uses; `ProviderContainer` with overrides for Riverpod.
- Widget tests with `pumpWidget` of the screen wrapped in the app's test harness (theme, l10n, providers overridden); find by key, text or semantics label.
- Goldens for visual components (`matchesGoldenFile`), updated only when the plan says which visual change is intended (`flutter test --update-goldens <file>`).
- Flows in `integration_test/` run on a simulator/emulator.
- Fixed clocks (`clock` package or injected), no real network (mock the data source).
- Run one file: `flutter test test/<path>_test.dart`.
