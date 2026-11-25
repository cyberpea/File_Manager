# Локальный CI/CD-контур (СЗ2)

Локальный конвейер непрерывной интеграции, тестирования, анализа безопасности и
доставки для файлового менеджера. Все шаги выполняются в изолированных
Docker-контейнерах, локальный запуск эмулирует сервер GitHub Actions утилитой
[`nektos/act`](https://nektosact.com/).

## Стадии

| Стадия | Job | Образ | Что делает |
|---|---|---|---|
| build | `build` | `python:3.14-slim` | `pip install`, `compileall`, tar-архив в `dist/` |
| test | `test` | `python:3.14-slim` | `pytest` с JUnit-отчётом в `reports/junit.xml` |
| sast | `sast_semgrep` | `semgrep/semgrep` | статический анализ кода, блокировка при High/Critical |
| sca | `sast_trivy` | `aquasec/trivy` | анализ зависимостей, блокировка при HIGH/CRITICAL |
| deploy | `deploy` | runner + Docker | сборка образа, запуск, smoke-тест `/healthz`, сохранение образа в `dist/` |

Стадии связаны через `needs`: `build → test → sast → deploy`. В GitHub Actions
явные `stages` заменяются графом зависимостей job-ов.

## Требования

- Docker Desktop (запущен).
- Python 3.14 не нужен локально: сборка и тесты идут в контейнере.
- Для локального запуска — `brew install act`.

## Запуск

```bash
cp .secrets.example .secrets
openssl rand -hex 32 | sed 's/^/APP_SECRET=/' >> .secrets
act push --secret-file .secrets
```

Отдельная стадия:

```bash
act push --secret-file .secrets -j sast_semgrep
```

> `.secrets` добавлен в `.gitignore` и `.dockerignore`. Секрет попадает в
> контейнер только через переменную окружения `APP_SECRET`; в коде и в
> репозитории его нет.

## Артефакты и кэш

- Артефакты GitHub: `build-artifacts`, `test-reports`, `semgrep-report`,
  `trivy-report`, `deploy-artifacts` (`actions/upload-artifact`), передача между
  стадиями `build → test → deploy` через `actions/download-artifact`.
- Локально при `act` файлы остаются в `dist/` (архив исходников, tar-образ) и
  `reports/` (JUnit, SARIF, JSON); последующие стадии проверяют наличие
  переданного артефакта `dist/file-manager-src.tar.gz`.
- Кэш: `PIP_CACHE_DIR` в `.cache/pip` (в облаке — `actions/cache` по хэшу
  `requirements.txt`, локально каталог просто сохраняется между запусками),
  база Trivy — в `.cache/trivy`.

## Секреты

- В облаке — repository secret `APP_SECRET`.
- Локально — файл `.secrets` (`act --secret-file`).
- Шаблоны без значений: `.env.example`, `.secrets.example`.
- Job `deploy` падает, если секрет не задан, а health-эндпоинт показывает лишь
  флаг `secret_configured`, никогда само значение.

## Безопасность

- Финальный образ — multi-stage сборка, запуск от непривилегированного
  пользователя `app` (UID/GID 10001), `HEALTHCHECK` по `/healthz`.
- Проброс `/var/run/docker.sock` в раннер даёт контроль над демоном хоста и
  допустим только в локальной учебной среде; в продакшене недопустим.
- Docker-in-Docker требует `--privileged` и несёт риск container escape.
- Actions пришпилены к commit SHA, чтобы исключить подмену тега (supply chain).

## Локальный HTTP-интерфейс

```bash
python -m file_manager.web
```

- `GET /healthz` — статус сервиса;
- `GET /` — краткие сведения о сервисе.

Доступа к файлам и базе нет, эндпоинты только служебные.
