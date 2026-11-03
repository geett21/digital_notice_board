# Digital Notice Board Management System

A Django and SQLite college notice board for LKCTC (Lyallpur Khalsa College Technical Campus, Cantt. Road, Jalandhar). Students register with their college, mobile number and branch, then sign in to browse current notices. Staff administrators use a separate login to create, publish, edit and delete notices.

## Requirements

- Python 3.10 or later
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
python manage.py createsuperuser
python manage.py runserver
```

If PowerShell prevents virtual-environment activation, either allow it for the current terminal with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, or call `.\venv\Scripts\python.exe` instead of activating it.

Open the site at <http://127.0.0.1:8000/>, create a student account at <http://127.0.0.1:8000/student/register/>, and log in at <http://127.0.0.1:8000/student/login/> using the college code, registration number or registered email address, and password. Before students log in, add each college and its code through the existing Django admin at <http://127.0.0.1:8000/admin/>. College names must match the name used during student registration. Students must register and log in to view notices. Staff use the separate login at <http://127.0.0.1:8000/admin-login/>. Keep the terminal running while using the site. Staff sign in with the username and password created by `createsuperuser`; credentials are not stored in application code.

## Setup on macOS or Linux

```bash
cd "/path/to/notice board"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Use the same browser URLs listed above while the development server is running.

## Using the application

### Students

- Create an account with a registration number, email address, password, college name, mobile number and branch (CSE, IT, BCA or ECE); a default LKCTC college name is provided.
- Log in with your college code, registration number or registered email address, and password to view current important and latest announcements for your college and branch.
- Open **All notices** to search notice titles/descriptions or filter by category.
- Select a notice to view its full description, category, publication date and expiry date.
- Use its PDF button to download an attachment, when available.
- Draft and expired notices are not included in the student notice board.
- Notice access requires a student account. Students only see published notices assigned to their college, for their selected branch and notices marked for all branches.

### Staff administrators

- Sign in at `/admin-login/` with an active Django staff account.
- The dashboard shows notice totals, published notices, expired notices and important notices.
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

- Set `DJANGO_SECRET_KEY` to a long, unique secret outside source control for persistent deployments.
- `DJANGO_DEBUG` defaults to `True` for local development; set it to `False` in production.
- Set `DJANGO_ALLOWED_HOSTS` to a comma-separated list of the production host names.
- Configure HTTPS, static-file serving, backups and persistent private media storage before deployment. `runserver` and the built-in media serving route are for development, not production.
- The secret key is generated for local development if `DJANGO_SECRET_KEY` is not set; setting the environment variable makes sessions persistent across server restarts.

## Checks and tests

```powershell
python manage.py check
python manage.py test notices
```
