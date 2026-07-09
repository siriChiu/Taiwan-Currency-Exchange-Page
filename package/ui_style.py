import streamlit as st


def hide_streamlit_cloud_badge() -> None:
    st.markdown(
        """
        <style>
            /* Unofficial Streamlit Community Cloud badge/banner hide hack. */
            #MainMenu,
            footer,
            header,
            [data-testid="stDecoration"],
            [data-testid="stStatusWidget"],
            [data-testid="stToolbar"],
            [data-testid="stHeaderActionElements"],
            [data-testid="stDeployButton"],
            [data-testid="stBaseButton-header"],
            [data-testid="manage-app-button"],
            [data-testid="stCommunityCloudBadge"],
            [data-testid*="viewerBadge"],
            [data-testid*="ViewerBadge"],
            [data-testid*="cloudBadge"],
            [data-testid*="CloudBadge"],
            [class*="viewerBadge"],
            [class*="ViewerBadge"],
            [class*="st-emotion-cache"][href*="streamlit"],
            a[href*="streamlit.io/cloud"],
            a[href*="streamlit.io/community-cloud"],
            a[href*="share.streamlit.io"] {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
