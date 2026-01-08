# INSTRUCTIONS TO RUN:

## Database Setup:
I have used MySql for the current project, therefore it is recommended to create and run a docker instance with the same.

```bash
docker run -d \
  --name $CONTAINER_NAME \
  -e MYSQL_ROOT_PASSWORD=$ROOT_PASS \
  -p 3306:3306 \
  mysql:8.0
```
```
docker exec -i $CONTAINER_NAME mysql -uroot -p$DB_ROOT_PASS <<EOF
CREATE DATABASE IF NOT EXISTS expense_tracker;
CREATE USER IF NOT EXISTS '$USER'@'%' IDENTIFIED BY '$PASSWORD';
GRANT ALL PRIVILEGES ON expense_tracker.* TO '$USER'@'%';
FLUSH PRIVILEGES;
EOF
```
```
cat src/schema.sql | docker exec -i $CONTAINER_NAME mysql -u$USER -p$PASSWORD expense_tracker
```

## Environment Variable Configs:
The setup process for Google Maps API was daunting and so a workaround using OpenStreetMap + Leaflet has been used in its place.
Make a `.env` file with the necessary passkeys as below:

```c
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=expense_tracker
MYSQL_USER=USER
MYSQL_PASS=PASSWORD
AVIATION_API_KEY=AVIATION_KEY
```
## General:
Run the following commands to launch:

```c
uv sync
uv run uvicorn src.main:app --reload
```

Access the website at the link displayed or 127.0.0.1:8000 after the above commands.
