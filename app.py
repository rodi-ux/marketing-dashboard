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
    ga4_url = "https://raw.githubusercontent.com/rodi-ux/marketing-dashboard/main/ga4_data.csv"
    stape_url = "https://raw.githubusercontent.com/rodi-ux/marketing-dashboard/main/stape_data.csv"
    ads_url = "https://raw.githubusercontent.com/rodi-ux/marketing-dashboard/main/google_ads_data.csv"

    ga4_df = pd.read_csv(ga4_url, parse_dates=["date"])
    stape_df = pd.read_csv(stape_url, parse_dates=["date"])
    ads_df = pd.read_csv(ads_url, parse_dates=["date"])

    # Merge GA4 + Stape by user_id and session_id if needed
    df = pd.merge(ga4_df, stape_df, how="outer", on=["user_id","session_id","date"], suffixes=("_ga4","_stape"))
    return df, ads_df

df, ads_df = load_data()

# ---------------------------
# Sidebar: filtros
# ---------------------------
st.sidebar.header("Filtros")
channels = df["channel"].dropna().unique()
campaigns = df["campaign"].dropna().unique()
devices = df["device"].dropna().unique()
utm_sources = df["utm_source"].dropna().unique()
countries = df["country"].dropna().unique() if "country" in df.columns else []

selected_channel = st.sidebar.multiselect("Channel", channels, default=list(channels))
selected_campaign = st.sidebar.multiselect("Campaign", campaigns, default=list(campaigns))
selected_device = st.sidebar.multiselect("Device", devices, default=list(devices))
selected_utm = st.sidebar.multiselect("UTM Source", utm_sources, default=list(utm_sources))
selected_country = st.sidebar.multiselect("Country", countries, default=list(countries))
date_range = st.sidebar.date_input("Date Range", [df["date"].min(), df["date"].max()])

uid_input = st.sidebar.text_input("User Explorer: user_id")

# Apply filters
filtered_df = df[
    (df["channel"].isin(selected_channel)) &
    (df["campaign"].isin(selected_campaign)) &
    (df["device"].isin(selected_device)) &
    (df["utm_source"].isin(selected_utm)) &
    ((df["country"].isin(selected_country)) if len(selected_country)>0 else True) &
    (df["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))
]

# ---------------------------
# Tabs
# ---------------------------
tab_overview, tab_funnel, tab_journey, tab_user, tab_debug, tab_marketing = st.tabs(
    ["Overview", "Funnel", "User Journey", "User Detail", "Tracking Debugger", "Marketing Performance"]
)

# ---------------------------
# Tab: Overview
# ---------------------------
with tab_overview:
    st.subheader("KPIs")
    col1, col2, col3, col4, col5 = st.columns(5)

    unique_users = filtered_df["user_id"].nunique()
    sessions_count = filtered_df["session_id"].nunique()
    leads = filtered_df[filtered_df["event"].isin(["form_submit","purchase"])]["user_id"].nunique()
    revenue = filtered_df["revenue"].sum()
    cost = filtered_df["cost"].sum() if "cost" in filtered_df.columns else 0
    cpl = (cost / leads) if leads>0 else np.nan
    roas = (revenue / cost) if cost>0 else np.nan

    col1.metric("Unique Users", f"{unique_users:,}")
    col2.metric("Sessions", f"{sessions_count:,}")
    col3.metric("Leads", f"{leads:,}")
    col4.metric("Revenue", f"CA$ {revenue:,.2f}", delta=f"ROAS: {roas:.2f}" if roas>0 else "N/A")
    col5.metric("CPL", f"CA$ {cpl:,.2f}" if not np.isnan(cpl) else "N/A")

    st.markdown("### Revenue & Sessions per Day")
    daily = filtered_df.groupby("date").agg(revenue=("revenue","sum"), sessions=("session_id","nunique")).reset_index()
    fig = px.line(daily, x="date", y=["revenue","sessions"], labels={"value":"Count","date":"Date"})
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Sessions & Revenue by Channel")
    channel_summary = filtered_df.groupby("channel").agg(sessions=("session_id","nunique"), revenue=("revenue","sum")).reset_index()
    fig2 = px.bar(channel_summary, x="channel", y=["sessions","revenue"], barmode="group")
    st.plotly_chart(fig2, use_container_width=True)

# ---------------------------
# Tab: Funnel
# ---------------------------
with tab_funnel:
    st.subheader("Funnel — multi-step conversion")
    funnel_steps = ["Homepage","Product","Cart","Checkout","purchase"]
    funnel_counts = []
    for step in funnel_steps:
        users_in_step = filtered_df[filtered_df["page"]==step]["user_id"].nunique() if step!="purchase" else filtered_df[filtered_df["event"]=="purchase"]["user_id"].nunique()
        funnel_counts.append(users_in_step)

    funnel_df = pd.DataFrame({"Step": funnel_steps, "Users": funnel_counts})
    funnel_df["Conversion"] = funnel_df["Users"] / funnel_df["Users"].iloc[0] * 100
    fig_funnel = px.funnel(funnel_df, x="Users", y="Step", text="Conversion")
    st.plotly_chart(fig_funnel, use_container_width=True)

# ---------------------------
# Tab: User Journey
# ---------------------------
with tab_journey:
    st.subheader("User Journey — Sankey & Top Routes")
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
    missing_utm = filtered_df[filtered_df["utm_source"].isna() | filtered_df["utm_medium"].isna()]
    st.write(f"Events missing UTM info: {len(missing_utm)}")
    st.dataframe(missing_utm)

# ---------------------------
# Tab: Marketing Performance
# ---------------------------
with tab_marketing:
    st.subheader("Marketing Performance")

    ads_summary = ads_df.groupby("campaign").agg(
        clicks=("clicks","sum"),
        impressions=("impressions","sum"),
        cost=("cost","sum"),
        conversions=("conversions","sum")
    ).reset_index()

    ads_summary["CPC"] = ads_summary["cost"] / ads_summary["clicks"]
    ads_summary["CTR"] = ads_summary["clicks"] / ads_summary["impressions"] * 100
    ads_summary["ROAS"] = revenue / ads_summary["cost"]

    st.dataframe(ads_summary)
    fig_ads = px.bar(ads_summary, x="campaign", y=["clicks","conversions"], barmode="group")
    st.plotly_chart(fig_ads, use_container_width=True)
