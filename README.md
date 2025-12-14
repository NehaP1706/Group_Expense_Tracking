# INSTRUCTIONS TO RUN:

## Database Setup:
I have used MySql for the current project, therefore it is recommended to create and run a docker instance with the same.

```bash
docker run -d \
  --name $CONTAINER_NAME \
  -e MYSQL_ROOT_PASSWORD=$DB_ROOT_PASS \
  -p 3306:3306 \
  mysql:8.0
```
```
docker exec -i $CONTAINER_NAME mysql -uroot -p$DB_ROOT_PASS <<EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME;
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
EOF
```
```
cat src/schema.sql | docker exec -i $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASS $DB_NAME
```

## Environment Variable Configs:
Make a `.env` file with the necessary psskeys as below:

```c
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=expense_tracker
MYSQL_USER=USER
MYSQL_PASS=PASSWORD
```
## General:
Run the following commands to launch:

```c
uv sync
uv run uvicorn src.main:app --reload
```

Access the website at the link displayed or 127.0.0.1:8000 after the above commands.
