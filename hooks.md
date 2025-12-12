# Datasette Plugin Hooks Reference

Complete reference for all Datasette plugin hooks. Each hook uses the `@hookimpl` decorator.

## Database Connection Hooks

### prepare_connection(conn, database, datasette)

Called when a new SQLite connection is created. Register custom SQL functions, aggregates, collations.

```python
@hookimpl
def prepare_connection(conn):
    conn.create_function("random_integer", 2, random.randint)
    conn.create_function("upper_custom", 1, lambda s: s.upper())
```

**Parameters:**
- `conn`: sqlite3 connection object
- `database`: string - database name
- `datasette`: Datasette instance

**Note:** Not called for internal database.

## Template Hooks

### prepare_jinja2_environment(env, datasette)

Customize Jinja2 environment. Register filters, globals, tests.

```python
@hookimpl
def prepare_jinja2_environment(env):
    env.filters["uppercase"] = lambda u: u.upper()
    env.globals["site_name"] = "My Site"
```

Can return awaitable function for async operations.

### extra_template_vars(template, database, table, columns, view_name, request, datasette)

Add variables to template context.

```python
@hookimpl
def extra_template_vars(request):
    return {"user_agent": request.headers.get("user-agent")}

# Async version
@hookimpl
def extra_template_vars(datasette, database):
    async def inner():
        db = datasette.databases[database]
        return {"tables": await db.table_names()}
    return inner
```

**Parameters:**
- `template`: string - template being rendered (e.g., "database.html")
- `database`: string or None
- `table`: string or None
- `columns`: list of strings or None
- `view_name`: string - "index", "database", "table", "row"
- `request`: Request object or None
- `datasette`: Datasette instance

## CSS/JavaScript Hooks

### extra_css_urls(template, database, table, columns, view_name, request, datasette)

Add CSS URLs to pages.

```python
@hookimpl
def extra_css_urls():
    return ["https://example.com/style.css"]

# With SRI hash
@hookimpl
def extra_css_urls():
    return [{
        "url": "https://example.com/style.css",
        "sri": "sha384-..."
    }]
```

### extra_js_urls(template, database, table, columns, view_name, request, datasette)

Add JavaScript URLs.

```python
@hookimpl
def extra_js_urls():
    return [{"url": "/-/static-plugins/my-plugin/app.js", "module": True}]
```

### extra_body_script(template, database, table, columns, view_name, request, datasette)

Add inline JavaScript to page end.

```python
@hookimpl
def extra_body_script():
    return {"module": True, "script": "console.log('loaded');"}
```

## Route Registration

### register_routes(datasette)

Add custom URL routes.

```python
from datasette import hookimpl, Response

@hookimpl
def register_routes():
    return [
        (r"^/-/my-page$", my_view),
        (r"^/-/user/(?P<username>[^/]+)$", user_view),
    ]

async def my_view(datasette, request):
    return Response.html("<h1>Hello</h1>")

async def user_view(request):
    username = request.url_vars["username"]
    return Response.json({"user": username})
```

**View function arguments (dependency injection):**
- `datasette`: Datasette instance
- `request`: Request object
- `scope`: ASGI scope dict
- `send`: ASGI send function
- `receive`: ASGI receive function

**Exceptions:**
- `raise datasette.NotFound` for 404
- `raise datasette.Forbidden` for 403

### register_commands(cli)

Add CLI commands.

```python
@hookimpl
def register_commands(cli):
    @cli.command()
    @click.argument("files", type=click.Path(exists=True), nargs=-1)
    def verify(files):
        """Verify database files"""
        for f in files:
            # validation logic
            pass
```

## Cell Rendering

### render_cell(row, value, column, table, database, datasette, request)

Customize how cell values display in HTML tables.

```python
import markupsafe
import json

@hookimpl
def render_cell(value, column):
    if column == "stars":
        return "⭐" * int(value)
    
    # Return HTML
    if column == "url":
        return markupsafe.Markup(f'<a href="{value}">{value}</a>')
    
    return None  # Let other hooks handle it
```

Return `None` to skip, string for text, `markupsafe.Markup` for HTML.

## Output Renderers

### register_output_renderer(datasette)

