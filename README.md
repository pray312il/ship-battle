# Морской бой

## Запуск приложения Морской бой

```
docker compose up --build -d
```

## Запуск тестов
```
docker compose exec app python -m pytest -v
```

## Документация API (Swagger)
### http://localhost:8000/docs