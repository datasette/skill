# Datasette Internals Reference

## Request Object

Passed to hooks as `request`. Represents incoming HTTP request.

### Properties

```python
request.method          # "GET", "POST", etc.
request.url             # Full URL: "https://example.com/db/table?foo=bar"
request.scheme          # "http" or "https"
request.host            # "example.com" or "localhost:8001"
request.path            # "/db/table"
request.full_path       # "/db/table?foo=bar"
request.headers         # Dict of headers
request.cookies         # Dict of cookies
request.args            # MultiParams for query string
request.url_vars        # Dict of URL path variables from regex groups
request.actor           # Current authenticated actor dict or None
request.scope           # ASGI scope dict
```

### Methods

```python
# Query string access (MultiParams)
request.args["foo"]           # First value, raises KeyError if missing
request.args.get("foo")       # First value or None
request.args.get("foo", "default")
request.args.getlist("foo")   # All values as list

# POST data
vars = await request.post_vars()  # Dict of form data
body = await request.post_body()  # Raw bytes

# Actor cookie for testing
cookie = datasette.client.actor_cookie({"id": "user"})
```

## Response Object

Return from view functions. Import: `from datasette import Response`

### Constructors

```python
# HTML response
Response.html("<h1>Hello</h1>")

# JSON response
Response.json({"key": "value"})

# Plain text
Response.text("Hello world")

# Redirect
Response.redirect("/new-path")
Response.redirect("/path", status=301)  # Permanent

# Generic
Response(
    body="content",           # str or bytes
    status=200,
    headers={"X-Custom": "value"},
    content_type="text/plain"
)
```

### Setting Cookies

```python
response = Response.html("<h1>Hi</h1>")
response.set_cookie("name", "value", max_age=3600, path="/", httponly=True)
```

## Datasette Object

Passed to hooks as `datasette`. Core application instance.

### Database Access

```python
# Get database by name
db = datasette.get_database("mydb")
db = datasette.get_database()  # First database

# All databases
for name, db in datasette.databases.items():
    pass
```

### Plugin Configuration

```python
# Get plugin config (respects database/table hierarchy)
config = datasette.plugin_config("datasette-my-plugin")
config = datasette.plugin_config("datasette-my-plugin", database="mydb")
config = datasette.plugin_config("datasette-my-plugin", database="mydb", table="users")
```

### Template Rendering

```python
html = await datasette.render_template(
    "my_template.html",
    context={"var": "value"},
    request=request
)
```

### Permission Checking

```python
allowed = await datasette.allowed(
    actor,
    "view-table",
    resource=("database_name", "table_name")
)

# Check with current request
allowed = await datasette.allowed(
    request.actor,
    "execute-sql",
    resource="database_name"
)
```

### URL Building

```python
datasette.urls.instance()           # "/"
datasette.urls.path("/-/plugins")   # "/-/plugins" (handles base_url)
datasette.urls.database("mydb")     # "/mydb"
datasette.urls.table("mydb", "users")  # "/mydb/users"
datasette.urls.row("mydb", "users", "123")  # "/mydb/users/123"
datasette.urls.static_plugins("my-plugin", "app.js")  # "/-/static-plugins/my-plugin/app.js"
```

### Event Tracking

```python
await datasette.track_event(MyCustomEvent(field="value"))
```

## Database Object

Represents a single SQLite database.

### Executing Queries

```python
db = datasette.get_database("mydb")

# Read-only query
result = await db.execute("SELECT * FROM users WHERE id = ?", [user_id])
result = await db.execute("SELECT * FROM users WHERE name = :name", {"name": "John"})

# Access results
for row in result.rows:
    print(row["name"], row["email"])

first_row = result.first()  # First row or None
all_rows = list(result.rows)

# Write query (INSERT, UPDATE, DELETE, CREATE)
await db.execute_write("INSERT INTO users (name) VALUES (?)", ["John"])
await db.execute_write("UPDATE users SET name = ? WHERE id = ?", ["Jane", 1])

# Write with return value
def do_insert(conn):
    cursor = conn.execute("INSERT INTO users (name) VALUES (?)", ["John"])
    return cursor.lastrowid

new_id = await db.execute_write_fn(do_insert)
```

### Database Metadata

```python
tables = await db.table_names()           # ["users", "posts"]
hidden = await db.hidden_table_names()    # ["_fts", "_cache"]
views = await db.view_names()             # ["user_posts"]
exists = await db.table_exists("users")   # True/False

# Table info
columns = await db.table_columns("users")  # ["id", "name", "email"]
pks = await db.primary_keys("users")       # ["id"]
count = await db.table_counts()            # {"users": 100, "posts": 500}
```

## Testing Utilities

### Creating Test Instance

```python
from datasette.app import Datasette
import pytest

@pytest.mark.asyncio
async def test_my_plugin():
    # In-memory database
    ds = Datasette(memory=True)
    
    # With database files
    ds = Datasette(["test.db", "other.db"])
    
    # With metadata/config
    ds = Datasette(
        memory=True,
        metadata={"title": "Test"},
        config={"settings": {"sql_time_limit_ms": 5000}}
    )
    
    # Invoke startup hooks
    await ds.invoke_startup()
```

### Making Test Requests

```python
# GET request
response = await ds.client.get("/mydb/users")
response = await ds.client.get("/mydb/users?name=John")

# POST request
response = await ds.client.post("/-/my-endpoint", data={"key": "value"})
response = await ds.client.post("/-/api", json={"key": "value"})

# With authenticated actor
response = await ds.client.get(
    "/-/admin",
    cookies={"ds_actor": ds.client.actor_cookie({"id": "admin"})}
)

# Check response
assert response.status_code == 200
assert response.json() == {"result": "success"}
assert "Expected text" in response.text
```

### Fixture Pattern

```python
import sqlite_utils

@pytest.fixture(scope="session")
def datasette(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("dbs") / "test.db"
    db = sqlite_utils.Database(db_path)
    db["users"].insert_all([
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ], pk="id")
    
    return Datasette([db_path])

@pytest.mark.asyncio
async def test_users(datasette):
    response = await datasette.client.get("/test/users.json?_shape=array")
    assert len(response.json()) == 2
```

### Temporary Plugin Registration

```python
@pytest.mark.asyncio
async def test_with_temp_plugin():
    class TestPlugin:
        __name__ = "TestPlugin"
        
        @hookimpl
        def register_routes(self):
            return [(r"^/-/test$", lambda: Response.text("test"))]
    
    ds = Datasette()
    ds.pm.register(TestPlugin(), name="test")
    try:
        response = await ds.client.get("/-/test")
        assert response.text == "test"
    finally:
        ds.pm.unregister(name="test")
```

## Common Imports

```python
from datasette import hookimpl, Response
from datasette.app import Datasette
from datasette.filters import FilterArguments
from datasette.permissions import Action, Resource, PermissionSQL
import markupsafe  # For HTML in render_cell
```
