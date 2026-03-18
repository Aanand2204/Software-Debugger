import json

class DiagramRenderer:
    """Renders professional-grade architectural blueprints from structured JSON data."""
    
    def __init__(self, width=1200, height=1000, theme="dark"):
        self.width = width
        self.height = height
        self.box_w = 230
        self.box_h = 130
        self.row_y = [100, 350, 600, 850] # Increased vertical spacing
        self.theme = theme.lower()
        if self.theme == "light":
            self.colors = ["#2E7D32", "#EF6C00", "#6A1B9A", "#1565C0"]
            self.glow_color = "#888888"
            self.bg_color = "#f4f4f9"
            self.text_color = "#222222"
            self.glass_start = "#ffffff;stop-opacity:0.9"
            self.glass_end = "#ffffff;stop-opacity:0.6"
        else:
            self.colors = ["#43A047", "#FB8C00", "#8E24AA", "#1E88E5"]
            self.glow_color = "#BB86FC"
            self.bg_color = "#0a0c10"
            self.text_color = "#ffffff"
            self.glass_start = "#ffffff;stop-opacity:0.08"
            self.glass_end = "#ffffff;stop-opacity:0.01"

    def render(self, data):
        try:
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    import ast
                    data = ast.literal_eval(data)
            
            nodes_raw = data.get("nodes", [])
            edges = data.get("edges", [])
            
            if not nodes_raw:
                return f'<svg viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg"><rect width="{self.width}" height="{self.height}" fill="{self.bg_color}"/><text x="{self.width/2}" y="{self.height/2}" font-family="Segoe UI, Arial" fill="#ff6b6b" font-size="20" text-anchor="middle">Error: The AI generated an empty architecture diagram.</text></svg>'
            
            # Map nodes to layers
            layers = [[], [], [], []]
            node_map = {}
            for n in nodes_raw:
                l_idx = n.get("layer", 0)
                if l_idx > 3: l_idx = 3
                layers[l_idx].append(n)

            import html
            json_payload = html.escape(json.dumps({"nodes": nodes_raw, "edges": edges}))
            
            svg = [
                f'<svg viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg">',
                '  <defs>',
                '    <linearGradient id="glassGrad" x1="0%" y1="0%" x2="100%" y2="100%">',
                f'      <stop offset="0%" style="stop-color:{self.glass_start}" />',
                f'      <stop offset="100%" style="stop-color:{self.glass_end}" />',
                '    </linearGradient>',
                f'    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceAlpha" stdDeviation="4"/><feFlood flood-color="{self.glow_color}" flood-opacity="0.2"/><feComposite in2="blur" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
                f'    <marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><polygon points="0 0, 10 4, 0 8" fill="{self.glow_color}"/></marker>',
                '  </defs>',
                f'  <rect width="{self.width}" height="{self.height}" fill="{self.bg_color}" rx="12"/>',
                f'  <desc id="json-payload">{json_payload}</desc>'
            ]
            
            # 1. Position and Render Nodes
            for l_idx, layer_nodes in enumerate(layers):
                count = len(layer_nodes)
                if count == 0: continue
                
                # Center nodes horizontally within the layer
                total_w = count * self.box_w + (count - 1) * 80 # 80 is gap
                start_x = (self.width - total_w) / 2
                
                for i, node in enumerate(layer_nodes):
                    x = start_x + i * (self.box_w + 80)
                    y = self.row_y[l_idx]
                    
                    node_id = node.get("id")
                    label = node.get("label", "Component")
                    color = self.colors[l_idx]
                    node_map[node_id] = {"id": node_id, "x": x, "y": y, "layer": l_idx, "color": color, "index": i}
                    
                    # Render Node
                    svg.append(f'  <g transform="translate({x}, {y})" filter="url(#glow)">')
                    svg.append(f'    <rect width="{self.box_w}" height="{self.box_h}" rx="12" fill="url(#glassGrad)" stroke="{color}" stroke-width="2" opacity="0.9"/>')
                    svg.append(f'    <rect width="4" height="{self.box_h/2}" x="0" y="{self.box_h/4}" fill="{color}" rx="2"/>') # Side indicator
                    
                    # Text wrapping/splitting
                    if "(" in label:
                        lines = label.split("(", 1)
                        lines[1] = "(" + lines[1]
                    else:
                        # Split by space if too long
                        if len(label) > 20:
                            mid = len(label) // 2
                            split_idx = label.find(" ", mid - 5, mid + 5)
                            if split_idx == -1: split_idx = label.find(" ", 0)
                            if split_idx != -1:
                                lines = [label[:split_idx], label[split_idx+1:]]
                            else:
                                lines = [label]
                        else:
                            lines = [label]

                    if len(lines) > 1:
                        svg.append(f'    <text x="{self.box_w/2}" y="{self.box_h/2 - 5}" font-family="Segoe UI, Inter, Arial" fill="{self.text_color}" font-size="15" font-weight="600" text-anchor="middle">{lines[0].strip()}</text>')
                        svg.append(f'    <text x="{self.box_w/2}" y="{self.box_h/2 + 20}" font-family="Segoe UI, Inter, Arial" fill="{color}" font-size="12" opacity="0.8" text-anchor="middle">{lines[1].strip()}</text>')
                    else:
                        svg.append(f'    <text x="{self.box_w/2}" y="{self.box_h/2 + 6}" font-family="Segoe UI, Inter, Arial" fill="{self.text_color}" font-size="16" font-weight="600" text-anchor="middle">{label}</text>')
                    svg.append('  </g>')

            # 2. Render Edges with Smooth Bézier Routing
            for i, edge in enumerate(edges):
                sid = edge.get("from")
                tid = edge.get("to")
                if sid not in node_map or tid not in node_map: continue
                
                s = node_map[sid]
                t = node_map[tid]
                
                # Jitter to prevent complete overlap on duplicate paths
                jitter = (i % 3) * 10 - 10
                
                x1 = s["x"] + self.box_w / 2 + jitter
                y1 = s["y"] + self.box_h
                x2 = t["x"] + self.box_w / 2 + jitter
                y2 = t["y"]
                
                color = s["color"]
                
                if s["layer"] == t["layer"]:
                    # Same layer: Bridge path
                    sy = s["y"] + self.box_h / 2 + jitter
                    if s["id"] == t["id"]:
                        # Self-loop
                        sx = s["x"] + self.box_w
                        path = f"M {sx} {sy - 10} C {sx+60} {sy - 20} {sx+60} {sy + 20} {sx} {sy + 10}"
                    else:
                        if s["x"] < t["x"]:
                            sx, tx = s["x"] + self.box_w, t["x"]
                        else:
                            sx, tx = s["x"], t["x"] + self.box_w
                        
                        # Arc for same-layer connection
                        ctrl_y = sy - 40 if s["x"] < t["x"] else sy + 40
                        path = f"M {sx} {sy} Q {(sx+tx)/2} {ctrl_y} {tx} {sy}"
                else:
                    # Discrete layers: Smooth S-Curve (Cubic Bézier)
                    # Vertical midpoint offset for the curve control points
                    v_gap = abs(y2 - y1)
                    c_dist = v_gap * 0.6
                    
                    if s["layer"] < t["layer"]:
                        # Flowing downwards
                        path = f"M {x1} {y1} C {x1} {y1 + c_dist} {x2} {y2 - c_dist} {x2} {y2}"
                    else:
                        # Flowing upwards (Back-reference)
                        # Go from left side to left side safely
                        start_x = s["x"]
                        start_y = s["y"] + self.box_h / 2 + jitter
                        end_x = t["x"]
                        end_y = t["y"] + self.box_h / 2 + jitter
                        mid_x = min(start_x, end_x) - 150
                        path = f"M {start_x} {start_y} C {mid_x} {start_y} {mid_x} {end_y} {end_x} {end_y}"
                
                svg.append(f'  <path d="{path}" fill="none" stroke="{color}" stroke-width="2.5" opacity="0.6" marker-end="url(#arrow)"/>')

            svg.append('</svg>')
            return "\n".join(svg)
        except Exception as e:
            import html
            err_msg = html.escape(str(e))
            bg = getattr(self, "bg_color", "#0a0c10")
            return f'<svg viewBox="0 0 1200 1000" xmlns="http://www.w3.org/2000/svg"><rect width="1200" height="1000" fill="{bg}"/><text x="600" y="500" font-family="Segoe UI, Arial" fill="#ff6b6b" font-size="20" text-anchor="middle">Error Rendering Diagram: {err_msg}</text></svg>'

def render_json_diagram(content):
    import re
    renderer = DiagramRenderer()
    match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if match:
        json_str = match.group(1)
        svg_output = renderer.render(json_str)
        return content.replace(match.group(0), f"### System Architecture Blueprint\n\n```svg\n{svg_output}\n```")
    return content
