.PHONY: native test-native test lint

native:
	mkdir -p bin
	cd native && go build -trimpath -o ../bin/mgwiki-scan ./cmd/mgwiki-scan

test-native:
	cd native && go vet ./... && go test ./...

test:
	python3 -m pytest

lint:
	ruff check mgwiki_editor tests
	ruff format --check mgwiki_editor tests
