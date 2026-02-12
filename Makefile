# Makefile para Dev Peace

.PHONY: install install-global service-linux service-macos clean

install:
	pip install -e .

install-global:
	./scripts/install-global.sh

service-linux:
	./scripts/install-service.sh

service-macos:
	./scripts/install-service-macos.sh

# Detecta OS e instala o serviço apropriado
service:
	@if [ "$$(uname)" = "Darwin" ]; then \
		make service-macos; \
	else \
		make service-linux; \
	fi

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
