# F&C Donation Platform

A student-friendly Flask + MySQL web application for managing food and clothing donations.

## 1. Main features

### Public pages
- Home page with sky-blue modern design
- About page
- Contact form
- Food donation page
- Clothes donation page
- Food request page
- Clothes request page
- Responsive navigation and footer

### Donor
- Register as donor
- Login/logout
- Donor dashboard
- Submit food donations
- Submit clothing donations
- See donation history
- See donation status
- Edit profile

### Recipient
- Register as recipient
- Login/logout
- Recipient dashboard
- Request food
- Request clothes
- See request history
- See request status
- Edit profile

### Admin
- Admin login
- Dashboard statistics
- View users
- View donations
- View requests
- View contact messages
- Change donation/request status
- Delete users, donations, requests and messages

## 2. Technologies used

- Python 3
- Flask
- MySQL
- mysql-connector-python
- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- Jinja2 templates

## 3. Project structure

```text
F_and_C_Donation_Platform/
│
├── app.py
├── config.py
├── fc_donation.sql
├── requirements.txt
├── README.md
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   └── images/
│       ├── hero-collage.jpg
│       ├── about-donation.jpg
│       ├── fresh-meals.jpg
│       ├── groceries.jpg
│       ├── childrens-wear.jpg
│       └── winter-clothes.jpg
│
└── templates/
    ├── base.html
    ├── index.html
    ├── about.html
    ├── contact.html
    ├── login.html
    ├── register.html
    ├── donate.html
    ├── request.html
    ├── donor_dashboard.html
    ├── receiver_dashboard.html
    ├── admin_dashboard.html
    ├── history.html
    └── profile.html
```

Do not copy a `venv` folder into the project. Create your own virtual environment on your computer.

## 4. Windows setup

Open PowerShell inside the project folder.

### Step A - create virtual environment

```powershell
python -m venv venv
```

### Step B - activate it

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` before the PowerShell path.

### Step C - install packages

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step D - create the MySQL database

Make sure MySQL Server and MySQL Workbench are running.

Open MySQL Workbench, create a SQL tab, paste the complete contents of:

```text
fc_donation.sql
```

and click the lightning/run button.

The SQL file creates:
- `fc_donation` database
- `users`
- `donations`
- `donation_requests`
- `contact_messages`

It also inserts small demo records so the website is not empty.

### Step E - check config.py

Default local MySQL settings are:

```python
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'fc_donation'
```

If your MySQL root account has a password, change:

```python
DB_PASSWORD = 'your_mysql_password'
```

Do not put spaces around the password.

### Step F - start Flask

```powershell
python app.py
```

You should see something similar to:

```text
* Running on http://127.0.0.1:5000
```

Open the browser and visit:

```text
http://127.0.0.1:5000
```

## 5. Demo login accounts

All demo accounts use:

```text
password123
```

### Donor

```text
Email: donor@example.com
Password: password123
```

### Recipient

```text
Email: receiver@example.com
Password: password123
```

### Admin

```text
Email: admin@example.com
Password: password123
```

Use the matching role button on the login page.

## 6. Recommended demo for your sir

Do not only open the home page. Show the complete workflow.

### Demo 1 - public website
1. Open Home.
2. Show the sky-blue hero section.
3. Explain the statistics are loaded from MySQL.
4. Open About.
5. Open Contact.
6. Submit a small test message.
7. Show that the message goes into the database.

### Demo 2 - donor workflow
1. Logout if necessary.
2. Login as:
   `donor@example.com`
3. Open Donor Dashboard.
4. Click Donate Food.
5. Enter:
   - Food Type: Cooked Meals
   - Quantity: 10
   - Pickup Address: Bharatpur, Chitwan
   - Condition: Fresh
6. Submit.
7. Open History.
8. Explain that the new record was inserted into MySQL with `Pending` status.

### Demo 3 - recipient workflow
1. Logout.
2. Login as:
   `receiver@example.com`
3. Open Request Food.
4. Fill the form.
5. Submit.
6. Open History.
7. Explain that the request is stored in the `donation_requests` table.

### Demo 4 - admin workflow
1. Logout.
2. Login as:
   `admin@example.com`
3. Open Admin Dashboard.
4. Show users, donations, requests and messages.
5. Find the new donation/request.
6. Change its status from `Pending` to `Approved`.
7. Click Save.
8. Logout and login again as donor/recipient.
9. Open the dashboard and show the changed status.

This last step is important because it demonstrates that the project is connected to a real database instead of being only static HTML.

## 7. What to say during presentation

You can explain it in simple student language:

> "Our project is called F&C Donation Platform. F&C stands for Food and Clothes. The main purpose is to connect donors and people who need food or clothes. I used Flask for the backend, MySQL for storing users and transaction records, HTML and Jinja templates for the pages, Bootstrap and CSS for responsive design, and JavaScript for small frontend interactions."

Then explain the three roles:

> "There are three roles: donor, recipient and admin. Donors can submit donations, recipients can submit requests, and the admin manages the records and updates their status."

For the database:

> "The main tables are users, donations, donation_requests and contact_messages. The donations and requests tables have foreign keys connected to the users table."

For security:

> "Passwords are not stored directly. Flask's Werkzeug password hashing is used."

For the design:

> "I changed the original dark blue interface to a sky-blue and white theme because it feels lighter and more friendly for a community donation website."

## 8. Database explanation for viva

### users
Stores:
- id
- name
- email
- password
- role
- phone
- address
- created_at

### donations
Stores:
- donor user id
- Food or Clothes
- item name
- quantity
- size
- description
- contact phone
- condition
- pickup location
- available date
- status

### donation_requests
Stores:
- recipient user id
- Food or Clothes
- item name
- quantity
- size
- reason
- address
- contact phone
- number of people
- needed date
- description
- status

### contact_messages
Stores messages submitted from the Contact page.

## 9. Important project flow

```text
User
  |
  +---- Register/Login
          |
          +---- Donor --------> Donation Form ----> MySQL
          |                         |
          |                         +------------> Admin Review
          |
          +---- Recipient ----> Request Form ----> MySQL
          |                         |
          |                         +------------> Admin Review
          |
          +---- Admin --------> View / Update / Delete
```

## 10. Common errors

### Error: No module named 'flask'

Activate the virtual environment first:

```powershell
.\venv\Scripts\Activate.ps1
```

Then:

```powershell
pip install -r requirements.txt
```

### Error: No module named 'mysql'

Run:

```powershell
pip install mysql-connector-python
```

### Error: Access denied for user 'root'

Open `config.py` and put your actual MySQL password in `DB_PASSWORD`.

### Error: Unknown database 'fc_donation'

Run `fc_donation.sql` in MySQL Workbench.

### Error: Port 5000 is already in use

Close the other Flask process or change the last line of `app.py` to:

```python
app.run(debug=True, port=5001)
```

Then open:

```text
http://127.0.0.1:5001
```

### Error: PowerShell will not activate venv

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## 11. If you want to reset the demo database

Run `fc_donation.sql` again.

Important: the SQL file contains `DROP TABLE` commands, so running it again clears the existing demo records before recreating the tables.

## 12. Notes

This is a local academic/student project. The admin, pickup and delivery workflow is represented inside the application; it does not connect to a real payment gateway, SMS service, map service or external NGO system.

For a classroom demonstration, the current features are enough to show a complete database-backed CRUD-style workflow.
