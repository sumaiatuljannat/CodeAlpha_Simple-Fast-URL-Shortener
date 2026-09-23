# ⚡ LinkSnap - URL Shortener Web Application

A clean, beginner-friendly, and lightweight URL Shortener web application built with **Python 3**, **Flask**, and **SQLite**. It allows users to convert long, unwieldy URLs into clean, compact links, redirects visitors in real-time, and tracks click analytics.

---

## 🌟 Features

- **Instant URL Shortening**: Generates unique, 6-character alphanumeric short codes.
- **Fast Redirection**: High-performance HTTP 302 redirection directly to the target URL.
- **Click Tracking & Analytics**: Tracks real-time click counts and timestamps for each link.
- **Input Validation & Security**:
  - Rejects empty submissions.
  - Ensures valid `http://` or `https://` protocols and domains.
  - Utilizes parameterized SQLite queries to prevent SQL injection vulnerabilities.
  - Escapes user inputs in Jinja2 templates.
- **User-Friendly Error Handling**:
  - Graceful custom 404 page for missing/expired short codes.
  - Friendly flash notifications for invalid submissions.
- **Modern Responsive Interface**:
  - Beautiful, minimalist UI crafted with pure CSS3 (no heavy UI frameworks needed).
  - One-click copy to clipboard with real-time visual feedback.
  - Fully responsive across desktop, tablet, and mobile screens.

---

## 🛠️ Technologies Used

- **Backend**: Python 3, Flask 3.1
- **Database**: SQLite3 (Standard Python Library)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (ES6)

---

## 📁 Project Structure

```text
url-shortener/
│
├── app.py              # Main Flask application & route controllers
├── schema.sql          # Database table schema definition
├── database.db         # SQLite database file (created automatically on startup)
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
│
├── templates/          # Jinja2 HTML templates
│   ├── index.html      # Home page (form & generated link display)
│   ├── stats.html      # Click analytics and details page
│   ├── 404.html        # Custom 404 Not Found page
│   └── error.html      # General error handling page
│
└── static/             # Static frontend assets
    ├── style.css       # Responsive custom CSS styles
    └── script.js       # Clipboard copy and client interactions
```

---

## 🚀 Installation & Setup on Windows

### 1. Clone or Open the Project
Open PowerShell or Command Prompt and navigate into the project directory:
```powershell
cd url-shortener
```

### 2. Create and Activate Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate on PowerShell:
.\venv\Scripts\Activate.ps1

# (Or on Command Prompt cmd.exe):
.\venv\Scripts\activate.bat
```

> **Note for PowerShell Users:** If you get an execution policy error, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 🏃 Running the Application

Start the Flask development server:
```powershell
python app.py
```

You will see:
```text
Database initialized successfully.
Starting Flask development server on http://127.0.0.1:5000 ...
 * Running on http://127.0.0.1:5000
```

Open your browser and visit: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 💡 Example Usage

1. **Shorten a Link**:
   - Enter `https://github.com/torvalds/linux` into the input box and click **Shorten URL**.
   - Get a short link like `http://127.0.0.1:5000/aB3x9z`.
2. **Copy & Share**:
   - Click **Copy Link** to copy it straight to your clipboard.
3. **Test Redirection**:
   - Paste `http://127.0.0.1:5000/aB3x9z` into a new tab and press Enter. You will instantly be redirected to the original GitHub repository.
4. **View Statistics**:
   - Navigate to `http://127.0.0.1:5000/stats/aB3x9z` to view the total clicks and link creation timestamp.

---

## 📸 Screenshots

*(Placeholder: Add screenshots of the Home page, generated link card, and analytics view here)*

| Home Page | Shortened Result | Statistics View |
| :---: | :---: | :---: |
| ![Home](https://via.placeholder.com/400x250?text=Home+Page) | ![Result](https://via.placeholder.com/400x250?text=Result+Card) | ![Stats](https://via.placeholder.com/400x250?text=Stats+Page) |

---

## 🔮 Future Improvements

- [ ] Custom custom aliases (e.g. `localhost:5000/my-custom-link`).
- [ ] Link expiration dates (TTL).
- [ ] QR code generation for shortened links.
- [ ] Geographic and referrer analytics breakdown.
- [ ] User authentication and personal link dashboard.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
