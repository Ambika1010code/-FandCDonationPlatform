# F&C Donation Platform - Presentation Guide

## Suggested 5-7 minute demonstration

### 1. Introduction (30 seconds)

Say:

> "Good morning sir. My project is F&C Donation Platform. F&C means Food and Clothes. The main idea is to provide a simple online system where donors can submit food or clothing donations, recipients can request support, and an admin can manage the records."

### 2. Technology (30 seconds)

Say:

> "For the frontend I used HTML, CSS, Bootstrap and JavaScript. For the backend I used Python Flask. MySQL is used for the database and Jinja is used to connect the backend data with HTML pages."

### 3. Show the home page (45 seconds)

Point out:
- Sky-blue theme
- Navigation bar
- Donate Now
- Request Help
- Dynamic activity numbers
- Donation categories
- How It Works section
- Responsive design

Say:

> "The main statistics are loaded from the database. They are not hard-coded on the dashboard."

### 4. Show donor workflow (1 minute)

Login:

```text
donor@example.com
password123
```

Then:
1. Open dashboard.
2. Click Donate Food.
3. Enter a small donation.
4. Submit.
5. Open History.
6. Show Pending status.

Say:

> "When I submit this form, Flask validates the input and inserts the record into the donations table. The initial status is Pending."

### 5. Show recipient workflow (1 minute)

Login:

```text
receiver@example.com
password123
```

Then:
1. Open Request Food.
2. Submit a request.
3. Open History.
4. Show Pending status.

Say:

> "The recipient workflow is similar, but the record is stored in donation_requests."

### 6. Show admin workflow (1.5 minutes)

Login:

```text
admin@example.com
password123
```

Then:
1. Open Admin Dashboard.
2. Show user count.
3. Show donation count.
4. Show request count.
5. Show messages.
6. Find the new donation.
7. Change Pending to Approved.
8. Save.
9. Find the request and change its status too.

Say:

> "The admin can manage the main records. The status update is stored in MySQL. If I log back into the donor or recipient account, the updated status is visible there."

### 7. Database (45 seconds)

Open MySQL Workbench and show:
- users
- donations
- donation_requests
- contact_messages

Explain the relationship:

```text
users.id
   |
   +---- donations.user_id
   |
   +---- donation_requests.user_id
```

Say:

> "The user ID is used as a foreign key, so each donation and request belongs to a particular user."

### 8. Security (20 seconds)

Say:

> "Passwords are hashed using Werkzeug's password hashing functions. I also use session-based login and role checks so donors, recipients and admins cannot directly open another role's dashboard."

### 9. Closing (20 seconds)

Say:

> "The project demonstrates a complete database-backed workflow: registration, authentication, donation, request, history, admin review, status update and contact management."

---

# Common viva questions

## Why did you choose Flask?

Answer:

> "Flask is lightweight and easy to understand for a student web application. It lets me define routes, process forms and connect Python code with Jinja templates."

## Why MySQL?

Answer:

> "MySQL is a relational database, so it is suitable for storing users and linking donations and requests to users with foreign keys."

## What is a session?

Answer:

> "A Flask session stores information such as user ID, name and role after login. It helps the application know which user is currently logged in."

## Why hash passwords?

Answer:

> "Passwords should not be stored as plain text. Hashing protects the original password value in the database."

## What is a foreign key?

Answer:

> "A foreign key connects one table to another. In this project, donations.user_id references users.id and donation_requests.user_id references users.id."

## What is CRUD?

Answer:

> "CRUD means Create, Read, Update and Delete. The project uses these operations for users, donations, requests and contact messages."

## Where is CRUD used?

Answer:

- Create: registration, donation, request, contact form
- Read: dashboards and history
- Update: profile and admin status
- Delete: admin management

## What happens when a donor submits a donation?

Answer:

> "The browser sends a POST request to Flask. Flask reads and validates the form, gets the logged-in user's ID from the session, inserts the record into MySQL and redirects the donor to history."

## What happens if a user is not logged in?

Answer:

> "Protected routes check the session and redirect the user to the login page."

## Can a donor open the admin dashboard?

Answer:

> "No. The admin dashboard checks the current session role and only allows the admin role."

## What is Jinja?

Answer:

> "Jinja is the template engine used by Flask. It allows Python data such as user names, database rows and status values to be displayed inside HTML."

## What is Bootstrap used for?

Answer:

> "Bootstrap provides responsive layout classes, forms, buttons, grid components and the mobile navigation."

## What is JavaScript used for?

Answer:

> "I use JavaScript for password visibility, account-role selection, delete confirmation and small form interactions."

## Is this connected to a real NGO?

Answer:

> "No. This academic version demonstrates the complete workflow locally. It is not connected to a real NGO, payment gateway, SMS provider or delivery service."

## What can be added in the future?

Answer:

- NGO accounts
- Volunteer accounts
- Email/SMS notifications
- Map and pickup tracking
- Donation matching
- File/image upload
- Online verification
- Production deployment
- HTTPS and stronger CSRF protection
- REST API

---

# If the sir asks why the statistics are small

Say:

> "The demonstration database contains sample records. The statistics are calculated from the current database instead of using fake production numbers."

This is better than claiming that the project has thousands of real donations.

---

# If the sir asks about the sky-blue redesign

Say:

> "I used sky blue as the main brand color because it gives the website a clean and friendly community-service appearance. White cards and light backgrounds keep the forms easy to read, while green is used for positive donation actions."

---

# Before presenting

Run:

```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

Check:

```text
http://127.0.0.1:5000
```

Make sure:
- MySQL is running
- `fc_donation` exists
- The demo accounts work
- Home opens
- Donor login works
- Recipient login works
- Admin login works
- A new donation can be inserted
- A new request can be inserted
- Admin can update a status
- History displays the status
- Contact message appears in admin

Do not demonstrate only the static home page. The strongest part of the project is the database workflow.
