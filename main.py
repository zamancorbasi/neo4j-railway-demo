import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from neo4j import GraphDatabase

app = FastAPI(title="Harmoni Digital Twin Graph")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@app.get("/api/graph-data")
def get_graph_data():
    query = """
    MATCH (n)-[r]->(m)
    RETURN 
        elementId(n) AS source_id, 
        labels(n)[0] AS source_label, 
        coalesce(n.name, n.code, n.id, n.key, labels(n)[0]) AS source_name,
        elementId(m) AS target_id, 
        labels(m)[0] AS target_label, 
        coalesce(m.name, m.code, m.id, m.key, labels(m)[0]) AS target_name,
        type(r) AS rel_type
    LIMIT 350
    """
    try:
        with driver.session() as session:
            result = session.run(query)
            nodes = {}
            links = []
            for record in result:
                s_id = str(record["source_id"])
                t_id = str(record["target_id"])
                if s_id not in nodes:
                    nodes[s_id] = {"id": s_id, "label": record["source_name"], "group": record["source_label"]}
                if t_id not in nodes:
                    nodes[t_id] = {"id": t_id, "label": record["target_name"], "group": record["target_label"]}
                links.append({"source": s_id, "target": t_id, "type": record["rel_type"]})
            return {"nodes": list(nodes.values()), "links": links}
    except Exception as e:
        return {"error": str(e)}

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Harmoni Digital Twin - Live Graph</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0d1117; color: #f0f6fc; margin: 0; padding: 20px; }
            #header { display: flex; justify-content: space-between; align-items: center; background-color: #161b22; padding: 16px 24px; border-radius: 10px; border: 1px solid #30363d; }
            button { background-color: #238636; color: white; padding: 10px 18px; font-weight: 600; border-radius: 6px; border: none; cursor: pointer; transition: 0.2s; }
            button:hover { background-color: #2ea043; }
            #network { width: 100%; height: 76vh; background-color: #161b22; border-radius: 10px; margin-top: 15px; border: 1px solid #30363d; }
            .legend { display: flex; gap: 14px; margin-top: 12px; font-size: 13px; flex-wrap: wrap; }
            .legend-item { display: flex; align-items: center; gap: 6px; }
            .badge { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
        </style>
    </head>
    <body>
        <div id="header">
            <div>
                <h2 style="margin: 0 0 5px 0;">🌋 Harmoni Digital Twin — Canlı Veritabanı Haritası</h2>
                <span style="color: #8b949e; font-size: 14px;">Railway Neo4j üzerinde çalışan ilişkisel graf modeli</span>
            </div>
            <button onclick="loadGraph()">Grafiği Yenile</button>
        </div>

        <div class="legend">
            <div class="legend-item"><span class="badge" style="background:#ef4444;"></span> Deprem / Yayılım Zonu</div>
            <div class="legend-item"><span class="badge" style="background:#f59e0b;"></span> NaTech Kaynak (Tank/Boru)</div>
            <div class="legend-item"><span class="badge" style="background:#3b82f6;"></span> Kritik Altyapı (Hastane/Liman)</div>
            <div class="legend-item"><span class="badge" style="background:#10b981;"></span> Mahalle / İlçe</div>
            <div class="legend-item"><span class="badge" style="background:#8b5cf6;"></span> Hiyerarşi (Zemin/Fay/Derinlik)</div>
            <div class="legend-item"><span class="badge" style="background:#ec4899;"></span> AFAD Müdahale / Ekipler</div>
        </div>

        <div id="network"></div>

        <script>
            function getColor(group) {
                switch(group) {
                    case 'EarthquakeScenario': case 'DispersionZone': return '#ef4444';
                    case 'CBRN_Event': return '#dc2626';
                    case 'CriticalInfrastructure': return '#f59e0b';
                    case 'District': case 'Neighbourhood': return '#10b981';
                    case 'SoilClass': case 'FaultMode': case 'DepthBin': case 'SoilClassParent': case 'FaultModeParent': case 'DepthBinParent': case 'MagnitudeBinParent': case 'DurationBinParent': return '#8b5cf6';
                    case 'InterventionPlan': case 'InterventionTask': case 'ResponseTeam': case 'ResponseRoute': case 'SafeZone': return '#ec4899';
                    default: return '#6b7280';
                }
            }

            async function loadGraph() {
                const res = await fetch('/api/graph-data');
                const data = await res.json();
                if(data.error) {
                    alert('Hata: ' + data.error);
                    return;
                }

                const container = document.getElementById('network');
                const graphData = {
                    nodes: new vis.DataSet(data.nodes.map(n => ({
                        id: n.id,
                        label: `${n.group}\\n(${n.label})`,
                        color: { background: getColor(n.group), border: '#ffffff' },
                        font: { color: '#ffffff', face: 'monospace', size: 11 },
                        shape: 'box',
                        margin: 8
                    }))),
                    edges: new vis.DataSet(data.links.map(l => ({
                        from: l.source,
                        to: l.target,
                        label: l.type,
                        font: { color: '#8b949e', size: 10, align: 'middle' },
                        arrows: 'to',
                        color: { color: '#30363d', highlight: '#58a6ff' }
                    })))
                };

                const options = {
                    physics: {
                        stabilization: true,
                        barnesHut: { springLength: 170, springConstant: 0.04, damping: 0.09 }
                    },
                    interaction: { hover: true, tooltipDelay: 150 }
                };

                new vis.Network(container, graphData, options);
            }

            window.onload = loadGraph;
        </script>
    </body>
    </html>
    """