Add custom output formats (e.g., `.csv`, `.xml`).

```python
@hookimpl
def register_output_renderer(datasette):
    return {
        "extension": "tsv",
        "render": render_tsv,
        "can_render": can_render_tsv,  # optional
    }

async def render_tsv(datasette, columns, rows):
    from datasette import Response
    lines = ["\t".join(columns)]
    for row in rows:
        lines.append("\t".join(str(v) for v in row))
    return Response("\n".join(lines), content_type="text/tab-separated-values")

def can_render_tsv(columns):
    return True  # or check specific columns
```

**Render function parameters:**
- `datasette`, `columns`, `rows`, `sql`, `query_name`, `database`, `table`, `request`, `error`, `truncated`, `view_name`

## Authentication & Permissions

### actor_from_request(datasette, request)

Authenticate users from request.

```python
@hookimpl
def actor_from_request(datasette, request):
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if validate_token(token):
            return {"id": "user123", "name": "John"}
    return None

# Async version
@hookimpl
def actor_from_request(datasette, request):
    async def inner():
        token = request.args.get("_token")
        if token:
            result = await datasette.get_database().execute(
                "SELECT * FROM sessions WHERE token = ?", [token]
            )
            if result.first():
                return {"token": token}
        return None
    return inner
```

### permission_allowed(datasette, actor, action, resource)

**Deprecated in favor of permission_resources_sql**. Control permission checks.

```python
@hookimpl
def permission_allowed(datasette, actor, action, resource):
    if action == "view-database" and resource == "secret":
        if actor and actor.get("is_admin"):
            return True
        return False
    return None  # Let other hooks decide
```

### permission_resources_sql(datasette, actor, action)

Return SQL for resource-based permissions.

```python
from datasette.permissions import PermissionSQL

@hookimpl
def permission_resources_sql(datasette, actor, action):
    if action != "view-table" or not actor:
        return None
    
    return PermissionSQL(
        sql="""
            SELECT database_name AS parent, table_name AS child, 1 AS allow,
                   'user has access' AS reason
            FROM user_permissions
            WHERE user_id = :user_id
        """,
        params={"user_id": actor.get("id")}
    )
```

### actors_from_ids(datasette, actor_ids)

Resolve actor IDs to full actor dictionaries.

```python
@hookimpl
def actors_from_ids(datasette, actor_ids):
    async def inner():
        db = datasette.get_database()
        sql = f"SELECT id, name FROM users WHERE id IN ({','.join('?' * len(actor_ids))})"
        result = await db.execute(sql, actor_ids)
        return {row["id"]: dict(row) for row in result.rows}
    return inner
```

## Lifecycle Hooks

### startup(datasette)

Run on server startup. Create tables, validate config.

```python
@hookimpl
def startup(datasette):
    config = datasette.plugin_config("my-plugin") or {}
    assert "api_key" in config, "my-plugin requires api_key"

# Async version
@hookimpl
def startup(datasette):
    async def inner():
        db = datasette.get_database()
        await db.execute_write("CREATE TABLE IF NOT EXISTS logs (msg TEXT)")
    return inner
```

### asgi_wrapper(datasette)

Wrap Datasette with ASGI middleware.

```python
from functools import wraps

@hookimpl
def asgi_wrapper(datasette):
    def wrap(app):
        @wraps(app)
        async def wrapped(scope, receive, send):
            async def custom_send(event):
                if event["type"] == "http.response.start":
                    headers = list(event.get("headers", []))
                    headers.append([b"x-custom", b"value"])
                    event = {**event, "headers": headers}
                await send(event)
            await app(scope, receive, custom_send)
        return wrapped
    return wrap
```

## Menu & Action Hooks

### menu_links(datasette, actor, request)

Add items to top-right menu.

```python
@hookimpl
def menu_links(datasette, actor):
    if actor and actor.get("id") == "admin":
        return [{"href": datasette.urls.path("/-/admin"), "label": "Admin"}]
```

### table_actions(datasette, actor, database, table, request)

Add items to table page action menu.

```python
@hookimpl
def table_actions(datasette, database, table):
    return [{
        "href": f"/{database}/{table}/-/export",
        "label": "Export Table",
        "description": "Download as Excel"
    }]
```

