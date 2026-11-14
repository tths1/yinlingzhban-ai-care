import base64
import json
import os
import ssl
from datetime import datetime
import urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent / 'dist'
PROFILE_PATH = Path(__file__).parent / 'elder_profile.json'
KEY = os.environ.get('DASHSCOPE_API_KEY', '').strip()
BASE_URL = os.environ.get(
    'DASHSCOPE_BASE_URL',
    'https://dashscope.aliyuncs.com/compatible-mode/v1',
).strip().rstrip('/')
# Use the host system's CA bundle so the same server works on macOS and Linux.
SSL_CONTEXT = ssl.create_default_context()


def load_profile(demo=False):
    try:
        source = Path(__file__).parent / ('demo_profile.json' if demo else 'elder_profile.json')
        return json.loads(source.read_text(encoding='utf-8'))
    except Exception:
        return {}


def select_relevant_records(message, profile):
    """Select records by topic so a newly added medication cannot hide activity data."""
    text = message.lower()
    records = profile.get('health_records', [])
    health_words = ('血压', '心率', '血糖', '睡眠', '健康', '状态', '头晕', '胸', '不适')
    activity_words = ('散步', '运动', '活动', '走')
    if any(word in text for word in activity_words):
        selected = [
            item for item in records
            if item.get('type') in ('活动', '血压', '血糖', '心率')
            or any(word in (item.get('name', '') + item.get('value', '')) for word in activity_words + health_words)
        ]
        return selected[-3:] or records[-3:]
    if any(word in text for word in health_words):
        return records[-3:]
    return []


def build_context(message, profile):
    """Send only the profile fields relevant to the user's question."""
    text = message.lower()
    context = {'profile': profile.get('profile', {})}
    if any(word in text for word in ('药', '吃', '服', '用药', '提醒')):
        context['medications'] = profile.get('medications', [])
    if '提醒' in text:
        context['care_actions'] = profile.get('care_actions', [])[-5:]
    records = select_relevant_records(message, profile)
    if records:
        context['health_records'] = records
        context['daily_status'] = profile.get('daily_status', {})
    return json.dumps(context, ensure_ascii=False)


