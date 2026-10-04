"""
Lightweight bubble-packing layout.
Plotly has no native "packed bubble" chart (Tableau's term for a
circle-packing view), so this places circles on a tight spiral, sized
by value, without true physics — visually equivalent for a handful of
categories, which is all these dashboards need.
"""
import math
import plotly.graph_objects as go


def packed_bubble_figure(labels, values, colors=None, title=""):
    n = len(labels)
    if n == 0:
        return go.Figure()

    max_v = max(values) if max(values) else 1
    sizes = [18 + 46 * (v / max_v) ** 0.5 for v in values]

    xs, ys = [0.0], [0.0]
    placed_r = [sizes[0]]
    golden_angle = math.pi * (3 - math.sqrt(5))

    for i in range(1, n):
        r = sizes[i]
        # spiral outward until it doesn't overlap previously placed circles
        t = 0.0
        while True:
            t += 0.35
            ang = i * golden_angle + t
            dist = 6 + 5.2 * t
            x, y = dist * math.cos(ang), dist * math.sin(ang)
            ok = all(
                (x - xs[j]) ** 2 + (y - ys[j]) ** 2 >= ((r + placed_r[j]) * 0.62) ** 2
                for j in range(len(xs))
            )
            if ok or t > 40:
                break
        xs.append(x)
        ys.append(y)
        placed_r.append(r)

    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers+text",
        marker=dict(size=sizes, color=colors, line=dict(color="white", width=2)),
        text=labels, textposition="middle center",
        textfont=dict(color="white", size=11),
        hovertext=[f"{l}: {v}" for l, v in zip(labels, values)],
        hoverinfo="text",
    ))
    fig.update_layout(
        title=title, showlegend=False,
        xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
    )
    return fig
