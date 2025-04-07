import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client

# --- CONFIG ---
SUPABASE_URL = "https://pckftxhpmfebxlnfhepq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBja2Z0eGhwbWZlYnhsbmZoZXBxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDMzNjQxNjMsImV4cCI6MjA1ODk0MDE2M30.5QhW4hOEpDg1CVHZuC_4-pgQ8LiX4f2EFFBq1R2gBJA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

system_current_date = datetime.date.today()
last_month_date = pd.Timestamp(system_current_date - datetime.timedelta(days=30))
st.set_page_config(layout="wide")

# Table names
EXPENSES_TABLE = "expenses"
PROJECTS_TABLE = "projects"
TASKS_TABLE = "tasks"

# --- Data Loaders & Savers ---
def load_table(table_name: str) -> pd.DataFrame:
    response = supabase.table(table_name).select("*").execute()
    return pd.DataFrame(response.data)

def save_table(df: pd.DataFrame, table_name: str):
    supabase.table(table_name).delete().neq("id", 0).execute()  # Clear table
    
    for _, row in df.iterrows():
        data = row.to_dict()

        # Convert datetime/date/Timestamp to ISO string
        for k, v in data.items():
            if isinstance(v, (datetime.datetime, datetime.date, pd.Timestamp)):
                data[k] = v.isoformat()

        data.pop("id", None)  # Remove ID if present
        supabase.table(table_name).insert(data).execute()

# --- Load Tables ---
expenses_df = load_table(EXPENSES_TABLE)
projects_df = load_table(PROJECTS_TABLE)
tasks_df = load_table(TASKS_TABLE)

# --- Default values if empty ---
if expenses_df.empty:
    expenses_df = pd.DataFrame([{
        "name": "", "web": "", "date": system_current_date,
        "type": "one", "price": 0, "comment": ""
    }])

if projects_df.empty:
    projects_df = pd.DataFrame([{
        "name": "", "client": "", "status": "pre-start", "type": "",
        "deadline": system_current_date, "price": 0,
        "comments": "", "effort": "0%", "time": ""
    }])

if tasks_df.empty:
    tasks_df = pd.DataFrame([{
        "task": "", "notes": "", "website": "", "priority": "medium"
    }])

# --- METRICS ---
st.title("📊 Dashboard Overview")

expenses_df["date"] = pd.to_datetime(expenses_df["date"], errors="coerce")
projects_df["deadline"] = pd.to_datetime(projects_df["deadline"], errors="coerce")

last_expenses = expenses_df[expenses_df["date"] >= last_month_date]
prev_expenses = expenses_df[expenses_df["date"] < last_month_date]
last_projects = projects_df[projects_df["deadline"] >= last_month_date]
prev_projects = projects_df[projects_df["deadline"] < last_month_date]

income_now = last_projects["price"].sum()
income_prev = prev_projects["price"].sum()
income_percent = f"{((income_now - income_prev) / income_prev * 100):.1f}%" if income_prev else "N/A"

expenses_now = last_expenses["price"].sum()
expenses_prev = prev_expenses["price"].sum()
expenses_percent = f"{((expenses_now - expenses_prev) / expenses_prev * 100):.1f}%" if expenses_prev else "N/A"

def compute_productivity(row):
    try:
        effort = float(row["effort"].replace("%", "")) / 100
        time_val = row["time"]
        time_hours = 1
        if "h" in time_val:
            time_hours = float(time_val.replace("h", ""))
        elif "d" in time_val:
            time_hours = float(time_val.replace("d", "")) * 24
        return (row["price"] * effort) / time_hours if time_hours else 0
    except:
        return 0

last_projects["ProductivityScore"] = last_projects.apply(compute_productivity, axis=1)
prev_projects["ProductivityScore"] = prev_projects.apply(compute_productivity, axis=1)
productivity_now = last_projects["ProductivityScore"].sum()
productivity_prev = prev_projects["ProductivityScore"].sum()
productivity_percent = f"{((productivity_now - productivity_prev) / productivity_prev * 100):.1f}%" if productivity_prev else "N/A"

project_count_now = len(last_projects)
project_count_prev = len(prev_projects)
project_count_percent = f"{((project_count_now - project_count_prev) / project_count_prev * 100):.1f}%" if project_count_prev else "N/A"

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Income (30d)", f"${income_now}", income_percent, border=True)
col2.metric("💸 Expenses (30d)", f"${expenses_now}", expenses_percent, border=True)
col3.metric("⚙️ Productivity", f"{productivity_now:.1f}", productivity_percent, border=True)
col4.metric("📁 Project Count", project_count_now, project_count_percent, border=True)

st.markdown("---")

# --- TABS UI ---
with st.container():
    tabs = st.tabs(["📁 Projects", "💸 Expenses", "✅ Tasks"])

    with tabs[0]:
        st.subheader("Projects")
        projects_column_config = {
            "name": "Name",
            "client": "Client",
            "status": st.column_config.SelectboxColumn("Status", options=["pre-start", "working", "done"]),
            "type": "Type",
            "deadline": st.column_config.DateColumn("Deadline"),
            "price": st.column_config.NumberColumn("Price", format="$%d"),
            "comments": "Comments",
            "effort": st.column_config.TextColumn("Effort (%)", help="e.g. 75%"),
            "time": st.column_config.TextColumn("Time", help="e.g. 12h or 3d")
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

    with tabs[1]:
        st.subheader("Expenses")
        expenses_column_config = {
            "name": "Name",
            "web": st.column_config.LinkColumn("Web"),
            "date": st.column_config.DateColumn("Date"),
            "type": st.column_config.SelectboxColumn("Type", options=["one", "monthly"]),
            "price": st.column_config.NumberColumn("Price", format="$%d"),
            "comment": "Comment"
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

    with tabs[2]:
        st.subheader("Tasks")
        tasks_column_config = {
            "task": "Task",
            "notes": "Notes",
            "website": st.column_config.LinkColumn("Website"),
            "priority": st.column_config.SelectboxColumn("Priority", options=["low", "medium", "Urgent"])
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

# --- CHART ---
st.markdown("---")
st.header("📈 Expenses and Projects Over Time")

expenses_chart_data = expenses_df[["date", "price"]].copy()
expenses_chart_data.rename(columns={"date": "Time", "price": "Expenses"}, inplace=True)

projects_chart_data = projects_df[["deadline", "price"]].copy()
projects_chart_data.rename(columns={"deadline": "Time", "price": "Projects"}, inplace=True)

combined_chart_data = pd.merge(
    expenses_chart_data,
    projects_chart_data,
    on="Time",
    how="outer"
).sort_values("Time").fillna(0)

st.line_chart(combined_chart_data.set_index("Time"))
