PREFIX ?= $(HOME)/.local

.PHONY: install uninstall test

install:
	install -D -m 755 wmbluetooth $(PREFIX)/bin/wmbluetooth

uninstall:
	rm -f $(PREFIX)/bin/wmbluetooth

test:
	python3 -m unittest discover -s tests -v
