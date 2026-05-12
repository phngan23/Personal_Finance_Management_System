# Personal Finance Management System (PFMS) - FinTrack

FinTrack is a comprehensive desktop application designed to help individuals, particularly students and young professionals in Vietnam, manage their personal finances effectively. This project integrates a robust **MySQL 8.0** backend with a modern **Python (CustomTkinter)** frontend, emphasizing database-level automation and data integrity.

## 🚀 Key Features

- **Multi-Source Account Management**: Track various fund sources, including Cash and Bank accounts.
- **Transaction Tracking**: Easily record, update, and delete income and expense entries.
- **Real-time Balance Synchronization**: Powered by a full-lifecycle suite of **6 Database Triggers** that ensure account balances are always accurate, even during account-to-account transfers.
- **Budget Planning & Alerts**: Set monthly spending limits per category. Visual alerts (OK, WARNING, EXCEEDED) are generated via database views based on real-time consumption.
- **Advanced Analytics**: 
  - **Performance Snapshots**: Side-by-side numerical summaries of daily, monthly, and yearly net savings.
  - **Visual Reports**: Interactive charts (Income vs. Expenses, Category Distribution, and Cumulative Balance Trend) with hover tooltips.
- **Robust Security**: Implements the Principle of Least Privilege (PoLP) with a restricted MySQL user (`finance_app`).

## 🛠️ Tech Stack

- **Database**: MySQL 8.0 (Views, Triggers, Stored Procedures, UDFs, Indexes)
- **Programming Language**: Python 3.x
- **GUI Framework**: CustomTkinter
- **Data Visualization**: Matplotlib & NumPy
- **Database Connector**: `mysql-connector-python`

## 🏗️ System Architecture

The project follows a structured **3-Layer Architecture**:
1. **Presentation Layer (`main.py`)**: Handles the UI and user interactions.
2. **Business Logic Layer (`models.py` & `reports.py`)**: Manages data processing and chart generation.
3. **Data Layer (MySQL)**: Enforces business invariants and maintains data integrity through advanced DB objects.

## 📂 Project Structure

```text
personal-finance/
├── database/
│   ├── schema.sql        # Table definitions and constraints
│   ├── sample_data.sql   # Large-scale dataset (50 users, 100 accounts, 1000+ records)
│   ├── objects.sql       # Views, Triggers, SPs, and UDFs
│   └── security.sql      # Database user roles and privileges
├── app/
│   ├── main.py           # Main GUI application
│   ├── models.py         # Database CRUD operations
│   ├── reports.py        # Matplotlib chart generators
│   └── db_connection.py  # Centralized connection factory
├── screenshot/           # Application screenshots
├── Topic.pdf             # Original project brief
└── ERD.png               # Entity-Relationship Diagram
```

## ⚙️ Installation & Setup
### Clone the repository

```bash
git clone https://github.com/phngan23/Personal_Finance_Management_System
cd Personal_Finance_Management_System
```

### Database Setup
- Import `database/schema.sql`, `database/objects.sql`, and `database/sample_data.sql` into your MySQL server.
- Run `database/security.sql` to set up the restricted user.

### Install Dependencies
```bash
pip install customtkinter mysql-connector-python matplotlib numpy
```

### Run the Application
```bash
python app/main.py
```
<img width="2879" height="1699" alt="dashboard" src="https://github.com/user-attachments/assets/584a4551-9d21-4bcc-b5e3-ac1f6d1ed43b" />

## Youtube Video Demo 
https://youtu.be/JX6rUBDnL4M

## 🤝 Acknowledgments
- Developer: Nguyen Phuong Ngan (Class DSEB 66B - NEU)
- Instructor: PhD. Tran Hung 

