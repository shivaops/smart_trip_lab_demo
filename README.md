# Smart Trip — AI-Assisted Airline Booking Demo

Smart Trip is an AI-assisted airline booking demo project created for learning, practice, and developer improvement.

This project was built using AI assistance along with developer review and correction. The purpose is to demonstrate how an idea can be quickly converted into a working application, while also showing that AI-generated code still requires developer review, testing, correction, validation, and improvement.

Learners can use this project to practice:

* How AI-assisted code is structured
* How to review and improve generated code
* How UI, API, database, and provider API work together
* How booking, payment, and itinerary flows can be connected
* How database-driven configuration controls the application
* How to start from a working project and improve it further

The main learning point is:

```text
AI can help generate code,
but developer review, testing, correction,
and improvement are still required.
```


For the complete Smart Trip explanation and demo flow, please watch the full playlist on my YouTube channel:

🎥 [Watch Full Smart Trip Playlist on ShivaOps](https://www.youtube.com/playlist?list=PLYkaOC9kXnifZLmJb9NehgmZYqmCEaiQ6)

---

## Windows Only

This setup guide is for the **Windows platform only**.

The project was tested on Windows. New learners should first run the project on Windows as-is.

After the project works successfully, you can do your own R&D and make changes as per your choice.

---

## Project Folder Structure

After downloading the project, the main folders are:

```text
smart_trip_lab_demo
│
├── smart_trip   
│
└── ars_api    
```

---

## smart_trip

This is the main Smart Trip application.

It handles:

* User interface
* AI chat flow
* Flight search
* Booking
* Payment
* Itinerary
* Audit trace

Runs on:

```text
http://127.0.0.1:8001
```

---

## ars_api

This is the airline provider simulator API.

It handles:

* Provider flight inventory
* Provider flight search
* Provider booking
* Provider payment
* Provider itinerary

Runs on:

```text
http://127.0.0.1:8002
```

---

## Required Software

Install the following software on Windows:

```text
Git for Windows
Python 3.13.5 or above
MySQL Server 8.0
MySQL Workbench
Ollama with Mistral model
```

Check installation from Windows Command Prompt:

```cmd
git --version
python --version
ollama --version
```

If you do not want to test the local AI/LLM flow immediately, you can install Ollama later.

Also keep your free-tier Gemini 2.5 Flash model API key ready. If you want to use a different Gemini model, update the `tt_agentic.llm_provider` table accordingly.

If you want me to create a separate video on the installation of all these required software tools, kindly comment on my ShivaOps YouTube channel. I will try to upload an installation video as soon as possible.

---

## Step 1 — Download Project from GitHub

Open **Windows Command Prompt**.

Go to the folder where you want to download the project.

Example:

```cmd
cd C:\
```

Clone the repository:

```cmd
git clone https://github.com/shivaops/smart_trip_lab_demo.git
```

Go inside the project folder:

```cmd
cd smart_trip_lab_demo
```

If your downloaded folder name is different, go inside your actual project folder.

Example:

```cmd
cd smart_trip_lab_demo
```

---

## Step 2 — Import Smart Trip Full Database Dump

Open **MySQL Workbench**.

Import the full database dump file from:

```text
smart_trip\smart_trip_full_db_dump
```

This dump contains the main Smart Trip and ARS database objects, master data, and configuration data.

After import, confirm that these schemas exist:

```text
tt_agentic
ars
```

The `tt_agentic` schema is used by the Smart Trip application.

The `ars` schema is used by the ARS provider simulator.

Important:

Do not rename these schemas during the first setup.

---

## Step 3 — Run ARS Flight Inventory Script

Open **MySQL Workbench**.

Open this SQL file:

```text
ars_api\ars_fill_flight_inventory_data.sql
```

At the top of the script, update the flight inventory start date and number of days if required.

```sql
-- First departure date to create inventory from
SET @INV_START_DATE = DATE('2026-06-26');

-- How many calendar days of flight inventory are required?
-- Example:
--   30  = 30 days from start date
--   90  = 90 days from start date
--   180 = 180 days from start date
--   365 = 365 days from start date
SET @INV_DAYS = 60;
```

Save the file after updating these values.

Then copy the full SQL code into the MySQL Workbench SQL editor, select all, and execute everything at once.

This script prepares ARS demo flight inventory data.

It creates or rebuilds demo flight and fare inventory for the ARS provider simulator.

After running the script, verify the data:

```sql
SELECT COUNT(*) FROM ars.flight;
SELECT COUNT(*) FROM ars.fare;

SELECT 
  MIN(scheduled_departure) AS first_departure,
  MAX(scheduled_departure) AS last_departure
FROM ars.flight;
```

Important:

This script is for local demo inventory setup only.

Run it only on your local demo database.

---

## Step 4 — Important Provider Configuration

Smart Trip calls the ARS provider API using provider configuration stored in the database.

Important provider value:

```text
provider_code : ARS_LOCAL
provider_name : bookmyflight.com
provider_type : EXTERNAL_API
base_url      : http://bookmyflight.local:8002
is_active     : 1
```

Smart Trip uses this value:

```text
http://bookmyflight.local:8002
```

So ARS API must run on port:

```text
8002
```

And the Windows hosts file must contain:

```text
127.0.0.1 bookmyflight.local
```

For the first setup, do not change the provider URL or port.

First run the project as-is.

---

## Step 5 — Update Windows Hosts File

Open **Notepad as Administrator**.

Open this file:

```text
C:\Windows\System32\drivers\etc\hosts
```

Add these lines:

```text
127.0.0.1 smarttrip.shivaops.local
127.0.0.1 bookmyflight.local
```

Save the file.

This allows these local URLs to work:

```text
http://smarttrip.shivaops.local:8001
http://bookmyflight.local:8002
```

---

## Step 6 — Configure Smart Trip `.env`

Open this file:

```text
smart_trip\.env
```

Update the MySQL username and password as per your local MySQL setup.

Example:

```env
TT_DB_HOST=127.0.0.1
TT_DB_PORT=3306
TT_DB_USER=root
TT_DB_PASSWORD=your_mysql_password
TT_DB_NAME=tt_agentic

SESSION_SECRET=change_me_to_a_long_random_secret
SESSION_COOKIE_NAME=tt_session
GEMINI_API_KEY=enter_your_api_key_here
```

Usually, beginners only need to change:

```env
TT_DB_USER=root
TT_DB_PASSWORD=your_mysql_password
```

Do not change this during the first setup:

```env
TT_DB_NAME=tt_agentic
```

---

## Step 7 — Configure ARS API `.env`

Open this file:

```text
ars_api\.env
```

Update the MySQL username and password as per your local MySQL setup.

Example:

```env
ARS_DB_HOST=127.0.0.1
ARS_DB_PORT=3306
ARS_DB_USER=root
ARS_DB_PASSWORD=your_mysql_password
ARS_DB_NAME=ars
```

Usually, beginners only need to change:

```env
ARS_DB_USER=root
ARS_DB_PASSWORD=your_mysql_password
```

Do not change this during the first setup:

```env
ARS_DB_NAME=ars
```

---

## Step 8 — Start Ollama

Open **Command Prompt**.

Run:

```cmd
ollama serve
```

If it says port `11434` is already in use, Ollama may already be running in the background after Windows startup or after installation.

To check installed models:

```cmd
ollama list
```

To check running model/process:

```cmd
ollama ps
```

If your model is different from `mistral`, update the related model value in the `tt_agentic.llm_provider` table accordingly.

Keep Ollama running if you want to test the local AI/LLM flow.

---

## Step 9 — Setup and Run ARS API

Open a **new Command Prompt**.

Go to the project folder:

```cmd
cd C:\smart_trip_lab_demo
```

If your folder name is different, use your actual project folder.

Go to the ARS API folder:

```cmd
cd ars_api
```

Create a virtual environment:

```cmd
python -m venv .venv
```

Activate the virtual environment:

```cmd
.venv\Scripts\activate
```

Install the required packages:

```cmd
pip install -r requirements.txt
```

Run ARS API:

```cmd
uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

Check in browser:

```text
http://127.0.0.1:8002/health
```

Expected result:

```json
{"status":"ok"}
```

Also check the local domain:

```text
http://bookmyflight.local:8002/health
```

Keep this Command Prompt running.

---

## Step 10 — Setup and Run Smart Trip

Open a **second new Command Prompt**.

Go to the project folder:

```cmd
cd C:\smart_trip_lab_demo
```

If your folder name is different, use your actual project folder.

Go to the Smart Trip folder:

```cmd
cd smart_trip
```

Create a virtual environment:

```cmd
python -m venv .venv
```

Activate the virtual environment:

```cmd
.venv\Scripts\activate
```

Install the required packages:

```cmd
pip install -r requirements.txt
```

Run Smart Trip:

```cmd
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Open in browser:

```text
http://127.0.0.1:8001
```

or:

```text
http://smarttrip.shivaops.local:8001
```

---

## Step 11 — Login

The demo database contains this user:

```text
username: shiva
password: shiva123
```

If you want to change the username, run this SQL in MySQL Workbench:

```sql
UPDATE tt_agentic.app_user
SET username = 'your_username'
WHERE user_id = 1;
```

If the password does not work, reset it.

Open Command Prompt:

```cmd
cd C:\smart_trip_lab_demo\smart_trip
```

Activate the virtual environment:

```cmd
.venv\Scripts\activate
```

Run the password reset script:

```cmd
python scripts\set_password.py your_username NewPassword123
```

Login with:

```text
username: your_username
password: NewPassword123
```

If you did not change the username, you can reset the default user password:

```cmd
python scripts\set_password.py shiva NewPassword123
```

Then login with:

```text
username: shiva
password: NewPassword123
```

---

## Correct Startup Order

Use this order every time:

```text
1. Start MySQL Server
2. Import smart_trip\smart_trip_full_db_dump using MySQL Workbench
3. Run ars_api\ars_fill_flight_inventory_data.sql using MySQL Workbench
4. Update .env files if required
5. Update Windows hosts file
6. Start Ollama if local AI flow is required
7. Start ARS API on port 8002
8. Start Smart Trip on port 8001
9. Open Smart Trip in browser
```

---

## Important Values for First Setup

Do not change these during the first setup:

```text
Smart Trip port: 8001
ARS API port: 8002
Smart Trip schema: tt_agentic
ARS schema: ars
Provider code: ARS_LOCAL
Provider base URL: http://bookmyflight.local:8002
```

If this URL is changed but ARS is not running on the same URL, Smart Trip may not connect to the provider API.

---

## If You Want to Change Provider URL Later

First run the project as-is.

After it works, you can change the provider URL for your own R&D.

Example:

```sql
UPDATE tt_agentic.api_provider
SET base_url = 'http://127.0.0.1:8002'
WHERE provider_code = 'ARS_LOCAL';
```

If you change the ARS port, update both:

```text
1. ARS uvicorn port
2. tt_agentic.api_provider.base_url
```

---

## Useful URLs

Smart Trip:

```text
http://127.0.0.1:8001
```

Smart Trip local domain:

```text
http://smarttrip.shivaops.local:8001
```

ARS API health check:

```text
http://127.0.0.1:8002/health
```

ARS API local domain:

```text
http://bookmyflight.local:8002/health
```

ARS manage booking:

```text
http://bookmyflight.local:8002/manage-booking
```

---

## Common Issues

### MySQL Connection Error

Check:

```text
MySQL Server is running
Smart Trip full DB dump is imported
ARS inventory SQL is executed
Schema tt_agentic exists
Schema ars exists
.env username is correct
.env password is correct
MySQL port is 3306
```

---

### Provider API Not Working

Check:

```text
ARS API is running on port 8002
http://127.0.0.1:8002/health works
Windows hosts file contains 127.0.0.1 bookmyflight.local
Provider base_url is http://bookmyflight.local:8002
```

---

### Login Not Working

Reset password:

```cmd
cd C:\smart_trip_lab_demo\smart_trip
.venv\Scripts\activate
python scripts\set_password.py username NewPassword123
```

Then login with:

```text
username: username
password: NewPassword123
```

---

### Port Already in Use

Required ports:

```text
8001  - Smart Trip
8002  - ARS API
11434 - Ollama
```

If any port is already used, stop the old running process first.

---

### Python Package Error

Activate the virtual environment and run:

```cmd
pip install -r requirements.txt
```

---

## Disclaimer

This is a demo/lab project only.

It is not connected to any real airline, real payment gateway, or live travel provider.

Use it only for learning, practice, and local demo testing.

---

## More Details


For full Smart Trip explanation and demo flow, please watch:

🎥 [ShivaOps Smart Trip YouTube Playlist](https://www.youtube.com/playlist?list=PLYkaOC9kXnifZLmJb9NehgmZYqmCEaiQ6)

