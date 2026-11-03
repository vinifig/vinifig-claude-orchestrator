# Flutter rules for code-implement

- Follow the existing structure and state management; new screens = View + ViewModel/Notifier + immutable state.
- No logic in `build`; no `setState` for data that belongs to the view model.
- After changing annotated models or providers: `dart run build_runner build --delete-conflicting-outputs`; commit the generated files only if the repository already commits them.
- Theme and tokens only (no `Color(0xFF...)` in widgets); strings through l10n (`AppLocalizations`), new keys in the ARB files.
- `const` constructors where possible; dispose controllers and subscriptions.
- Gates: `dart format --output=none --set-exit-if-changed lib test`, `flutter analyze` (zero issues), `flutter test`.
