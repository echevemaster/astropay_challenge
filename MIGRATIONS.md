# Database Migrations Guide with Docker

This guide explains how to run Alembic migrations using Docker.

## Option 1: Run migrations with Docker Compose (Recommended)

### Run migrations once

```bash
docker-compose --profile migrate run --rm migrations
```

This command:
- Uses the `migrate` profile to activate the migrations service
- Runs `alembic upgrade head`
- Automatically removes itself after execution (`--rm`)
- Waits for PostgreSQL to be healthy before running

### Run migrations after starting services

```bash
# 1. Start infrastructure services
docker-compose up -d postgres redis elasticsearch kafka zookeeper

# 2. Wait for PostgreSQL to be ready (optional, but recommended)
docker-compose exec postgres pg_isready -U astropay

# 3. Run migrations
docker-compose --profile migrate run --rm migrations
```

## Option 2: Run migrations manually in a container

If you prefer more control, you can run migrations manually:

```bash
# Create a temporary container and run migrations
docker-compose run --rm \
  -e DATABASE_URL=postgresql://astropay:astropay@postgres:5432/activity_feed \
  --entrypoint bash \
  api \
  -c "pip install -r requirements.txt && alembic upgrade head"
```

Or using the migrations service directly:

```bash
docker-compose build migrations
docker-compose --profile migrate run --rm migrations
```

## Option 3: Run from your local machine

If you have Python and dependencies installed locally:

```bash
# Make sure services are running
docker-compose up -d

# Run migrations locally
alembic upgrade head
```

## Useful Alembic Commands

### View migration status
```bash
docker-compose --profile migrate run --rm migrations alembic current
```

### View migration history
```bash
docker-compose --profile migrate run --rm migrations alembic history
```

### Create a new migration
```bash
docker-compose --profile migrate run --rm migrations alembic revision --autogenerate -m "migration description"
```

### Revert the last migration
```bash
docker-compose --profile migrate run --rm migrations alembic downgrade -1
```

### Revert all migrations
```bash
docker-compose --profile migrate run --rm migrations alembic downgrade base
```

## Verify migrations were applied

```bash
# Connect to PostgreSQL and verify tables
docker-compose exec postgres psql -U astropay -d activity_feed -c "\dt"

# View Alembic version table
docker-compose exec postgres psql -U astropay -d activity_feed -c "SELECT * FROM alembic_version;"
```

## Troubleshooting

### Error: "relation does not exist"
- Make sure PostgreSQL is fully started
- Verify that the `activity_feed` database exists
- Run migrations again

### Error: "connection refused"
- Verify PostgreSQL service is running: `docker-compose ps`
- Check logs: `docker-compose logs postgres`
- Make sure to use the service name (`postgres`) in the connection URL, not `localhost`

### Error: "alembic: command not found"
- Make sure the Dockerfile installs dependencies correctly
- Rebuild the image: `docker-compose build migrations`

## Recommended Complete Flow

```bash
# 1. Build images
docker-compose build

# 2. Start infrastructure services
docker-compose up -d postgres redis elasticsearch kafka zookeeper

# 3. Wait for PostgreSQL to be ready
sleep 5
docker-compose exec postgres pg_isready -U astropay

# 4. Run migrations
docker-compose --profile migrate run --rm migrations

# 5. Start the application
docker-compose up api
```

## Important Notes

- The migrations service uses the `migrate` profile so it doesn't start automatically with `docker-compose up`
- Migrations run against the database in the `postgres` container
- The connection URL uses the Docker service name (`postgres`) not `localhost`
- The volume mounts local code so changes are reflected immediately
