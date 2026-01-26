.PHONY: run migrate docker-build docker-up docker-down docker-migrate

run:
	uvicorn app.main:app --reload

migrate:
	alembic upgrade head

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-migrate:
	docker-compose exec app alembic upgrade head