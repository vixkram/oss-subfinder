.PHONY: build run test

build:
	docker-compose build

run:
	docker-compose up backend postgres massdns-builder

test:
	docker-compose run --rm backend pytest
