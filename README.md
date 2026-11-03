# Digital Notice Board Management System

A Django and SQLite college notice board for LKCTC (Lyallpur Khalsa College Technical Campus, Cantt. Road, Jalandhar). Students register with their college, mobile number and branch, then sign in to browse current notices. Staff administrators use a separate login to create, publish, edit and delete notices.

## Requirements

- Python 3.12 or later (required by the pinned Django 6.1 release)
- pip
- A modern browser
- Internet access for the Bootstrap, Bootstrap Icons and font CDNs used by the interface

## Setup on Windows PowerShell

Open PowerShell in the project directory:

```powershell
cd "D:\notice board"
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py runserver
```

If PowerShell prevents virtual-environment activation, either allow it for the current terminal with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, or call `.\venv\Scripts\python.exe` instead of activating it.

Open the site at <http://127.0.0.1:8000/>, create a student account at <http://127.0.0.1:8000/student/register/>, and log in at <http://127.0.0.1:8000/student/login/> using the college code, registration number or registered email address, and password. Before students register, create each college and assign it a unique login code in the Django admin at <http://127.0.0.1:8000/admin/>. Registration only offers colleges with a configured code, so students cannot accidentally create an unloginable college record. Students must register and log in to view notices. Staff use the separate login at <http://127.0.0.1:8000/admin-login/>. Keep the terminal running while using the site. Staff sign in with the username and password created by `createsuperuser`; credentials are not stored in application code.

## Setup on macOS or Linux

```bash
cd "/path/to/notice board"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py runserver
```

Use the same browser URLs listed above while the development server is running.

## Using the application

### Students

- Create an account with your full name, registration number, email address, password, configured college, mobile number, branch (CSE, IT, BCA or ECE) and semester.
- Log in with your college code, registration number or registered email address, and password to view current important and latest announcements for your college and branch.
- The home page shows your college, branch and semester alongside a personalized student welcome.
- Use **Forgot password?** to request a single-use password reset link. Locally, reset emails are written to the development server console.
- Open **All notices** to search notice titles/descriptions or filter by category.
- Select a notice to view its full description, category, publication date and expiry date.
- Use its PDF button to download an attachment, when available.
- Draft and expired notices are not included in the student notice board.
- Notice access requires a student account. Students only see published notices assigned to their college, for their selected branch and notices marked for all branches.

### Staff administrators

- Sign in at `/admin-login/` with an active Django staff account.
- The dashboard shows notice totals, published notices, expired notices and important notices.
- View the registered student count and manage student profiles through Django admin. Filter recent notices by category and target branch from the dashboard.
- Add or edit notices, assign each notice to a college, select the target branch (CSE, IT, BCA, ECE or all branches), set expiry dates, mark important notices, and publish or unpublish them.
- Attachments must be genuine PDF files no larger than 10 MB.
- Delete a notice from the dashboard and confirm the deletion on the next page.
- Log out using the dashboard or navigation-bar logout button.

Categories are Examination, Results, Events, Holidays, Admissions, Sports, Placement, General, Scholarships and Time Table.

The board also includes an About page and a Contact Us form. Contact submissions are stored for authorized staff; administrators can review them in the dashboard or Django admin.

## Project layout

```text
manage.py
noticeboard/       Django project settings and root URLs
notices/           Notice model, forms, views, validation and tests
notices/templates/ Public and administrator pages
notices/static/    Shared responsive stylesheet
media/notices/     Uploaded PDF attachments (created as needed)
db.sqlite3         Local SQLite database (created by migrations)
```

## Configuration and deployment notes

- `DJANGO_DEBUG` defaults to `False`; set it to `True` only for local development.
- Set `DJANGO_SECRET_KEY` to a long, unique secret in Render's environment settings. Render deployments fail fast when it is missing; the generated key fallback is for local development only.
- Set `DJANGO_ALLOWED_HOSTS` to a comma-separated list of the production host names and `DJANGO_CSRF_TRUSTED_ORIGINS` to their full HTTPS origins, for example `https://digital-notice-board-839q.onrender.com`.
- WhiteNoise serves fingerprinted static assets. In Render, use `pip install -r requirements.txt && python manage.py collectstatic --noinput` as the build command, and `python manage.py migrate --noinput && gunicorn noticeboard.wsgi:application --bind 0.0.0.0:$PORT` as the start command.
- SQLite remains the default local database. Render's filesystem is ephemeral unless a persistent disk is attached. To keep SQLite data across deploys, attach a persistent disk mounted at `/var/data`, set `DATABASE_PATH=/var/data/db.sqlite3`, and keep the service to one instance; use regular database backups. Uploaded notice files also need persistent storage, so set `MEDIA_ROOT=/var/data/media` on that disk. Without a disk, the database and uploaded files can be lost when Render restarts or redeploys the service.
- For student password resets in production, configure an SMTP provider using Render environment variables: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL`. Never put SMTP credentials or secret keys in Git.
- `DATABASE_PATH`, `MEDIA_ROOT`, `DJANGO_TIME_ZONE`, `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_COOKIES`, and `DJANGO_HSTS_SECONDS` can be set through environment variables. The default time zone is `Asia/Kolkata`; Render HTTPS and secure cookies are enabled automatically on Render.
- Configure HTTPS, backups and persistent private media storage before deployment. `runserver` and the built-in media serving route are for development, not production.

## Checks and tests

```powershell
python manage.py check
python manage.py test notices
```
