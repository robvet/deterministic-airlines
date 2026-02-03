"""
Streamlit UI for Deterministic Airlines Demo.

Calls FastAPI backend at http://localhost:8000/chat
Run with: streamlit run streamlit_app.py
"""
import requests
import streamlit as st
import streamlit.components.v1 as components
from components.seat_map import render_seat_map_html

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Deterministic Airlines", layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    /* Reduce top padding */
    .block-container {
        padding-top: 3rem;
    }
    .agent-header {
        background-color: #2563eb;
        color: white;
        padding: 10px 15px;
        border-radius: 8px 8px 0 0;
        margin-bottom: 0;
    }
    .customer-header {
        background-color: #2563eb;
        color: white;
        padding: 10px 15px;
        border-radius: 8px 8px 0 0;
        margin-bottom: 0;
    }
    .stExpander {
        border: 1px solid #e5e7eb;
        border-radius: 0;
    }
    .title-banner {
        background-color: #1e3a5f;
        color: white;
        text-align: center;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 28px;
        font-weight: bold;
    }
    /* Slightly lighter chat input container */
    [data-testid="stChatInput"] {
        background-color: #3a4556 !important;
        border-radius: 8px !important;
    }
    [data-testid="stChatInput"] > div {
        background-color: #3a4556 !important;
    }
    .stChatInput {
        background-color: #3a4556 !important;
    }
    .stChatInput > div {
        background-color: #3a4556 !important;
        border-color: #4a5568 !important;
    }
    .stChatInput textarea {
        background-color: #3a4556 !important;
    }
    [data-testid="stBottom"] > div {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# Page title
st.markdown("<div class='title-banner'>✈️ Deterministic Airlines</div>", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None


def call_api(user_input: str) -> dict:
    """Call FastAPI backend."""
    response = requests.post(
        f"{API_URL}/chat",
        json={"message": user_input, "customer_name": "Workshop Attendee"},
        timeout=30
    )
    response.raise_for_status()
    return response.json()


# Layout
left, right = st.columns([1, 1])

# Left panel - Agent Dashboard
with left:
    st.markdown('<div class="agent-header"><b>🤖 Agent Dashboard</b></div>', unsafe_allow_html=True)
    
    # Intent Classification Routing
    with st.expander("📋 Intent Classification Routing", expanded=True):
        resp = st.session_state.last_response
        if resp:
            st.json({
                "routed to": resp.get("routed_to"),
                "confidence score": resp.get("confidence"),
                "rewritten prompt": resp.get("rewritten_input"),
            })
        else:
            st.text("No conversation yet")
    
    # Seat Map - Show when seat-related request detected
    resp = st.session_state.last_response
    if resp and resp.get("routed_to") == "seat":
        with st.expander("💺 Seat Map", expanded=True):
            components.html(render_seat_map_html(), height=580, scrolling=True)
    
    # Guardrails (placeholder)
    with st.expander("🛡️ Guardrails", expanded=False):
        st.text("Input validation: Enabled")
        st.text("Output filtering: Enabled")
    
    # Runner Output / API Status
    with st.expander("📡 API Status", expanded=False):
        try:
            health = requests.get(f"{API_URL}/health", timeout=5).json()
            st.success(f"Backend: {health['status']}")
            st.text(f"Endpoint: {API_URL}")
        except Exception as e:
            st.error(f"API offline: {e}")
    
    # Reset button
    if st.button("🔄 Reset Conversation"):
        st.session_state.messages = []
        st.session_state.last_response = None
        st.rerun()

# Right panel - Customer View
with right:
    st.markdown('<div class="customer-header"><b>💬 Customer View</b></div>', unsafe_allow_html=True)
    
    # Chat history
    chat_container = st.container(height=300)
    with chat_container:
        if not st.session_state.messages:
            st.markdown("**Hi! I'm your airline assistant. How can I help today?**")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    
    # ==========================================================================
    # SUGGESTIONS - Collapsible panel with prompt buttons (expanded by default)
    # ==========================================================================
    with st.expander("💡 Suggestions", expanded=True):
        # Row 1: FAQ & Baggage
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("📋 Baggage policy", use_container_width=True, help="FAQ: What is the baggage policy?"):
                st.session_state.pending_input = "What is the baggage policy?"
        with col2:
            if st.button("💼 Lost bag claim", use_container_width=True, help="Baggage: Report lost luggage"):
                st.session_state.pending_input = "My bag is missing, I need to file a claim"
        with col3:
            if st.button("📶 WiFi on flights", use_container_width=True, help="FAQ: Is there WiFi on flights?"):
                st.session_state.pending_input = "Is there WiFi available on flights?"
        
        # Row 2: Booking & Cancel
        col4, col5, col6 = st.columns([1, 1, 1])
        with col4:
            if st.button("📅 Book DA100 to LA", use_container_width=True, help="Book flight DA100: JFK → LAX"):
                st.session_state.pending_input = "I want to book flight DA100 to Los Angeles"
        with col5:
            if st.button("📅 Book DA200 to Chicago", use_container_width=True, help="Book flight DA200: LAX → ORD"):
                st.session_state.pending_input = "Book flight DA200 to Chicago"
        with col6:
            if st.button("❌ Cancel IR-D204", use_container_width=True, help="Cancel Morgan Lee's booking"):
                st.session_state.pending_input = "Cancel my booking IR-D204"
        
        # Row 3: Flight Status & Seat
        col7, col8, col9 = st.columns([1, 1, 1])
        with col7:
            if st.button("🛫 Status PA441", use_container_width=True, help="Flight Status: Check PA441 (disrupted)"):
                st.session_state.pending_input = "What is the status of flight PA441?"
        with col8:
            if st.button("💺 Change to window", use_container_width=True, help="Seat: Request window seat"):
                st.session_state.pending_input = "I'd like to change to a window seat please"
        with col9:
            if st.button("♿ Special needs seat", use_container_width=True, help="Seat: Request special service seat"):
                st.session_state.pending_input = "I need a front row seat for medical reasons"
        
        # Row 4: Compensation
        col10, col11, col12 = st.columns([1, 1, 1])
        with col10:
            if st.button("🏨 Delay compensation", use_container_width=True, help="Compensation: Request for flight delay"):
                st.session_state.pending_input = "My flight PA441 was delayed 5 hours, I need compensation"
        with col11:
            if st.button("🔄 Missed connection", use_container_width=True, help="Compensation: Missed connection help"):
                st.session_state.pending_input = "I missed my connection because of the delay on PA441"
        with col12:
            if st.button("🎫 IR-D204 vouchers", use_container_width=True, help="Compensation: Check vouchers for disrupted trip"):
                st.session_state.pending_input = "What vouchers are available for booking IR-D204?"
    
    # ==========================================================================
    # FLIGHT INFORMATION - Reference data (collapsed by default)
    # ==========================================================================
    with st.expander("✈️ Flight Information", expanded=False):
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("**📋 Existing Bookings**")
            st.code("""IR-D204 - Morgan Lee
  Paris → New York → Austin
  Status: DISRUPTED
  Flights: PA441, NY802

LL0EZ6 - Taylor Lee  
  San Francisco → Los Angeles
  Status: ON TIME
  Flight: FLT-123""", language=None)
        
        with col_right:
            st.markdown("**🛫 Available Flights**")
            st.code("""DA100: JFK → LAX  $299
DA101: JFK → LAX  $349
DA200: LAX → ORD  $275
DA305: ORD → MIA  $225""", language=None)
            
            st.markdown("**🏙️ Cities**")
            st.code("""JFK - New York
LAX - Los Angeles
ORD - Chicago
MIA - Miami
CDG - Paris
AUS - Austin
SFO - San Francisco""", language=None)
    
    # Process pending input from buttons
    if "pending_input" in st.session_state:
        pending = st.session_state.pending_input
        del st.session_state.pending_input
        st.session_state.messages.append({"role": "user", "content": pending})
        with st.spinner("Thinking..."):
            try:
                response = call_api(pending)
                st.session_state.last_response = response
                st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})
        st.rerun()
    
    # Chat input with sample hint
    if prompt := st.chat_input("Try: 'What is the baggage policy?' or 'Book flight DA100'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Thinking..."):
            try:
                response = call_api(prompt)
                st.session_state.last_response = response
                st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})
        
        st.rerun()
