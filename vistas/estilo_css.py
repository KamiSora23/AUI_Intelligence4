"""Sistema visual principal de AUI Intelligence.

La hoja se mantiene en un único bloque para evitar reglas superpuestas y
conservar la misma densidad visual en todas las vistas de Streamlit.
"""

import streamlit as st


def aplicar_estilos_sidebar() -> None:
    """Conserva el punto de entrada usado por versiones anteriores."""
    aplicar_estilos_modernos()


def aplicar_estilos_modernos() -> None:
    """Inyecta el tema oscuro, compacto y adaptable de la aplicación."""
    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
            --app-bg: #080A10;
            --sidebar-bg: #10131B;
            --surface: #131722;
            --surface-raised: #181D2A;
            --surface-hover: #202738;
            --surface-input: #0E121B;
            --line: #2B3345;
            --line-strong: #3C4860;
            --text: #F7F8FC;
            --text-soft: #CFD5E2;
            --muted: #8D97AA;
            --accent: #8B7CFF;
            --accent-strong: #6F5EF4;
            --accent-soft: rgba(139, 124, 255, .14);
            --cyan: #5CDCF4;
            --green: #4DD6A5;
            --amber: #F2B84B;
            --red: #FF6F87;
            --shadow-sm: 0 8px 22px rgba(0, 0, 0, .2);
            --shadow-md: 0 18px 44px rgba(0, 0, 0, .28);
            --radius-sm: 9px;
            --radius: 12px;
            --radius-lg: 16px;
            --ease: cubic-bezier(.22, 1, .36, 1);
        }

        @keyframes aui-fade-up {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes aui-pulse {
            0%, 100% { opacity: .65; transform: scale(.9); }
            50% { opacity: 1; transform: scale(1.08); }
        }

        html,
        body,
        [class*="css"] {
            font-family: Inter, "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
        }

        html,
        body,
        .stApp {
            background: var(--app-bg);
            color: var(--text);
        }

        .stApp {
            background-image:
                radial-gradient(circle at 92% -8%, rgba(139, 124, 255, .11), transparent 28rem),
                radial-gradient(circle at 18% 102%, rgba(92, 220, 244, .045), transparent 30rem);
        }

        #MainMenu,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stHeader"],
        [data-testid="stSidebarHeader"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        [data-testid="stElementContainer"]:has(
            [data-testid="stMarkdownContainer"] > style:only-child
        ) {
            display: none !important;
        }

        h1, h2, h3, h4, h5, h6,
        p, label, span, div {
            color: var(--text);
        }

        p,
        .stCaption,
        [data-testid="stCaptionContainer"] {
            color: var(--muted) !important;
        }

        a {
            color: var(--cyan) !important;
        }

        hr {
            margin: .9rem 0 !important;
            border-color: var(--line) !important;
        }

        /* Application shell */
        html body section[data-testid="stSidebar"] {
            left: 0 !important;
            width: 244px !important;
            min-width: 244px !important;
            max-width: 244px !important;
            transform: none !important;
            background:
                linear-gradient(180deg, rgba(139, 124, 255, .08), transparent 11rem),
                var(--sidebar-bg) !important;
            border-right: 1px solid var(--line) !important;
            box-shadow: 12px 0 32px rgba(0, 0, 0, .2);
            transition:
                min-width .18s ease,
                max-width .18s ease,
                transform .18s ease !important;
        }

        html body section[data-testid="stSidebar"][aria-expanded="false"] {
            left: 0 !important;
            transform: none !important;
        }

        html body section[data-testid="stSidebar"] > div:first-child {
            width: 244px !important;
            padding: .65rem .68rem .8rem !important;
            overflow-x: hidden !important;
        }

        html body .stApp section[data-testid="stSidebar"]
        [data-testid="stVerticalBlock"] {
            gap: .2rem !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            background: transparent;
        }

        .main .block-container:not(:has(.auth-context)),
        [data-testid="stMainBlockContainer"]:not(:has(.auth-context)) {
            width: 100% !important;
            max-width: none !important;
            padding: 0 1rem 1.6rem !important;
        }

        .main .block-container:not(:has(.auth-context))
        > [data-testid="stVerticalBlock"],
        [data-testid="stMainBlockContainer"]:not(:has(.auth-context))
        > [data-testid="stVerticalBlock"] {
            gap: .72rem !important;
        }

        [data-testid="stHorizontalBlock"] {
            gap: .72rem !important;
        }

        /* Sidebar identity */
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: .68rem;
            padding: .45rem .42rem .72rem;
        }

        .brand-mark {
            width: 36px;
            height: 36px;
            flex: 0 0 36px;
            filter: drop-shadow(0 7px 14px rgba(139, 124, 255, .32));
        }

        .sidebar-brand__name {
            color: #FFFFFF !important;
            font-size: .92rem;
            font-weight: 760;
            letter-spacing: -.02em;
        }

        .sidebar-brand__meta {
            margin-top: .1rem;
            color: #7F899C !important;
            font-size: .58rem;
            font-weight: 750;
            letter-spacing: .13em;
            text-transform: uppercase;
        }

        .user-card {
            margin: 0 .08rem .72rem;
            padding: .7rem .75rem;
            background: #171C28;
            border: 1px solid var(--line);
            border-radius: var(--radius);
        }

        .user-title {
            overflow: hidden;
            color: #F5F7FC !important;
            font-size: .76rem;
            font-weight: 720;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .user-role {
            margin-top: .12rem;
            color: #929BAE !important;
            font-size: .65rem;
        }

        .connection-line {
            display: flex;
            align-items: center;
            gap: .38rem;
            margin-top: .45rem;
            color: #ADB5C5 !important;
            font-size: .61rem;
        }

        .connection-line span {
            width: 6px;
            height: 6px;
            flex: 0 0 6px;
            background: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 10px rgba(77, 214, 165, .65);
        }

        .sidebar-nav-label {
            margin: .15rem .42rem .42rem;
            color: #727C90 !important;
            font-size: .56rem;
            font-weight: 800;
            letter-spacing: .13em;
            text-transform: uppercase;
        }

        html body section[data-testid="stSidebar"] .stButton {
            width: 100%;
            margin: 0 0 .12rem !important;
        }

        html body section[data-testid="stSidebar"] .stButton button {
            display: flex !important;
            align-items: center !important;
            justify-content: stretch !important;
            width: 100% !important;
            min-height: 40px !important;
            padding: .26rem .4rem !important;
            color: #B9C1D0 !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 10px !important;
            box-shadow: none !important;
            transition:
                color .16s ease,
                background .16s ease,
                border-color .16s ease,
                transform .16s var(--ease) !important;
        }

        html body section[data-testid="stSidebar"] .stButton button > div {
            width: 100% !important;
            min-width: 0 !important;
        }

        html body section[data-testid="stSidebar"] .stButton button > div > span {
            display: grid !important;
            grid-template-columns: 30px minmax(0, 1fr) !important;
            align-items: center !important;
            gap: .55rem !important;
            width: 100% !important;
            min-width: 0 !important;
        }

        html body section[data-testid="stSidebar"] .stButton button
        span[data-testid="stIconMaterial"] {
            display: grid !important;
            place-items: center !important;
            width: 30px !important;
            height: 30px !important;
            min-width: 30px !important;
            margin: 0 !important;
            color: #9FA9BD !important;
            background: #1B202D !important;
            border: 1px solid #31394B !important;
            border-radius: 8px !important;
            font-size: 1rem !important;
        }

        html body section[data-testid="stSidebar"] .stButton button
        [data-testid="stMarkdownContainer"] {
            width: 100% !important;
            min-width: 0 !important;
            text-align: left !important;
        }

        html body section[data-testid="stSidebar"] .stButton button p {
            overflow: hidden;
            width: 100%;
            margin: 0 !important;
            color: inherit !important;
            font-size: .72rem !important;
            font-weight: 620 !important;
            line-height: 1.2 !important;
            text-align: left !important;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        html body section[data-testid="stSidebar"] .stButton button:hover {
            color: #FFFFFF !important;
            background: #1A202D !important;
            border-color: #343D50 !important;
            transform: translateX(2px);
        }

        html body section[data-testid="stSidebar"] .stButton button[kind="primary"] {
            color: #FFFFFF !important;
            background:
                linear-gradient(90deg, rgba(139, 124, 255, .2), rgba(139, 124, 255, .08))
                !important;
            border-color: rgba(139, 124, 255, .48) !important;
            box-shadow: inset 3px 0 0 var(--accent) !important;
        }

        html body section[data-testid="stSidebar"] .stButton button[kind="primary"]
        span[data-testid="stIconMaterial"] {
            color: #FFFFFF !important;
            background: linear-gradient(145deg, #8B7CFF, #6757DC) !important;
            border-color: #A69BFF !important;
            box-shadow: 0 6px 14px rgba(111, 94, 244, .3);
        }

        /* Sticky page header */
        [data-testid="stMainBlockContainer"]
        > [data-testid="stVerticalBlock"]
        > [data-testid="stElementContainer"]:has(.page-hero) {
            position: sticky;
            top: 0;
            z-index: 700;
            width: calc(100% + 2.65rem) !important;
            max-width: none !important;
            margin: 0 -1rem;
        }

        .page-hero {
            position: relative;
            display: grid;
            grid-template-columns: minmax(240px, auto) minmax(220px, 1fr) auto;
            align-items: center;
            gap: 1.2rem;
            min-height: 68px;
            margin: 0;
            padding: .58rem 1rem;
            background: rgba(13, 16, 24, .94);
            border-bottom: 1px solid var(--line-strong);
            box-shadow: 0 10px 28px rgba(0, 0, 0, .24);
            backdrop-filter: blur(18px) saturate(1.15);
        }

        .page-hero::after {
            content: "";
            position: absolute;
            inset: auto 0 -1px;
            height: 1px;
            background: linear-gradient(90deg, var(--accent), var(--cyan) 48%, transparent 88%);
        }

        .page-hero__identity {
            display: flex;
            align-items: center;
            gap: .68rem;
            min-width: 0;
        }

        .page-hero__icon,
        .section-heading__icon {
            display: grid;
            place-items: center;
            flex: 0 0 auto;
        }

        .page-hero__icon {
            width: 40px;
            height: 40px;
            color: #FFFFFF;
            background: linear-gradient(145deg, #8273F5, #5F51CB);
            border: 1px solid #9D93F9;
            border-radius: 11px;
            box-shadow: 0 8px 18px rgba(102, 85, 220, .28);
        }

        .ui-icon {
            width: 20px;
            height: 20px;
        }

        .page-hero .eyebrow {
            display: block;
            margin-bottom: .1rem;
            color: var(--cyan) !important;
            font-size: .53rem;
            font-weight: 800;
            letter-spacing: .15em;
            text-transform: uppercase;
        }

        .page-hero h1 {
            margin: 0;
            padding: 0 !important;
            color: #FFFFFF !important;
            font-size: clamp(1.15rem, 1.7vw, 1.45rem);
            font-weight: 790;
            letter-spacing: -.03em;
            line-height: 1.08;
        }

        .page-hero__description {
            margin: 0 !important;
            max-width: 680px;
            color: #9DA7B9 !important;
            font-size: .7rem !important;
            line-height: 1.4 !important;
        }

        .page-hero__status {
            display: inline-flex;
            align-items: center;
            gap: .4rem;
            padding: .34rem .55rem;
            color: #BEC5D3 !important;
            background: #171C27;
            border: 1px solid #343D50;
            border-radius: 999px;
            font-size: .58rem;
            font-weight: 700;
            white-space: nowrap;
        }

        .page-hero__pulse {
            width: 6px;
            height: 6px;
            background: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 0 3px rgba(77, 214, 165, .12);
            animation: aui-pulse 2.4s ease-in-out infinite;
        }

        /* Section titles */
        .section-heading {
            display: flex;
            align-items: center;
            gap: .55rem;
            margin: .22rem 0 .4rem;
            animation: aui-fade-up .3s var(--ease) both;
        }

        .section-heading__icon {
            width: 30px;
            height: 30px;
            color: #CBC5FF;
            background: #1C2130;
            border: 1px solid #343D52;
            border-radius: 8px;
        }

        .section-heading__icon .ui-icon {
            width: 15px;
            height: 15px;
        }

        .section-heading h2 {
            margin: 0;
            padding: 0 !important;
            color: #F5F7FB !important;
            font-size: .9rem;
            font-weight: 720;
            letter-spacing: -.01em;
        }

        .section-heading p {
            margin: .06rem 0 0;
            color: #858FA2 !important;
            font-size: .64rem;
        }

        /* General surfaces */
        .css-card,
        .card-container,
        [data-testid="stForm"],
        [data-testid="stExpander"],
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stFileUploaderDropzone"] {
            background: var(--surface) !important;
            border: 1px solid var(--line) !important;
            border-radius: var(--radius) !important;
            box-shadow: var(--shadow-sm) !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            padding: .72rem .78rem;
        }

        [data-testid="stForm"] {
            padding: .9rem !important;
        }

        [data-testid="stExpander"] {
            overflow: hidden;
        }

        [data-testid="stExpander"] summary {
            min-height: 40px;
            padding: .2rem .68rem !important;
            color: var(--text-soft) !important;
            background: #171C27;
            font-size: .72rem;
            font-weight: 660;
        }

        [data-testid="stExpander"][open] summary {
            border-bottom: 1px solid var(--line);
        }

        /* Metrics */
        .metric-card {
            position: relative;
            min-height: 98px;
            overflow: hidden;
            padding: .72rem .78rem;
            background: linear-gradient(145deg, #181D2A, #131722);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            animation: aui-fade-up .35s var(--ease) both;
            transition:
                transform .18s var(--ease),
                border-color .18s ease,
                box-shadow .18s ease;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #46516A;
            box-shadow: var(--shadow-md);
        }

        .metric-card::before {
            content: "";
            position: absolute;
            inset: 0 0 auto;
            height: 2px;
            background: linear-gradient(90deg, var(--accent), #B2A9FF);
        }

        .metric-card--danger::before {
            background: linear-gradient(90deg, var(--red), #FF9BAB);
        }

        .metric-card--warning::before {
            background: linear-gradient(90deg, var(--amber), #FFD27A);
        }

        .metric-card--success::before {
            background: linear-gradient(90deg, var(--green), #82E8C4);
        }

        .metric-card__topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .5rem;
        }

        .metric-card__icon {
            display: grid;
            place-items: center;
            width: 27px;
            height: 27px;
            color: #D8D3FF;
            background: var(--accent-soft);
            border: 1px solid rgba(139, 124, 255, .34);
            border-radius: 8px;
        }

        .metric-card--danger .metric-card__icon {
            color: #FFB6C2;
            background: rgba(255, 111, 135, .1);
            border-color: rgba(255, 111, 135, .28);
        }

        .metric-card--warning .metric-card__icon {
            color: #FFD98F;
            background: rgba(242, 184, 75, .1);
            border-color: rgba(242, 184, 75, .28);
        }

        .metric-card--success .metric-card__icon {
            color: #A8F1D5;
            background: rgba(77, 214, 165, .1);
            border-color: rgba(77, 214, 165, .28);
        }

        .ui-icon--metric {
            width: 14px;
            height: 14px;
        }

        .metric-title {
            color: #919BAD !important;
            font-size: .57rem;
            font-weight: 800;
            letter-spacing: .1em;
            text-transform: uppercase;
        }

        .metric-value {
            margin-top: .28rem;
            color: #FFFFFF !important;
            font-size: clamp(1.12rem, 1.75vw, 1.4rem);
            font-weight: 790;
            letter-spacing: -.035em;
        }

        .metric-subtitle {
            margin-top: .1rem;
            color: #818B9E !important;
            font-size: .6rem;
        }

        /* Inputs and actions */
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div {
            min-height: 40px;
            color: #F1F4FA !important;
            background: var(--surface-input) !important;
            border-color: #343D50 !important;
            border-radius: 9px !important;
            box-shadow: none !important;
        }

        .stTextInput input:hover,
        .stTextArea textarea:hover,
        .stNumberInput input:hover,
        [data-baseweb="select"] > div:hover {
            border-color: #525D74 !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px rgba(139, 124, 255, .11) !important;
        }

        .stTextInput label,
        .stTextArea label,
        .stNumberInput label,
        .stSelectbox label,
        .stSlider label,
        .stFileUploader label {
            color: #B8C0CF !important;
            font-size: .67rem !important;
            font-weight: 650 !important;
        }

        .stButton > button,
        .stFormSubmitButton > button,
        .stDownloadButton > button {
            min-height: 40px;
            color: #FFFFFF !important;
            background: linear-gradient(135deg, #8273F6, #6353D6) !important;
            border: 1px solid #9E94FA !important;
            border-radius: 9px !important;
            box-shadow: 0 7px 18px rgba(92, 75, 205, .23);
            font-size: .72rem;
            font-weight: 690;
            transition:
                transform .16s var(--ease),
                filter .16s ease,
                box-shadow .16s ease !important;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        .stDownloadButton > button:hover {
            filter: brightness(1.08);
            transform: translateY(-1px);
            box-shadow: 0 10px 22px rgba(92, 75, 205, .3);
        }

        .stButton > button[kind="secondary"],
        .stDownloadButton > button[kind="secondary"] {
            color: #D2D8E4 !important;
            background: #1A1F2C !important;
            border-color: #394256 !important;
            box-shadow: none;
        }

        [data-testid="stSegmentedControl"] {
            padding: .25rem;
            background: #10141E;
            border: 1px solid var(--line);
            border-radius: 10px;
        }

        [data-testid="stSegmentedControl"] button {
            min-height: 34px;
            border-radius: 7px !important;
            font-size: .66rem;
        }

        [data-testid="stSlider"] [role="slider"] {
            background: var(--accent) !important;
            border-color: #B3AAFF !important;
        }

        [data-testid="stProgressBar"] > div > div {
            background: linear-gradient(90deg, var(--accent), var(--cyan)) !important;
        }

        [data-testid="stFileUploaderDropzone"] {
            padding: 1rem !important;
            background:
                linear-gradient(135deg, rgba(139, 124, 255, .06), rgba(92, 220, 244, .025))
                !important;
            border-style: dashed !important;
            border-color: #485269 !important;
        }

        /* Tabs and messages */
        [role="tablist"] {
            display: inline-flex !important;
            width: auto !important;
            max-width: 100%;
            gap: .2rem;
            padding: .24rem;
            overflow-x: auto;
            background: #111620;
            border: 1px solid var(--line);
            border-radius: 10px;
        }

        [data-baseweb="tab"] {
            min-height: 34px;
            padding: .38rem .65rem !important;
            border-radius: 7px;
        }

        [data-testid="stTab"] {
            color: #929CAE !important;
            font-size: .66rem;
            font-weight: 700;
            white-space: nowrap;
        }

        [aria-selected="true"][data-baseweb="tab"] {
            background: #242A3A !important;
            box-shadow: inset 0 0 0 1px #414B61;
        }

        [aria-selected="true"] [data-testid="stTab"] {
            color: #FFFFFF !important;
        }

        [data-testid="stAlert"] {
            padding: .65rem .75rem !important;
            background: #171C28 !important;
            border: 1px solid #394257 !important;
            border-left: 3px solid var(--accent) !important;
            border-radius: 10px !important;
            box-shadow: var(--shadow-sm);
        }

        [data-testid="stAlert"] p {
            color: #C8CFDC !important;
            font-size: .68rem;
        }

        /* Status */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: .36rem;
            padding: .27rem .5rem;
            color: #B7C0CF !important;
            background: #1B202C;
            border: 1px solid #394255;
            border-radius: 999px;
            font-size: .56rem;
            font-weight: 800;
            letter-spacing: .04em;
            text-transform: uppercase;
        }

        .status-badge > span {
            width: 5px;
            height: 5px;
            background: currentColor;
            border-radius: 50%;
        }

        .status-badge--high {
            color: #FF95A7 !important;
            background: rgba(255, 111, 135, .08);
            border-color: rgba(255, 111, 135, .34);
        }

        .status-badge--medium {
            color: #F8CA71 !important;
            background: rgba(242, 184, 75, .08);
            border-color: rgba(242, 184, 75, .34);
        }

        .status-badge--low {
            color: #7FE1BE !important;
            background: rgba(77, 214, 165, .08);
            border-color: rgba(77, 214, 165, .34);
        }

        /* Tables */
        .data-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .8rem;
            margin-bottom: .42rem;
            padding: .55rem .68rem;
            background: #191E2A;
            border: 1px solid var(--line);
            border-radius: 9px;
        }

        .data-toolbar > div {
            display: flex;
            align-items: baseline;
            gap: .35rem;
        }

        .data-toolbar__count {
            color: #FFFFFF !important;
            font-size: .98rem;
            font-weight: 800;
        }

        .data-toolbar__label {
            color: #B5ACFF !important;
            font-size: .56rem;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        .data-toolbar p {
            margin: 0;
            color: #8C96A8 !important;
            font-size: .61rem;
        }

        .responsive-table-shell {
            width: 100%;
            overflow: hidden;
            background: #0E121A;
            border: 1px solid #343D50;
            border-radius: 12px;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, .035),
                0 12px 28px rgba(0, 0, 0, .12);
        }

        .responsive-table {
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
        }

        .responsive-table th,
        .responsive-table td {
            min-width: 0;
            padding: .7rem .72rem;
            overflow-wrap: anywhere;
            word-break: normal;
            white-space: normal !important;
            text-align: left;
            vertical-align: top;
            border: 0;
            border-bottom: 1px solid #252C3A;
        }

        .responsive-table th {
            color: #C0C8D8 !important;
            background:
                linear-gradient(180deg, #242639 0%, #1A1E2A 100%);
            font-size: .56rem;
            font-weight: 800;
            letter-spacing: .095em;
            line-height: 1.25;
            text-transform: uppercase;
            border-bottom-color: #4A456F;
        }

        .responsive-table td {
            color: #D5DAE4 !important;
            background: #111620;
            font-size: .65rem;
            line-height: 1.42;
        }

        .responsive-table tbody tr:nth-child(even) td {
            background: #151A25;
        }

        .responsive-table tbody td:first-child {
            border-left: 3px solid transparent;
        }

        .responsive-table tbody tr:has(.status-badge--high) td:first-child {
            border-left-color: var(--red);
        }

        .responsive-table tbody tr:has(.status-badge--medium) td:first-child {
            border-left-color: var(--amber);
        }

        .responsive-table tbody tr:has(.status-badge--low) td:first-child {
            border-left-color: var(--green);
        }

        .responsive-table tbody tr:last-child td {
            border-bottom: 0;
        }

        .responsive-table tbody tr {
            transition: background .15s ease;
        }

        .responsive-table tbody tr:hover td {
            background: #1D2432;
        }

        .table-cell__primary,
        .table-cell__secondary,
        .table-cell__meta {
            display: block;
            overflow-wrap: anywhere;
            white-space: normal;
        }

        .table-cell__primary {
            color: #F5F7FB !important;
            font-size: .67rem;
            font-weight: 730;
            line-height: 1.35;
        }

        .table-cell__secondary {
            margin-top: .18rem;
            color: #A1AABA !important;
            font-size: .62rem;
            line-height: 1.4;
        }

        .table-cell__meta {
            margin-top: .2rem;
            color: #75DDF1 !important;
            font-size: .56rem;
            font-weight: 700;
        }

        /* Charts */
        [data-testid="stPlotlyChart"] {
            overflow: hidden;
            padding: .18rem;
            background: #111620 !important;
            border: 1px solid var(--line);
            border-radius: var(--radius);
        }

        [data-testid="stPlotlyChart"] .modebar {
            opacity: .25;
            transition: opacity .16s ease;
        }

        [data-testid="stPlotlyChart"]:hover .modebar {
            opacity: .9;
        }

        /* Review case rows */
        [data-testid="stElementContainer"]:has(.case-card-marker) {
            display: none !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.case-card-marker) {
            position: relative;
            overflow: hidden;
            padding: .7rem .8rem !important;
            background: #141925 !important;
            border-color: #2D3547 !important;
            transition:
                background .16s ease,
                border-color .16s ease,
                transform .16s var(--ease);
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.case-card-marker)::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 2px;
            background: linear-gradient(180deg, var(--accent), var(--cyan));
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.case-card-marker):hover {
            background: #1A202E !important;
            border-color: #424D64 !important;
            transform: translateY(-1px);
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.case-card-marker)
        [data-testid="stHorizontalBlock"] {
            align-items: center;
            gap: .8rem !important;
        }

        .case-card__risk {
            display: flex;
            align-items: flex-start;
            flex-direction: column;
            gap: .27rem;
        }

        .case-card__risk > span:not(.status-badge) {
            color: #C8CFDC !important;
            font-size: .63rem;
            font-weight: 680;
        }

        .case-card__risk small {
            color: #838DA0 !important;
            font-size: .56rem;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.case-card-marker)
        .stButton > button {
            min-height: 36px;
            font-size: .65rem;
        }

        /* Login */
        .main .block-container:has(.auth-context),
        [data-testid="stMainBlockContainer"]:has(.auth-context) {
            width: 100% !important;
            max-width: none !important;
            height: 100svh;
            padding: 0 !important;
            overflow: hidden;
        }

        [data-testid="stHorizontalBlock"]:has(.auth-context) {
            width: 100%;
            height: 100svh;
            gap: 0 !important;
            background:
                radial-gradient(circle at 14% 14%, rgba(139, 124, 255, .16), transparent 24rem),
                radial-gradient(circle at 82% 88%, rgba(92, 220, 244, .07), transparent 22rem),
                #090B11;
        }

        [data-testid="stColumn"]:has(.auth-context) {
            display: flex;
            align-items: stretch;
            padding: .75rem 0 .75rem .75rem;
        }

        [data-testid="stColumn"]:has(.auth-form-header) {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem 1.4rem;
        }

        .auth-context {
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            width: 100%;
            height: calc(100svh - 1.5rem);
            min-height: 0;
            overflow: hidden;
            padding: clamp(1.4rem, 3vw, 2.6rem);
            background:
                linear-gradient(145deg, rgba(29, 34, 48, .97), rgba(14, 18, 27, .99));
            border: 1px solid #343C50;
            border-radius: 18px;
            box-shadow: 0 28px 70px rgba(0, 0, 0, .35);
        }

        .auth-context::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            opacity: .28;
            background-image:
                linear-gradient(rgba(132, 143, 164, .06) 1px, transparent 1px),
                linear-gradient(90deg, rgba(132, 143, 164, .06) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: linear-gradient(145deg, #000, transparent 78%);
        }

        .auth-context__brand,
        .auth-context__copy,
        .auth-map,
        .auth-context__footer {
            position: relative;
            z-index: 1;
        }

        .auth-context__brand {
            display: flex;
            align-items: center;
            gap: .7rem;
        }

        .auth-context__mark {
            width: 38px;
            height: 38px;
        }

        .auth-context__brand strong {
            display: block;
            color: #FFFFFF !important;
            font-size: .9rem;
        }

        .auth-context__brand span {
            display: block;
            margin-top: .08rem;
            color: #8993A5 !important;
            font-size: .58rem;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        .auth-context__copy {
            width: min(100%, 650px);
        }

        .auth-context__index {
            color: var(--cyan) !important;
            font-size: .58rem;
            font-weight: 800;
            letter-spacing: .14em;
        }

        .auth-context__copy h1 {
            margin: .55rem 0 .65rem;
            padding: 0 !important;
            color: #FFFFFF !important;
            font-size: clamp(2rem, 4.2vw, 4.2rem);
            font-weight: 780;
            letter-spacing: -.055em;
            line-height: .98;
        }

        .auth-context__copy h1 em {
            color: #A9A0FF !important;
            font-style: normal;
        }

        .auth-context__copy p {
            width: min(100%, 530px);
            margin: 0;
            color: #9EA8B9 !important;
            font-size: clamp(.72rem, 1vw, .88rem);
            line-height: 1.6;
        }

        .auth-map {
            width: min(100%, 660px);
            height: clamp(120px, 22vh, 210px);
            overflow: hidden;
            background: rgba(9, 12, 18, .5);
            border: 1px solid #2F3748;
            border-radius: 14px;
        }

        .auth-map__image {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
            opacity: .8;
        }

        .auth-map__scan {
            position: absolute;
            inset: 0 auto 0 -20%;
            width: 18%;
            background: linear-gradient(90deg, transparent, rgba(92, 220, 244, .1), transparent);
            animation: auth-scan 5.5s ease-in-out infinite;
        }

        @keyframes auth-scan {
            from { left: -20%; }
            to { left: 105%; }
        }

        .auth-context__footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: #7E889A !important;
            font-size: .58rem;
        }

        .auth-context__footer span {
            display: inline-flex;
            align-items: center;
            gap: .38rem;
            color: inherit !important;
        }

        .auth-context__footer i {
            width: 6px;
            height: 6px;
            background: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 10px rgba(77, 214, 165, .65);
        }

        [data-testid="stColumn"]:has(.auth-form-header)
        [data-testid="stForm"] {
            width: min(100%, 380px);
            padding: clamp(1.15rem, 3vw, 1.8rem) !important;
            background: #131722 !important;
            border-color: #353D50 !important;
            border-radius: 16px !important;
            box-shadow: 0 22px 56px rgba(0, 0, 0, .32) !important;
        }

        .auth-form-header {
            margin-bottom: 1rem;
        }

        .auth-form-header__mark {
            display: none;
            width: 34px;
            height: 34px;
            margin-bottom: .7rem;
        }

        .auth-form-header > span {
            color: var(--cyan) !important;
            font-size: .55rem;
            font-weight: 800;
            letter-spacing: .14em;
        }

        .auth-form-header h2 {
            margin: .32rem 0 .28rem;
            padding: 0 !important;
            color: #FFFFFF !important;
            font-size: 1.7rem;
            font-weight: 780;
            letter-spacing: -.04em;
        }

        .auth-form-header p {
            margin: 0;
            color: #8E98AA !important;
            font-size: .68rem;
        }

        .auth-form-footer {
            display: flex;
            justify-content: center;
            gap: .8rem;
            margin-top: .7rem;
            color: #737E90 !important;
            font-size: .56rem;
        }

        .auth-form-footer span {
            color: inherit !important;
        }

        /* Responsive */
        @media (max-width: 1120px) {
            .page-hero {
                grid-template-columns: minmax(220px, 1fr) auto;
            }

            .page-hero__description {
                display: none;
            }

            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
            }

            [data-testid="column"] {
                flex: 1 1 280px !important;
                width: auto !important;
                min-width: min(100%, 260px) !important;
            }

            .metric-card {
                min-height: 94px;
            }
        }

        @media (max-width: 900px) {
            [data-testid="stColumn"]:has(.auth-context) {
                display: none !important;
            }

            [data-testid="stColumn"]:has(.auth-form-header) {
                flex: 1 1 100% !important;
                max-width: 100%;
                padding: 1rem;
            }

            .auth-form-header__mark {
                display: block;
            }
        }

        @media (max-width: 760px) {
            html body section[data-testid="stSidebar"],
            html body section[data-testid="stSidebar"][aria-expanded="false"] {
                width: 60px !important;
                min-width: 60px !important;
                max-width: 60px !important;
                transform: none !important;
            }

            html body section[data-testid="stSidebar"] > div:first-child {
                width: 60px !important;
                padding: .45rem .3rem .7rem !important;
            }

            [data-testid="stAppViewContainer"]:has([data-testid="stSidebar"])
            [data-testid="stMain"] {
                width: calc(100% - 60px) !important;
                margin-left: 60px !important;
            }

            html body section[data-testid="stSidebar"] .sidebar-brand {
                justify-content: center;
                padding: .42rem 0 .65rem;
            }

            html body section[data-testid="stSidebar"] .sidebar-brand > div,
            html body section[data-testid="stSidebar"] .user-card,
            html body section[data-testid="stSidebar"] .sidebar-nav-label,
            html body section[data-testid="stSidebar"] hr {
                display: none !important;
            }

            html body section[data-testid="stSidebar"] .brand-mark {
                width: 32px !important;
                height: 32px !important;
                flex-basis: 32px !important;
            }

            html body section[data-testid="stSidebar"] .stButton {
                margin-bottom: .25rem !important;
            }

            html body section[data-testid="stSidebar"] .stButton button {
                width: 42px !important;
                min-width: 42px !important;
                min-height: 42px !important;
                margin: 0 auto !important;
                padding: 0 !important;
                justify-content: center !important;
            }

            html body section[data-testid="stSidebar"] .stButton button > div {
                width: auto !important;
            }

            html body section[data-testid="stSidebar"] .stButton button > div > span {
                display: flex !important;
                justify-content: center !important;
                width: auto !important;
                gap: 0 !important;
            }

            html body section[data-testid="stSidebar"] .stButton button
            [data-testid="stMarkdownContainer"] {
                display: none !important;
            }

            html body section[data-testid="stSidebar"] .stButton button
            span[data-testid="stIconMaterial"] {
                width: 30px !important;
                height: 30px !important;
                min-width: 30px !important;
            }

            .main .block-container:not(:has(.auth-context)),
            [data-testid="stMainBlockContainer"]:not(:has(.auth-context)) {
                padding: 0 .5rem 1.2rem !important;
            }

            [data-testid="stMainBlockContainer"]
            > [data-testid="stVerticalBlock"]
            > [data-testid="stElementContainer"]:has(.page-hero) {
                width: calc(100% + 1.65rem) !important;
                margin: 0 -.5rem;
            }

            .page-hero {
                min-height: 60px;
                grid-template-columns: 1fr;
                padding: .48rem .55rem;
            }

            .page-hero__icon {
                width: 36px;
                height: 36px;
            }

            .page-hero__status,
            .page-hero__description {
                display: none;
            }

            .page-hero h1 {
                font-size: 1.1rem;
            }

            .data-toolbar {
                align-items: flex-start;
                flex-direction: column;
                gap: .15rem;
            }

            .responsive-table-shell {
                overflow: visible;
                background: transparent;
                border: 0;
            }

            .responsive-table,
            .responsive-table tbody,
            .responsive-table tr,
            .responsive-table td {
                display: block;
                width: 100%;
            }

            .responsive-table colgroup,
            .responsive-table thead {
                display: none;
            }

            .responsive-table tr {
                overflow: hidden;
                margin-bottom: .45rem;
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 10px;
            }

            .responsive-table td,
            .responsive-table tbody tr:nth-child(even) td {
                display: grid;
                grid-template-columns: minmax(72px, 30%) minmax(0, 1fr);
                gap: .5rem;
                padding: .52rem .58rem;
                background: transparent;
                border-bottom: 1px solid #282F3F;
            }

            .responsive-table td::before {
                content: attr(data-label);
                color: #7F899C;
                font-size: .52rem;
                font-weight: 800;
                letter-spacing: .07em;
                line-height: 1.3;
                text-transform: uppercase;
            }

            .responsive-table tr td:last-child {
                border-bottom: 0;
            }
        }

        @media (max-width: 640px) {
            [data-testid="stColumn"]:has(.auth-form-header) {
                padding: .65rem;
            }

            [data-testid="stColumn"]:has(.auth-form-header)
            [data-testid="stForm"] {
                width: min(100%, 360px);
                padding: 1rem !important;
            }

            .auth-form-footer {
                margin-top: .45rem;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .01ms !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inyectar_estilo_css_empresarial() -> None:
    """Alias semántico usado por la aplicación."""
    aplicar_estilos_modernos()
