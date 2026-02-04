"""
Streamlit UI for Deterministic Airlines Demo.

Calls FastAPI backend at http://localhost:8000/chat
Run with: streamlit run streamlit_app.py
"""
import sys
import os
# Add parent directory to path for app imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import streamlit as st
import streamlit.components.v1 as components
from components.seat_map import render_seat_map_html
from app.utils.prompt_converter import PromptConverter

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
    
    # ==========================================================================
    # PROMPT CONVERTER - Convert plain prompts to Chain of Thought prompts
    # ==========================================================================
    with st.expander("🔄 CoT Prompt Converter", expanded=False):
        st.caption("Converts plain prompts into Chain of Thought prompts with step-by-step reasoning")
        
        # Initialize state
        if "converter_input" not in st.session_state:
            st.session_state.converter_input = ""
        if "converter_output" not in st.session_state:
            st.session_state.converter_output = ""
        if "converter_thinking" not in st.session_state:
            st.session_state.converter_thinking = ""
        
        # Sample prompts for quick testing
        st.markdown("**Try a sample:**")
        sample_prompts = [
            "Cancel my booking IR-D204",
            "What is the baggage allowance for international flights?",
            "Book a flight from NYC to LA for next Friday"
        ]
        
        def set_sample(sample_text):
            st.session_state.converter_input = sample_text
            st.session_state.converter_output = ""
            st.session_state.converter_thinking = ""
        
        sample_cols = st.columns(3)
        for idx, sample in enumerate(sample_prompts):
            with sample_cols[idx]:
                st.button(f"💬 Simple Prompt {idx + 1}", key=f"sample_{idx}", 
                         use_container_width=True, on_click=set_sample, args=(sample,))
        
        # Input text area
        input_prompt = st.text_area(
            "Plain Prompt",
            height=80,
            placeholder="e.g., What is the weather like in Paris?",
            key="converter_input"
        )
        
        # Model selection and convert button
        col_model, col_button = st.columns([1, 2])
        with col_model:
            use_inference = st.checkbox("Use inference model", value=False, 
                                        help="Higher quality but slower/costlier")
        with col_button:
            convert_clicked = st.button("🔄 Convert to Chain of Thought", use_container_width=True)
        
        if convert_clicked:
            if input_prompt.strip():
                with st.spinner("Converting..."):
                    try:
                        converter = PromptConverter()
                        converted, thinking = converter.convert_with_reasoning(input_prompt, use_inference_model=use_inference)
                        st.session_state.converter_output = converted
                        st.session_state.converter_thinking = thinking
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please enter a prompt to convert")
        
        # Show thinking process if available
        if st.session_state.converter_thinking:
            with st.expander("💭 Conversion Reasoning", expanded=False):
                st.markdown(st.session_state.converter_thinking)
        
        # Output text area
        if st.session_state.converter_output:
            st.text_area(
                "Chain of Thought Prompt",
                value=st.session_state.converter_output,
                height=200,
                disabled=True,
                key="converter_output_area"
            )
            
            # Clear button
            def clear_converter():
                st.session_state.converter_input = ""
                st.session_state.converter_output = ""
                st.session_state.converter_thinking = ""
            
            st.button("🗑️ Clear", key="clear_converter", on_click=clear_converter)
    
    # ==========================================================================
    # EVALUATIONS - Run evaluation steps from the dashboard
    # ==========================================================================
    with st.expander("📊 Evaluations", expanded=False):
        import os
        import sys
        import subprocess
        from datetime import datetime
        
        # Helper to get file age info
        def get_file_age_info(filepath):
            """Returns (exists, age_str) for a file."""
            if not os.path.exists(filepath):
                return False, None
            mtime = os.path.getmtime(filepath)
            age_seconds = (datetime.now() - datetime.fromtimestamp(mtime)).total_seconds()
            
            if age_seconds < 60:
                age_str = "just now"
            elif age_seconds < 3600:
                mins = int(age_seconds / 60)
                age_str = f"{mins} minute{'s' if mins != 1 else ''} ago"
            elif age_seconds < 86400:
                hours = int(age_seconds / 3600)
                age_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = int(age_seconds / 86400)
                age_str = f"{days} day{'s' if days != 1 else ''} ago"
            
            return True, age_str
        
        def get_results_info(results_dir):
            """Returns (count, latest_age) for result files."""
            if not os.path.exists(results_dir):
                return 0, None
            files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
            if not files:
                return 0, None
            latest = max(files, key=lambda f: os.path.getmtime(os.path.join(results_dir, f)))
            _, age_str = get_file_age_info(os.path.join(results_dir, latest))
            return len(files), age_str
        
        src2_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        test_data_path = os.path.join(src2_dir, "evaluations", "data", "test_data.jsonl")
        results_dir = os.path.join(src2_dir, "evaluations", "results")
        test_data_exists, test_data_age = get_file_age_info(test_data_path)
        results_count, results_age = get_results_info(results_dir)
        
        # Initialize state
        if "eval_output" not in st.session_state:
            st.session_state.eval_output = None
        if "eval_running" not in st.session_state:
            st.session_state.eval_running = False
        if "confirm_overwrite" not in st.session_state:
            st.session_state.confirm_overwrite = False
        if "confirm_delete_testdata" not in st.session_state:
            st.session_state.confirm_delete_testdata = False
        if "confirm_delete_results" not in st.session_state:
            st.session_state.confirm_delete_results = False
        if "foundry_status" not in st.session_state:
            st.session_state.foundry_status = None  # None = not tested, dict with success/message
        
        # Use the same Python interpreter that's running Streamlit (venv)
        python_exe = sys.executable
        
        # =======================================================================
        # ROW 1: Generate Test Data | Run Evaluation | View Results | Delete
        # =======================================================================
        col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
        
        with col1:
            # Generate Test Data with confirmation if file exists
            if st.session_state.confirm_overwrite:
                st.warning(f"Overwrite test data ({test_data_age})?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes", key="confirm_yes", use_container_width=True):
                        st.session_state.confirm_overwrite = False
                        st.session_state.eval_command = "generate"
                        st.session_state.eval_running = True
                        st.rerun()
                with c2:
                    if st.button("No", key="confirm_no", use_container_width=True):
                        st.session_state.confirm_overwrite = False
                        st.rerun()
            else:
                if st.button("📝 Generate Test Data", use_container_width=True, 
                            help="Run 16 test queries through agent",
                            disabled=st.session_state.eval_running):
                    if test_data_exists:
                        st.session_state.confirm_overwrite = True
                        st.rerun()
                    else:
                        st.session_state.eval_command = "generate"
                        st.session_state.eval_running = True
                        st.rerun()
        
        with col2:
            if st.button("🧪 Run Evaluation", use_container_width=True,
                        help="Evaluate responses using GPT as judge",
                        disabled=st.session_state.eval_running or not test_data_exists):
                st.session_state.eval_command = "eval"
                st.session_state.eval_running = True
                st.rerun()
        
        with col3:
            if st.button("🔍 View Results", use_container_width=True,
                        help="View latest evaluation results",
                        disabled=results_count == 0):
                st.session_state.eval_command = "view_results"
                st.rerun()
        
        with col4:
            # Delete test data
            if st.session_state.confirm_delete_testdata:
                if st.button("❌", key="del_td_confirm", use_container_width=True, help="Confirm delete"):
                    if os.path.exists(test_data_path):
                        os.remove(test_data_path)
                    st.session_state.confirm_delete_testdata = False
                    st.session_state.eval_output = {"title": "Deleted", "success": True, "stdout": "test_data.jsonl deleted"}
                    st.rerun()
            else:
                if st.button("🗑️", key="del_testdata", use_container_width=True, 
                            help="Delete test_data.jsonl",
                            disabled=not test_data_exists):
                    st.session_state.confirm_delete_testdata = True
                    st.rerun()
        
        # =======================================================================
        # ROW 2: Upload to Foundry | Status info | | Delete results
        # =======================================================================
        col5, col6, col7, col8 = st.columns([3, 3, 3, 1])
        
        with col5:
            if st.button("☁️ Upload to Foundry", use_container_width=True,
                        help="Re-run evaluation and upload to Azure AI Foundry",
                        disabled=st.session_state.eval_running or not test_data_exists):
                st.session_state.eval_command = "upload_foundry"
                st.session_state.eval_running = True
                st.rerun()
        
        with col6:
            if test_data_exists:
                st.caption(f"📄 Test data: {test_data_age}")
            else:
                st.caption("📄 No test data")
        
        with col7:
            if results_count > 0:
                st.caption(f"📊 {results_count} result(s), latest: {results_age}")
            else:
                st.caption("📊 No results yet")
        
        with col8:
            # Delete all results
            if st.session_state.confirm_delete_results:
                if st.button("❌", key="del_res_confirm", use_container_width=True, help="Confirm delete all"):
                    if os.path.exists(results_dir):
                        for f in os.listdir(results_dir):
                            if f.endswith('.json'):
                                os.remove(os.path.join(results_dir, f))
                    st.session_state.confirm_delete_results = False
                    st.session_state.eval_output = {"title": "Deleted", "success": True, "stdout": f"Deleted {results_count} result file(s)"}
                    st.rerun()
            else:
                if st.button("🗑️", key="del_results", use_container_width=True,
                            help="Delete all result files",
                            disabled=results_count == 0):
                    st.session_state.confirm_delete_results = True
                    st.rerun()
        
        # =======================================================================
        # Process evaluation commands
        # =======================================================================
        if st.session_state.get("eval_command"):
            cmd = st.session_state.eval_command
            st.session_state.eval_command = None
            
            if cmd == "generate":
                with st.spinner("Generating test data (running 16 queries)..."):
                    try:
                        # Delete old evaluation results since they'll be invalid with new test data
                        deleted_count = 0
                        if os.path.exists(results_dir):
                            for f in os.listdir(results_dir):
                                if f.endswith('.json'):
                                    os.remove(os.path.join(results_dir, f))
                                    deleted_count += 1
                        
                        # Set PYTHONIOENCODING to handle Unicode output
                        env = os.environ.copy()
                        env["PYTHONIOENCODING"] = "utf-8"
                        
                        result = subprocess.run(
                            [python_exe, "-m", "evaluations.generate_test_data"],
                            cwd=src2_dir,
                            capture_output=True,
                            text=True,
                            timeout=120,
                            env=env
                        )
                        
                        # Append cleanup info to output
                        cleanup_msg = f"\n[Cleanup] Deleted {deleted_count} old evaluation result(s)" if deleted_count > 0 else ""
                        st.session_state.eval_output = {
                            "title": "Generate Test Data",
                            "success": result.returncode == 0,
                            "stdout": result.stdout + cleanup_msg,
                            "stderr": result.stderr
                        }
                    except subprocess.TimeoutExpired:
                        st.session_state.eval_output = {"title": "Generate Test Data", "success": False, "stderr": "Timeout after 120s"}
                    except Exception as e:
                        st.session_state.eval_output = {"title": "Generate Test Data", "success": False, "stderr": str(e)}
                st.session_state.eval_running = False
                st.rerun()
            
            elif cmd == "eval":
                with st.spinner("Running evaluation (GPT judge scoring)..."):
                    try:
                        eval_cmd = [python_exe, "-m", "evaluations.run_eval", "--data", "evaluations/data/test_data.jsonl"]
                        
                        # Set PYTHONIOENCODING to handle Unicode from Azure SDK
                        env = os.environ.copy()
                        env["PYTHONIOENCODING"] = "utf-8"
                        
                        result = subprocess.run(
                            eval_cmd,
                            cwd=src2_dir,
                            capture_output=True,
                            text=True,
                            timeout=180,
                            env=env
                        )
                        st.session_state.eval_output = {
                            "title": "Run Evaluation (Local)",
                            "success": result.returncode == 0,
                            "stdout": result.stdout,
                            "stderr": result.stderr
                        }
                    except subprocess.TimeoutExpired:
                        st.session_state.eval_output = {"title": "Run Evaluation", "success": False, "stderr": "Timeout"}
                    except Exception as e:
                        st.session_state.eval_output = {"title": "Run Evaluation", "success": False, "stderr": str(e)}
                st.session_state.eval_running = False
                st.rerun()
            
            elif cmd == "upload_foundry":
                with st.spinner("Running evaluation + uploading to Foundry..."):
                    try:
                        eval_cmd = [python_exe, "-m", "evaluations.run_eval", "--data", "evaluations/data/test_data.jsonl", "--log-to-foundry"]
                        
                        env = os.environ.copy()
                        env["PYTHONIOENCODING"] = "utf-8"
                        
                        result = subprocess.run(
                            eval_cmd,
                            cwd=src2_dir,
                            capture_output=True,
                            text=True,
                            timeout=240,
                            env=env
                        )
                        st.session_state.eval_output = {
                            "title": "Upload to Foundry",
                            "success": result.returncode == 0,
                            "stdout": result.stdout,
                            "stderr": result.stderr
                        }
                    except subprocess.TimeoutExpired:
                        st.session_state.eval_output = {"title": "Upload to Foundry", "success": False, "stderr": "Timeout after 240s"}
                    except Exception as e:
                        st.session_state.eval_output = {"title": "Upload to Foundry", "success": False, "stderr": str(e)}
                st.session_state.eval_running = False
                st.rerun()
            
            elif cmd == "view_results":
                import json
                if os.path.exists(results_dir):
                    files = sorted([f for f in os.listdir(results_dir) if f.endswith('.json')], reverse=True)
                    if files:
                        latest = os.path.join(results_dir, files[0])
                        with open(latest, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        st.session_state.eval_output = {
                            "title": f"Latest Results: {files[0]}",
                            "success": True,
                            "data": data
                        }
                    else:
                        st.session_state.eval_output = {"title": "View Results", "success": False, "stderr": "No result files found"}
                else:
                    st.session_state.eval_output = {"title": "View Results", "success": False, "stderr": "Results directory not found"}
                st.rerun()
        
        # =======================================================================
        # Display output
        # =======================================================================
        if st.session_state.eval_output:
            st.divider()
            output = st.session_state.eval_output
            st.markdown(f"**{output['title']}**")
            
            if output.get("success"):
                st.success("Completed successfully")
                if output.get("data"):
                    # Show summary metrics first
                    data = output["data"]
                    metrics = data.get("metrics", {})
                    rows = data.get("rows", [])
                    
                    if metrics:
                        st.markdown("##### Aggregate Scores (1-5 scale)")
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Relevance", f"{metrics.get('relevance.relevance', 0):.2f}")
                        m2.metric("Coherence", f"{metrics.get('coherence.coherence', 0):.2f}")
                        m3.metric("Groundedness", f"{metrics.get('groundedness.groundedness', 0):.2f}")
                        m4.metric("Fluency", f"{metrics.get('fluency.fluency', 0):.2f}")
                        
                        st.markdown("##### Pass Rates (threshold: 3)")
                        p1, p2, p3, p4 = st.columns(4)
                        p1.metric("Relevance", f"{metrics.get('relevance.binary_aggregate', 0)*100:.0f}%")
                        p2.metric("Coherence", f"{metrics.get('coherence.binary_aggregate', 0)*100:.0f}%")
                        p3.metric("Groundedness", f"{metrics.get('groundedness.binary_aggregate', 0)*100:.0f}%")
                        p4.metric("Fluency", f"{metrics.get('fluency.binary_aggregate', 0)*100:.0f}%")
                    
                    if rows:
                        st.caption(f"📋 {len(rows)} test cases evaluated")
                    
                    # View Full JSON button
                    with st.expander("📄 View Full JSON", expanded=False):
                        st.json(data)
                
                elif output.get("stdout"):
                    st.code(output["stdout"][-2000:] if len(output.get("stdout", "")) > 2000 else output["stdout"])
            else:
                st.error("Failed")
                if output.get("stderr"):
                    st.code(output["stderr"][-1000:] if len(output.get("stderr", "")) > 1000 else output["stderr"])
            
            if st.button("Clear Output", use_container_width=False):
                st.session_state.eval_output = None
                st.rerun()
        
        # =======================================================================
        # FOUNDRY CONNECTIVITY TEST (centered link at bottom)
        # =======================================================================
        st.divider()
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            if st.button("🔗 Test Foundry Connection", key="test_foundry", use_container_width=True):
                try:
                    from dotenv import load_dotenv
                    load_dotenv(os.path.join(src2_dir, "..", ".env"))
                    
                    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
                    
                    if not endpoint:
                        st.session_state.foundry_status = {
                            "success": False, 
                            "message": "AZURE_AI_PROJECT_ENDPOINT not set in .env"
                        }
                    else:
                        from azure.identity import DefaultAzureCredential
                        credential = DefaultAzureCredential()
                        token = credential.get_token("https://cognitiveservices.azure.com/.default")
                        st.session_state.foundry_status = {
                            "success": True,
                            "message": f"Auth OK: {endpoint[:60]}..."
                        }
                except Exception as e:
                    st.session_state.foundry_status = {"success": False, "message": str(e)[:100]}
                st.rerun()
        
        # Show status if tested
        if st.session_state.foundry_status:
            status = st.session_state.foundry_status
            if status["success"]:
                st.success(f"✅ {status['message']}")
            else:
                st.error(f"❌ {status['message']}")
    
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
