# 等效直连通道（实践中实际使用的路径）

`SKILL.md` 的规范路径是全局注册的 `xiangsu-mcp-manager` MCP server，工具列表自动暴露
`edit_by_dsl` / `import_resource` / `set_preview_video` / `interact_by_dsl` 等。

但在三次换壳任务的实操会话里，宿主工具列表**未包含这些 DSL 工具**，实际走的是**直连
`xiangsu-mcp-manager` 背后的 HTTP 端点**的同效通道。两条通道指向同一个服务，效果一致：
`http://127.0.0.1:17320/mcp`（JSON-RPC over HTTP + SSE）。

> 优先用 `SKILL.md` 的规范 MCP 通道；仅当该通道不可用、又需要直接驱动 DSL 工具时，用本文件方法。

## 直连脚本

把下面内容存为 `xs_rpc.py`（历史上位于 `C:/Users/18168/AppData/Local/Temp/xs_rpc.py`）：

```python
"""像塑 MCP HTTP JSON-RPC 助手。用法: python xs_rpc.py <tool_name> <json_args_file>"""
import json, sys, urllib.request

URL = 'http://127.0.0.1:17320/mcp'

def rpc(payload, sid=None):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
    if sid: headers['Mcp-Session-Id'] = sid
    req = urllib.request.Request(URL, json.dumps(payload).encode(), headers)
    resp = urllib.request.urlopen(req, timeout=120)
    sid_out = resp.headers.get('Mcp-Session-Id')
    raw = resp.read().decode('utf-8')
    data_lines = [l[5:].strip() for l in raw.splitlines() if l.startswith('data:')]
    if data_lines: raw = ''.join(data_lines)
    obj = json.loads(raw) if raw.strip() else None
    return sid_out, obj

class Client:
    def __enter__(self):
        sid, _ = rpc({'jsonrpc':'2.0','id':0,'method':'initialize','params':{
            'protocolVersion':'2025-03-26','capabilities':{},
            'clientInfo':{'name':'workbuddy-agent','version':'1.0.0'}}})
        rpc({'jsonrpc':'2.0','method':'notifications/initialized'}, sid)
        self.sid = sid; self._id = 10; return self
    def __exit__(self,*a): return False
    def call(self, name, args):
        self._id += 1
        _, r = rpc({'jsonrpc':'2.0','id':self._id,'method':'tools/call',
                    'params':{'name':name,'arguments':args}}, self.sid)
        return r

def text_of(result):
    try: return result['result']['content'][0]['text']
    except Exception: return json.dumps(result, ensure_ascii=False)
```

调用示例（参数写进 JSON 文件，避免 shell 转义）：

```bash
# 读取工程上下文
echo '{"instance_id":1}' > /tmp/args.json
python xs_rpc.py get_project_context /tmp/args.json

# 设置预览视频
echo '{"instance_id":1,"video":"<视频资源 GUID 或路径>"}' > /tmp/args.json
python xs_rpc.py set_preview_video /tmp/args.json

# 编辑：导入资源刷新
echo '{"command":"import_resource","path":"Assets/香蕉/纹理/香蕉_1_color.png"}' > /tmp/args.json
python xs_rpc.py edit_by_dsl /tmp/args.json

# 编辑：改组件属性
echo '{"command":"set_component","component_id":"c26","property":"texture","value":"eye_strawberry.png"}' > /tmp/args.json
python xs_rpc.py edit_by_dsl /tmp/args.json

# 预览截图
echo '{"instance_id":1,"action":"screenshot","path":"/tmp/shot.png"}' > /tmp/args.json
python xs_rpc.py interact_by_dsl /tmp/args.json
```

> 注意：`edit_by_dsl` 的 `command` 取值与参数结构以宿主当前暴露的 schema 为准，
> 上面是三次任务中验证可用的形态；若字段名有差异，先 `get_project_context` 读手册再调。
