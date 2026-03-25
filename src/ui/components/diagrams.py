import streamlit as st
import os
import re
import html
import json
import hashlib

def render_svg(code, name="diagram", theme="dark"):
    """Renders Raw SVG code by injecting it directly via st.components (Most Robust)."""
    try:
        clean_svg = code.strip()
        # Remove potential surrounding backticks
        if "```" in clean_svg:
            match = re.search(r"```(?:svg)?\n?(.*?)\n?```", clean_svg, re.DOTALL)
            if match: clean_svg = match.group(1).strip()
        
        # Ensure it starts with <svg
        if not clean_svg.startswith("<svg"):
            idx = clean_svg.find("<svg")
            if idx != -1: clean_svg = clean_svg[idx:]
            else: clean_svg = f'<svg viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">{clean_svg}</svg>'
        
        # Cleanup trailing junk
        last_tag = clean_svg.rfind("</svg>")
        if last_tag != -1: clean_svg = clean_svg[:last_tag+6]

        bg_color = "#ffffff" if theme.lower() == "light" else "#0a0c10"

        st.components.v1.html(f"""
            <div style="background: {bg_color}; border-radius: 8px; padding: 10px; display: flex; justify-content: center; align-items: center; overflow: auto;">
                {clean_svg}
            </div>
            <style>
                svg {{ max-width: 100%; height: auto; display: block; margin: auto; }}
                body {{ margin: 0; background: {bg_color}; }}
            </style>
        """, height=500, scrolling=True)
        
        col1, col2 = st.columns(2)
        
        # Clean up name for file export (e.g. "Diagram Type: Use Case" -> "USE_CASE")
        clean_name = re.sub(r'diagram\s*type\s*[:\-]*\s*', '', name, flags=re.IGNORECASE).strip()
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', clean_name).strip('_').upper()
        clean_name = re.sub(r'_+', '_', clean_name)
        if not clean_name: clean_name = "DIAGRAM"
        export_name = f"{clean_name}_{theme.upper()}"
        
        with col1:
            st.download_button(label=f"📥 Download SVG", data=clean_svg, file_name=f"{export_name}.svg", mime="image/svg+xml")
        
        with col2:
            try:
                from svglib.svglib import svg2rlg
                from reportlab.graphics import renderPM
                import io, os, tempfile
                with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w", encoding="utf-8") as tf:
                    tf.write(clean_svg)
                    tmp_path = tf.name
                
                drawing = svg2rlg(tmp_path)
                if drawing:
                    png_io = io.BytesIO()
                    renderPM.drawToFile(drawing, png_io, fmt="PNG")
                    st.download_button(label=f"📥 Download PNG", data=png_io.getvalue(), file_name=f"{export_name}.png", mime="image/png")
                os.remove(tmp_path)
            except Exception as e:
                st.error(f"PNG conversion unavailable: {e}")
                
    except Exception as e:
        st.error(f"Failed to render visualization: {e}")
        st.code(code, language="xml")

def render_diagram(code, name="diagram", lang="mermaid"):
    """Fallback for legacy content."""
    if lang == "svg": render_svg(code, name)
    else:
        st.info(f"Rendering {lang} is restricted on this host. Below is the source:")
        st.code(code, language=lang)

def display_content_with_diagrams(content, headers=None, key_prefix="general"):
    """Helper to detect and display diagrams within a message."""
    svg_blocks = re.findall(r"```svg\n?(.*?)\n?```", content, re.DOTALL)
    mermaid_blocks = re.findall(r"```mermaid\n?(.*?)\n?```", content, re.DOTALL)
    dot_blocks = re.findall(r"```(?:dot|graphviz)\n?(.*?)\n?```", content, re.DOTALL)
    
    # Emergency Fallback: Raw tags (More robust regex)
    if not any([svg_blocks, mermaid_blocks, dot_blocks]):
        svg_blocks = re.findall(r"(<svg\b[^>]*>.*?</svg>)", content, re.DOTALL | re.IGNORECASE)
    
    if svg_blocks or mermaid_blocks or dot_blocks:
        if headers is None:
            headers = re.findall(r"###?\s+(.*?)\n", content)
        
        block_idx = 0
        for block in svg_blocks:
            label = headers[block_idx] if headers and block_idx < len(headers) else f"Visualization {block_idx+1}"
            st.subheader(f"🖼️ {label}")
            
            theme_choice = "Dark"
            json_payload_match = re.search(r'<desc id="json-payload">(.*?)</desc>', block, re.DOTALL)
            if json_payload_match:
                unique_hash = hashlib.md5(block.encode('utf-8', errors='ignore')).hexdigest()[:8]
                theme_choice = st.selectbox("Appearance", ["Dark", "Light"], key=f"theme_{key_prefix}_{label}_{block_idx}_{unique_hash}", index=0)
                try:
                    json_data = json.loads(html.unescape(json_payload_match.group(1)))
                    from src.utils.diagram_renderer import DiagramRenderer
                    renderer = DiagramRenderer(theme=theme_choice)
                    block = renderer.render(json.dumps(json_data))
                except Exception as e:
                    pass
            
            render_svg(block, name=label, theme=theme_choice)
            block_idx += 1
            
        for block in mermaid_blocks:
            label = headers[block_idx] if block_idx < len(headers) else f"Mermaid Code {block_idx+1}"
            render_diagram(block, name=label, lang="mermaid")
            block_idx += 1
            
        for block in dot_blocks:
            label = headers[block_idx] if block_idx < len(headers) else f"DOT Code {block_idx+1}"
            render_diagram(block, name=label, lang="dot")
            block_idx += 1
    else:
        st.markdown(content)
