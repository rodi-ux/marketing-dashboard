import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Marketing Dashboard", layout="wide")
st.title("📊 Marketing Dashboard – Mosaicos no Canadá")

# ---------------------------
# LOAD DATA
# ---------------------------
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/rodi-ux/marketing-dashboard/main/data.csv"
    df = pd.read_csv(url, parse_dates=["date"])
    return df

df = load_data()

# ---------------------------
# Sidebar: filtros e user
# ---------------------------
st.sidebar.header("Filtros")
channels = df["channel"].unique()
campaigns = df["campaign"].unique()

selected_channel = st.sidebar.multiselect("Select Channel", channels, default=list(channels))
selected_campaign = st.sidebar.multiselect("Select Campaign", campaigns, default=list(campaigns))
date_range = st.sidebar.date_input("Select Date Range", [df["date"].min(), df["date"].max()])

uid_input = st.sidebar.text_input("User Explorer: user_id")

# Apply filters
filtered_df = df[
    (df["channel"].isin(selected_channel)) &
    (df["campaign"].isin(selected_campaign)) &
    (df["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))
]

# ---------------------------
# Tabs
# ---------------------------
tab_overview, tab_journey, tab_user, tab_debug, tab_marketing = st.tabs(
    ["Overview", "User Journey", "User Detail", "Tracking Debugger", "Marketing Performance"]
)

# ---------------------------
# Tab: Overview
# ---------------------------
with tab_overview:
    st.subheader("Overview — KPIs")
    col1, col2, col3, col4, col5 = st.columns(5)

    unique_users = filtered_df["user_id"].nunique()
    sessions_count = filtered_df["session_id"].nunique()
    leads = filtered_df[filtered_df["event"].isin(["form_submit","purchase"])]["user_id"].nunique()
    revenue = filtered_df["revenue"].sum()
    cost = filtered_df["cost"].sum()
    cpl = (cost / leads) if leads>0 else np.nan
    roas = (revenue / cost) if cost>0 else np.nan

    # KPIs com cores
    col1.metric("Unique Users", f"{unique_users:,}")
    col2.metric("Sessions", f"{sessions_count:,}")
    col3.metric("Leads", f"{leads:,}")
    col4.metric("Revenue", f"CA$ {revenue:,.2f}", delta=f"ROAS: {roas:.2f}" if roas>0 else "N/A")
    col5.metric("CPL", f"CA$ {cpl:,.2f}" if not np.isnan(cpl) else "N/A")

    st.markdown("### Revenue & Sessions per Day")
    daily = filtered_df.groupby("date").agg(revenue=("revenue","sum"), sessions=("session_id","nunique")).reset_index()
    fig = px.line(daily, x="date", y=["revenue","sessions"], labels={"value":"Count","date":"Date"})
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Sessions per Channel")
    channel_summary = filtered_df.groupby("channel").agg(sessions=("session_id","nunique"), revenue=("revenue","sum")).reset_index()
    fig2 = px.bar(channel_summary, x="channel", y=["sessions","revenue"], barmode="group")
    st.plotly_chart(fig2, use_container_width=True)

# ---------------------------
# Tab: User Journey
# ---------------------------
with tab_journey:
    st.subheader("User Journey — Sankey & Routes")
    # Agrupar páginas pequenas
    page_counts = filtered_df["page"].value_counts()
    small_pages = page_counts[page_counts<3].index.tolist()
    filtered_df["page_group"] = filtered_df["page"].apply(lambda x: "Other" if x in small_pages else x)

    first_events = filtered_df.sort_values("date").groupby("user_id").first().reset_index()
    last_events = filtered_df.sort_values("date").groupby("user_id").last().reset_index()

    sources = first_events["utm_source"].fillna("direct")
    pages = first_events["page_group"]
    outcome = filtered_df.groupby("user_id").last()["event"].apply(lambda x: "Converted" if x=="purchase" else "Not Converted")

    nodes = list(pd.concat([sources, pages, outcome]).unique())
    node_index = {n:i for i,n in enumerate(nodes)}

    link_source, link_target, link_value = [], [], []
    f1 = pd.concat([sources, pages], axis=1).groupby([0,1]).size().reset_index(name="count")
    for _, r in f1.iterrows():
        link_source.append(node_index[r[0]])
        link_target.append(node_index[r[1]])
        link_value.append(int(r["count"]))
    f2 = pd.concat([pages, outcome], axis=1).groupby([0,1]).size().reset_index(name="count")
    for _, r in f2.iterrows():
        link_source.append(node_index[r[0]])
        link_target.append(node_index[r[1]])
        link_value.append(int(r["count"]))

    sankey = go.Figure(go.Sankey(
        node=dict(label=nodes),
        link=dict(source=link_source, target=link_target, value=link_value)
    ))
    sankey.update_layout(height=500)
    st.plotly_chart(sankey, use_container_width=True)

    st.markdown("### Top Routes")
    routes = filtered_df.groupby("user_id").apply(lambda g: " → ".join(g.sort_values("date")["page_group"].tolist())).reset_index(name="route")
    top_routes = routes["route"].value_counts().reset_index(name="count")
    st.dataframe(top_routes.head(20))

# ---------------------------
# Tab: User Detail
# ---------------------------
with tab_user:
    st.subheader("User Detail Explorer")
    uid = uid_input.strip()
    if uid=="":
        uid = np.random.choice(filtered_df["user_id"].unique())
        st.info(f"Sample user: {uid}")

    user_df = filtered_df[filtered_df["user_id"]==uid].sort_values("date")
    if user_df.empty:
        st.warning("No events for this user in current data.")
    else:
        st.write(user_df[["date","page","event","campaign","utm_source","device","revenue"]])
        timeline_df = user_df.copy()
        timeline_df["start"] = timeline_df["date"]
        timeline_df["end"] = timeline_df["date"] + pd.to_timedelta(1, unit="h")
        fig = px.timeline(timeline_df, x_start="start", x_end="end", y="event", color="page", title=f"Timeline for {uid}")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        csv = user_df.to_csv(index=False).encode("utf-8")
        st.download_button("Export user CSV", data=csv, file_name=f"{uid}_events.csv", mime="text/csv")

# ---------------------------
# Tab: Tracking Debugger
# ---------------------------
with tab_debug:
    st.subheader("Tracking Debugger")
    missing_utm = filtered_df[filtered_df["utm_source"].isna() | (filtered_df["utm_source"]=="")]
    st.write("Events missing UTM/source:", len(missing_utm))
    st.dataframe(missing_utm.head(50))

    sessions_no_purchase = filtered_df.groupby("session_id").filter(lambda x: not (x["event"]=="purchase").any())
    st.write("Sessions without purchase (sample):", sessions_no_purchase["session_id"].nunique())
    st.dataframe(sessions_no_purchase.head(50))

# ---------------------------
# Tab: Marketing Performance
# ---------------------------
with tab_marketing:
    st.subheader("Marketing Performance")
    camp_summary = filtered_df.groupby("campaign").agg(
        clicks=("clicks","sum"),
        cost=("cost","sum"),
        conversions=("conversions","sum"),
        revenue=("revenue","sum")
    ).reset_index()
    if not camp_summary.empty:
        camp_summary["CPL"] = camp_summary["cost"] / camp_summary["conversions"].replace(0,np.nan)
        camp_summary["ROAS"] = camp_summary["revenue"] / camp_summary["cost"].replace(0,np.nan)
        st.dataframe(camp_summary)
        fig = px.bar(camp_summary, x="campaign", y=["cost","conversions","revenue"], barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No campaigns data available.")
