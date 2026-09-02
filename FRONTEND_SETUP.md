# HelpDesk Frontend

Includes Login, Signup, Reset Password, Google SSO button, Dashboard, Tickets list/search/filter/pagination, Create/Edit/Delete/View Ticket, Attachment upload, Profile, JWT Bearer handling and permissions display.

## Add this to app/__init__.py inside create_app()

```python
from app.routes.frontend import frontend_bp
app.register_blueprint(frontend_bp)
```

Keep your existing auth_bp and attachment_bp registrations.

## Ticket API paths
Auth paths are already matched to your auth.py. Ticket paths are centralized in `app/static/js/config.js`:

```javascript
tickets: "/tickets",
ticketSearch: "/tickets/search",
ticketById: id => `/tickets/${id}`
```

If your tickets.py uses different paths, edit only these entries.

## Google SSO
Put your Google OAuth Client ID in `app/static/js/config.js`.

## Run

```bash
python run.py
```

Open `http://127.0.0.1:5000/login`.
