HIRELENS BACKEND SETUP

STEP 1:
Keep your existing hirelens_db database.

Do not delete the users and jobs tables.

STEP 2:
Open MySQL Workbench.

Open database_schema.sql.

Execute the complete SQL code.

It creates:
1. candidate_profiles
2. resumes
3. applications

STEP 3:
Open VS Code terminal inside Backend folder.

Run:

python -m venv venv

venv\Scripts\activate

python -m pip install -r requirements.txt

STEP 4:
Check MySQL connection settings in database.py.

Default settings:

host = localhost
user = root
password = 1234
database = hirelens_db

Change the password if your MySQL password is different.

STEP 5:
Start Flask:

python app.py

STEP 6:
Open browser:

http://127.0.0.1:5000/

Database health:

http://127.0.0.1:5000/api/health