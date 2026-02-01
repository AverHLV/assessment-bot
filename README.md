# assessment-bot

A backend for a Discord bot to store assessments of different pieces of art (movies, series, books, etc.).

## Project

The project and its associated services are executed in `Docker` containers assembled in `docker-compose`.
Interaction with the project occurs using `make` commands.

- Python executable inside container: `/opt/venv/app-4PlAip0Q/bin/python`.
- Project path inside container: `/app`.

## Setup

Fill in the `.env` file, use `.env.example`:
```
$ cp .env.example .env
```

Build containers:
```
$ make container@build
```

Start containers:
```
$ make container@start
```

Prepare dev environment (run db migrations, etc.):
```
$ make project@build-dev
```

Restart containers:
```
$ make container@restart
```

Install pre-commit hooks, install `pre-commit` on your system first, then:
```
$ pre-commit install
```

For help with the available commands:
```
$ make help
```

## Interaction with the project

Run console:
```
$ make container@console
```

Execute needed commands (examples):
```
$ ./manage.py makemigrations
$ ./manage.py shell
```
