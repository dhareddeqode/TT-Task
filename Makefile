setup:
	docker compose up

start:
	docker compose up

stop:
	docker compose down

cleanup:
	docker compose down -v

createsupseruser:
	docker compose exec -it web python manage.py createsuperuser --email=admin@test.com --username=admin

runtests:
	docker compose -f docker-compose.test.yaml up --abort-on-container-exit --exit-code-from web-test
