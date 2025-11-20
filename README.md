# 🤖 ASA - Autonomous Software Agent
### The Robot That Fixes Your Bugs Automatically!

---

## 📖 Table of Contents
1. [What is This?](#what-is-this)
2. [What You'll Need](#what-youll-need)
3. [Installing Software (Step-by-Step)](#installing-software)
4. [Downloading ASA](#downloading-asa)
5. [Setting Up ASA](#setting-up-asa)
6. [Running ASA](#running-asa)
7. [Using ASA](#using-asa)
8. [Troubleshooting](#troubleshooting)
9. [Costs](#costs)
10. [Getting Help](#getting-help)

---

## 🎯 What is This?

**ASA** (Autonomous Software Agent) is like a robot programmer that can:
- Read your code
- Understand bugs
- Write tests to check for bugs
- Fix the bugs automatically
- Create a Pull Request on GitHub

**You don't need to know programming!** Just tell it what's broken in plain English.

**Example:**
- You: "The login button doesn't work"
- ASA: *reads code, writes test, fixes bug, creates Pull Request*
- You: Review and approve the fix

---

## 📋 What You'll Need

Before we start, we need to install some programs. Think of them like apps on your phone:

| Program | What It Does | Cost |
|---------|--------------|------|
| **Python 3.11** | The "brain" language | FREE ✅ |
| **Node.js 18** | Runs the website | FREE ✅ |
| **Git** | Downloads and manages code | FREE ✅ |
| **Docker** | Runs tests safely | FREE ✅ |
| **VS Code** | View and edit files | FREE ✅ |
| **GitHub Account** | Stores your code online | FREE ✅ |
| **OpenAI Account** | AI to fix bugs | PAID 💰 (~$1-5/month) |

**Total cost: About $1-5 per month** (just for OpenAI)

---

## 🔧 Installing Software

### Step 1: Install Python 3.11

**What is Python?** A programming language that makes computers do things.

#### 🪟 Windows Instructions:

1. **Download Python:**
   - Open your web browser (Chrome, Edge, Firefox, etc.)
   - Go to: `https://www.python.org/downloads/`
   - Click the big yellow button: **"Download Python 3.11.X"**
   - Wait for download to finish

2. **Install Python:**
   - Find the downloaded file (usually in Downloads folder)
   - Double-click `python-3.11.X.exe`
   - **⚠️ IMPORTANT:** Check the box that says **"Add Python to PATH"** (at the bottom!)
   - Click **"Install Now"**
   - Wait 2-3 minutes
   - Click **"Close"** when done

3. **Check if it worked:**
   - Press **Windows Key + R** on your keyboard
   - Type: `cmd` and press **Enter**
   - A black window opens (this is Command Prompt)
   - Type: `python --version` and press **Enter**
   - You should see: `Python 3.11.X`
   - ✅ Success! Close the window.

#### 🍎 Mac Instructions:

1. **Download Python:**
   - Go to: `https://www.python.org/downloads/`
   - Click: **"Download Python 3.11.X"**

2. **Install Python:**
   - Find the downloaded `.pkg` file
   - Double-click it
   - Click **"Continue"** through all steps
   - Enter your Mac password when asked

3. **Check if it worked:**
   - Press **Cmd + Space** and type: `Terminal`
   - Press **Enter** (a window with text opens)
   - Type: `python3 --version` and press **Enter**
   - You should see: `Python 3.11.X`
   - ✅ Success!

#### 🐧 Linux Instructions:

```bash
sudo apt update
sudo apt install python3.11 python3.11-pip
python3.11 --version
```

---

### Step 2: Install Node.js 18

**What is Node.js?** Runs the website part of ASA (the buttons and forms you click).

#### 🪟 Windows Instructions:

1. **Download Node.js:**
   - Go to: `https://nodejs.org/`
   - Click the button that says: **"18.X.X LTS"** (LTS = stable version)
   - Wait for download

2. **Install Node.js:**
   - Find `node-v18.X.X.msi` in Downloads
   - Double-click it
   - Click **"Next"** on every screen (defaults are fine)
   - Click **"Install"**
   - Wait 3-5 minutes
   - Click **"Finish"**

3. **Check if it worked:**
   - Press **Windows Key + R**
   - Type: `cmd` and press **Enter**
   - Type: `node --version` and press **Enter**
   - You should see: `v18.X.X`
   - ✅ Success!

#### 🍎 Mac Instructions:

1. Go to: `https://nodejs.org/`
2. Click: **"18.X.X LTS"**
3. Open the downloaded `.pkg` file
4. Click through installer
5. Check: Open Terminal, type `node --version`

#### 🐧 Linux Instructions:

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version
```

---

### Step 3: Install Git

**What is Git?** Helps download code and track changes.

#### 🪟 Windows Instructions:

1. **Download Git:**
   - Go to: `https://git-scm.com/download/win`
   - Download starts automatically

2. **Install Git:**
   - Open the downloaded file
   - Click **"Next"** on everything
   - **⚠️ IMPORTANT:** When you see "Adjusting your PATH environment", select: **"Git from the command line and also from 3rd-party software"**
   - Continue clicking **"Next"**
   - Click **"Install"**
   - Click **"Finish"**

3. **Check if it worked:**
   - Open Command Prompt
   - Type: `git --version`
   - You should see: `git version 2.X.X`
   - ✅ Success!

#### 🍎 Mac Instructions:

1. Open Terminal
2. Type: `git --version`
3. If Git is not installed, Mac will ask: "Install Developer Tools?"
4. Click **"Install"**
5. Wait 5-10 minutes

#### 🐧 Linux Instructions:

```bash
sudo apt install git
git --version
```

---

### Step 4: Install Docker

**What is Docker?** Creates safe "containers" to run tests without breaking your computer.

#### 🪟 Windows Instructions:

1. **Download Docker Desktop:**
   - Go to: `https://www.docker.com/products/docker-desktop/`
   - Click: **"Download for Windows"**
   - Wait for download (it's big, ~500MB)

2. **Install Docker:**
   - Run: `Docker Desktop Installer.exe`
   - Click **"OK"** to all prompts
   - Wait 5-10 minutes
   - **⚠️ You MUST restart your computer** when it asks!

3. **After Restart:**
   - Docker Desktop should start automatically
   - You'll see a whale icon 🐳 in your taskbar (bottom-right)
   - Wait until the whale stops animating (means Docker is ready)

4. **Check if it worked:**
   - Open Command Prompt
   - Type: `docker --version`
   - You should see: `Docker version XX.X.X`
   - ✅ Success!

#### 🍎 Mac Instructions:

1. Go to: `https://www.docker.com/products/docker-desktop/`
2. Download **"Docker Desktop for Mac"**
3. Drag Docker icon to Applications folder
4. Open Docker from Applications
5. Click **"Open"** when Mac asks for confirmation
6. Wait for Docker to start (whale icon appears in menu bar)

#### 🐧 Linux Instructions:

```bash
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
# Log out and log back in
docker --version
```

---

### Step 5: Install VS Code (Optional but Recommended)

**What is VS Code?** A nice program to view and edit code files (like Notepad but better).

#### All Systems:

1. Go to: `https://code.visualstudio.com/`
2. Click the big **"Download"** button
3. Install it (click "Next" on everything)
4. Open VS Code

**Helpful Extensions** (optional):
1. Click the Extensions icon (looks like 4 squares on the left)
2. Search and install:
   - "Python" by Microsoft
   - "Prettier - Code formatter"
   - "GitLens"

---

### Step 6: Create GitHub Account

**What is GitHub?** A website where programmers store code (like Google Drive for code).

1. **Sign Up:**
   - Go to: `https://github.com/`
   - Click: **"Sign up"**
   - Enter your email address
   - Create a password (write it down!)
   - Choose a username (can be anything)
   - Click **"Continue"**
   - Solve the puzzle
   - Click **"Create account"**

2. **Verify Email:**
   - Check your email
   - Click the verification link
   - ✅ Account created!

3. **Create Access Token** (this is like a password for ASA):
   - Log into GitHub
   - Click your profile picture (top-right corner)
   - Click: **"Settings"**
   - Scroll down on the left side
   - Click: **"Developer settings"** (at the very bottom)
   - Click: **"Personal access tokens"** → **"Tokens (classic)"**
   - Click: **"Generate new token"** → **"Generate new token (classic)"**
   - Give it a name: `ASA Token`
   - Check these boxes:
     - ✅ **repo** (check the main box, sub-boxes auto-check)
     - ✅ **workflow**
   - Scroll down and click: **"Generate token"**
   - **⚠️ COPY THE TOKEN!** It starts with `ghp_...`
   - **Paste it in a text file and save it** - you can't see it again!

---

### Step 7: Create OpenAI Account

**What is OpenAI?** The company that made ChatGPT. We use their AI to understand and fix bugs.

**⚠️ This costs money:** About $1-5 per month for testing. You need a credit card.

1. **Sign Up:**
   - Go to: `https://platform.openai.com/signup`
   - Sign up with email or Google
   - Verify your email

2. **Add Payment Method:**
   - Go to: `https://platform.openai.com/account/billing/overview`
   - Click: **"Add payment method"**
   - Enter credit card details
   - **Set a spending limit:** Click "Usage limits" and set Monthly budget to **$10**

3. **Get API Key:**
   - Go to: `https://platform.openai.com/api-keys`
   - Click: **"Create new secret key"**
   - Name it: `ASA Key`
   - Click: **"Create secret key"**
   - **⚠️ COPY THE KEY!** It starts with `sk-...`
   - **Save it in a text file** - you can't see it again!

---

## 📥 Downloading ASA

Now let's get the actual ASA code!

### Method 1: Download as ZIP (Easier for Beginners)

1. Go to your ASA GitHub repository in your web browser
2. Click the green **"Code"** button
3. Click: **"Download ZIP"**
4. Find the ZIP file in your Downloads folder
5. **Right-click** the ZIP → **"Extract All..."**
6. Extract to: `C:\ASA` (Windows) or `~/Desktop/ASA` (Mac/Linux)
7. ✅ Done!

### Method 2: Clone with Git (Recommended)

1. **Windows:**
   - Press **Windows Key + R**
   - Type: `cmd` and press **Enter**
   - Type these commands one at a time:
     ```
     cd Desktop
     git clone https://github.com/YOUR-USERNAME/ASA.git
     cd ASA
     ```

2. **Mac/Linux:**
   - Open Terminal
   - Type:
     ```bash
     cd ~/Desktop
     git clone https://github.com/YOUR-USERNAME/ASA.git
     cd ASA
     ```

**Replace `YOUR-USERNAME`** with your actual GitHub username!

---

## ⚙️ Setting Up ASA

### Part 1: Set Up the Backend (The Brain)

The backend is the smart part that talks to OpenAI.

#### Step 1: Open Command Prompt/Terminal in the ASA folder

**Windows:**
1. Open File Explorer
2. Go to the `ASA` folder (where you extracted/cloned it)
3. Click in the address bar (where it shows the path)
4. Type: `cmd` and press **Enter**
5. A Command Prompt window opens in that folder!

**Mac:**
1. Open Finder, go to the ASA folder
2. Right-click the folder → **"Services"** → **"New Terminal at Folder"**

**Linux:**
1. Right-click the ASA folder → **"Open in Terminal"**

#### Step 2: Go to Backend Folder

Type this command and press **Enter**:
```bash
cd backend
```

#### Step 3: Install Python Packages

Type these commands one at a time:

**Windows:**
```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt
```

**What's happening?** This downloads all the Python "ingredients" ASA needs.

**How long?** 2-5 minutes. You'll see lots of text scrolling. That's normal!

**Done when:** You see your cursor blinking again (ready for next command).

#### Step 4: Set Up Database

Type:

**Windows:**
```cmd
python -m alembic upgrade head
```

**Mac/Linux:**
```bash
python3 -m alembic upgrade head
```

**What's happening?** Creating a database to store information about your bug fix tasks.

**What is Alembic?** Think of it like a "save point" system for your database. When the code changes and needs new database tables or columns, Alembic safely updates your database without losing data. It's already set up - you just need to run this command once!

**You should see:**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Running upgrade  -> 338cc9f9ac27, Initial migration with all models
```

✅ Database is ready!

---

### Part 2: Set Up the Frontend (The Website)

The frontend is the part you see and click.

#### Step 1: Go Back and Enter Frontend Folder

Type these commands:
```bash
cd ..
cd frontend
```

(`..` means "go back one folder")

#### Step 2: Install Node Packages

Type:
```bash
npm install
```

**How long?** 3-7 minutes. Lots of text will scroll. That's normal!

**Done when:** You see `added XXX packages` and your cursor is back.

---

### Part 3: Create Configuration File (IMPORTANT!)

This file holds your secret keys. We need to create it!

#### Step 1: Go Back to Backend Folder

Type:
```bash
cd ..
cd backend
```

#### Step 2: Create the .env File

**Windows:**
```cmd
notepad .env
```
When Notepad asks "Cannot find the file. Do you want to create a new file?", click **"Yes"**

**Mac:**
```bash
nano .env
```

**Linux:**
```bash
nano .env
```

#### Step 3: Copy This Text into the File

Copy and paste this EXACTLY:

```
# OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# GitHub Personal Access Token
GITHUB_TOKEN=ghp_your-token-here

# Database URL
DATABASE_URL=sqlite:///./asa.db

# Enable detailed logging (optional)
ENABLE_OPENTELEMETRY=false

# Model Configuration
DEFAULT_MODEL=gpt-4o-mini
```

#### Step 4: Replace Your Keys

1. Find the line: `OPENAI_API_KEY=sk-your-key-here`
2. Replace `sk-your-key-here` with your ACTUAL OpenAI key (from Step 7)
3. Find the line: `GITHUB_TOKEN=ghp_your-token-here`
4. Replace `ghp_your-token-here` with your ACTUAL GitHub token (from Step 6)

**Example of what it should look like:**
```
OPENAI_API_KEY=sk-abc123def456ghi789jkl012mno345pqr678stu
GITHUB_TOKEN=ghp_xyz789abc123def456ghi789jkl012mno345pqr
```

#### Step 5: Save the File

**Windows (Notepad):**
- Click: **File** → **Save**
- Close Notepad

**Mac/Linux (nano):**
- Press: **Ctrl + X**
- Press: **Y** (for "Yes, save")
- Press: **Enter**

**⚠️ SUPER IMPORTANT:**
- Never share this file with anyone!
- Never upload it to GitHub!
- It contains your secret keys!

---

## 🚀 Running ASA

Now the fun part! Let's start everything up.

**⚠️ IMPORTANT:** ASA needs **4 things running** at the same time:
1. Redis (database for task queue)
2. Backend server (the API)
3. Background worker (processes tasks)
4. Frontend website (the UI)

We'll start them one by one, each in its own terminal window.

---

### Part 1: Start Redis

**What is Redis?** A fast database that ASA uses to manage the task queue.

#### Step 1: Open a Terminal

**Windows:** Press Windows Key + R, type `cmd`, press Enter

**Mac/Linux:** Open Terminal app

#### Step 2: Start Redis with Docker

Type:
```bash
docker run -d -p 6379:6379 --name asa-redis redis:latest
```

**What's happening?**
- Downloads Redis (first time only, ~30MB)
- Runs it in the background
- Connects it to port 6379

**First time:** You'll see downloading messages (wait 1-2 minutes)
**After first time:** Starts instantly

**You should see:** A long container ID like `abc123def456...`

**✅ Redis is running!**

**To check it's running:**
```bash
docker ps
```
You should see `asa-redis` in the list.

---

### Part 2: Start the Backend Server

#### Step 1: Open a NEW Terminal Window

**Don't close the first one!** We need Redis to keep running.

**Windows:** Press Windows Key + R, type `cmd`, press Enter

**Mac/Linux:** Open a new Terminal window

#### Step 2: Go to Backend Folder

Type:
```bash
cd C:\Users\gsrev\OneDrive\Desktop\ASA\backend
```
(Adjust path if you put ASA somewhere else)

#### Step 3: Start the Server

Type:

**Windows:**
```cmd
python -m uvicorn app.main:app --reload
```

**Mac/Linux:**
```bash
python3 -m uvicorn app.main:app --reload
```

#### Step 4: Wait for Success Message

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**✅ Backend is running!**

**⚠️ KEEP THIS WINDOW OPEN!** Don't close it. Minimize it if you want.

#### Step 5: Test It

1. Open your web browser
2. Go to: `http://localhost:8000/docs`
3. You should see a fancy page with "FastAPI" at the top
4. ✅ It works!

---

### Part 3: Start the Background Worker

**What is this?** The worker processes your bug fix tasks in the background.

#### Step 1: Open ANOTHER New Terminal Window

**Keep the other two running!** (Redis and Backend)

#### Step 2: Go to Backend Folder

Type:
```bash
cd C:\Users\gsrev\OneDrive\Desktop\ASA\backend
```

#### Step 3: Start the Worker

Type:

**Windows:**
```bash
python start_worker.py
```

**Mac/Linux:**
```bash
rq worker asa_tasks --with-scheduler
```

**Why different?** Windows doesn't support the `fork()` system call, so we use a special script instead.

**You should see:**
```
INFO: Worker started
INFO: Listening on default queue
```

**✅ Worker is running!**

**⚠️ KEEP THIS WINDOW OPEN TOO!**

---

### Part 4: Start the Frontend Website

#### Step 1: Open YET ANOTHER Terminal Window

**Keep all three previous ones running!** (Redis, Backend, Worker)

**Windows:**
- Press **Windows Key + R**
- Type: `cmd`
- Press **Enter**

**Mac:**
- Press **Cmd + Space**
- Type: `Terminal`
- Press **Enter**

#### Step 2: Go to Frontend Folder

Type:
```bash
cd Desktop/ASA/frontend
```

(Adjust path if you put ASA somewhere else)

#### Step 3: Start the Website

Type:
```bash
npm start
```

#### Step 4: Website Opens Automatically

- A browser window should open automatically
- You'll see the ASA web interface!
- If it doesn't open, manually go to: `http://localhost:3000`

**✅ Frontend is running!**

---

## 🎮 Using ASA to Fix Bugs

### Example: Fix a Bug in Your Code

1. **Make sure you have a GitHub repository**
   - If you don't have one, create a test repo on GitHub
   - Upload some code with a bug

2. **In the ASA web interface** (http://localhost:3000):

   You'll see a form with three boxes:

   **Repository URL:**
   - Paste your GitHub repo URL
   - Example: `https://github.com/username/my-project`

   **Bug Description:**
   - Describe the bug in plain English
   - Example: "The login button doesn't work when I click it"
   - Example: "The homepage shows an error message"

   **Test Command:** (optional)
   - How to run your tests
   - Example: `npm test` (for JavaScript projects)
   - Example: `pytest` (for Python projects)
   - Example: Leave blank if you don't have tests

3. **Click "Submit Task"**

4. **Watch the Progress:**
   - The task appears in the list
   - Status updates every few seconds
   - You'll see: QUEUED → CLONING_REPO → TESTING → FIXING → COMPLETED

5. **Check the Results:**
   - When status shows "COMPLETED"
   - Go to your GitHub repository
   - Click "Pull requests" tab
   - You'll see a new PR created by ASA!
   - Review the fix
   - If it looks good, click "Merge pull request"

---

## 🔧 Common Problems and Solutions

### Problem: "python: command not found"

**Why:** Python isn't installed or not in PATH

**Fix:**
1. Make sure you installed Python (see Step 1)
2. **Windows:** Restart Command Prompt
3. **Mac/Linux:** Try `python3` instead of `python`
4. **Windows:** Did you check "Add Python to PATH" during install? If not, reinstall Python

---

### Problem: "npm: command not found"

**Why:** Node.js isn't installed

**Fix:**
1. Make sure you installed Node.js (see Step 2)
2. Restart your terminal/command prompt
3. **Windows:** Restart your computer

---

### Problem: "Port 8000 already in use"

**Why:** Another program is using port 8000, or you started the backend twice

**Fix Option 1:** Stop the other program
**Fix Option 2:** Use a different port:
```bash
python -m uvicorn app.main:app --reload --port 8001
```
(Then use `http://localhost:8001` instead of 8000)

---

### Problem: "Docker daemon not running"

**Why:** Docker Desktop isn't started

**Fix:**
1. **Windows:** Look for Docker Desktop in Start Menu, click it
2. **Mac:** Look for Docker in Applications, open it
3. Wait for the whale icon to appear and stop animating
4. Try your command again

---

### Problem: "OpenAI API Error: Incorrect API key"

**Why:** Your API key in `.env` is wrong

**Fix:**
1. Open the `.env` file in the backend folder
2. Check your `OPENAI_API_KEY=...` line
3. Make sure the FULL key is there (starts with `sk-`)
4. No spaces before or after the `=`
5. Save the file
6. Stop the backend (Ctrl+C) and start it again

---

### Problem: "GitHub Authentication Failed"

**Why:** Your GitHub token in `.env` is wrong

**Fix:**
1. Open `.env` file
2. Check your `GITHUB_TOKEN=...` line
3. Make sure the FULL token is there (starts with `ghp_`)
4. Create a new token if needed (see Step 6)
5. Save and restart backend

---

### Problem: "Module not found" or "Import Error"

**Why:** Python packages not installed

**Fix:**
```bash
cd backend
pip install -r requirements.txt
```

---

### Problem: Frontend Shows "Cannot connect to backend"

**Why:** Backend isn't running

**Fix:**
1. Make sure the backend terminal window is still open
2. You should see: "Uvicorn running on http://127.0.0.1:8000"
3. If not, start the backend again (see "Part 1: Start the Backend")

---

### Problem: "Database Error" or "Table doesn't exist"

**Why:** Database not set up correctly or out of sync with code

**Fix Option 1** (Safe - keeps your data):
```bash
cd backend
# Check current migration status
python -m alembic current

# Apply any pending migrations
python -m alembic upgrade head
```

**Fix Option 2** (Fresh start - DELETES ALL DATA):
```bash
cd backend
# Delete old database (WARNING: You'll lose all task history!)
del asa.db  # Windows
rm asa.db   # Mac/Linux

# Create fresh database
python -m alembic upgrade head
```

**What's the difference?**
- **Option 1:** Keeps your existing tasks and data, just updates the database structure
- **Option 2:** Deletes everything and starts fresh (only use if Option 1 doesn't work)

---

### Problem: Everything Installed But Still Not Working

**Nuclear Option:** Start fresh

```bash
# Stop both frontend and backend (Ctrl+C in both terminals)

# Backend fresh start:
cd backend
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
python -m alembic upgrade head

# Frontend fresh start:
cd ../frontend
rmdir /s node_modules  # Windows
rm -rf node_modules    # Mac/Linux
npm install
```

---

## 💰 How Much Does This Cost?

### OpenAI API Costs:

The only thing that costs money is OpenAI. How much you pay depends on how much you use it:

| Usage | Approximate Cost |
|-------|------------------|
| Testing (5-10 small bugs) | $0.50 - $2.00 |
| Regular use (20-30 bugs/month) | $2.00 - $10.00 |
| Heavy use (50+ bugs/month) | $10.00 - $30.00 |

**Tips to save money:**
1. Set a monthly budget limit in your OpenAI account ($10 is good for testing)
2. Use the cheaper model: `gpt-4o-mini` (already set in `.env`)
3. Only use ASA for real bugs, not testing

### Everything Else is FREE!
- Python: Free ✅
- Node.js: Free ✅
- Docker: Free ✅
- GitHub: Free ✅
- VS Code: Free ✅

---

## 📚 Learn More

### Helpful Resources:

**Beginner Tutorials:**
- Python: https://www.learnpython.org/
- Git: https://try.github.io/
- Command Line: Search YouTube for "command line for beginners"

**Documentation:**
- Read `COMPLETE_IMPLEMENTATION.md` for detailed technical info
- Check `BLUEPRINT_COMPLETION_REPORT.md` for implementation details

**Database Migrations:**
ASA uses Alembic to manage database changes safely. If you're a developer modifying the code:
- `python -m alembic current` - See current database version
- `python -m alembic history` - See all migration history
- `python -m alembic upgrade head` - Apply all pending migrations
- `python -m alembic revision --autogenerate -m "Description"` - Create new migration after changing models.py

### Video Tutorials:
Search on YouTube for:
- "How to use command prompt for beginners"
- "Git and GitHub for beginners"
- "Python basics for complete beginners"

---

## 🆘 Getting Help

If you're stuck:

### Step 1: Read the Error Message
The error message usually tells you what's wrong. Look for:
- "No such file or directory" → You're in the wrong folder
- "Command not found" → Software not installed
- "Permission denied" → Run as administrator/sudo
- "Port already in use" → Something already using that port

### Step 2: Check This Guide
- Look in the "Common Problems" section above
- Make sure you followed every step

### Step 3: Check the Logs
- **Backend logs:** Look at the terminal where uvicorn is running
- **Frontend logs:** Look at the terminal where npm is running
- Errors will be in red text usually

### Step 4: Google the Error
- Copy the error message
- Google it
- Someone has probably had the same problem!

### Step 5: Ask for Help
- Create an issue on GitHub
- Include:
  - What you were trying to do
  - What happened instead
  - The full error message
  - Your operating system (Windows/Mac/Linux)

---

## ✅ Quick Checklist

Before running ASA, make sure:

- [ ] Python 3.11 installed (`python --version` works)
- [ ] Node.js 18 installed (`node --version` works)
- [ ] Git installed (`git --version` works)
- [ ] Docker installed and running (whale icon visible)
- [ ] GitHub account created
- [ ] OpenAI account created with payment method
- [ ] ASA code downloaded
- [ ] `.env` file created with your keys
- [ ] Backend packages installed (`pip install -r requirements.txt`)
- [ ] Frontend packages installed (`npm install`)
- [ ] Database created (`alembic upgrade head`)

---

## 🎉 You Did It!

Congratulations! You now have ASA running on your computer.

**What's next?**
1. Try fixing a real bug in your code
2. Experiment with different bug descriptions
3. Read `COMPLETE_IMPLEMENTATION.md` to understand how ASA works
4. Customize ASA for your specific needs

**Remember:**
- Redis must be running (port 6379)
- The backend must be running (port 8000)
- The worker must be running (processes tasks)
- The frontend must be running (port 3000)
- Keep all 4 windows/processes running while using ASA
- Don't share your `.env` file with anyone!

**Happy bug fixing!** 🐛➡️✨

---

## 📞 Quick Reference

**You need 4 terminal windows running:**

**Terminal 1 - Redis:**
```bash
docker run -d -p 6379:6379 --name asa-redis redis:latest
```

**Terminal 2 - Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload
```

**Terminal 3 - Worker:**

Windows:
```bash
cd backend
python start_worker.py
```

Mac/Linux:
```bash
cd backend
rq worker asa_tasks --with-scheduler
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm start
```

**Access Points:**
- Frontend UI: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Stop Everything:**
- Press `Ctrl + C` in terminals 2, 3, and 4
- Stop Redis: `docker stop asa-redis`

**Restart Everything Next Time:**

```bash
# Terminal 1
docker start asa-redis

# Terminal 2
cd backend && python -m uvicorn app.main:app --reload

# Terminal 3 (Windows)
cd backend && python start_worker.py

# Terminal 3 (Mac/Linux)
cd backend && rq worker asa_tasks --with-scheduler

# Terminal 4
cd frontend && npm start
```

---

*Made with ❤️ for developers who hate bugs*
