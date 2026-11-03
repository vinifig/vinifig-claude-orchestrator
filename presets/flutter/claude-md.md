### Flutter stack

- Run `dart format`, `flutter analyze` and `flutter test` before saying done (the gates in `.claude/orchestrator.json`).
- Generated code (`*.g.dart`, `*.freezed.dart`) is regenerated with `dart run build_runner build --delete-conflicting-outputs`, never edited by hand.
- Signing files (`key.properties`, keystores, provisioning profiles, `.p8`) are secrets: never read, copy or commit them. Store releases (`flutter build ipa/appbundle` uploads, `fastlane` lanes that publish) need the approver's written yes.
