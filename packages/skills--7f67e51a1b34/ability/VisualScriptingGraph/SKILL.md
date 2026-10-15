---
name: VisualScriptingGraph
description: 脚本Graph理解 - 查看和分析脚本Graph、ComponentGraph 和 Subgraph，用于理解已有的可视化脚本。
---

# VisualScriptingGraph

Use this skill when logic already lives in visual scripting and the task is to understand it, explain it, or prepare a later migration path. The current MCP surface only supports **reading saved graph data**.

## Core rules

- Do **not** promise graph authoring, graph mutation, or automatic graph-to-script conversion through MCP.
- Ordinary scene/resource edits outside the graph are still normal scene edits; the read-only rule only applies to the saved graph files themselves.
- Read the graph first, then decide whether the requested change is:
  - a normal scene/resource change outside the graph,
  - a later APJS coexistence task,
  - or a later full porting task.

## A project can contain three graph containers

`read_visual_scripting_graph` is not just the project graph. It reads all three saved graph surfaces:

| Kind | On disk | Returned as |
| --- | --- | --- |
| Project graph | `Graph/graph.json` | `containers` |
| Component Graph asset | `Assets/**/*.compgraph` | `componentGraphs` |
| Subgraph asset | `Assets/**/*.ssubgraph` | `subgraphs` |

## Reading workflow

1. Call `read_visual_scripting_graph` with no params first.
2. Read the high-level inventory:
   - `containers`: the main project-graph containers
   - `componentGraphs`: reusable `.compgraph` assets
   - `subgraphs`: reusable `.ssubgraph` assets
3. If you only need one project-graph container, rerun with `container_id`.
4. If the summarized result hides a field you actually need, rerun with `full: true`.
5. If a node points at a scene object or component GUID, use `inspect` or `get_scene` to resolve that target in the current project.

## How to interpret the result

- `containers` describe the main visual-scripting panel graph saved under the project.
- `componentGraphs` are reusable graph assets attached through component-style authoring flows.
- `subgraphs` are reusable graph fragments. Their shared definition lives in `subgraphs`, but each use site can still carry different tuned input values.
- Per-instance subgraph tuning lives on the group-node input ports at the use site inside `containers` or `componentGraphs`, not inside the shared `subgraphs` definition itself.
- `PropertyNode.targetGuid` is the key field when a graph node is bound to a specific scene object or component.

## Guardrails

- The tool reads saved on-disk data only. Unsaved graph-panel edits are invisible until the project is saved.
- `container_id` only filters project-graph containers. It does not filter `componentGraphs` or `subgraphs`.
- `full: true` returns raw payloads and is much noisier; use it only when the summarized structure is not enough.
- If the project returns `hasGraph: false`, there is no saved visual scripting graph to analyze.
- This skill does not include graph editing, graph generation, or automatic graph-to-script conversion.
