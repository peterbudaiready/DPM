import streamlit as st
import pandas as pd
import sqlite3
import os
import datetime

# --- SETUP ---
system_current_date = datetime.date.today()
last_month_date = pd.Timestamp(system_current_date - datetime.timedelta(days=30))

st.set_page_config(layout="wide")

# Database
DB_FILE = "data.db"
EXPENSES_TABLE = "expenses"
PROJECTS_TABLE = "projects"
TASKS_TABLE = "tasks"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Expenses table
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {EXPENSES_TABLE} (
            Name TEXT,
            Web TEXT,
            Date DATE,
            Type TEXT,
            Price INTEGER,
            Comment TEXT
        )
    """)

    # Projects table
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {PROJECTS_TABLE} (
            Name TEXT,
            Client TEXT,
            Status TEXT,
            Type TEXT,
            Deadline DATE,
            Price INTEGER,
            Comments TEXT,
            Effort TEXT,
            Time TEXT
        )
    """)

    # Tasks table
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {TASKS_TABLE} (
            Task TEXT,
            Notes TEXT,
            Website TEXT,
            Priority TEXT
        )
    """)

    conn.commit()
    conn.close()

def load_table(table_name, expected_columns):
    if os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        except Exception as e:
            st.error(f"Error loading {table_name}: {e}")
            df = pd.DataFrame(columns=list(expected_columns.keys()))
        conn.close()
    else:
        df = pd.DataFrame(columns=list(expected_columns.keys()))

    for col, default_val in expected_columns.items():
        if col not in df.columns:
            df[col] = default_val
    return df

def save_table(df, table_name):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

# --- INIT ---
init_db()

# Configs
expected_expenses_columns = {
    "Name": "",
    "Web": "",
    "Date": system_current_date,
    "Type": "one",
    "Price": 0,
    "Comment": ""
}

expected_projects_columns = {
    "Name": "",
    "Client": "",
    "Status": "pre-start",
    "Type": "",
    "Deadline": system_current_date,
    "Price": 0,
    "Comments": "",
    "Effort": "0%",
    "Time": ""
}

expected_tasks_columns = {
    "Task": "",
    "Notes": "",
    "Website": "",
    "Priority": "medium"
}

# Load data
expenses_df = load_table(EXPENSES_TABLE, expected_expenses_columns)
projects_df = load_table(PROJECTS_TABLE, expected_projects_columns)
tasks_df = load_table(TASKS_TABLE, expected_tasks_columns)

# --- METRICS SECTION ---
st.title("📊 Dashboard Overview")

# Parse dates
expenses_df["Date"] = pd.to_datetime(expenses_df["Date"], errors="coerce")
projects_df["Deadline"] = pd.to_datetime(projects_df["Deadline"], errors="coerce")

# Filter last 30 days
last_expenses = expenses_df[expenses_df["Date"] >= last_month_date]
prev_expenses = expenses_df[expenses_df["Date"] < last_month_date]
last_projects = projects_df[projects_df["Deadline"] >= last_month_date]
prev_projects = projects_df[projects_df["Deadline"] < last_month_date]

# Metrics calc
income_now = last_projects["Price"].sum()
income_prev = prev_projects["Price"].sum()
income_delta = income_now - income_prev
income_percent = f"{((income_delta / income_prev) * 100):.1f}%" if income_prev else "N/A"

expenses_now = last_expenses["Price"].sum()
expenses_prev = prev_expenses["Price"].sum()
expenses_delta = expenses_now - expenses_prev
expenses_percent = f"{((expenses_delta / expenses_prev) * 100):.1f}%" if expenses_prev else "N/A"

# Productivity estimate
def compute_productivity(row):
    try:
        effort = float(row["Effort"].replace("%", "")) / 100
        time_val = row["Time"]
        time_hours = 1
        if "h" in time_val:
            time_hours = float(time_val.replace("h", ""))
        elif "d" in time_val:
            time_hours = float(time_val.replace("d", "")) * 24
        return (row["Price"] * effort) / time_hours if time_hours else 0
    except:
        return 0

last_projects["ProductivityScore"] = last_projects.apply(compute_productivity, axis=1)
productivity_now = last_projects["ProductivityScore"].sum()
prev_projects["ProductivityScore"] = prev_projects.apply(compute_productivity, axis=1)
productivity_prev = prev_projects["ProductivityScore"].sum()
productivity_delta = productivity_now - productivity_prev
productivity_percent = f"{((productivity_delta / productivity_prev) * 100):.1f}%" if productivity_prev else "N/A"

# Project count
project_count_now = len(last_projects)
project_count_prev = len(prev_projects)
project_count_delta = project_count_now - project_count_prev
project_count_percent = f"{((project_count_delta / project_count_prev) * 100):.1f}%" if project_count_prev else "N/A"

# Display
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Income (30d)", f"${income_now}", income_percent, border=True)
col2.metric("💸 Expenses (30d)", f"${expenses_now}", expenses_percent, border=True)
col3.metric("⚙️ Productivity", f"{productivity_now:.1f}", productivity_percent, border=True)
col4.metric("📁 Project Count", project_count_now, project_count_percent, border=True)

st.markdown("---")

# --- MAIN DATA TABS ---
with st.container():
    tabs = st.tabs(["📁 Projects", "💸 Expenses", "✅ Tasks"])

    # --- Projects Tab ---
    with tabs[0]:
        st.subheader("Projects")
        if projects_df.empty:
            projects_df = pd.DataFrame({k: [v] for k, v in expected_projects_columns.items()})
        projects_df["Deadline"] = pd.to_datetime(projects_df["Deadline"], errors="coerce").dt.date

        projects_column_config = {
            "Name": "Name",
            "Client": "Client",
            "Status": st.column_config.SelectboxColumn("Status", options=["pre-start", "working", "done"]),
            "Type": "Type",
            "Deadline": st.column_config.DateColumn("Deadline"),
            "Price": st.column_config.NumberColumn("Price", format="$%d"),
            "Comments": "Comments",
            "Effort": st.column_config.TextColumn("Effort (%)", help="e.g. 75%"),
            "Time": st.column_config.TextColumn("Time", help="e.g. 12h or 3d")
        }

        edited_projects_df = st.data_editor(
            projects_df,
            column_config=projects_column_config,
            num_rows="dynamic",
            use_container_width=True,
            key="projects_editor"
        )

        if st.button("Save Projects Changes"):
            save_table(edited_projects_df, PROJECTS_TABLE)
            st.success("Projects saved!")

    # --- Expenses Tab ---
    with tabs[1]:
        st.subheader("Expenses")
        if expenses_df.empty:
            expenses_df = pd.DataFrame({k: [v] for k, v in expected_expenses_columns.items()})
        expenses_df["Date"] = pd.to_datetime(expenses_df["Date"], errors="coerce").dt.date

        expenses_column_config = {
            "Name": "Name",
            "Web": st.column_config.LinkColumn("Web"),
            "Date": st.column_config.DateColumn("Date"),
            "Type": st.column_config.SelectboxColumn("Type", options=["one", "monthly"]),
            "Price": st.column_config.NumberColumn("Price", format="$%d"),
            "Comment": "Comment"
        }

        edited_expenses_df = st.data_editor(
            expenses_df,
            column_config=expenses_column_config,
            num_rows="dynamic",
            use_container_width=True,
            key="expenses_editor"
        )

        if st.button("Save Expenses Changes"):
            save_table(edited_expenses_df, EXPENSES_TABLE)
            st.success("Expenses saved!")

    # --- Tasks Tab ---
    with tabs[2]:
        st.subheader("Tasks")
        if tasks_df.empty:
            tasks_df = pd.DataFrame({k: [v] for k, v in expected_tasks_columns.items()})

        tasks_column_config = {
            "Task": "Task",
            "Notes": "Notes",
            "Website": st.column_config.LinkColumn("Website"),
            "Priority": st.column_config.SelectboxColumn("Priority", options=["low", "medium", "Urgent"])
        }

        edited_tasks_df = st.data_editor(
            tasks_df,
            column_config=tasks_column_config,
            num_rows="dynamic",
            use_container_width=True,
            key="tasks_editor"
        )

        if st.button("Save Tasks Changes"):
            save_table(edited_tasks_df, TASKS_TABLE)
            st.success("Tasks saved!")

# --- CHART ALWAYS VISIBLE ---
st.markdown("---")
st.header("📈 Expenses and Projects Over Time")

expenses_chart_data = expenses_df[["Date", "Price"]].copy()
expenses_chart_data.rename(columns={"Date": "Time", "Price": "Expenses"}, inplace=True)

projects_chart_data = projects_df[["Deadline", "Price"]].copy()
projects_chart_data.rename(columns={"Deadline": "Time", "Price": "Projects"}, inplace=True)

combined_chart_data = pd.merge(
    expenses_chart_data,
    projects_chart_data,
    on="Time",
    how="outer"
).sort_values("Time").fillna(0)

st.line_chart(combined_chart_data.set_index("Time"))
