import networkx as nx
import plotly.graph_objects as go
import pandas as pd

def construir_grafo_bipartito_fraccionamiento(df_relacionados: pd.DataFrame, ruc_entidad_foco: str = None):
    """
    Construye un Grafo Bipartito / Multicapa con NetworkX conectando:
    - Nodos Entidad (Color Azul Corporativo)
    - Nodos Convocatoria (Color según Puntaje de Riesgo: Rojo > 0.70, Naranja, Verde)
    - Nodos CUBSO / Categoría de Bien (Color Gris / Violeta)
    Retorna la figura interactiva de Plotly de la red.
    """
    G = nx.Graph()

    if df_relacionados.empty:
        fig = go.Figure()
        fig.update_layout(title="Sin datos suficientes para construir la red de contrataciones.")
        return fig, G

    # Agregar nodos y aristas
    for _, row in df_relacionados.iterrows():
        entidad_node = f"RUC: {row['entidad_ruc']}"
        conv_node = f"Conv #{row['id_convocatoria']}"
        cubso_node = f"CUBSO: {row.get('codigo_cubso', 'N/A') or 'GENERAL'}"

        score_riesgo = float(row.get('puntaje_riesgo', 0.0))

        # El puntaje se almacena en una escala de 0 a 100.
        if score_riesgo >= 71.0:
            color_conv = "#FF6174"
        elif score_riesgo >= 41.0:
            color_conv = "#FFB547"
        else:
            color_conv = "#2DD4BF"

        # Agregar Entidad
        if not G.has_node(entidad_node):
            G.add_node(entidad_node, tipo='Entidad', color='#1E88E5', size=25, label=row['entidad_nombre'])

        # Agregar Convocatoria
        G.add_node(
            conv_node,
            tipo='Convocatoria',
            color=color_conv,
            size=18,
            monto=row['monto_referencial'],
            descripcion=row['descripcion_item'][:60],
            riesgo=score_riesgo
        )

        # Agregar CUBSO
        if not G.has_node(cubso_node):
            G.add_node(cubso_node, tipo='CUBSO', color='#8E44AD', size=15, label=cubso_node)

        # Enlaces
        G.add_edge(entidad_node, conv_node, weight=1)
        G.add_edge(conv_node, cubso_node, weight=1)

    # Disposición espacial (Layout Fruchterman-Reingold / Spring)
    pos = nx.spring_layout(G, k=0.5, seed=42)

    # Aristas (Edges)
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.5, color='#CBD5E1'),
        hoverinfo='none',
        mode='lines'
    )

    # Nodos (Nodes)
    node_x = []
    node_y = []
    node_colors = []
    node_sizes = []
    node_hovertext = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        attrs = G.nodes[node]
        node_colors.append(attrs.get('color', '#94A3B8'))
        node_sizes.append(attrs.get('size', 15))

        if attrs.get('tipo') == 'Convocatoria':
            hover = f"<b>{node}</b><br>Monto: S/ {attrs.get('monto', 0):,.2f}<br>Puntaje: {attrs.get('riesgo', 0):.1f}<br>Descripción: {attrs.get('descripcion')}"
        else:
            hover = f"<b>{node}</b><br>Tipo: {attrs.get('tipo')}"

        node_hovertext.append(hover)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[node if len(node) < 15 else node[:12]+"..." for node in G.nodes()],
        textposition="top center",
        hovertext=node_hovertext,
        marker=dict(
            color=node_colors,
            size=node_sizes,
            line=dict(width=1.5, color='#FFFFFF')
        )
    )

    # Crear Figura
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=dict(text="Relaciones entre operaciones y categorías", x=0.5, font=dict(size=14, color="#C4CEE0")),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=10, l=10, r=10, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="#C4CEE0"),
    )

    return fig, G
