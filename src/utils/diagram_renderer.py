import json

class DiagramRenderer:
    """Renders professional-grade architectural blueprints from structured JSON data."""
    
    def __init__(self, width=1200, height=1000):
        self.width = width
        self.height = height
        self.box_w = 230
        self.box_h = 130
        self.row_y = [100, 350, 600, 850] # Increased vertical spacing
        self.colors = ["#43A047", "#FB8C00", "#8E24AA", "#1E88E5"] # Green, Orange, Purple, Blue
        self.glow_color = "#BB86FC"

    def render(self, data):
        try:
            if isinstance(data, str):
                data = json.loads(data)
            
            nodes_raw = data.get("nodes", [])
            edges = data.get("edges", [])
            
            # Map nodes to layers
            layers = [[], [], [], []]
            node_map = {}
            for n in nodes_raw:
                l_idx = n.get("layer", 0)
                if l_idx > 3: l_idx = 3
                layers[l_idx].append(n)

            svg = [
                f'<svg viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg">',
                '  <defs>',
                '    <linearGradient id="glassGrad" x1="0%" y1="0%" x2="100%" y2="100%">',
                '      <stop offset="0%" style="stop-color:#ffffff;stop-opacity:0.08" />',
                '      <stop offset="100%" style="stop-color:#ffffff;stop-opacity:0.01" />',
                '    </linearGradient>',
                f'    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceAlpha" stdDeviation="4"/><feFlood flood-color="{self.glow_color}" flood-opacity="0.2"/><feComposite in2="blur" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
                f'    <marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><polygon points="0 0, 10 4, 0 8" fill="{self.glow_color}"/></marker>',
                '  </defs>',
                f'  <rect width="{self.width}" height="{self.height}" fill="#0a0c10" rx="12"/>'
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
                    node_map[node_id] = {"x": x, "y": y, "layer": l_idx, "color": color, "index": i}
                    
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
                        svg.append(f'    <text x="{self.box_w/2}" y="{self.box_h/2 - 5}" font-family="Segoe UI, Inter, Arial" fill="#ffffff" font-size="15" font-weight="600" text-anchor="middle">{lines[0].strip()}</text>')
                        svg.append(f'    <text x="{self.box_w/2}" y="{self.box_h/2 + 20}" font-family="Segoe UI, Inter, Arial" fill="{color}" font-size="12" opacity="0.8" text-anchor="middle">{lines[1].strip()}</text>')
                    else:
                        svg.append(f'    <text x="{self.box_w/2}" y="{self.box_h/2 + 6}" font-family="Segoe UI, Inter, Arial" fill="#ffffff" font-size="16" font-weight="600" text-anchor="middle">{label}</text>')
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
                        # Use a wider side-arc to minimize clutter
                        mid_x = min(x1, x2) - 150
                        path = f"M {x1} {y1-self.box_h} C {mid_x} {y1-self.box_h} {mid_x} {y2+self.box_h} {x2+self.box_w} {y2+self.box_h/2}"
                
                svg.append(f'  <path d="{path}" fill="none" stroke="{color}" stroke-width="2.5" opacity="0.6" marker-end="url(#arrow)"/>')

            svg.append('</svg>')
            return "\n".join(svg)
        except Exception as e:
            return f"<!-- Rendering Error: {str(e)} -->"

def render_json_diagram(content):
    import re
    renderer = DiagramRenderer()
    match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if match:
        json_str = match.group(1)
        svg_output = renderer.render(json_str)
        return content.replace(match.group(0), f"### System Architecture Blueprint\n\n```svg\n{svg_output}\n```")
    return content
