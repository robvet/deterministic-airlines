"""
HTML Seat Map Component for Streamlit.

Renders an airline-style seat map using embedded HTML/CSS/JS.
Clicking a seat visually highlights it (client-side only).

Usage:
    import streamlit.components.v1 as components
    from components.seat_map import render_seat_map_html
    
    components.html(render_seat_map_html(selected_seat="12A"), height=600)
"""


def render_seat_map_html(selected_seat: str | None = None) -> str:
    """
    Generate HTML for an interactive seat map.
    
    Args:
        selected_seat: Pre-selected seat to highlight (e.g., "12A")
    
    Returns:
        HTML string to render with st.components.v1.html()
    """
    selected_js = f'"{selected_seat}"' if selected_seat else 'null'
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f4f8; padding: 15px; }}
        .container {{ max-width: 350px; margin: 0 auto; background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h3 {{ text-align: center; color: #1e3a5f; margin-bottom: 15px; font-size: 18px; }}
        .legend {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 20px; font-size: 11px; }}
        .legend-item {{ display: flex; align-items: center; gap: 4px; }}
        .legend-box {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid #ccc; }}
        .legend-available {{ background: #d1fae5; border-color: #6ee7b7; }}
        .legend-occupied {{ background: #d1d5db; }}
        .legend-exit {{ background: #fef3c7; border-color: #fcd34d; }}
        .legend-selected {{ background: #059669; }}
        
        .cabin {{ margin-bottom: 20px; }}
        .cabin-title {{ text-align: center; font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 8px; border-bottom: 1px solid #e5e7eb; padding-bottom: 5px; }}
        .row {{ display: flex; justify-content: center; align-items: center; gap: 3px; margin-bottom: 3px; }}
        .row-num {{ width: 20px; font-size: 10px; color: #94a3b8; text-align: right; margin-right: 5px; }}
        .aisle {{ width: 15px; }}
        .seat {{ width: 28px; height: 28px; font-size: 10px; font-weight: 500; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s; }}
        .seat:hover:not(.occupied) {{ transform: scale(1.1); }}
        .seat.available {{ background: #d1fae5; border-color: #6ee7b7; color: #065f46; }}
        .seat.occupied {{ background: #d1d5db; color: #6b7280; cursor: not-allowed; }}
        .seat.exit {{ background: #fef3c7; border-color: #fcd34d; color: #92400e; }}
        .seat.selected {{ background: #059669; color: white; border-color: #047857; }}
        
        .selection {{ text-align: center; margin-top: 15px; padding: 10px; background: #eff6ff; border-radius: 8px; font-size: 13px; color: #1e40af; }}
        .selection.hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h3>🛫 Select Your Seat</h3>
        <div class="legend">
            <div class="legend-item"><div class="legend-box legend-available"></div>Available</div>
            <div class="legend-item"><div class="legend-box legend-occupied"></div>Occupied</div>
            <div class="legend-item"><div class="legend-box legend-exit"></div>Exit Row</div>
            <div class="legend-item"><div class="legend-box legend-selected"></div>Selected</div>
        </div>
        <div id="seatMap"></div>
        <div id="selection" class="selection hidden"></div>
    </div>
    
    <script>
        const OCCUPIED = new Set(['1A','2B','3C','5A','5F','7B','7E','9A','9F','10C','10D','12A','12F','14B','14E','16A','16F','18C','18D','20A','20F','22B','22E','24A','24F']);
        const EXIT_ROWS = new Set([4, 16]);
        let selectedSeat = {selected_js};
        
        const cabins = [
            {{ name: 'Business Class', rows: [1,2,3,4], seats: ['A','B','C','D'] }},
            {{ name: 'Economy Plus', rows: [5,6,7,8], seats: ['A','B','C','D','E','F'] }},
            {{ name: 'Economy', rows: [...Array(16)].map((_,i)=>i+9), seats: ['A','B','C','D','E','F'] }}
        ];
        
        function render() {{
            const container = document.getElementById('seatMap');
            container.innerHTML = cabins.map(cabin => `
                <div class="cabin">
                    <div class="cabin-title">${{cabin.name}}</div>
                    ${{cabin.rows.map(row => {{
                        const isExit = EXIT_ROWS.has(row);
                        const left = cabin.seats.slice(0, cabin.seats.length/2);
                        const right = cabin.seats.slice(cabin.seats.length/2);
                        return `<div class="row">
                            <span class="row-num">${{row}}</span>
                            ${{left.map(s => seatBtn(row, s, isExit)).join('')}}
                            <span class="aisle"></span>
                            ${{right.map(s => seatBtn(row, s, isExit)).join('')}}
                        </div>`;
                    }}).join('')}}
                </div>
            `).join('');
            updateSelection();
        }}
        
        function seatBtn(row, letter, isExit) {{
            const id = row + letter;
            const occupied = OCCUPIED.has(id);
            const selected = selectedSeat === id;
            let cls = 'seat ';
            if (occupied) cls += 'occupied';
            else if (selected) cls += 'selected';
            else if (isExit) cls += 'exit';
            else cls += 'available';
            return `<button class="${{cls}}" onclick="selectSeat('${{id}}',${{occupied}})" title="Seat ${{id}}${{isExit?' (Exit Row)':''}}">${{letter}}</button>`;
        }}
        
        function selectSeat(id, occupied) {{
            if (occupied) return;
            selectedSeat = id;
            render();
        }}
        
        function updateSelection() {{
            const el = document.getElementById('selection');
            if (selectedSeat) {{
                el.textContent = '✅ Selected: Seat ' + selectedSeat;
                el.classList.remove('hidden');
            }} else {{
                el.classList.add('hidden');
            }}
        }}
        
        render();
    </script>
</body>
</html>
'''