### database_actions(datasette, actor, database, request)
### homepage_actions(datasette, actor, request)
### row_actions(datasette, actor, request, database, table, row)
### query_actions(datasette, actor, database, query_name, request, sql, params)
### view_actions(datasette, actor, database, view, request)

All follow same pattern as `table_actions`.

## Content Injection Hooks

### top_homepage(datasette, request)
### top_database(datasette, request, database)
### top_table(datasette, request, database, table)
### top_row(datasette, request, database, table, row)
### top_query(datasette, request, database, sql)
### top_canned_query(datasette, request, database, query_name)

Return HTML to display at top of respective pages.

```python
@hookimpl
def top_table(datasette, database, table):
    return f"<div class='notice'>Viewing {table}</div>"
```

## Event Tracking

### track_event(datasette, event)

Called when events occur (login, table creation, etc.).

```python
@hookimpl
def track_event(event):
    print(f"Event: {event.name}, Actor: {event.actor}, Props: {event.properties()}")

# Async version for database logging
@hookimpl
def track_event(datasette, event):
    async def inner():
        db = datasette.get_database()
        await db.execute_write(
            "INSERT INTO events (type, actor, props) VALUES (?, ?, ?)",
            [event.name, json.dumps(event.actor), json.dumps(event.properties())]
        )
    return inner
```

### register_events(datasette)

Register custom event types.

```python
from dataclasses import dataclass
from datasette import Event

@dataclass
class MyCustomEvent(Event):
    name = "my-custom-event"
    custom_field: str

@hookimpl
def register_events():
    return [MyCustomEvent]
```

## Canned Queries

### canned_queries(datasette, database, actor)

Add programmatic canned queries.

```python
@hookimpl
def canned_queries(datasette, database):
    if database == "main":
        return {
            "recent_users": {
                "sql": "SELECT * FROM users ORDER BY created DESC LIMIT 10",
                "title": "Recent Users"
            }
        }
```

## Request Filtering

### filters_from_request(request, database, table, datasette)

Add WHERE clauses based on request.

```python
from datasette.filters import FilterArguments

@hookimpl
def filters_from_request(request):
    if request.args.get("_active"):
        return FilterArguments(
            where_clauses=["active = :active"],
            params={"active": 1},
            human_descriptions=["Active only"]
        )
```

## Error Handling

### forbidden(datasette, request, message)

Customize 403 responses.

```python
@hookimpl
def forbidden(request, message):
    from datasette import Response
    return Response.redirect(f"/-/login?error={message}")
```

### handle_exception(datasette, request, exception)

Handle unexpected exceptions.

```python
@hookimpl
def handle_exception(datasette, exception):
    import sentry_sdk
    sentry_sdk.capture_exception(exception)
```

## Miscellaneous

### skip_csrf(datasette, scope)

Disable CSRF for specific paths.

```python
@hookimpl
def skip_csrf(scope):
    return scope["path"] == "/api/webhook"
```

### jinja2_environment_from_request(datasette, request, env)

Return custom Jinja environment per request.

### register_facet_classes()

Register custom facet types (advanced).

### register_magic_parameters(datasette)

Add magic parameters for canned queries.

```python
from uuid import uuid4

@hookimpl
def register_magic_parameters(datasette):
    return [
        ("uuid", lambda key, request: str(uuid4()) if key == "new" else None),
    ]
```

### register_actions(datasette)

Register custom permission actions.

```python
from datasette.permissions import Action, Resource

class DocumentResource(Resource):
    name = "document"
    parent_name = None
    
    def __init__(self, doc_id):
        super().__init__(parent=doc_id, child=None)
    
    @classmethod
    def resources_sql(cls):
        return "SELECT id AS parent, NULL AS child FROM documents"

@hookimpl
def register_actions(datasette):
    return [
        Action(name="view-document", abbr="vdoc", resource_class=DocumentResource),
    ]
```

### publish_subcommand(publish)

Add `datasette publish` subcommands.

```python
@hookimpl
def publish_subcommand(publish):
    @publish.command()
    @click.option("--api-key", required=True)
    def my_host(api_key):
        """Publish to my hosting provider"""
        pass
```
