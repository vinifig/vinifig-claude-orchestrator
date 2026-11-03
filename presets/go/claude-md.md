### Go stack

- `gofmt`, `go vet` and `go test -race ./...` before saying done; `golangci-lint run` when the repo has a config.
- Errors wrapped with context (`fmt.Errorf("...: %w", err)`), checked with `errors.Is/As`; no panics in library code.
- `context.Context` first parameter on anything that does I/O; respect cancellation.