def build_evidence(message, profile):
    """Return short, human-readable evidence chips for the UI."""
    text = message.lower()
    evidence = []
    if any(word in text for word in ('药', '吃', '服', '用药', '提醒')):
        for item in profile.get('medications', [])[-3:]:
            name = item.get('name') or '未命名药品'
            dose = item.get('dose') or '规格待确认'
            status = item.get('status') or '状态待确认'
            evidence.append(f'用药档案：{name} · {dose} · {status}')
    if '提醒' in text:
        for item in profile.get('care_actions', [])[-3:]:
            evidence.append(f"照护任务：{item.get('label', '未命名')} · {item.get('status', '待处理')}")
    for item in select_relevant_records(message, profile):
        evidence.append(
            f"{item.get('type', '健康记录')}：{item.get('name', '未命名')} · {item.get('value', '待补充')}"
        )
    return evidence[:4]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/profile':
            query = parse_qs(parsed.query)
            demo = query.get('demo', ['0'])[0] == '1'
            output = json.dumps(load_profile(demo), ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(output)))
            self.end_headers()
            self.wfile.write(output)
            return
        super().do_GET()

    def do_POST(self):
        if self.path not in ('/api/chat', '/api/vision', '/api/record', '/api/action', '/api/task'):
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(length) or '{}')
        if self.path == '/api/vision':
            self.handle_vision(body)
            return
        if self.path == '/api/record':
            self.handle_record(body)
            return
        if self.path == '/api/action':
            self.handle_action(body)
            return
        if self.path == '/api/task':
            self.handle_task(body)
            return
        message = str(body.get('message', '')).strip()
        profile = load_profile(bool(body.get('demo')))
        reply = self.fallback(message, profile)
        evidence = build_evidence(message, profile)
        live = False
        if KEY and message:
            try:
                context = build_context(message, profile)
                payload = {
                    'model': 'qwen-plus',
                    'messages': [
                        {
                            'role': 'system',
                            'content': (
                                '你是银龄智伴养老陪护助手。根据提供的老人档案和日常记录，'
                                '给出温和、具体、易懂的生活建议。只使用与问题相关的上下文。'
                                '不要诊断、改药或替代医生。若出现胸痛、呼吸困难、意识异常、'
                                '严重头晕等危险信号，优先建议立即联系家属和急救服务。'
                                '涉及用药时只复述档案中的计划，并提醒以医生处方和药盒为准。'
                                '档案没有记录的服用时间、次数或用法不得自行补充，只能明确说待确认。'
                                '没有记录不等于没有症状，不得把未记录内容当成事实。'
                            )
                        },
                        {
                            'role': 'user',
                            'content': f'老人问题：{message}\n相关档案上下文：{context}'
                        }
                    ]
                }
                request = urllib.request.Request(
                    f'{BASE_URL}/chat/completions',
                    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(request, timeout=30, context=SSL_CONTEXT) as response:
                    result = json.loads(response.read().decode('utf-8'))
                reply = result['choices'][0]['message']['content'].replace('\n', '<br>')
                live = True
            except Exception as error:
                print('Qwen request failed:', error)
        output = json.dumps({'reply': reply, 'live': live, 'evidence': evidence}, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    def handle_record(self, body):
        demo = bool(body.get('demo'))
        profile = load_profile(demo)
        target_path = Path(__file__).parent / ('demo_profile.json' if demo else 'elder_profile.json')
        record = {
            'date': str(body.get('date', '')),
            'time': str(body.get('time', '')),
            'type': str(body.get('type', '')),
            'name': str(body.get('name', '')),
            'value': str(body.get('value', '')),
            'source': str(body.get('source', '手动录入')),
            'reminder': str(body.get('reminder', '')).strip()
        }
        if not record['name'] or not record['value']:
            self.send_error(400, 'name and value are required')
            return
        profile.setdefault('health_records', []).append(record)
        if record['type'] == '用药':
            profile.setdefault('medications', []).append({
                'name': record['name'], 'dose': record['value'],
                'time': record['time'], 'status': '待确认'
            })
        if record['reminder']:
            profile.setdefault('care_actions', []).append({
                'type': 'reminder',
                'label': f"{record['name']} · {record['reminder']}",
                'status': '待处理',
                'created_at': datetime.now().isoformat(timespec='minutes')
            })
        temp_path = target_path.with_suffix('.tmp')
        temp_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
        temp_path.replace(target_path)
        output = json.dumps({
            'ok': True,
            'count': len(profile.get('health_records', [])),
            'record': record
        }, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    def handle_action(self, body):
        demo = bool(body.get('demo'))
        profile = load_profile(demo)
        target_path = Path(__file__).parent / ('demo_profile.json' if demo else 'elder_profile.json')
        label = str(body.get('label', '')).strip()
        action_type = str(body.get('type', 'follow_up')).strip()
        if not label:
            self.send_error(400, 'label is required')
            return
        action = {
            'type': action_type,
            'label': label,
            'status': '已创建',
            'created_at': datetime.now().isoformat(timespec='minutes')
        }
        profile.setdefault('care_actions', []).append(action)
        temp_path = target_path.with_suffix('.tmp')
        temp_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
        temp_path.replace(target_path)
        output = json.dumps({'ok': True, 'action': action}, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    def handle_task(self, body):
        """Soft-delete a built-in care task and remember it across reloads."""
        task_id = str(body.get('id', '')).strip()
        if not task_id:
            self.send_error(400, 'id is required')
            return
        demo = bool(body.get('demo'))
        profile = load_profile(demo)
        target_path = Path(__file__).parent / ('demo_profile.json' if demo else 'elder_profile.json')
        deleted = profile.setdefault('deleted_tasks', [])
        if task_id not in deleted:
            deleted.append(task_id)
        temp_path = target_path.with_suffix('.tmp')
        temp_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
        temp_path.replace(target_path)
        output = json.dumps({'ok': True, 'id': task_id}, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    def handle_vision(self, body):
        image = str(body.get('image', ''))
        result = '未配置千问视觉模型，演示识别：照片中的健康数据需要确认后保存。'
        fields = {'name': '', 'dose': '', 'time': '', 'date': '', 'value': ''}
        live = False
        if KEY and image.startswith('data:image/'):
            try:
                mime, encoded = image.split(';base64,', 1)
                payload = {
                    'model': 'qwen3-vl-plus',
                    'messages': [{
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': '请识别这张药盒或血压计照片中的信息。只提取可见的药品名称、规格、服用时间、血压、心率和日期，无法确认的字段写“无法确认”。用简洁中文分行返回，不做医疗诊断。'},
                            {'type': 'image_url', 'image_url': {'url': image}}
                        ]
                    }]
                }
                request = urllib.request.Request(
                    f'{BASE_URL}/chat/completions',
                    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(request, timeout=45, context=SSL_CONTEXT) as response:
                    data = json.loads(response.read().decode('utf-8'))
                raw = data['choices'][0]['message']['content']
                result = raw.replace('\n', '<br>')
                for line in raw.splitlines():
                    line = line.strip().replace('：', ':')
                    if line.startswith('药品名称:'): fields['name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('规格:'): fields['dose'] = line.split(':', 1)[1].strip()
                    elif line.startswith('服用时间:'): fields['time'] = line.split(':', 1)[1].strip()
                    elif line.startswith('日期:'): fields['date'] = line.split(':', 1)[1].strip()
                fields['value'] = fields['dose']
                live = True
            except Exception as error:
                print('Qwen vision request failed:', error)
        output = json.dumps({'result': result, 'fields': fields, 'live': live}, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    @staticmethod
    def fallback(message, profile):
        if any(word in message for word in ('药', '吃', '用药')):
            medications = profile.get('medications', [])
            if not medications:
                return '当前档案还没有用药记录。可以先在“健康档案”中录入药品，或上传药盒照片并确认保存。'
            item = medications[0]
            plan = item.get('dose') or '规格待确认'
            when = item.get('time') or '服用时间待确认'
            return f"档案中记录了 {item.get('name', '未命名药品')}，{plan}，{when}。请以医生处方和药盒说明为准。"
        if any(word in message for word in ('散步', '活动', '运动')):
            steps = profile.get('daily_status', {}).get('steps')
            if steps is None:
                return '当前档案还没有今天的活动记录。若身体没有明显不适，可以先录入一次散步或活动，再让我结合记录给出建议。'
            return f'今天记录了 {steps} 步。若没有头晕、胸闷等不适，可以晚饭后慢走 10 到 15 分钟，并带好手机。'
        if any(word in message for word in ('血压', '心率')):
            records = profile.get('health_records', [])
            item = next((x for x in reversed(records) if x.get('type') in ('血压', '心率')), None)
            if not item:
                return '当前档案还没有血压或心率记录。可以先录入一次测量结果，再让我帮你一起观察变化。'
            return f"最近一次记录为{item.get('value', '待补充')}。建议继续按计划记录；如有明显不适，请联系家属或医护人员。"
        return '我已经结合你的档案记下了。可以问我用药、血压、睡眠或今天适合做什么活动。'


if __name__ == '__main__':
    print('银龄智伴 running at http://127.0.0.1:4173; Qwen live:', bool(KEY))
    ThreadingHTTPServer(('127.0.0.1', 4173), Handler).serve_forever()
